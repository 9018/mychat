// ── API Key 路由 ─────────────────────────────────────────────
const { getApiKeyFromEnv, saveApiKeyToEnv } = require('../lib/env-store');

function register(router) {
  // GET /api/key — 读取保存的 API Key
  router.get('/api/key', (req, res) => {
    const apiKey = getApiKeyFromEnv();
    res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
    res.end(JSON.stringify({ apiKey }));
  });

  // POST /api/key — 保存 API Key
  router.post('/api/key', (req, res) => {
    const apiKey = (req.body.apiKey || '').trim();
    saveApiKeyToEnv(apiKey);
    res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
    res.end(JSON.stringify({ success: true }));
  });
}

module.exports = { register };
