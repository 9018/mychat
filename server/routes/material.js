// ── 素材分析助手路由 ──────────────────────────────────────────
const path = require('path');
const { readJSON, writeJSON } = require('../lib/file-store');

const CONFIG_PATH = path.join(__dirname, '..', '..', 'material_config.json');
const PROMPTS_PATH = path.join(__dirname, '..', '..', 'material_prompts.json');
const HISTORY_PATH = path.join(__dirname, '..', '..', 'material_history.json');

function register(router) {
  // ── 配置读写 ──
  router.get('/api/material/config', (req, res) => {
    const config = readJSON(CONFIG_PATH, {
      prompt_template: '',
      default_generate_count: 10,
      saved_template: '',
    });
    res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
    res.end(JSON.stringify(config));
  });

  router.post('/api/material/config', (req, res) => {
    writeJSON(CONFIG_PATH, req.body);
    res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
    res.end(JSON.stringify({ success: true }));
  });

  // ── Prompt 列表读写 ──
  router.get('/api/material/prompts', (req, res) => {
    const data = readJSON(PROMPTS_PATH, { imported_text: '', prompts: [] });
    res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
    res.end(JSON.stringify(data));
  });

  router.post('/api/material/prompts', (req, res) => {
    writeJSON(PROMPTS_PATH, req.body);
    res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
    res.end(JSON.stringify({ success: true }));
  });

  router.delete('/api/material/prompts', (req, res) => {
    writeJSON(PROMPTS_PATH, { imported_text: '', prompts: [] });
    res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
    res.end(JSON.stringify({ success: true }));
  });

  // ── 生图历史 ──
  router.get('/api/material/history', (req, res) => {
    const history = readJSON(HISTORY_PATH, []);
    res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
    res.end(JSON.stringify(history));
  });
}

module.exports = { register };
