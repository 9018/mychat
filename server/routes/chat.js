// ── 聊天数据路由（设置 + 消息历史） ────────────────────────────
const path = require('path');
const { readJSON, writeJSON } = require('../lib/file-store');

const SETTINGS_PATH = path.join(__dirname, '..', '..', 'chat_settings.json');
const MESSAGES_PATH = path.join(__dirname, '..', '..', 'chat_messages.json');

function register(router) {
  // ── 聊天设置 ──
  router.get('/api/chat/settings', (req, res) => {
    const settings = readJSON(SETTINGS_PATH, {
      systemPrompt: '',
      temperature: 1.0,
      topP: 1.0,
      maxTokens: '',
      stream: true,
      enableThinking: false,
      thinkingBudget: 2048,
    });
    res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
    res.end(JSON.stringify(settings));
  });

  router.post('/api/chat/settings', (req, res) => {
    writeJSON(SETTINGS_PATH, req.body);
    res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
    res.end(JSON.stringify({ success: true }));
  });

  // ── 聊天消息历史 ──
  router.get('/api/chat/messages', (req, res) => {
    const messages = readJSON(MESSAGES_PATH, []);
    res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
    res.end(JSON.stringify(messages));
  });

  router.post('/api/chat/messages', (req, res) => {
    writeJSON(MESSAGES_PATH, req.body);
    res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
    res.end(JSON.stringify({ success: true }));
  });

  router.delete('/api/chat/messages', (req, res) => {
    writeJSON(MESSAGES_PATH, []);
    res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
    res.end(JSON.stringify({ success: true }));
  });
}

module.exports = { register };
