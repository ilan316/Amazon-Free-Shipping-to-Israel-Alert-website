const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const BASE_URL = 'https://www.amzfreeil.com';
const ROOT = __dirname;

const SKIP_FILES = new Set([
  'googlee05047a57abdd8ac.html',
  '404.html',
  'guide.html', // redirect stub — canonical points to web-guide.html
]);

const SKIP_PREFIXES = ['preview-', 'footer-preview'];

function shouldSkip(filename) {
  if (SKIP_FILES.has(filename)) return true;
  if (SKIP_PREFIXES.some(p => filename.startsWith(p))) return true;
  return false;
}

function hasNoIndex(filePath) {
  const content = fs.readFileSync(filePath, 'utf-8');
  if (/<meta[^>]+name=["']robots["'][^>]+content=["'][^"']*noindex/i.test(content)) return true;
  if (/<meta[^>]+content=["'][^"']*noindex[^"']*["'][^>]+name=["']robots["']/i.test(content)) return true;
  if (/<meta[^>]+http-equiv=["']refresh["']/i.test(content)) return true; // redirect stub
  return false;
}

const TODAY = new Date().toISOString().split('T')[0];

function git(args) {
  return execSync(`git ${args}`, {
    cwd: ROOT,
    encoding: 'utf-8',
    stdio: ['ignore', 'pipe', 'ignore'],
    maxBuffer: 64 * 1024 * 1024,
  });
}

// lastmod נגזר מתאריך ה-commit האחרון של הקובץ, לא מ-mtime. mtime שונה בין
// המחשב המקומי (זמן אמת מהדיסק) ל-CI (checkout טרי = הכל מקבל את זמן הריצה),
// ולכן כל 18 השורות התהפכו הלוך ושוב בין ה-hook המקומי לבין ה-Action. תאריך
// ה-commit זהה בשני המקומות, כך שהפלט אידמפוטנטי.
// קריאת git אחת לכל ההיסטוריה — לא קריאה לכל קובץ.
function buildGitDates() {
  const map = new Map();
  let out;
  try {
    out = git('-c core.quotePath=false log --format=%x00%cI --name-only');
  } catch {
    return null; // אין git / אין היסטוריה — ראה fallback ב-getLastMod
  }
  let commitDate = null;
  for (const line of out.split('\n')) {
    if (line.startsWith('\0')) {
      commitDate = line.slice(1).trim().split('T')[0];
    } else if (line.trim() && commitDate && !map.has(line.trim())) {
      map.set(line.trim(), commitDate); // הפגיעה הראשונה = ה-commit העדכני ביותר
    }
  }
  return map;
}

// קובץ ששונה ועדיין לא נכנס ל-commit צריך את תאריך היום: ה-hook רץ לפני
// שה-commit נוצר, אז git log עדיין מחזיר עבורו את התאריך *הישן*.
function buildDirtySet() {
  const set = new Set();
  try {
    for (const line of git('-c core.quotePath=false status --porcelain').split('\n')) {
      const p = line.slice(3).trim();
      if (!p) continue;
      const arrow = p.indexOf(' -> '); // שינוי שם
      set.add(arrow === -1 ? p : p.slice(arrow + 4));
    }
  } catch { /* אין git — הסט נשאר ריק */ }
  return set;
}

// מוצא אחרון אם git לא זמין בכלל: משמרים את מה שכבר קיים ב-sitemap.xml
// במקום להחתים את כל האתר בתאריך היום.
function readExistingLastmods() {
  const map = new Map();
  try {
    const xml = fs.readFileSync(path.join(ROOT, 'sitemap.xml'), 'utf-8');
    const re = /<loc>([^<]+)<\/loc>\s*<lastmod>([^<]+)<\/lastmod>/g;
    let m;
    while ((m = re.exec(xml)) !== null) map.set(m[1], m[2]);
  } catch { /* אין sitemap קודם */ }
  return map;
}

const gitDates = buildGitDates();
const dirty = buildDirtySet();
const previous = gitDates ? null : readExistingLastmods();

function getLastMod(filePath, url) {
  if (!gitDates) return previous.get(url) || TODAY;
  const rel = path.relative(ROOT, filePath).split(path.sep).join('/');
  if (dirty.has(rel)) return TODAY;
  return gitDates.get(rel) || TODAY; // קובץ חדש שטרם נכנס ל-commit
}

const urls = [];

// Root HTML files
for (const file of fs.readdirSync(ROOT).filter(f => f.endsWith('.html'))) {
  if (shouldSkip(file)) continue;
  const filePath = path.join(ROOT, file);
  if (hasNoIndex(filePath)) continue;
  const url = file === 'index.html' ? `${BASE_URL}/` : `${BASE_URL}/${file}`;
  urls.push({ url, lastmod: getLastMod(filePath) });
}

// Blog directory
const blogDir = path.join(ROOT, 'blog');
if (fs.existsSync(blogDir)) {
  for (const file of fs.readdirSync(blogDir).filter(f => f.endsWith('.html'))) {
    if (shouldSkip(file)) continue;
    const filePath = path.join(blogDir, file);
    if (hasNoIndex(filePath)) continue;
    const url = file === 'index.html' ? `${BASE_URL}/blog/` : `${BASE_URL}/blog/${file}`;
    urls.push({ url, lastmod: getLastMod(filePath) });
  }
}

// Root pages first, then blog; alphabetical within each group
urls.sort((a, b) => {
  const aB = a.url.includes('/blog/'), bB = b.url.includes('/blog/');
  if (aB !== bB) return aB ? 1 : -1;
  return a.url.localeCompare(b.url);
});

const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls.map(({ url, lastmod }) =>
  `  <url>\n    <loc>${url}</loc>\n    <lastmod>${lastmod}</lastmod>\n  </url>`
).join('\n')}
</urlset>\n`;

fs.writeFileSync(path.join(ROOT, 'sitemap.xml'), xml);
console.log(`sitemap.xml: ${urls.length} URLs`);
urls.forEach(({ url, lastmod }) => console.log(`  ${lastmod}  ${url}`));
