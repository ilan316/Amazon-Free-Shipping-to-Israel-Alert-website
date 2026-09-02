module.exports = async function handler(req, res) {
  const url = process.env.UPSTASH_REDIS_REST_URL;
  const token = process.env.UPSTASH_REDIS_REST_TOKEN;
  const r = await fetch(`${url}/mget/download_count/last_download_at/total_shares`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const data = await r.json();
  const [count, lastAt, shares] = data.result ?? [0, null, 0];

  const lastStr = lastAt
    ? new Date(lastAt).toLocaleString('he-IL', { timeZone: 'Asia/Jerusalem' })
    : 'אין עדיין';

  res.setHeader('Content-Type', 'text/html; charset=utf-8');
  res.end(`<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
<meta charset="utf-8">
<title>סטטיסטיקות הורדות</title>
<style>
  body { font-family: system-ui, sans-serif; background: #0f172a; color: #e2e8f0; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }
  .card { background: #1e293b; border-radius: 16px; padding: 40px 60px; text-align: center; }
  h1 { color: #38bdf8; margin-bottom: 32px; font-size: 1.4rem; }
  .stat { margin: 20px 0; }
  .label { font-size: 0.85rem; color: #94a3b8; margin-bottom: 6px; }
  .value { font-size: 2.5rem; font-weight: 700; color: #f1f5f9; }
  .sub { font-size: 1.1rem; color: #cbd5e1; }
</style>
</head>
<body>
<div class="card">
  <h1>📊 סטטיסטיקות הורדות — amzfreeil.com</h1>
  <div class="stat">
    <div class="label">סה"כ הורדות (Windows)</div>
    <div class="value">${count ?? 0}</div>
  </div>
  <div class="stat">
    <div class="label">הורדה אחרונה</div>
    <div class="sub">${lastStr}</div>
  </div>
  <div class="stat">
    <div class="label">סה"כ שיתופים</div>
    <div class="value">${shares ?? 0}</div>
  </div>
</div>
</body>
</html>`);
};
