module.exports = async function handler(req, res) {
  const url = process.env.UPSTASH_REDIS_REST_URL;
  const token = process.env.UPSTASH_REDIS_REST_TOKEN;
  await fetch(`${url}/pipeline`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify([
      ['incr', 'download_count'],
      ['set', 'last_download_at', new Date().toISOString()],
    ]),
  });
  res.redirect(302, '/AmazonIsraelFreeShipAlert_Setup.exe');
};
