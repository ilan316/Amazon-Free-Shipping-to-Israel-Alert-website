"""
Interactive blog post pipeline:
  Step 1 — Fetch & filter candidate products
  Step 2 — Pick product, enter prices, confirm
  Step 3 — Generate draft (noindex, no push)

After review:
  python tools/publish_post.py <slug>   ← Step 4

Usage: python tools/pipeline.py
"""
import sys
import json
import re
import os
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

TOOLS_DIR = Path(__file__).parent
PUBLISHED_ASINS_FILE = TOOLS_DIR / "published_asins.json"
API_URL = "https://app.amzfreeil.com/api/public/free-products"

CATEGORY_KEYWORDS = [
    "Electronics", "Computer", "Camera", "Audio", "Phone",
    "Tablet", "Gaming", "Storage", "Wireless", "Smart", "TV",
]
MIN_PRICE_ILS = 200


def load_published_asins():
    if PUBLISHED_ASINS_FILE.exists():
        return set(json.loads(PUBLISHED_ASINS_FILE.read_text(encoding="utf-8")))
    return set()


def parse_price(raw):
    try:
        return float(re.sub(r"[^\d.]", "", str(raw or "")))
    except (ValueError, TypeError):
        return 0


def step1_scan():
    print("=" * 55)
    print("  שלב 1 — סריקת מוצרים")
    print("=" * 55)
    print(f"מושך מוצרים מ-{API_URL}...")
    try:
        r = requests.get(API_URL, timeout=15)
        r.raise_for_status()
        products = r.json()
    except Exception as e:
        print(f"שגיאה: {e}")
        sys.exit(1)

    published = load_published_asins()

    candidates = []
    for p in products:
        asin = p.get("asin", "")
        if not asin or asin in published:
            continue
        price = parse_price(p.get("last_price"))
        if price < MIN_PRICE_ILS:
            continue
        category = p.get("amazon_category", "") or p.get("_category", "") or ""
        if not any(kw.lower() in category.lower() for kw in CATEGORY_KEYWORDS):
            continue
        candidates.append({
            "asin": asin,
            "name": (p.get("name") or p.get("name_he") or "")[:70],
            "name_he": (p.get("name_he") or p.get("name") or "")[:70],
            "price_amazon": price,
            "category": category,
        })

    if not candidates:
        print("לא נמצאו מוצרים מתאימים.")
        sys.exit(0)

    print(f"\n{len(candidates)} מוצרים נמצאו:\n")
    for i, c in enumerate(candidates, 1):
        name = c["name_he"] or c["name"]
        print(f"  [{i}] {c['asin']}  |  ₪{c['price_amazon']:.0f} באמזון")
        print(f"       {name[:65]}")
        print()

    return candidates


def step2_pick(candidates):
    print("=" * 55)
    print("  שלב 2 — בחירת מוצר + מחירים")
    print("=" * 55)

    while True:
        raw = input("בחר מספר מוצר (או ASIN ישירות): ").strip()
        if not raw:
            continue
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(candidates):
                product = candidates[idx]
                break
            print(f"  ⚠️  מספר לא תקין (1–{len(candidates)})")
        else:
            matches = [c for c in candidates if c["asin"].upper() == raw.upper()]
            if matches:
                product = matches[0]
                break
            print("  ⚠️  ASIN לא נמצא ברשימה")

    print(f"\nנבחר: {product['asin']} — {product['name'][:60]}")
    print(f"  מחיר באמזון (כפי שמוצג לישראל, ILS): ₪{product['price_amazon']:.0f}")
    print()

    while True:
        raw = input("מחיר בארץ (₪, מ-Zap): ").strip().replace(",", "")
        try:
            israel_price = float(raw)
            break
        except ValueError:
            print("  ⚠️  הזן מספר בלבד")

    while True:
        raw = input("מחיר סופי באמזון כולל Import Fees (₪): ").strip().replace(",", "")
        try:
            amazon_price = float(raw)
            break
        except ValueError:
            print("  ⚠️  הזן מספר בלבד")

    savings = round(israel_price - amazon_price)

    print()
    print("=" * 55)
    print("  אישור לפני יצירת דראפט")
    print("=" * 55)
    print(f"  מוצר:        {product['asin']}")
    print(f"  מחיר בארץ:   ₪{israel_price:,.0f}")
    print(f"  מחיר אמזון:  ₪{amazon_price:,.2f}")
    print(f"  חיסכון:      ~₪{savings:,}")
    print()

    confirm = input("להמשיך ולצור דראפט? (y/n): ").strip().lower()
    if confirm not in ("y", "yes", "כן", "י"):
        print("בוטל.")
        sys.exit(0)

    return product["asin"], israel_price, amazon_price


def step3_generate(asin, israel_price, amazon_price):
    print()
    print("=" * 55)
    print("  שלב 3 — יצירת דראפט")
    print("=" * 55)
    import subprocess
    result = subprocess.run(
        [sys.executable, str(TOOLS_DIR / "generate_post.py"),
         asin, str(israel_price), str(amazon_price)],
        cwd=str(TOOLS_DIR.parent),
    )
    if result.returncode != 0:
        print("שגיאה ביצירת הפוסט.")
        sys.exit(1)

    print()
    print("=" * 55)
    print("  שלב 4 — כשמוכן לפרסום:")
    print("  python tools/publish_post.py <slug>")
    print("=" * 55)


def main():
    candidates = step1_scan()
    asin, israel_price, amazon_price = step2_pick(candidates)
    step3_generate(asin, israel_price, amazon_price)


if __name__ == "__main__":
    main()
