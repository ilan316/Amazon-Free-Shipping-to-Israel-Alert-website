module.exports = async function handler(req, res) {
  if (req.method !== 'POST') {
    res.status(405).end();
    return;
  }

  const { type, id, name, channel } = req.body || {};

  if (type !== 'product' && type !== 'blog') {
    res.status(400).json({ error: 'invalid type' });
    return;
  }
  const idPattern = type === 'product' ? /^[A-Z0-9]{10}$/ : /^[a-z0-9-]+$/;
  if (!id || !idPattern.test(id)) {
    res.status(400).json({ error: 'invalid id' });
    return;
  }

  const url = process.env.UPSTASH_REDIS_REST_URL;
  const token = process.env.UPSTASH_REDIS_REST_TOKEN;

  const shareKey = type === 'product' ? `product_shares:${id}` : `blog_shares:${id}`;
  const setKey = type === 'product' ? 'product_share_asins' : 'blog_share_slugs';
  const nameHashKey = type === 'product' ? 'product_names' : 'blog_titles';

  const commands = [
    ['incr', shareKey],
    ['sadd', setKey, id],
    ['incr', 'total_shares'],
  ];
  if (name) {
    commands.push(['hset', nameHashKey, id, String(name).slice(0, 200)]);
  }
  if (channel) {
    commands.push(['hincrby', `share_channels:${id}`, String(channel).slice(0, 30), 1]);
  }

  await fetch(`${url}/pipeline`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify(commands),
  });

  res.status(204).end();
};
