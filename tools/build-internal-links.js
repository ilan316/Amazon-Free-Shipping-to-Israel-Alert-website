#!/usr/bin/env node
/**
 * build-internal-links.js — בונה את רשת הקישורים הפנימיים של האתר.
 *
 * אידמפוטנטי: ריצה שנייה ברצף חייבת להשאיר `git diff` ריק. זו בדיקת הקבלה.
 *
 * מה הוא עושה:
 *   1. סורק blog/*.html, מסווג כל קובץ כסקירת מוצר או כמדריך עריכתי
 *      (deny-list סגור ב-tools/category-map.json), ומשייך דלי קטגוריה.
 *   2. מזריק בלוק "מוצרים דומים" בין <!-- RELATED:START --> ל-<!-- RELATED:END -->
 *      בכל סקירה — 4 סקירות מאותו דלי, round-robin, כך שכל סקירה מקבלת
 *      בדיוק 4 קישורים נכנסים חדשים.
 *   3. משכתב את ה-breadcrumb של הסקירות ל: דף הבית › סקירות מוצרים › {קטגוריה} › {מוצר}
 *      (גם בטקסט וגם ב-BreadcrumbList JSON-LD).
 *   4. מתקן קישור שבור: ../mekhs-umaam-amazon-israel.html → mekhs-umaam-amazon-israel.html
 *   5. בונה מחדש את prices.html בין <!-- HUB:START --> ל-<!-- HUB:END --> —
 *      תפריט עוגנים + סקשן לכל דלי. הכרטיסים מועברים verbatim, המחירים נשמרים.
 *   6. כותב blog/categories.json (ארטיפקט אודיט).
 *
 * ללא תלויות. Node 18+.
 */

'use strict';

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const BLOG_DIR = path.join(ROOT, 'blog');
const PRICES = path.join(ROOT, 'prices.html');
const MAP_FILE = path.join(__dirname, 'category-map.json');
const AUDIT_FILE = path.join(BLOG_DIR, 'categories.json');

const RELATED_COUNT = 4;

// ---------------------------------------------------------------- utilities

/** מסיר variation selector כדי שהשוואת אימוג'י תהיה יציבה. */
const normEmoji = (s) => (s || '').replace(/️/g, '');

/** BOM-safe read/write — prices.html שומר BOM ואסור לאבד אותו. */
function readFile(p) {
  return fs.readFileSync(p, 'utf8');
}

/**
 * שומר על סגנון סופי-השורה של הקובץ המקורי. עותק העבודה כאן הוא CRLF
 * (core.autocrlf), וכתיבת LF הייתה מייצרת דיף ענק ומדומה.
 */
function writeIfChanged(p, next, changed) {
  const prev = fs.existsSync(p) ? readFile(p) : null;
  if (prev !== null && prev.includes('\r\n')) {
    next = next.replace(/\r\n/g, '\n').replace(/\n/g, '\r\n');
  }
  if (prev === next) return false;
  fs.writeFileSync(p, next, 'utf8');
  changed.push(path.relative(ROOT, p).replace(/\\/g, '/'));
  return true;
}

function esc(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/** ההופכי של esc — הכרחי כדי לא לקודד פעמיים בין ריצות (&quot; → &amp;quot;). */
function unesc(s) {
  return String(s)
    .replace(/&quot;/g, '"')
    .replace(/&#0?39;/g, "'")
    .replace(/&apos;/g, "'")
    .replace(/&nbsp;/g, ' ')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&amp;/g, '&');
}

/** ה-JSON-LD מכיל את השם כמחרוזת JSON — מרכאות כפולות חייבות בריחה. */
function jsonStr(s) {
  return JSON.stringify(String(s));
}

// ------------------------------------------------------------- category map

const cmap = JSON.parse(readFile(MAP_FILE));
const BUCKETS = cmap.buckets;
const BUCKET_BY_ID = new Map(BUCKETS.map((b) => [b.id, b]));
const EMOJI_MAP = new Map(
  Object.entries(cmap.emoji).map(([k, v]) => [normEmoji(k), v])
);
const LEAF_MAP = new Map(Object.entries(cmap.leaves));
const OVERRIDES = new Map(Object.entries(cmap.overrides));
const EDITORIAL = new Set(cmap.editorial);
const KEYWORDS = (cmap.keywords || []).map((r) => ({
  bucket: r.bucket,
  match: r.match.map((s) => s.toLowerCase()),
}));

const warnings = [];
const keywordFallbacks = [];

/**
 * רשת ביטחון לאימוג'י לא ממופה. ה-eyebrow נכתב ע"י LLM בהנחיה פתוחה
 * (blog_utils.py), ולכן כל נישה חדשה עלולה ליפול ל-misc. מחפשים רמז בשם
 * המוצר (עברית) וב-slug (אנגלית) יחד. הכלל הראשון שמתאים מנצח — הסדר
 * ב-category-map.json הוא שמכריע בין חופפים (מצלמת ילדים ≠ בקבוק לילדים).
 */
function classifyByKeyword(post) {
  const hay = `${post.name} ${post.slug}`.toLowerCase();
  for (const rule of KEYWORDS) {
    const hit = rule.match.find((kw) => hay.includes(kw));
    if (hit) return { bucket: rule.bucket, hit };
  }
  return null;
}

function classify(post) {
  if (OVERRIDES.has(post.slug)) return OVERRIDES.get(post.slug);
  if (post.leaf && LEAF_MAP.has(post.leaf)) return LEAF_MAP.get(post.leaf);
  const e = normEmoji(post.emoji);
  if (e && EMOJI_MAP.has(e)) return EMOJI_MAP.get(e);

  const kw = classifyByKeyword(post);
  if (kw) {
    keywordFallbacks.push({
      slug: post.slug,
      emoji: post.emoji,
      keyword: kw.hit,
      bucket: kw.bucket,
    });
    return kw.bucket;
  }

  warnings.push(
    `אימוג'י לא ממופה "${post.emoji}" (leaf: "${post.leaf}") — ${post.slug} שויך ל-misc`
  );
  return 'misc';
}

// ----------------------------------------------------------------- scan blog

/** חילוץ שם המוצר מהפריט האחרון ב-breadcrumb (יציב בין הפורמט הישן לחדש). */
function extractCrumbName(html) {
  const nav = html.match(/<nav class="blog-breadcrumb"[\s\S]*?<\/nav>/);
  if (!nav) return null;
  const spans = [...nav[0].matchAll(/<span(?![^>]*aria-hidden)[^>]*>([\s\S]*?)<\/span>/g)];
  if (!spans.length) return null;
  return unesc(spans[spans.length - 1][1].replace(/<[^>]+>/g, '')).trim();
}

function scanPosts() {
  const posts = [];
  for (const file of fs.readdirSync(BLOG_DIR).filter((f) => f.endsWith('.html'))) {
    const slug = file.replace(/\.html$/, '');
    if (EDITORIAL.has(slug)) continue;

    const abs = path.join(BLOG_DIR, file);
    const html = readFile(abs);

    const crumbName = extractCrumbName(html);
    const post = {
      slug,
      file: abs,
      html,
      noindex: /<meta[^>]+name=["']robots["'][^>]+noindex/i.test(html),
      image: (html.match(/<meta property="og:image" content="([^"]+)"/) || [, ''])[1],
      emoji: (html.match(/<p class="eyebrow">\s*(\S+)/) || [, ''])[1],
      leaf: (html.match(/"category":\s*"([^"]*)"/) || [, ''])[1],
      // "AMD Ryzen 7 9800X3D — ביקורת" → "AMD Ryzen 7 9800X3D"
      name: (crumbName || '').replace(/\s*—\s*ביקורת\s*$/, '').trim(),
      crumbName: crumbName || '',
    };
    if (!post.name) {
      warnings.push(`אין breadcrumb תקין ב-${slug} — הקובץ דולג`);
      continue;
    }
    post.bucket = classify(post);
    posts.push(post);
  }
  posts.sort((a, b) => a.slug.localeCompare(b.slug));
  return posts;
}

// ------------------------------------------------------- related-block build

function relatedCard(target) {
  const b = BUCKET_BY_ID.get(target.bucket);
  return [
    `        <a class="blog-index-card" href="${target.slug}.html">`,
    `          <img class="blog-index-card__thumb" src="${esc(target.image)}" alt="${esc(target.name)}" width="280" height="147" loading="lazy" style="object-fit:contain;background:#fff;padding:10px;" />`,
    `          <div class="blog-card-body" style="padding:20px;">`,
    `            <div class="blog-index-card__cat">${b.emoji} ${esc(b.label)}</div>`,
    `            <h3 class="blog-index-card__title">${esc(target.name)}</h3>`,
    `            <div class="blog-index-card__footer"><span class="blog-index-card__read">לסקירה ←</span></div>`,
    `          </div>`,
    `        </a>`,
  ].join('\n');
}

function relatedBlock(post, targets) {
  const b = BUCKET_BY_ID.get(post.bucket);
  return [
    `    <!-- RELATED:START -->`,
    `    <section class="section" style="max-width:860px;margin:0 auto 48px;">`,
    `      <h2 style="font-family:Rubik,sans-serif;font-size:1.25rem;margin-bottom:8px;">מוצרים דומים</h2>`,
    `      <p style="color:#4d5a70;font-size:.9rem;margin:0 0 24px;">עוד סקירות בקטגוריית <a href="../prices.html#cat-${post.bucket}" style="color:var(--brand-deep, #ff6a00);">${b.emoji} ${esc(b.label)}</a></p>`,
    `      <div class="blog-index-grid">`,
    targets.map(relatedCard).join('\n'),
    `      </div>`,
    `    </section>`,
    `    <!-- RELATED:END -->`,
  ].join('\n');
}

/**
 * מתכנן את בלוקי "מוצרים דומים" לכל הסקירות יחד, בשני שלבים:
 *   1. round-robin בתוך הדלי — פיזור אחיד, כל סקירה מקבלת עד 4 יוצאים.
 *   2. דליים קטנים (misc/kids) לא מספקים 4 — משלימים מהמאגר הגלובלי, כשהמועמדים
 *      ממוינים לפי מספר הקישורים הנכנסים שכבר צברו. זה מנתב את ההשלמות דווקא
 *      לסקירות הרעבות — בדיוק אלה שבדליים הקטנים — במקום לפזר אותן אקראית.
 * דטרמיניסטי לחלוטין (מיון לפי slug בשוויון), ולכן אידמפוטנטי.
 */
function planTargets(posts, byBucket, indexable) {
  const plan = new Map();
  const inbound = new Map(indexable.map((p) => [p.slug, 0]));

  // --- שלב 1
  for (const post of posts) {
    const pool = byBucket.get(post.bucket).filter((p) => !p.noindex);
    const out = [];
    if (pool.length > 1) {
      const i = pool.findIndex((p) => p.slug === post.slug);
      const base = i >= 0 ? i : 0;
      for (let k = 1; k < pool.length && out.length < RELATED_COUNT; k++) {
        const cand = pool[(base + k) % pool.length];
        if (cand.slug !== post.slug) out.push(cand);
      }
    }
    for (const t of out) inbound.set(t.slug, inbound.get(t.slug) + 1);
    plan.set(post.slug, out);
  }

  // --- שלב 2
  for (const post of posts) {
    const out = plan.get(post.slug);
    if (out.length >= RELATED_COUNT) continue;
    const seen = new Set([post.slug, ...out.map((p) => p.slug)]);
    const cands = indexable
      .filter((p) => !seen.has(p.slug))
      .sort((a, b) => inbound.get(a.slug) - inbound.get(b.slug) || (a.slug < b.slug ? -1 : 1));
    for (const cand of cands) {
      if (out.length >= RELATED_COUNT) break;
      out.push(cand);
      inbound.set(cand.slug, inbound.get(cand.slug) + 1);
    }
  }

  // --- שלב 3: איזון נכנסים
  // סה"כ הקישורים היוצאים (153×4) גדול ממכפלת הסקירות המאונדקסות ב-4 (148×4),
  // ולכן לכל גירעון קיים בהכרח עודף במקום אחר. מעבירים קישור מיעד רווי אל
  // סקירה רעבה, עד שאין גירעונות. סדר קבוע ⇒ אידמפוטנטי.
  const bySlug = new Map(indexable.map((p) => [p.slug, p]));
  for (let pass = 0; pass < 50; pass++) {
    const deficits = indexable
      .filter((p) => inbound.get(p.slug) < RELATED_COUNT)
      .sort((a, b) => inbound.get(a.slug) - inbound.get(b.slug) || (a.slug < b.slug ? -1 : 1));
    if (!deficits.length) break;
    let moved = 0;
    for (const p of deficits) {
      if (inbound.get(p.slug) >= RELATED_COUNT) continue;
      for (const donor of posts) {
        if (donor.slug === p.slug) continue;
        const out = plan.get(donor.slug);
        if (out.some((x) => x.slug === p.slug)) continue;
        const idx = out.findIndex((t) => inbound.get(t.slug) > RELATED_COUNT);
        if (idx < 0) continue;
        inbound.set(out[idx].slug, inbound.get(out[idx].slug) - 1);
        out[idx] = bySlug.get(p.slug);
        inbound.set(p.slug, inbound.get(p.slug) + 1);
        moved++;
        break;
      }
    }
    if (!moved) {
      warnings.push('לא ניתן היה לאזן את כל הקישורים הנכנסים ל-4');
      break;
    }
  }

  return plan;
}

// -------------------------------------------------------------- breadcrumbs

function breadcrumbHtml(post) {
  const b = BUCKET_BY_ID.get(post.bucket);
  return [
    `        <nav class="blog-breadcrumb" aria-label="פירורי לחם">`,
    `          <a href="../index.html">דף הבית</a>`,
    `          <span aria-hidden="true">›</span>`,
    `          <a href="../prices.html">סקירות מוצרים</a>`,
    `          <span aria-hidden="true">›</span>`,
    `          <a href="../prices.html#cat-${post.bucket}">${esc(b.label)}</a>`,
    `          <span aria-hidden="true">›</span>`,
    `          <span aria-current="page">${esc(post.crumbName)}</span>`,
    `        </nav>`,
  ].join('\n');
}

/** מחליף את שלושת הפריטים ב-BreadcrumbList בארבעה, בהתאמה ל-breadcrumb הגלוי. */
function rewriteBreadcrumbJsonLd(html, post) {
  const b = BUCKET_BY_ID.get(post.bucket);
  const items = [
    { name: 'דף הבית', item: 'https://www.amzfreeil.com/' },
    { name: 'סקירות מוצרים', item: 'https://www.amzfreeil.com/prices.html' },
    { name: b.label, item: `https://www.amzfreeil.com/prices.html#cat-${post.bucket}` },
    {
      name: post.crumbName,
      item: `https://www.amzfreeil.com/blog/${post.slug}.html`,
    },
  ];
  const body = items
    .map((it, i) =>
      [
        `      {`,
        `        "@type": "ListItem",`,
        `        "position": ${i + 1},`,
        `        "name": ${jsonStr(it.name)},`,
        `        "item": ${jsonStr(it.item)}`,
        `      }`,
      ].join('\n')
    )
    .join(',\n');

  const re = /"@type":\s*"BreadcrumbList",\s*"itemListElement":\s*\[[\s\S]*?\]\s*\}/;
  if (!re.test(html)) {
    warnings.push(`לא נמצא BreadcrumbList ב-${post.slug}`);
    return html;
  }
  return html.replace(
    re,
    () =>
      '"@type": "BreadcrumbList",\n    "itemListElement": [\n' + body + '\n    ]\n  }'
  );
}

// ------------------------------------------------------------- post rewrites

const OLD_RELATED_RE =
  /\n[ \t]*<section class="section" style="max-width:860px;margin:0 auto 64px;">\s*\n[ \t]*<h2[^>]*>מאמרים קשורים<\/h2>[\s\S]*?\n[ \t]*<\/section>/;

function rewritePost(post, targets) {
  let html = post.html;

  // 1. breadcrumb גלוי
  html = html.replace(
    /[ \t]*<nav class="blog-breadcrumb"[\s\S]*?<\/nav>/,
    breadcrumbHtml(post)
  );

  // 2. BreadcrumbList ב-JSON-LD
  html = rewriteBreadcrumbJsonLd(html, post);

  // 3. קישור מכס שבור — ../ מתוך /blog/ נותן 404
  html = html.replace(
    /href="\.\.\/mekhs-umaam-amazon-israel\.html"/g,
    'href="mekhs-umaam-amazon-israel.html"'
  );

  // 4. בלוק "מוצרים דומים"
  const block = relatedBlock(post, targets);
  if (/<!-- RELATED:START -->/.test(html)) {
    html = html.replace(
      /[ \t]*<!-- RELATED:START -->[\s\S]*?<!-- RELATED:END -->/,
      block
    );
  } else if (OLD_RELATED_RE.test(html)) {
    // מוסיפים לפני סקשן "מאמרים קשורים" הקיים — הוא נשאר, הוא מקשר למדריכים
    html = html.replace(OLD_RELATED_RE, (m) => '\n' + block + m);
  } else {
    html = html.replace(/\n[ \t]*<\/main>/, '\n' + block + '\n  </main>');
  }

  return html;
}

// ------------------------------------------------------------- prices.html

const HUB_START = '    <!-- HUB:START -->';
const HUB_END = '    <!-- HUB:END -->';

/** חותך כרטיס price-card שלם (כולל הערת הכותרת שמעליו) מתוך prices.html. */
function extractCards(html) {
  const cards = [];
  const re = /<div class="price-card">/g;
  let m;
  while ((m = re.exec(html))) {
    // סוף: הסריקה קדימה עד שסוגרים את ה-div
    const scan = /<div\b|<\/div>/g;
    scan.lastIndex = m.index;
    let depth = 0;
    let end = -1;
    let t;
    while ((t = scan.exec(html))) {
      depth += t[0] === '</div>' ? -1 : 1;
      if (depth === 0) {
        end = t.index + t[0].length;
        break;
      }
    }
    if (end === -1) throw new Error('prices.html: כרטיס לא סגור סביב offset ' + m.index);

    // התחלה: תחילת השורה, ואם יש הערה בשורה שמעל — כוללים אותה
    let start = html.lastIndexOf('\n', m.index) + 1;
    const prevLineStart = html.lastIndexOf('\n', start - 2) + 1;
    const prevLine = html.slice(prevLineStart, start - 1);
    if (/^\s*<!--[\s\S]*-->\s*$/.test(prevLine)) start = prevLineStart;

    const text = html.slice(start, end);
    const slug = (text.match(/href="blog\/([^"]+)\.html"/) || [, ''])[1];
    cards.push({ slug, text });
    re.lastIndex = end;
  }
  return cards;
}

function buildHub(cards, posts) {
  const bySlug = new Map(posts.map((p) => [p.slug, p]));
  const groups = new Map(BUCKETS.map((b) => [b.id, []]));
  const orphanCards = [];

  for (const card of cards) {
    const post = bySlug.get(card.slug);
    if (!post) {
      orphanCards.push(card.slug);
      groups.get('misc').push(card);
      continue;
    }
    groups.get(post.bucket).push(card);
  }

  const active = BUCKETS.filter((b) => groups.get(b.id).length > 0);

  const nav = [
    `    <nav class="hub-nav" aria-label="קטגוריות סקירות">`,
    ...active.map(
      (b) =>
        `      <a href="#cat-${b.id}">${b.emoji} ${esc(b.label)} <span>${groups.get(b.id).length}</span></a>`
    ),
    `    </nav>`,
  ].join('\n');

  const sections = active
    .map((b) =>
      [
        ``,
        `    <section class="hub-section" id="cat-${b.id}">`,
        `      <h2 class="hub-section-title">${b.emoji} ${esc(b.label)}</h2>`,
        `      <div class="prices-grid">`,
        ``,
        groups.get(b.id).map((c) => c.text).join('\n\n'),
        ``,
        `      </div>`,
        `    </section>`,
      ].join('\n')
    )
    .join('\n');

  return {
    html: [HUB_START, nav, sections, HUB_END].join('\n'),
    groups,
    orphanCards,
    active,
  };
}

/** ItemList עם קישור לכל סקירה — נותן לגוגל את הרשימה המלאה בעמוד אחד. */
function buildCollectionSchema(cards, posts) {
  const bySlug = new Map(posts.map((p) => [p.slug, p]));
  const listed = cards.filter((c) => bySlug.has(c.slug) && !bySlug.get(c.slug).noindex);
  // שורה אחת לפריט — 148 פריטים בפורמט מלא הוסיפו ~40KB לעמוד שכבר גדול.
  // גוגל מסתפק ב-url ב-ItemList מסוג "רשימת עמודים".
  const elements = listed
    .map(
      (c, i) =>
        `        { "@type": "ListItem", "position": ${i + 1}, "url": "https://www.amzfreeil.com/blog/${bySlug.get(c.slug).slug}.html" }`
    )
    .join(',\n');

  return [
    `  <script type="application/ld+json">`,
    `  {`,
    `    "@context": "https://schema.org",`,
    `    "@type": "CollectionPage",`,
    `    "name": "סקירות מוצרים: אמזון מול ישראל",`,
    `    "url": "https://www.amzfreeil.com/prices.html",`,
    `    "description": "קטלוג סקירות מוצרים באמזון לפי קטגוריה, כולל השוואת מחיר לישראל, מע\\"מ ייבוא ומשלוח חינם.",`,
    `    "inLanguage": "he-IL",`,
    `    "isPartOf": { "@type": "WebSite", "name": "AMZ Free Ship Alert", "url": "https://www.amzfreeil.com/" },`,
    `    "mainEntity": {`,
    `      "@type": "ItemList",`,
    `      "numberOfItems": ${listed.length},`,
    `      "itemListElement": [`,
    elements,
    `      ]`,
    `    }`,
    `  }`,
    `  </script>`,
  ].join('\n');
}

const HUB_CSS = `
    /* --- HUB (נבנה ע"י tools/build-internal-links.js) --- */
    .hub-nav {
      max-width: 1020px;
      margin: 0 auto 36px;
      padding: 0 16px;
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      justify-content: center;
    }
    .hub-nav a {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: #fff;
      border: 1.5px solid rgba(23,32,51,.12);
      border-radius: 999px;
      padding: 7px 14px;
      font-size: .85rem;
      font-weight: 600;
      color: #172033;
      text-decoration: none;
      transition: border-color .15s, transform .15s;
    }
    .hub-nav a:hover { border-color: #ff9900; transform: translateY(-1px); }
    .hub-nav a span {
      background: rgba(255,153,0,.14);
      color: #8a5200;
      border-radius: 999px;
      padding: 1px 7px;
      font-size: .75rem;
    }
    .hub-section { scroll-margin-top: 120px; }
    .hub-section-title {
      font-family: Rubik, sans-serif;
      font-size: 1.3rem;
      font-weight: 800;
      color: #172033;
      max-width: 1020px;
      margin: 0 auto 16px;
      padding: 0 16px;
    }
    .hub-section .prices-grid { margin-bottom: 40px; }
`;

function rewritePrices(posts) {
  const original = readFile(PRICES);
  let html = original;

  const hasMarkers = html.includes(HUB_START);
  const region = hasMarkers
    ? html.slice(html.indexOf(HUB_START), html.indexOf(HUB_END) + HUB_END.length)
    : null;

  const cards = extractCards(region !== null ? region : html);
  const hub = buildHub(cards, posts);

  if (hasMarkers) {
    html =
      html.slice(0, html.indexOf(HUB_START)) +
      hub.html +
      html.slice(html.indexOf(HUB_END) + HUB_END.length);
  } else {
    // ריצה ראשונה: מחליפים את ה-.prices-grid השטוח היחיד באזור המסומן
    const gridStart = html.indexOf('    <div class="prices-grid">');
    if (gridStart === -1) throw new Error('prices.html: לא נמצא .prices-grid');
    const scan = /<div\b|<\/div>/g;
    scan.lastIndex = gridStart;
    let depth = 0;
    let end = -1;
    let t;
    while ((t = scan.exec(html))) {
      depth += t[0] === '</div>' ? -1 : 1;
      if (depth === 0) {
        end = t.index + t[0].length;
        break;
      }
    }
    if (end === -1) throw new Error('prices.html: .prices-grid לא סגור');
    html = html.slice(0, gridStart) + hub.html + html.slice(end);
  }

  // סכמה: WebPage → CollectionPage + ItemList (ומתעדכן בכל ריצה).
  // הסדר נלקח מהכרטיסים אחרי הקיבוץ, כדי שהוא יתאים לסדר בעמוד כבר בריצה הראשונה.
  const orderedCards = hub.active.flatMap((b) => hub.groups.get(b.id));
  const schema = buildCollectionSchema(orderedCards, posts);
  html = html.replace(
    /[ \t]*<script type="application\/ld\+json">\s*\n\s*\{\s*\n\s*"@context"[\s\S]*?<\/script>/,
    schema
  );

  // CSS של ההאב — מוזרק פעם אחת בלבד
  if (!html.includes('.hub-nav {')) {
    html = html.replace(/\n(\s*)\.prices-grid \{/, HUB_CSS + '\n$1.prices-grid {');
  }

  return { html, hub, cards };
}

// -------------------------------------------------------------------- main

function main() {
  const posts = scanPosts();
  const indexable = posts.filter((p) => !p.noindex);

  const byBucket = new Map(BUCKETS.map((b) => [b.id, []]));
  for (const p of posts) byBucket.get(p.bucket).push(p);

  const plan = planTargets(posts, byBucket, indexable);

  const changed = [];

  // --- סקירות
  for (const post of posts) {
    const targets = plan.get(post.slug);
    const next = rewritePost(post, targets);
    writeIfChanged(post.file, next, changed);
  }

  // --- prices.html
  const { html: pricesHtml, hub, cards } = rewritePrices(posts);
  writeIfChanged(PRICES, pricesHtml, changed);

  // --- ארטיפקט אודיט
  const audit = {
    generatedBy: 'tools/build-internal-links.js',
    totals: {
      reviews: posts.length,
      indexable: indexable.length,
      noindex: posts.length - indexable.length,
      cardsInHub: cards.length,
    },
    buckets: BUCKETS.map((b) => ({
      id: b.id,
      label: b.label,
      posts: byBucket.get(b.id).map((p) => p.slug),
    })).filter((b) => b.posts.length),
    noindexDrafts: posts.filter((p) => p.noindex).map((p) => p.slug),
    missingFromHub: posts
      .filter((p) => !cards.some((c) => c.slug === p.slug))
      .map((p) => p.slug),
    keywordFallbacks,
    warnings,
  };
  writeIfChanged(AUDIT_FILE, JSON.stringify(audit, null, 2) + '\n', changed);

  // --- דוח
  console.log(`סקירות: ${posts.length} (מהן ${audit.totals.noindex} noindex)`);
  for (const b of audit.buckets) console.log(`  ${b.label}: ${b.posts.length}`);
  if (hub.orphanCards.length)
    console.log(`\nכרטיסים ב-prices.html בלי קובץ סקירה: ${hub.orphanCards.join(', ')}`);
  if (audit.missingFromHub.length)
    console.log(`סקירות שחסרות מ-prices.html: ${audit.missingFromHub.join(', ')}`);
  if (keywordFallbacks.length) {
    console.log('\nסווגו לפי מילת מפתח (אימוג\'י לא ממופה):');
    for (const f of keywordFallbacks)
      console.log(`  ~ ${f.slug}: "${f.emoji}" → ${f.bucket} (מילה: "${f.keyword}")`);
  }
  if (warnings.length) {
    console.log('\nאזהרות:');
    for (const w of warnings) console.log('  ! ' + w);
  }
  console.log(
    changed.length
      ? `\nעודכנו ${changed.length} קבצים.`
      : '\nאין שינויים (אידמפוטנטי).'
  );
}

main();
