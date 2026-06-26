"""
Scan free products and show candidates for blog posts.
Usage: python tools/scan_products.py
"""
import sys
import json
import os
import re
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


def main():
    print(f"Fetching products from {API_URL}...")
    try:
        resp = requests.get(API_URL, timeout=15)
        resp.raise_for_status()
        products = resp.json()
    except Exception as e:
        print(f"Error fetching products: {e}")
        sys.exit(1)

    published = load_published_asins()

    candidates = []
    for p in products:
        asin = p.get("asin", "")
        if not asin or asin in published:
            continue

        raw_price = str(p.get("last_price", "") or "")
        try:
            price = float(re.sub(r"[^\d.]", "", raw_price))
        except (ValueError, TypeError):
            price = 0
        if price < MIN_PRICE_ILS:
            continue

        category = p.get("amazon_category", "") or p.get("_category", "") or ""
        if not any(kw.lower() in category.lower() for kw in CATEGORY_KEYWORDS):
            continue

        candidates.append({
            "asin": asin,
            "name": (p.get("name_he") or p.get("name") or "")[:80],
            "price": price,
            "category": category,
        })

    if not candidates:
        print("No candidates found (check filters or all already published).")
        return

    print(f"\n{len(candidates)} products found (electronics, ₪{MIN_PRICE_ILS}+, not yet published):\n")
    for i, c in enumerate(candidates, 1):
        print(f"  [{i}] {c['asin']} | {c['name']:<60} | ₪{c['price']:.0f}")

    print(f"\nTo generate a post:")
    print(f"  python tools/generate_post.py <ASIN> <israel_price_ils> <amazon_price_ils>")
    print(f"\nExample:")
    if candidates:
        first = candidates[0]
        print(f"  python tools/generate_post.py {first['asin']} <zap_price> <amazon_final_ils>")


if __name__ == "__main__":
    main()
