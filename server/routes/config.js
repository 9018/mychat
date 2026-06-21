// ── 配置路由 ────────────────────────────────────────────────
const path = require('path');
const { readJSON, writeJSON } = require('../lib/file-store');

const CONFIG_PATH = path.join(__dirname, '..', '..', 'config.json');

function register(router) {
  // GET /api/config — 读取本地配置
  router.get('/api/config', (req, res) => {
    const config = readJSON(CONFIG_PATH, {});
    res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
    res.end(JSON.stringify(config));
  });

  // POST /api/config — 写入本地配置（整体覆盖）
  router.post('/api/config', (req, res) => {
    writeJSON(CONFIG_PATH, req.body);
    res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
    res.end(JSON.stringify({ success: true }));
  });
}

module.exports = { register };
