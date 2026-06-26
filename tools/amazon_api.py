"""
Amazon Creators API — product data fetcher
Usage: python amazon_api.py <ASIN>
"""

import sys
import json
import os
import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

CLIENT_ID     = os.environ["AMAZON_CLIENT_ID"]
CLIENT_SECRET = os.environ["AMAZON_CLIENT_SECRET"]
PARTNER_TAG   = os.getenv("AMAZON_PARTNER_TAG", "amzfreeil-20")
MARKETPLACE   = os.getenv("AMAZON_MARKETPLACE", "www.amazon.com")

TOKEN_URL  = "https://api.amazon.com/auth/o2/token"
PAAPI_URL  = "https://creatorsapi.amazon/catalog/v1/getItems"


def get_token():
    resp = requests.post(TOKEN_URL, json={
        "grant_type":    "client_credentials",
        "client_id":     CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope":         "creatorsapi::default",
    }, headers={"Content-Type": "application/json"})
    resp.raise_for_status()
    return resp.json()["access_token"]


def get_product(asin: str) -> dict:
    token = get_token()
    payload = {
        "itemIds":     [asin],
        "itemIdType":  "ASIN",
        "partnerTag":  PARTNER_TAG,
        "partnerType": "Associates",
        "marketplace": MARKETPLACE,
        "resources": [
            "images.primary.small",
            "itemInfo.title",
            "itemInfo.features",
            "itemInfo.manufactureInfo",
        ],
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type":  "application/json",
        "x-marketplace": MARKETPLACE,
    }
    resp = requests.post(PAAPI_URL, json=payload, headers=headers)
    resp.raise_for_status()
    data = resp.json()

    item = data["itemsResult"]["items"][0]

    title     = item.get("itemInfo", {}).get("title", {}).get("displayValue", "")
    features  = item.get("itemInfo", {}).get("features", {}).get("displayValues", [])
    image_url = item.get("images", {}).get("primary", {}).get("small", {}).get("url", "")
    aff_url   = f"https://www.amazon.com/dp/{asin}?tag={PARTNER_TAG}"

    mfr   = item.get("itemInfo", {}).get("manufactureInfo", {}) or {}
    model = mfr.get("model", {}).get("displayValue", "") if mfr else ""

    return {
        "asin":     asin,
        "title":    title,
        "features": features,
        "image":    image_url,
        "model":    model,
        "url":      aff_url,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python amazon_api.py <ASIN>")
        sys.exit(1)

    asin = sys.argv[1]
    try:
        product = get_product(asin)
        print(json.dumps(product, ensure_ascii=False, indent=2))
    except requests.HTTPError as e:
        print(f"HTTP Error: {e.response.status_code} — {e.response.text}")
        sys.exit(1)
