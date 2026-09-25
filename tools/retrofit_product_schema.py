"""Retrofit של סכמת ה-Product בפוסטים שכבר פורסמו.

רקע: GSC דיווח על 4 בעיות "Merchant listings" — שתיים קריטיות
(image חסר, price חסר בתוך offers) ושתיים לא-קריטיות
(shippingDetails, hasMerchantReturnPolicy).

הפתרון בגנרטור (backend/blog_utils.py בריפו של ה-SaaS):
  * image  — נוסף ל-Product (הוא כבר היה קיים ב-Article, זה פשוט באג).
  * offers — הוסר לגמרי. המחירים בפוסטים הם snapshot חד-פעמי מיום
    הפרסום ואין שום pipeline שמרענן אותם, אז Offer עם price היה הופך
    את הדפים ל-merchant listings עם מחיר מיושן לצמיתות. בלי offers
    הדף נשאר Product snippet תקין ושתי השגיאות הקריטיות נעלמות.

הסקריפט הזה מיישר את 258 הפוסטים הקיימים לאותו מצב. אידמפוטנטי —
קובץ שכבר תוקן מדולג.

הרצה:
    py -3 tools/retrofit_product_schema.py --dry-run
    py -3 tools/retrofit_product_schema.py
"""

import argparse
import json
import re
import sys
from pathlib import Path

BLOG_DIR = Path(__file__).resolve().parent.parent / "blog"

# הסכמה מוזרקת כבלוק ld+json יחיד בכל קובץ, ב-indent=2 / ensure_ascii=False.
SCHEMA_RE = re.compile(
    r'(<script type="application/ld\+json">\n)(.*?)(\n  </script>)',
    re.DOTALL,
)


def retrofit(raw: str) -> tuple[str, list[str]]:
    """מחזיר (html מעודכן, רשימת שינויים). רשימה ריקה = אין מה לשנות."""
    match = SCHEMA_RE.search(raw)
    if not match:
        return raw, []

    nodes = json.loads(match.group(2))
    if not isinstance(nodes, list):
        return raw, []

    article = next((n for n in nodes if n.get("@type") == "Article"), None)
    product = next((n for n in nodes if n.get("@type") == "Product"), None)
    if product is None:
        return raw, []

    changes = []

    if "offers" in product:
        del product["offers"]
        changes.append("offers removed")

    if not product.get("image"):
        image = (article or {}).get("image")
        if image:
            # image נכנס אחרי sku, כמו בגנרטור, כדי ששני המקורות ייראו זהים.
            rebuilt = {}
            for key, value in product.items():
                rebuilt[key] = value
                if key == "sku":
                    rebuilt["image"] = image
            if "image" not in rebuilt:
                rebuilt["image"] = image
            product.clear()
            product.update(rebuilt)
            changes.append("image added")
        else:
            changes.append("!! no image on Article — skipped")
            return raw, changes

    if not changes:
        return raw, []

    # השורה הראשונה של הבלוק מוזחת ע"י התבנית בגנרטור ("  {schema}").
    # בלי לשחזר את ההזחה הזאת כל קובץ מקבל שורת diff מיותרת.
    lead = re.match(r"[ \t]*", match.group(2)).group(0)
    serialized = lead + json.dumps(nodes, ensure_ascii=False, indent=2)
    updated = raw[: match.start(2)] + serialized + raw[match.end(2) :]
    return updated, changes


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    touched = 0
    skipped = 0
    problems = []

    for path in sorted(BLOG_DIR.glob("*.html")):
        raw = path.read_text(encoding="utf-8")
        updated, changes = retrofit(raw)

        if any(c.startswith("!!") for c in changes):
            problems.append(f"{path.name}: {', '.join(changes)}")
            continue
        if not changes:
            skipped += 1
            continue

        touched += 1
        print(f"{'[dry] ' if args.dry_run else ''}{path.name}: {', '.join(changes)}")
        if not args.dry_run:
            path.write_text(updated, encoding="utf-8")

    print(f"\nעודכנו: {touched} | ללא שינוי: {skipped} | בעיות: {len(problems)}")
    for problem in problems:
        print(f"  {problem}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
