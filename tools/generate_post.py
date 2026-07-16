"""
Generate a Hebrew blog post + prices.html card from Amazon product data.
Usage: python tools/generate_post.py <ASIN> <israel_price_ils> <amazon_price_ils>
Requires ANTHROPIC_API_KEY in tools/.env
"""
import sys
import json
import os
import re
from datetime import date
from pathlib import Path
import anthropic
import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

PARTNER_TAG = os.getenv("AMAZON_PARTNER_TAG", "amzfreeil-20")

TOOLS_DIR = Path(__file__).parent
PROJECT_DIR = TOOLS_DIR.parent
PUBLISHED_ASINS_FILE = TOOLS_DIR / "published_asins.json"
BLOG_DIR = PROJECT_DIR / "blog"
PRICES_HTML = PROJECT_DIR / "prices.html"

MONTHS_HE = ["ינואר","פברואר","מרץ","אפריל","מאי","יוני",
              "יולי","אוגוסט","ספטמבר","אוקטובר","נובמבר","דצמבר"]


def load_published_asins():
    if PUBLISHED_ASINS_FILE.exists():
        return json.loads(PUBLISHED_ASINS_FILE.read_text(encoding="utf-8"))
    return []


def save_published_asins(asins):
    PUBLISHED_ASINS_FILE.write_text(
        json.dumps(asins, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def get_product_data(asin):
    sys.path.insert(0, str(TOOLS_DIR))
    from amazon_api import get_product
    return get_product(asin)


def generate_content(product, israel_price, amazon_price):
    client = anthropic.Anthropic()
    today_display = date.today().strftime("%d/%m/%Y")
    savings = round(float(israel_price) - float(amazon_price))

    features_text = "\n".join(f"- {f}" for f in product.get("features", []))

    prompt = f"""אתה כותב תוכן בעברית לאתר amzfreeil.com — אתר ישראלי שעוזר לאנשים לקנות מאמזון.

מוצר: {product['title']}
דגם: {product.get('model', '')}
ASIN: {product['asin']}
מאפיינים (מדף אמזון הרשמי):
{features_text}

מחיר בישראל: ₪{israel_price}
מחיר באמזון (כולל מע"מ ייבוא + משלוח חינם): ₪{amazon_price}
חיסכון: ~₪{savings}
תאריך: {today_display}

החזר JSON בדיוק בפורמט הבא (ללא markdown, ללא טקסט לפני/אחרי):
{{
  "slug": "שם-קובץ-קצר-באנגלית-amazon-israel",
  "title_he": "כותרת מלאה בעברית לפוסט — כדאי לקנות מאמזון לישראל? (2026)",
  "title_short": "מילת קטגוריה בעברית + מותג/דגם באנגלית — למשל 'מיני מחשב GMKtec M8', 'כונן SSD פנימי Samsung 990 PRO 2TB', 'מברשת שיניים חשמלית Philips Sonicare 6700'",
  "description_he": "תיאור SEO בעברית, עד 155 תווים",
  "eyebrow": "אייקון + קטגוריה (למשל: 💻 ביקורת מוצר)",
  "reading_time": "כ-5 דקות",
  "section1_p1": "<p>פסקה ראשונה — מה המוצר ולמה פופולרי (HTML, <bdi> לאנגלית)</p>",
  "section1_p2": "<p>פסקה שנייה — ייחודיות המוצר</p>",
  "specs_rows": [
    {{"label": "מפרט", "value": "ערך"}}
  ],
  "who_profile1_title": "🎮 כותרת פרופיל 1",
  "who_profile1_text": "<p>טקסט פרופיל 1 (HTML)</p>",
  "who_profile2_title": "🖥️ כותרת פרופיל 2",
  "who_profile2_text": "<p>טקסט פרופיל 2</p>",
  "who_profile3_title": "💼 כותרת פרופיל 3",
  "who_profile3_text": "<p>טקסט פרופיל 3</p>",
  "tip_html": "<p class=\\"blog-tip\\">💡 <strong>טיפ:</strong> טקסט טיפ שימושי</p>",
  "pros": ["יתרון 1", "יתרון 2", "יתרון 3", "יתרון 4", "יתרון 5"],
  "cons": ["מה לשים לב 1", "מה לשים לב 2", "מה לשים לב 3", "מה לשים לב 4"],
  "faqs": [
    {{"q": "שאלה?", "a": "תשובה (HTML, <bdi> לאנגלית)"}}
  ],
  "summary_p1": "<p>פסקת סיכום ראשונה (HTML)</p>",
  "summary_p2": "<p>פסקת סיכום שנייה עם אזכור המשלוח (HTML)</p>",
  "cta_h3": "רוצה לדעת ברגע שיש משלוח חינם על המוצר הזה?",
  "cta_p": "הוסף את המוצר לניטור — ואנחנו נשלח לך מייל ברגע שהמשלוח חינם. ללא עלות, ללא כרטיס אשראי.",
  "breadcrumb_label": "שם מוצר קצר — ביקורת"
}}

כללים:
- כתוב עברית טבעית ומקצועית
- עטוף מונחים אנגליים ב-<bdi></bdi>
- אל תמציא מחירים — רק המספרים שקיבלת
- אל תמציא מפרטים — רק מה שמופיע ב"מאפיינים"
- slug: קצר, אנגלית, מקפים, מסתיים ב-amazon-israel
- FAQs: בדיוק 4 שאלות
- specs_rows: חלץ מהמאפיינים (4-8 שורות)
- title_short: חובה להתחיל במילת קטגוריה בעברית (מיני מחשב / אוזניות / כונן SSD / מברשת שיניים חשמלית / כרטיס מסך וכו'), ואז המותג והדגם באנגלית. אסור כותרת באנגלית בלבד, ואסור שהעברית תבוא אחרי האנגלית. שם המותג והדגם נשארים באנגלית — לא לתרגם. בלי תגי HTML."""

    message = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    content = _sanitize_quotes(json.loads(raw))
    _validate_title_short(content)
    return content


# Guard: title_short חייב להתחיל במילת קטגוריה בעברית (א-ת), אחרת כרטיס המחיר
# ב-prices.html ייכתב באנגלית בלבד. אם המודל התעלם מההוראה — עוצרים את הפרסום
# עם שגיאה ברורה במקום להשחית את הדף בשקט.
def _validate_title_short(content):
    title = (content.get("title_short") or "").strip()
    if not title or not re.match(r"^[א-ת]", title):
        raise ValueError(
            f"title_short חייב להתחיל במילת קטגוריה בעברית, אבל התקבל: {title!r}\n"
            "הפרסום נעצר. הרץ שוב את הגנרטור (המודל לא עקב אחרי פורמט הכותרת)."
        )


# Straight double-quotes inside Hebrew abbreviations (מע"מ, מ"מ, סל"ד, ש"ח)
# break HTML attributes when inserted raw into <meta content="...">. Convert
# any quote sitting between two Hebrew letters to the correct gershayim (״).
_HEB_QUOTE = re.compile(r"(?<=[֐-׿])\"(?=[֐-׿])")


def _sanitize_quotes(obj):
    if isinstance(obj, str):
        return _HEB_QUOTE.sub("״", obj)
    if isinstance(obj, list):
        return [_sanitize_quotes(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _sanitize_quotes(v) for k, v in obj.items()}
    return obj


def build_html(product, content, israel_price, amazon_price):
    today = date.today()
    today_he = f"{today.day} ב{MONTHS_HE[today.month - 1]} {today.year}"
    today_iso = today.isoformat()
    today_display = today.strftime("%d/%m/%Y")
    savings = round(float(israel_price) - float(amazon_price))
    asin = product["asin"]
    image = product.get("image", "").replace("._SL160_.", "._SL1000_.")
    aff_url = f"https://www.amazon.com/dp/{asin}?tag={PARTNER_TAG}"
    slug = content["slug"]
    blog_url = f"https://www.amzfreeil.com/blog/{slug}.html"

    specs_rows_html = ""
    for i, row in enumerate(content.get("specs_rows", [])):
        bg = "background:rgba(0,0,0,.02);" if i % 2 == 1 else ""
        specs_rows_html += (
            f'            <tr style="{bg}border-bottom:1px solid rgba(23,32,51,.07);">\n'
            f'              <td style="padding:10px 14px;">{row["label"]}</td>\n'
            f'              <td style="padding:10px 14px;"><bdi>{row["value"]}</bdi></td>\n'
            f"            </tr>\n"
        )

    pros_html = "\n".join(f"              <li>{p}</li>" for p in content.get("pros", []))
    cons_html = "\n".join(f"              <li>{c}</li>" for c in content.get("cons", []))

    faqs_html = ""
    faq_schema = []
    for faq in content.get("faqs", []):
        faqs_html += (
            f'        <div class="blog-faq-item">\n'
            f'          <p class="blog-faq-q">{faq["q"]}</p>\n'
            f'          <p class="blog-faq-a">{faq["a"]}</p>\n'
            f"        </div>\n"
        )
        faq_schema.append({
            "@type": "Question",
            "name": faq["q"],
            "acceptedAnswer": {"@type": "Answer", "text": faq["a"]},
        })

    schema = json.dumps([
        {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": content["title_he"],
            "description": content["description_he"],
            "url": blog_url,
            "datePublished": today_iso,
            "dateModified": today_iso,
            "inLanguage": "he-IL",
            "image": image,
            "author": {"@type": "Person", "name": "אילן", "url": "https://www.amzfreeil.com/about.html"},
            "publisher": {
                "@type": "Organization",
                "name": "AMZ Free Ship Alert",
                "url": "https://www.amzfreeil.com",
                "logo": {"@type": "ImageObject", "url": "https://www.amzfreeil.com/logo-new.png"},
            },
        },
        {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": faq_schema,
        },
        {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "דף הבית", "item": "https://www.amzfreeil.com/"},
                {"@type": "ListItem", "position": 2, "name": "בלוג", "item": "https://www.amzfreeil.com/blog/"},
                {"@type": "ListItem", "position": 3, "name": content["breadcrumb_label"], "item": blog_url},
            ],
        },
    ], ensure_ascii=False, indent=2)

    return f"""<!doctype html>
<html lang="he-IL" dir="rtl">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{content['title_he']} | AMZ Free Ship Alert</title>
  <meta name="description" content="{content['description_he']}" />

  <meta property="og:title" content="{content['title_he']}" />
  <meta property="og:description" content="{content['description_he']}" />
  <meta property="og:image" content="{image}" />
  <meta property="og:image:width" content="1000" />
  <meta property="og:image:height" content="1000" />
  <meta property="og:type" content="article" />
  <meta property="og:url" content="{blog_url}" />
  <meta property="og:locale" content="he_IL" />
  <meta property="article:published_time" content="{today_iso}" />
  <meta property="article:modified_time" content="{today_iso}" />

  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="{content['title_he']}" />
  <meta name="twitter:description" content="{content['description_he']}" />
  <meta name="twitter:image" content="{image}" />

  <link rel="icon" type="image/png" href="../logo-new.png" />
  <meta name="robots" content="noindex,nofollow" />
  <link rel="canonical" href="{blog_url}" />
  <link rel="alternate" hreflang="he-IL" href="{blog_url}" />
  <link rel="alternate" hreflang="x-default" href="{blog_url}" />
  <link rel="stylesheet" href="../styles.css" media="print" onload="this.media='all'" />
  <noscript><link rel="stylesheet" href="../styles.css" /></noscript>

  <script type="application/ld+json">
  {schema}
  </script>
</head>
<body>
  <a href="#main-content" class="skip-nav">דלג לתוכן הראשי</a>
  <div class="bg-glow bg-glow-a"></div>
  <div class="bg-glow bg-glow-b"></div>

  <div id="fixed-header">
    <div class="urgency-bar">
      <span class="urgency-dot"></span>
      לא כל מוצר באמזון נשלח חינם לישראל — <strong>קבל התראה ברגע שמוצר מציע משלוח חינם</strong>
    </div>
    <div class="topbar-outer">
      <header class="topbar" id="topbar">
        <a class="brand" href="../index.html">
          <picture>
            <source srcset="../logo-new.webp" type="image/webp">
            <img src="../logo-new.png" alt="AMZ Free Ship Alert — לוגו" class="brand-logo-img" width="36" height="36" />
          </picture>
          <span>AMZ Free Ship Alert</span>
        </a>
        <nav id="main-nav">
          <a href="../index.html#features">יכולות</a>
          <a href="../index.html#how">איך זה עובד</a>
          <a href="../web-guide.html">מדריך מקוון</a>
          <a href="../index.html#faq">שאלות נפוצות</a>
          <span class="nav-break"></span>
          <a href="../free-products.html">מוצרים בחינם 🚚</a>
          <a href="../search.html">חיפוש מוצרים 🔍</a>
          <a href="../prices.html">סקירות 📝</a>
          <a href="../about.html">אודות</a>
          <a href="../blog/" class="nav-active">בלוג</a>
          <a href="../index.html#contact">צרו קשר</a>
        </nav>
        <div class="nav-cta-group">
          <a class="btn btn-primary btn-sm" href="https://app.amzfreeil.com" target="_blank" id="nav-web-btn" aria-label="כניסה למוניטור" style="padding:12px 24px;">🌐 כניסה למוניטור</a>
        </div>
        <button class="hamburger" id="hamburger-btn" aria-label="פתח תפריט" aria-expanded="false" aria-controls="main-nav">
          <svg width="22" height="22" viewBox="0 0 22 22" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect y="4" width="22" height="2" rx="1" fill="currentColor"/>
            <rect y="10" width="22" height="2" rx="1" fill="currentColor"/>
            <rect y="16" width="22" height="2" rx="1" fill="currentColor"/>
          </svg>
        </button>
      </header>
    </div>
  </div>

  <main id="main-content">

    <section class="blog-hero">
      <div class="blog-hero-inner">
        <nav class="blog-breadcrumb" aria-label="ניווט קווי">
          <a href="../index.html">דף הבית</a>
          <span aria-hidden="true">›</span>
          <a href="../blog/">בלוג</a>
          <span aria-hidden="true">›</span>
          <span>{content['breadcrumb_label']}</span>
        </nav>
        <p class="eyebrow">{content['eyebrow']}</p>
        <h1>{content['title_he']}</h1>
        <div class="blog-meta">
          <span>{today_he}</span>
          <span class="blog-meta-sep">·</span>
          <span>זמן קריאה: {content['reading_time']}</span>
          <span class="blog-meta-sep">·</span>
          <span>כתב: <a href="https://www.amzfreeil.com/about.html" style="color:inherit">אילן</a></span>
        </div>
      </div>
    </section>

    <img
      src="{image}"
      alt="{product['title']}"
      class="blog-hero-img"
      width="1000" height="1000"
      loading="eager"
      style="object-fit:contain;background:#f5f5f5;max-height:420px;"
    />

    <article class="blog-body">

      <div class="blog-takeaway">
        <p class="blog-takeaway__title">✅ בקצרה — מה חשוב לדעת</p>
        <ul>
          <li>נכון ל-{today_display}: בישראל ₪{israel_price} | באמזון (כולל מע"מ + משלוח חינם) ₪{amazon_price} — חיסכון של ~₪{savings}</li>
          <li>המשלוח החינם <strong>זמני ומשתנה</strong> — בדקו לפני רכישה</li>
        </ul>
      </div>

      <section>
        <h2>מה זה {content['title_short']} ולמה כולם מדברים עליו?</h2>
        {content['section1_p1']}
        {content['section1_p2']}
      </section>

      <section>
        <h2>מפרט טכני — כל מה שצריך לדעת</h2>
        <table style="width:100%;border-collapse:collapse;font-size:.93rem;margin:16px 0;">
          <thead>
            <tr style="background:rgba(255,153,0,.1);font-weight:700;">
              <th style="padding:10px 14px;text-align:right;border-bottom:2px solid rgba(23,32,51,.12);">מפרט</th>
              <th style="padding:10px 14px;text-align:right;border-bottom:2px solid rgba(23,32,51,.12);">ערך</th>
            </tr>
          </thead>
          <tbody>
{specs_rows_html}          </tbody>
        </table>
      </section>

      <section>
        <h2>למי זה מתאים?</h2>
        <h3>{content['who_profile1_title']}</h3>
        {content['who_profile1_text']}
        <h3>{content['who_profile2_title']}</h3>
        {content['who_profile2_text']}
        <h3>{content['who_profile3_title']}</h3>
        {content['who_profile3_text']}
        {content['tip_html']}
      </section>

      <section>
        <h2>כמה עולה {content['title_short']}?</h2>
        <table style="width:100%;border-collapse:collapse;font-size:.95rem;margin:16px 0;">
          <thead>
            <tr style="background:rgba(255,153,0,.1);font-weight:700;">
              <th style="padding:10px 14px;text-align:right;border-bottom:2px solid rgba(23,32,51,.12);">מקור</th>
              <th style="padding:10px 14px;text-align:right;border-bottom:2px solid rgba(23,32,51,.12);">מחיר</th>
            </tr>
          </thead>
          <tbody>
            <tr style="border-bottom:1px solid rgba(23,32,51,.07);">
              <td style="padding:10px 14px;">בישראל (הזול ביותר)</td>
              <td style="padding:10px 14px;font-weight:700;">₪{israel_price}</td>
            </tr>
            <tr style="background:rgba(22,125,70,.05);border-bottom:1px solid rgba(23,32,51,.07);">
              <td style="padding:10px 14px;">אמזון <small style="color:#4d5a70;">(כולל מע"מ ייבוא + משלוח חינם)</small></td>
              <td style="padding:10px 14px;font-weight:700;color:#167d46;">₪{amazon_price}</td>
            </tr>
            <tr style="border-bottom:1px solid rgba(23,32,51,.07);">
              <td style="padding:10px 14px;">חיסכון</td>
              <td style="padding:10px 14px;font-weight:700;color:#167d46;">~₪{savings}</td>
            </tr>
          </tbody>
        </table>
        <p style="font-size:.8rem;color:#4d5a70;margin:0 0 16px;">* נכון ל-{today_display}. המחירים משתנים — בדקו לפני רכישה.</p>

        <div style="background:rgba(255,153,0,.08);border:1.5px solid rgba(255,153,0,.4);border-radius:12px;padding:14px 18px;margin:16px 0;font-size:.9rem;line-height:1.7;">
          <strong>⚠️ חשוב: המחיר באמזון כולל כבר את מע"מ הייבוא</strong><br>
          אמזון מציג מחיר סופי לישראל כולל <bdi>"Import Fees Deposit"</bdi> — אין הפתעות במכס. <a href="../mekhs-umaam-amazon-israel.html" style="color:var(--brand-deep, #ff6a00);">מדריך מלא על מכס ומע"מ ←</a>
        </div>

        <div style="text-align:center;margin:24px 0;">
          <a href="{aff_url}" target="_blank" rel="noopener sponsored"
             style="display:inline-block;background:linear-gradient(135deg,#ff9900,#ff6a00);color:#172033;font-weight:800;padding:14px 32px;border-radius:14px;text-decoration:none;font-size:1.05rem;box-shadow:0 8px 24px rgba(255,153,0,.3);">
            בדוק מחיר נוכחי באמזון ←
          </a>
          <p style="font-size:.78rem;color:#4d5a70;margin:10px 0 0;">קישור שותף — לא עולה לכם יותר</p>
        </div>
      </section>

      <section>
        <h2>רוצה לדעת כשיש משלוח חינם על המוצר הזה?</h2>
        <p>המשלוח החינם של אמזון לישראל מופיע ונעלם — לפעמים ליום, לפעמים לשבוע. במקום לבדוק ידנית כל יום, תנו לנו לעשות את זה בשבילכם.</p>
        <div style="background:rgba(22,125,70,.07);border:1.5px solid rgba(22,125,70,.3);border-radius:16px;padding:24px 26px;margin:20px 0;">
          <p style="margin:0 0 6px;font-weight:700;font-size:1.05rem;">📬 קבל התראה ברגע שמשלוח חינם זמין</p>
          <p style="margin:0 0 18px;font-size:.9rem;color:#4d5a70;">תוסיף את המוצר לניטור — נשלח לך מייל ברגע שהמשלוח מתעדכן לחינם.</p>
          <a href="https://app.amzfreeil.com" target="_blank" rel="noopener"
             style="display:inline-block;background:linear-gradient(135deg,#ff9900,#ff6a00);color:#172033;font-weight:800;padding:13px 28px;border-radius:12px;text-decoration:none;font-size:1rem;">
            הירשם לקבל התראה ←
          </a>
        </div>
      </section>

      <section>
        <h2>איך לקנות — מדריך קצר</h2>
        <h3>שלב 1: ודאו שהמוצר מתאים לכם</h3>
        <p>קראו את המפרט למעלה וודאו שהמוצר תואם לציוד שלכם.</p>
        <h3>שלב 2: ודאו שיש חשבון אמזון</h3>
        <p>אם אין — פתחו אחד. אין עלות. כתובת המשלוח תהיה הכתובת שלכם בישראל.</p>
        <h3>שלב 3: בדקו שהמוצר מציג <bdi>"FREE Shipping to Israel"</bdi></h3>
        <p>בדף המוצר, תחת סעיף <bdi>"Delivery"</bdi>, חפשו את הכיתוב הזה. אם הוא מופיע — אתם מוכנים לרכישה.</p>
        <h3>שלב 4: קנו</h3>
        <p>לחצו על הכפתור למטה. תוודאו שהמוכר הוא <bdi>Amazon.com</bdi> או <bdi>Sold by Amazon</bdi> — לא מוכר צד שלישי.</p>
        <div style="text-align:center;margin:28px 0;">
          <a href="{aff_url}" target="_blank" rel="noopener sponsored"
             style="display:inline-block;background:linear-gradient(135deg,#ff9900,#ff6a00);color:#172033;font-weight:800;padding:14px 32px;border-radius:14px;text-decoration:none;font-size:1.05rem;box-shadow:0 8px 24px rgba(255,153,0,.35);">
            צפה במוצר באמזון ←
          </a>
          <p style="font-size:.78rem;color:#4d5a70;margin:10px 0 0;">קישור שותף — לא עולה לכם יותר</p>
        </div>
      </section>

      <section>
        <h2>יתרונות וחסרונות</h2>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:16px 0;">
          <div style="background:rgba(22,125,70,.06);border:1px solid rgba(22,125,70,.2);border-radius:14px;padding:18px;">
            <p style="font-weight:700;margin:0 0 12px;color:#167d46;">✅ יתרונות</p>
            <ul style="margin:0;padding-right:18px;line-height:2;font-size:.9rem;">
{pros_html}
            </ul>
          </div>
          <div style="background:rgba(220,50,50,.04);border:1px solid rgba(220,50,50,.15);border-radius:14px;padding:18px;">
            <p style="font-weight:700;margin:0 0 12px;color:#b91c1c;">⚠️ מה לשים לב</p>
            <ul style="margin:0;padding-right:18px;line-height:2;font-size:.9rem;">
{cons_html}
            </ul>
          </div>
        </div>
      </section>

      <section class="blog-faq">
        <h2>שאלות נפוצות</h2>
{faqs_html}      </section>

      <section>
        <h2>סיכום</h2>
        {content['summary_p1']}
        {content['summary_p2']}
      </section>

      <div class="blog-cta-box">
        <p class="blog-cta-box__icon">🔔</p>
        <h3>{content['cta_h3']}</h3>
        <p>{content['cta_p']}</p>
        <a class="btn btn-primary btn-xl" href="https://app.amzfreeil.com" target="_blank" rel="noopener">
          <span>הירשם חינם ←</span>
          <small>עובד מיד · ללא כרטיס אשראי</small>
        </a>
      </div>

      <div style="background:rgba(23,32,51,.04);border:1px solid rgba(23,32,51,.1);border-radius:12px;padding:14px 18px;margin:24px 0;font-size:.82rem;color:#4d5a70;line-height:1.7;">
        <strong>גילוי נאות:</strong> הקישורים לאמזון בעמוד זה הם קישורי שותף של תוכנית <bdi>Amazon Associates</bdi>. אם תרכשו מוצר דרכם, אנו עשויים לקבל עמלה קטנה — ללא כל עלות נוספת מצידכם. זהו המודל שמאפשר לנו לספק את השירות ללא תשלום.
      </div>

      <div class="author-bio">
        <div class="author-bio__avatar">א</div>
        <div class="author-bio__info">
          <p class="author-bio__name">אילן</p>
          <p class="author-bio__desc">מפתח Python עצמאי עם 5+ שנות ניסיון. יצר את <strong>AMZ Free Ship Alert</strong> כדי לעזור לישראלים לחסוך בקניות מאמזון — בלי לפספס הזדמנויות משלוח חינם. <a href="../about.html">קרא עוד אודותי →</a></p>
        </div>
      </div>
    </article>

    <section class="section" style="max-width:860px;margin:0 auto 64px;">
      <h2 style="font-family:Rubik,sans-serif;font-size:1.25rem;margin-bottom:24px;">מאמרים קשורים</h2>
      <div class="blog-index-grid" style="grid-template-columns:repeat(auto-fill,minmax(260px,1fr));">
        <a class="blog-index-card" href="hamutzarim-hakhi-kedaim-laknot-bamazon-israel.html">
          <div class="blog-card-body" style="padding:20px;">
            <div class="blog-index-card__cat">🛒 מדריך קנייה</div>
            <h3 class="blog-index-card__title">המוצרים הכי כדאיים לקנות באמזון לישראל</h3>
            <div class="blog-index-card__footer"><span class="blog-index-card__read">קריאה: ~5 דקות ←</span></div>
          </div>
        </a>
        <a class="blog-index-card" href="mishloach-hinam-amazon-israel.html">
          <div class="blog-card-body" style="padding:20px;">
            <div class="blog-index-card__cat">📦 מדריך</div>
            <h3 class="blog-index-card__title">משלוח חינם מאמזון לישראל: המדריך המלא</h3>
            <div class="blog-index-card__footer"><span class="blog-index-card__read">קריאה: ~4 דקות ←</span></div>
          </div>
        </a>
        <a class="blog-index-card" href="mekhs-umaam-amazon-israel.html">
          <div class="blog-card-body" style="padding:20px;">
            <div class="blog-index-card__cat">💰 מסים</div>
            <h3 class="blog-index-card__title">מכס ומע"מ על קניות מאמזון לישראל</h3>
            <div class="blog-index-card__footer"><span class="blog-index-card__read">קריאה: ~5 דקות ←</span></div>
          </div>
        </a>
      </div>
    </section>
  </main>

  <footer>
    <div class="footer-topbar">
      <a class="brand" href="../index.html">
        <picture>
          <source srcset="../logo-new.webp" type="image/webp">
          <img src="../logo-new.png" alt="לוגו AMZ Free Ship Alert" class="brand-logo-img" width="36" height="36" loading="lazy" />
        </picture>
        <span>AMZ Free Ship Alert</span>
      </a>
      <div class="footer-links-wrap">
        <div class="footer-links">
          <a href="../privacy.html">מדיניות פרטיות</a>
          <a href="../terms.html">תנאי שימוש</a>
          <a href="../about.html">אודות</a>
          <a href="../web-guide.html">מדריך מקוון</a>
          <a href="../index.html#disclosure">גילוי נאות</a>
        </div>
        <div class="footer-social">
          <a href="https://www.facebook.com/AmzFreeIL/" target="_blank" rel="noopener noreferrer">פייסבוק</a>
          <a href="https://www.instagram.com/amzfreeil/" target="_blank" rel="noopener noreferrer">אינסטגרם</a>
          <a href="https://t.me/amzfreeil" target="_blank" rel="noopener noreferrer">טלגרם</a>
        </div>
      </div>
    </div>
    <p class="footer-copy">© 2026 AMZ Free Ship Alert · אין לאתר זה כל זיקה, שותפות או שיוך ל-Amazon Inc</p>
  </footer>

  <script src="../script.js"></script>
</body>
</html>"""


def add_price_card(asin, product, israel_price, amazon_price, slug, content):
    today_display = date.today().strftime("%d/%m/%Y")
    savings = round(float(israel_price) - float(amazon_price))
    image_thumb = product.get("image", "")
    aff_url = f"https://www.amazon.com/dp/{asin}?tag={PARTNER_TAG}"
    # Hebrew-category-first title (עברית+אנגלית), NOT the raw English Amazon title.
    title = content["title_short"]

    card_html = f"""
      <!-- {title[:60]} -->
      <div class="price-card">
        <div class="price-card-img">
          <a href="blog/{slug}.html">
            <img src="{image_thumb}"
                 alt="{title}" width="100" height="100" loading="lazy" />
          </a>
        </div>
        <div class="price-card-body">
          <h2 class="price-card-title">{title}</h2>
          <table class="price-table">
            <thead>
              <tr><th>מקור</th><th>מחיר</th></tr>
            </thead>
            <tbody>
              <tr>
                <td>בישראל (הזול ביותר)</td>
                <td>₪{israel_price}</td>
              </tr>
              <tr class="amazon-row">
                <td>אמזון <small style="font-weight:400;color:#4d5a70;">(כולל מע"מ + משלוח חינם)</small></td>
                <td>₪{amazon_price}</td>
              </tr>
              <tr class="saving">
                <td>חיסכון</td>
                <td>~₪{savings}</td>
              </tr>
            </tbody>
          </table>
          <p class="price-date">* נכון ל-{today_display}</p>
          <div class="price-card-footer">
            <a href="{aff_url}"
               target="_blank" rel="noopener sponsored" class="btn-amazon">
              קנה באמזון ←
            </a>
            <a href="blog/{slug}.html" class="btn-review">
              קרא ביקורת מלאה →
            </a>
          </div>
        </div>
      </div>
"""

    prices_content = PRICES_HTML.read_text(encoding="utf-8")
    prices_content = prices_content.replace(
        "    </div>\n\n    <!-- Alert CTA -->",
        card_html + "\n    </div>\n\n    <!-- Alert CTA -->"
    )
    PRICES_HTML.write_text(prices_content, encoding="utf-8")


def main():
    if len(sys.argv) < 4:
        print("Usage: python tools/generate_post.py <ASIN> <israel_price_ils> <amazon_price_ils>")
        print("Example: python tools/generate_post.py B0BHJJ9Y77 1477 1338.85")
        sys.exit(1)

    asin = sys.argv[1]
    israel_price = sys.argv[2]
    amazon_price = sys.argv[3]

    published = load_published_asins()
    if asin in published:
        print(f"ASIN {asin} already published. Skipping.")
        sys.exit(0)

    print(f"[1/5] Fetching product data for {asin}...")
    product = get_product_data(asin)
    print(f"  → {product['title']}")

    print("[2/5] Generating Hebrew content with Claude Opus 4.8...")
    content = generate_content(product, israel_price, amazon_price)
    slug = content["slug"]
    print(f"  → slug: {slug}")

    output_path = BLOG_DIR / f"{slug}.html"
    if output_path.exists():
        print(f"  ⚠️  {slug}.html already exists — overwriting")

    print("[3/5] Building HTML file...")
    html = build_html(product, content, israel_price, amazon_price)
    output_path.write_text(html, encoding="utf-8")
    print(f"  → Written: blog/{slug}.html")

    print("[4/5] Adding price card to prices.html...")
    add_price_card(asin, product, israel_price, amazon_price, slug, content)
    print("  → prices.html updated")

    print("[5/5] Saving ASIN to published_asins.json...")
    published.append(asin)
    save_published_asins(published)

    print(f"""
✅ Draft ready — review before publishing:
   blog/{slug}.html   ← noindex active, review the content
   prices.html        ← new card added, check alignment

When satisfied:
   1. Remove <meta name="robots" content="noindex,nofollow" /> from blog/{slug}.html
   2. Run:
      git add blog/{slug}.html prices.html tools/published_asins.json
      git commit -m "blog: publish {content['title_short']} review + prices card"
      git push
   3. Ping IndexNow so Bing crawls it within minutes:
      python tools/indexnow.py https://www.amzfreeil.com/blog/{slug}.html
""")


if __name__ == "__main__":
    main()
