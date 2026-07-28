#!/usr/bin/env python3
"""Weekly Google Search Console monitor for www.amzfreeil.com.

Replaces the manual "export ZIPs from the GSC UI" loop. Pulls live indexing
status for every URL in sitemap.xml plus Search Analytics, diffs against the
previous run, and only makes noise when something actually changed.

Secrets live OUTSIDE this repo (the repo is public):

    C:\\Users\\ilan\\Claude\\gsc-monitor\\
        config.env      RESEND_API_KEY / ALERT_EMAIL / GSC_KEY_JSON
        state.json      previous run's coverageState per URL + IndexNow log
        reports\\gsc-YYYY-MM-DD.md

Override the location with the GSC_MONITOR_HOME environment variable.

Usage:
    python tools/gsc_monitor.py                 # full weekly run
    python tools/gsc_monitor.py --dry-run       # no IndexNow, no email, no state write
    python tools/gsc_monitor.py --no-indexnow --no-email
    python tools/gsc_monitor.py --urls list.txt # inspect only these URLs

Scheduled weekly by the Windows task "GSCMonitor" (Sunday 06:00).
Remove it with:  schtasks /delete /tn GSCMonitor /f
"""
import argparse
import json
import os
import re
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

sys.path.insert(0, str(Path(__file__).resolve().parent))
from indexnow import submit as indexnow_submit  # noqa: E402

# The Windows console defaults to cp1255 here, which mangles the Hebrew summary
# in both the terminal and the scheduled-task log.
for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

PROJECT_DIR = Path(__file__).resolve().parent.parent
SITE = "https://www.amzfreeil.com/"
SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]

HOME = Path(os.environ.get("GSC_MONITOR_HOME", r"C:\Users\ilan\Claude\gsc-monitor"))
CONFIG_FILE = HOME / "config.env"
STATE_FILE = HOME / "state.json"
REPORTS_DIR = HOME / "reports"
OBSIDIAN_INBOX = Path(r"C:\Users\ilan\2nd Brain\Claude Code\אינבוקס")

# The service-account file name embeds the GCP project id, and this repo is
# public — glob the folder instead of naming it. GSC_KEY_JSON in config.env wins.
KEY_DIR = Path(r"C:\Users\ilan\Claude\gsc-service-account")

# Google's inspection API returns these verbatim. Anything not listed here is
# treated as "not indexed" — the set only grows, so fail safe rather than crash.
INDEXED_STATES = {"Submitted and indexed", "Indexed, not submitted in sitemap"}
ERROR_STATES = {"Not found (404)", "Server error (5xx)", "Redirect error",
                "Blocked by robots.txt", "Soft 404", "Blocked due to unauthorized request (401)",
                "Blocked due to access forbidden (403)"}
UNKNOWN_STATE = "URL is unknown to Google"

INDEXNOW_MAX_PER_RUN = 20
INDEXNOW_COOLDOWN_DAYS = 14
IMPRESSION_DROP_ALERT = 0.15  # 15% week-over-week drop is worth surfacing

INSPECT_WORKERS = 5
INSPECT_RETRIES = 4
RECHECK_PAUSE = 1.0


# ── config ────────────────────────────────────────────────────────────────────

def load_config():
    """Read config.env into a dict. Missing file is fine — defaults cover it."""
    cfg = {}
    if CONFIG_FILE.exists():
        for line in CONFIG_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            cfg[k.strip()] = v.strip()
    if not cfg.get("GSC_KEY_JSON"):
        found = sorted(KEY_DIR.glob("*.json")) if KEY_DIR.is_dir() else []
        if not found:
            sys.exit(f"לא נמצא מפתח חשבון שירות ב-{KEY_DIR} ואין GSC_KEY_JSON ב-{CONFIG_FILE}")
        cfg["GSC_KEY_JSON"] = str(found[0])
    cfg.setdefault("ALERT_EMAIL", "alerts@amzfreeil.com")
    cfg.setdefault("FROM_EMAIL", "AMZ Free Ship Alert <alerts@amzfreeil.com>")
    return cfg


def sitemap_urls():
    """Every URL in the committed sitemap. This is the monitored universe —
    no dependency on a hand-downloaded CSV."""
    sitemap = (PROJECT_DIR / "sitemap.xml").read_text(encoding="utf-8")
    return re.findall(r"<loc>\s*(.*?)\s*</loc>", sitemap)


def gsc_service(cfg):
    creds = service_account.Credentials.from_service_account_file(
        cfg["GSC_KEY_JSON"], scopes=SCOPES)
    return build("searchconsole", "v1", credentials=creds, cache_discovery=False), creds


# ── URL inspection ────────────────────────────────────────────────────────────

def inspect_all(creds, urls, prev_states):
    """Inspect every URL. Returns {url: {state, lastCrawl, robots, canonical}}.

    A fresh service object per thread: googleapiclient's http object is not
    thread-safe and silently corrupts responses if shared.

    Under concurrency the API intermittently answers "URL is unknown to Google"
    for pages it knows perfectly well — two runs minutes apart disagreed on 17
    URLs during development. Every result that would trigger an action (unknown,
    an error state, or a page that just fell out of the index) is therefore
    re-inspected once, serially, and the second answer wins. Without this the
    weekly alert cries wolf and IndexNow gets fed pages that were never missing.
    """
    def one(url):
        svc = build("searchconsole", "v1", credentials=creds, cache_discovery=False)
        for attempt in range(INSPECT_RETRIES):
            try:
                res = svc.urlInspection().index().inspect(body={
                    "inspectionUrl": url,
                    "siteUrl": SITE,
                    "languageCode": "en",   # keep coverageState in stable English
                }).execute()
                r = res["inspectionResult"]["indexStatusResult"]
                return url, {
                    "state": r.get("coverageState") or "unknown",
                    "lastCrawl": (r.get("lastCrawlTime") or "")[:10],
                    "robots": r.get("robotsTxtState") or "",
                    "canonical": r.get("googleCanonical") or "",
                }
            except HttpError as e:
                if e.resp.status in (429, 500, 503) and attempt < INSPECT_RETRIES - 1:
                    time.sleep(2 ** attempt)
                    continue
                return url, {"state": f"API_ERROR {e.resp.status}", "lastCrawl": "",
                             "robots": "", "canonical": ""}
            except Exception as e:  # network hiccup — retry, then give up
                if attempt < INSPECT_RETRIES - 1:
                    time.sleep(2 ** attempt)
                    continue
                return url, {"state": f"API_ERROR {type(e).__name__}", "lastCrawl": "",
                             "robots": "", "canonical": ""}

    with ThreadPoolExecutor(INSPECT_WORKERS) as ex:
        result = dict(ex.map(one, urls))

    # Only re-verify results that both look actionable AND differ from last week.
    # A URL that has been sitting at the same non-indexed state for weeks needs no
    # second opinion; a URL that just moved does. The first run has no baseline, so
    # it re-verifies everything once and is correspondingly slow — that is the point.
    suspicious = [
        u for u, i in result.items()
        if (i["state"] in ERROR_STATES
            or (prev_states.get(u) in INDEXED_STATES and i["state"] not in INDEXED_STATES)
            or (i["state"] == UNKNOWN_STATE and prev_states.get(u) != UNKNOWN_STATE))
    ]
    if suspicious:
        print(f"אימות חוזר ל-{len(suspicious)} תוצאות חשודות…")
        for url in suspicious:
            time.sleep(RECHECK_PAUSE)
            _, second = one(url)
            if not second["state"].startswith("API_ERROR"):
                result[url] = second
    return result


# ── search analytics ──────────────────────────────────────────────────────────

def analytics(svc, dimensions, start, end, limit=500):
    rows = svc.searchanalytics().query(siteUrl=SITE, body={
        "startDate": start.isoformat(),
        "endDate": end.isoformat(),
        "dimensions": dimensions,
        "rowLimit": limit,
    }).execute().get("rows", [])
    return {tuple(r["keys"]): r for r in rows}


def perf_windows(svc):
    """Last 28 days vs the 28 days before that. GSC data lags ~3 days, so the
    window ends 3 days back — otherwise the recent half looks artificially low."""
    end = date.today() - timedelta(days=3)
    cur_start = end - timedelta(days=27)
    prev_end = cur_start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=27)
    return {
        "cur": {"start": cur_start, "end": end,
                "pages": analytics(svc, ["page"], cur_start, end),
                "queries": analytics(svc, ["query"], cur_start, end)},
        "prev": {"start": prev_start, "end": prev_end,
                 "pages": analytics(svc, ["page"], prev_start, prev_end),
                 "queries": analytics(svc, ["query"], prev_start, prev_end)},
    }


def totals(rows):
    clicks = sum(r["clicks"] for r in rows.values())
    imps = sum(r["impressions"] for r in rows.values())
    return clicks, imps


# ── diffing ───────────────────────────────────────────────────────────────────

def classify(prev_states, cur):
    """Compare this run to the last one. First run has no baseline, so every
    bucket except the 'still_*' counts comes out empty — that's correct."""
    out = {"newly_indexed": [], "dropped": [], "new_error": [],
           "still_unknown": [], "still_discovered": []}
    for url, info in cur.items():
        state = info["state"]
        was = prev_states.get(url)
        indexed_now = state in INDEXED_STATES
        indexed_before = was in INDEXED_STATES if was else None

        if state.startswith("API_ERROR"):
            continue
        if indexed_now and indexed_before is False:
            out["newly_indexed"].append((url, was, state))
        elif indexed_before and not indexed_now:
            out["dropped"].append((url, was, state))
        if state in ERROR_STATES and was != state:
            out["new_error"].append((url, was or "—", state))
        if state == UNKNOWN_STATE:
            out["still_unknown"].append(url)
        elif state == "Discovered - currently not indexed":
            out["still_discovered"].append(url)
    return out


# ── actions ───────────────────────────────────────────────────────────────────

def run_indexnow(unknown_urls, sent_log, enabled):
    """Ping IndexNow for URLs Google has never even seen. Capped and rate-limited
    per URL so this never turns into spam against the search engines."""
    if not enabled or not unknown_urls:
        return []
    now = datetime.now(timezone.utc)
    due = []
    for url in unknown_urls:
        last = sent_log.get(url)
        if last:
            age = (now - datetime.fromisoformat(last)).days
            if age < INDEXNOW_COOLDOWN_DAYS:
                continue
        due.append(url)
    due = due[:INDEXNOW_MAX_PER_RUN]
    if not due:
        return []
    if indexnow_submit(due) == 0:
        stamp = now.isoformat()
        for url in due:
            sent_log[url] = stamp
        return due
    return []


def send_alert(cfg, subject, body_md, enabled):
    if not enabled:
        return False
    key = cfg.get("RESEND_API_KEY")
    if not key:
        print("!! RESEND_API_KEY not set — skipping email alert")
        return False
    html = "<pre style='font-family:ui-monospace,monospace;font-size:13px'>" \
           + body_md.replace("&", "&amp;").replace("<", "&lt;") + "</pre>"
    resp = requests.post("https://api.resend.com/emails",
                         headers={"Authorization": f"Bearer {key}"},
                         json={"from": cfg["FROM_EMAIL"], "to": [cfg["ALERT_EMAIL"]],
                               "subject": subject, "html": html},
                         timeout=30)
    ok = resp.status_code in (200, 201)
    print(f"email -> HTTP {resp.status_code}" + ("" if ok else f" {resp.text[:200]}"))
    return ok


# ── report ────────────────────────────────────────────────────────────────────

def build_report(cur, diff, perf, counts, first_run, indexnow_sent):
    c_clicks, c_imps = totals(perf["cur"]["pages"])
    p_clicks, p_imps = totals(perf["prev"]["pages"])
    d_imps = (c_imps - p_imps) / p_imps if p_imps else 0.0
    d_clicks = (c_clicks - p_clicks) / p_clicks if p_clicks else 0.0

    L = [f"# GSC — {date.today().isoformat()}", ""]
    if first_run:
        L += ["> ריצה ראשונה — אין בסיס להשוואה. הדוח הבא יראה מעברים.", ""]

    L += ["## אינדוקס", "", f"סה\"כ {len(cur)} URLs ב-sitemap.", "",
          "| מצב | כמות |", "|---|---|"]
    for state, n in counts.most_common():
        L.append(f"| {state} | {n} |")
    L.append("")

    L += ["## ביצועים (28 יום מול 28 הקודמים)", "",
          f"- קליקים: {c_clicks} ({d_clicks:+.0%})",
          f"- חשיפות: {c_imps} ({d_imps:+.0%})",
          f"- חלון: {perf['cur']['start']} → {perf['cur']['end']}", ""]

    def section(title, rows, fmt):
        if not rows:
            return
        L.append(f"## {title} ({len(rows)})")
        L.append("")
        for r in rows[:40]:
            L.append("- " + fmt(r))
        if len(rows) > 40:
            L.append(f"- …ועוד {len(rows) - 40}")
        L.append("")

    short = lambda u: u.replace(SITE, "/")
    section("נכנסו לאינדקס", diff["newly_indexed"], lambda r: f"`{short(r[0])}` — {r[1]} → {r[2]}")
    section("⚠️ נשמטו מהאינדקס", diff["dropped"], lambda r: f"`{short(r[0])}` — {r[1]} → {r[2]}")
    section("⚠️ שגיאות חדשות", diff["new_error"], lambda r: f"`{short(r[0])}` — {r[2]}")

    # Query movers — only where the volume is meaningful enough to act on.
    movers = []
    for k, row in perf["cur"]["queries"].items():
        prev = perf["prev"]["queries"].get(k)
        if not prev or row["impressions"] < 20:
            continue
        delta = row["position"] - prev["position"]  # positive = worse
        if abs(delta) >= 3:
            movers.append((k[0], prev["position"], row["position"], row["impressions"]))
    movers.sort(key=lambda m: m[2] - m[1])
    section("תזוזות מיקום בשאילתות", movers,
            lambda m: f"{m[0]} — {m[1]:.1f} → {m[2]:.1f} ({m[3]} חשיפות)")

    if indexnow_sent:
        L += [f"## נשלחו ל-IndexNow ({len(indexnow_sent)})", ""]
        L += [f"- `{short(u)}`" for u in indexnow_sent] + [""]

    section("לא ידועים לגוגל", [(u,) for u in diff["still_unknown"]], lambda r: f"`{short(r[0])}`")
    section("התגלו ולא אונדקסו", [(u,) for u in diff["still_discovered"]], lambda r: f"`{short(r[0])}`")

    L += ["## פעולות ידניות שנותרו", "",
          "אי אפשר לבקש אינדוקס או להריץ validation דרך ה-API — רק בממשק GSC.", ""]
    return "\n".join(L), d_imps


def write_obsidian_loop(report_md, reasons):
    """Only write when there is something to act on — otherwise the inbox fills
    with weekly noise and stops being read."""
    OBSIDIAN_INBOX.mkdir(parents=True, exist_ok=True)
    path = OBSIDIAN_INBOX / f"loop-gsc-{date.today().isoformat()}.md"
    body = ("# לולאה פתוחה — ניטור GSC\n\n"
            f"נוצר אוטומטית ע\"י `tools/gsc_monitor.py` ב-{date.today().isoformat()}.\n\n"
            "**למה זה כאן:**\n" + "\n".join(f"- {r}" for r in reasons) + "\n\n---\n\n"
            + report_md + "\n")
    path.write_text(body, encoding="utf-8")
    return path


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true",
                    help="no IndexNow, no email, no state write")
    ap.add_argument("--no-indexnow", action="store_true")
    ap.add_argument("--no-email", action="store_true")
    ap.add_argument("--urls", help="file with one URL per line, instead of sitemap.xml")
    args = ap.parse_args()

    cfg = load_config()
    HOME.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    urls = ([u.strip() for u in Path(args.urls).read_text(encoding="utf-8").splitlines() if u.strip()]
            if args.urls else sitemap_urls())
    print(f"בודק {len(urls)} URLs…")

    state = json.loads(STATE_FILE.read_text(encoding="utf-8")) if STATE_FILE.exists() else {}
    prev_states = state.get("states", {})
    first_run = not prev_states

    svc, creds = gsc_service(cfg)
    cur = inspect_all(creds, urls, prev_states)
    counts = Counter(i["state"] for i in cur.values())
    diff = classify(prev_states, cur)

    perf = perf_windows(svc)

    indexnow_log = state.get("indexnow", {})
    sent = run_indexnow(diff["still_unknown"], indexnow_log,
                        enabled=not (args.dry_run or args.no_indexnow))

    report, d_imps = build_report(cur, diff, perf, counts, first_run, sent)
    report_path = REPORTS_DIR / f"gsc-{date.today().isoformat()}.md"
    report_path.write_text(report, encoding="utf-8")

    # Decide whether this run is worth a human's attention.
    reasons = []
    if diff["dropped"]:
        reasons.append(f"{len(diff['dropped'])} דפים נשמטו מהאינדקס")
    if diff["new_error"]:
        reasons.append(f"{len(diff['new_error'])} שגיאות סריקה חדשות")
    if diff["newly_indexed"]:
        reasons.append(f"{len(diff['newly_indexed'])} דפים נכנסו לאינדקס")
    if d_imps <= -IMPRESSION_DROP_ALERT:
        reasons.append(f"חשיפות ירדו {d_imps:.0%}")
    if first_run:
        reasons.append("ריצה ראשונה — קביעת בסיס")

    regression = bool(diff["dropped"] or diff["new_error"])
    if regression:
        send_alert(cfg, f"⚠️ GSC — רגרסיה באינדוקס ({date.today().isoformat()})",
                   report, enabled=not (args.dry_run or args.no_email))

    loop_path = None
    if reasons and not args.dry_run:
        loop_path = write_obsidian_loop(report, reasons)

    if not args.dry_run:
        # A failed call says nothing about the page. Persisting "API_ERROR" would
        # make next week read it as a state transition, so carry the last known
        # state forward instead and leave brand-new URLs out of the baseline.
        new_states = dict(prev_states)
        for u, i in cur.items():
            if not i["state"].startswith("API_ERROR"):
                new_states[u] = i["state"]
        if not args.urls:
            # Full sitemap run: drop URLs that no longer exist on the site.
            # A --urls subset run must not prune everything it didn't look at.
            new_states = {u: s for u, s in new_states.items() if u in cur}
        STATE_FILE.write_text(json.dumps({
            "lastRun": datetime.now(timezone.utc).isoformat(),
            "states": new_states,
            "indexnow": indexnow_log,
        }, ensure_ascii=False, indent=1), encoding="utf-8")

    print()
    for st, n in counts.most_common():
        print(f"{n:5}  {st}")
    print()
    c_clicks, c_imps = totals(perf["cur"]["pages"])
    print(f"28 יום: {c_clicks} קליקים / {c_imps} חשיפות ({d_imps:+.0%})")
    print(f"נכנסו לאינדקס: {len(diff['newly_indexed'])} | נשמטו: {len(diff['dropped'])} "
          f"| שגיאות חדשות: {len(diff['new_error'])} | IndexNow: {len(sent)}")
    print(f"דוח: {report_path}")
    if loop_path:
        print(f"אינבוקס: {loop_path}")
    if args.dry_run:
        print("(dry-run — לא נשלח IndexNow/מייל, state לא נשמר)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
