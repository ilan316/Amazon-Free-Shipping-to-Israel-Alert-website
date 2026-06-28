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

function getLastMod(relPath) {
  try {
    const date = execSync(`git log -1 --format="%ai" -- "${relPath}"`, { cwd: ROOT }).toString().trim();
    if (!date) return new Date().toISOString().split('T')[0];
    return date.split(' ')[0];
  } catch {
    return new Date().toISOString().split('T')[0];
  }
}

const urls = [];

// Root HTML files
for (const file of fs.readdirSync(ROOT).filter(f => f.endsWith('.html'))) {
  if (shouldSkip(file)) continue;
  const filePath = path.join(ROOT, file);
  if (hasNoIndex(filePath)) continue;
  const url = file === 'index.html' ? `${BASE_URL}/` : `${BASE_URL}/${file}`;
  urls.push({ url, lastmod: getLastMod(file) });
}

// Blog directory
const blogDir = path.join(ROOT, 'blog');
if (fs.existsSync(blogDir)) {
  for (const file of fs.readdirSync(blogDir).filter(f => f.endsWith('.html'))) {
    if (shouldSkip(file)) continue;
    const filePath = path.join(blogDir, file);
    if (hasNoIndex(filePath)) continue;
    const url = file === 'index.html' ? `${BASE_URL}/blog/` : `${BASE_URL}/blog/${file}`;
    urls.push({ url, lastmod: getLastMod(`blog/${file}`) });
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
