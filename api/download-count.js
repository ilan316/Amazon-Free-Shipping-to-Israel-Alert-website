module.exports = async function handler(req, res) {
  const r = await fetch(`${process.env.UPSTASH_REDIS_REST_URL}/get/download_count`, {
    headers: { Authorization: `Bearer ${process.env.UPSTASH_REDIS_REST_TOKEN}` },
  });
  const data = await r.json();
  res.json({ count: data.result ?? 0 });
};
