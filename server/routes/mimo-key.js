// ── MiMo API Key 路由 ────────────────────────────────────────
const fs = require('fs');
const path = require('path');
const { ENV_PATH } = require('../lib/env-store');

function register(router) {
  router.get('/api/mimo-key', (req, res) => {
    let key = '';
    try {
      if (fs.existsSync(ENV_PATH)) {
        const content = fs.readFileSync(ENV_PATH, 'utf8');
        const match = content.match(/MIMO_API_KEY\s*=\s*([^\r\n]+)/);
        if (match) key = match[1].trim();
      }
    } catch {}
    res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
    res.end(JSON.stringify({ apiKey: key }));
  });

  router.post('/api/mimo-key', (req, res) => {
    const apiKey = (req.body.apiKey || '').trim();
    try {
      let content = fs.existsSync(ENV_PATH) ? fs.readFileSync(ENV_PATH, 'utf8') : '';
      if (content.includes('MIMO_API_KEY=')) {
        content = content.replace(/MIMO_API_KEY\s*=\s*[^\r\n]*/, `MIMO_API_KEY=${apiKey}`);
      } else {
        content += (content.endsWith('\n') || content === '' ? '' : '\n') + `MIMO_API_KEY=${apiKey}\n`;
      }
      fs.writeFileSync(ENV_PATH, content, 'utf8');
    } catch (e) {
      res.writeHead(500, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ error: e.message }));
      return;
    }
    res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
    res.end(JSON.stringify({ success: true }));
  });
}

module.exports = { register };
