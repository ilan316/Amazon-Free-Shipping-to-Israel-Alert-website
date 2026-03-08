module.exports = async function handler(req, res) {
  await fetch(`${process.env.UPSTASH_REDIS_REST_URL}/incr/download_count`, {
    headers: { Authorization: `Bearer ${process.env.UPSTASH_REDIS_REST_TOKEN}` },
  });
  res.redirect(302, '/AmazonIsraelFreeShipAlert_Setup.exe');
};
