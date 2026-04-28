module.exports = async function handler(req, res) {
  const url = process.env.UPSTASH_REDIS_REST_URL;
  const token = process.env.UPSTASH_REDIS_REST_TOKEN;
  const r = await fetch(`${url}/mget/download_count/last_download_at`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const data = await r.json();
  const [count, last_download_at] = data.result ?? [0, null];
  res.json({ count: count ?? 0, last_download_at: last_download_at ?? null });
};
