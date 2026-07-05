module.exports = async function handler(req, res) {
  if (req.method !== 'POST') {
    res.status(405).end();
    return;
  }

  const { asin, name } = req.body || {};
  if (!asin || !/^[A-Z0-9]{10}$/.test(asin)) {
    res.status(400).json({ error: 'invalid asin' });
    return;
  }

  const url = process.env.UPSTASH_REDIS_REST_URL;
  const token = process.env.UPSTASH_REDIS_REST_TOKEN;

  const commands = [
    ['incr', `product_views:${asin}`],
    ['sadd', 'product_view_asins', asin],
  ];
  if (name) {
    commands.push(['hset', 'product_names', asin, String(name).slice(0, 200)]);
  }

  await fetch(`${url}/pipeline`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify(commands),
  });

  res.status(204).end();
};
