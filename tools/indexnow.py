#!/usr/bin/env python3
"""Submit URLs to IndexNow (Bing, Yandex, and other participating engines).

IndexNow tells search engines to (re)crawl a URL within minutes instead of
waiting days for the next crawl. Ownership is proven by the key file hosted
at the site root: https://www.amzfreeil.com/<KEY>.txt

Usage:
    python tools/indexnow.py https://www.amzfreeil.com/blog/new-post.html [more-urls...]
    python tools/indexnow.py --sitemap        # submit every URL in sitemap.xml

Run this right after publishing (removing noindex + pushing) a page.
"""
import sys
import re
import json
from pathlib import Path
import requests

PROJECT_DIR = Path(__file__).resolve().parent.parent
HOST = "www.amzfreeil.com"
KEY = "f8c1d493ab8b4cf9cbd3de7089865276"
KEY_LOCATION = f"https://{HOST}/{KEY}.txt"
ENDPOINT = "https://api.indexnow.org/indexnow"


def sitemap_urls():
    sitemap = (PROJECT_DIR / "sitemap.xml").read_text(encoding="utf-8")
    return re.findall(r"<loc>\s*(.*?)\s*</loc>", sitemap)


def submit(urls):
    urls = [u for u in urls if u.startswith(f"https://{HOST}")]
    if not urls:
        print("No valid URLs to submit (must be https://%s/...)" % HOST)
        return 1
    payload = {
        "host": HOST,
        "key": KEY,
        "keyLocation": KEY_LOCATION,
        "urlList": urls,
    }
    resp = requests.post(
        ENDPOINT,
        data=json.dumps(payload),
        headers={"Content-Type": "application/json; charset=utf-8"},
        timeout=30,
    )
    print(f"Submitted {len(urls)} URL(s) -> HTTP {resp.status_code}")
    # 200 = accepted, 202 = accepted (validation pending). Both are success.
    if resp.status_code not in (200, 202):
        print(resp.text[:500])
        return 1
    for u in urls:
        print("  -", u)
    return 0


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 1
    if args[0] == "--sitemap":
        return submit(sitemap_urls())
    return submit(args)


if __name__ == "__main__":
    sys.exit(main())
