// ── 历史记录路由 ─────────────────────────────────────────────
const path = require('path');
const { readJSON, writeJSON, downloadMedia, removeMedia } = require('../lib/file-store');

const HISTORY_PATH = path.join(__dirname, '..', '..', 'history.json');

const DEFAULT_HISTORY = [
  { id: 'h_1', title: '宇航员 · 红色星球', kind: 'video', ar: '16:9', tone: 268, prompt: 'A young astronaut walking across a red desert planet, dust blowing in the wind, slow cinematic tracking shot, dramatic sunset lighting, realistic sci-fi style', model: 'agnes-video-v2.0', width: 1152, height: 768, url: '' },
  { id: 'h_2', title: '赛博女神肖像', kind: 'image', ar: '1:1', tone: 320, prompt: 'A stunning portrait of a cybernetic goddess, intricate neon makeup, glowing neural pathways, cyberpunk city background, hyperrealistic, octane render, 8k', model: 'agnes-image-2.1-flash', width: 1024, height: 1024, url: '' },
  { id: 'h_3', title: '雨夜霓虹街道', kind: 'video', ar: '9:16', tone: 210, prompt: 'A rainy night in Tokyo, neon street signs reflecting on wet asphalt, people walking with umbrellas, cinematic atmosphere, slow tracking shot', model: 'agnes-video-v2.0', width: 720, height: 1280, url: '' },
  { id: 'h_4', title: '极简产品主图', kind: 'image', ar: '1:1', tone: 150, prompt: 'Minimalist product shot of a luxury perfume bottle on a concrete pedestal, soft studio lighting, clean shadows, elegant composition', model: 'agnes-image-2.1-flash', width: 1024, height: 1024, url: '' }
];

function getHistory() {
  let history = readJSON(HISTORY_PATH, null);
  if (!history) {
    writeJSON(HISTORY_PATH, DEFAULT_HISTORY);
    history = [...DEFAULT_HISTORY];
  }
  return history;
}

function register(router) {
  // GET /api/history — 获取历史记录列表
  router.get('/api/history', (req, res) => {
    const history = getHistory();
    res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
    res.end(JSON.stringify(history));
  });

  // POST /api/history — 保存历史记录项
  router.post('/api/history', async (req, res) => {
    try {
      const item = req.body;
      const kind = item.kind || 'image';
      const rawUrl = item.url || '';

      let localUrl = rawUrl;
      let filename = null;

      if (rawUrl) {
        if (rawUrl.startsWith('data:') || rawUrl.startsWith('http://') || rawUrl.startsWith('https://')) {
          const result = await downloadMedia(rawUrl, kind);
          if (result) {
            localUrl = result;
            const parts = result.split('/');
            filename = parts[parts.length - 1];
          } else {
            // 下载失败，降级使用原 URL
            localUrl = rawUrl;
          }
        }
      }

      const historyItem = {
        id: item.id || ('h_' + Date.now()),
        title: item.title,
        kind: item.kind,
        ar: item.ar,
        tone: item.tone || 292,
        prompt: item.prompt,
        model: item.model,
        width: item.width,
        height: item.height,
        url: localUrl,
        filename: filename
      };

      const history = getHistory();
      history.unshift(historyItem);

      // 限制最多保存 100 条
      if (history.length > 100) {
        const removed = history.pop();
        if (removed && removed.filename) {
          removeMedia(removed.filename);
        }
      }

      writeJSON(HISTORY_PATH, history);

      res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ success: true, item: historyItem }));
    } catch (err) {
      console.error('保存历史失败:', err);
      res.writeHead(500, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ error: err.message }));
    }
  });

  // DELETE /api/history — 删除历史记录项
  router.delete('/api/history', (req, res) => {
    try {
      const id = req.query.id;
      if (!id) {
        res.writeHead(400);
        res.end('Missing id');
        return;
      }

      const history = getHistory();
      const itemToDelete = history.find(h => h.id === id);
      if (itemToDelete && itemToDelete.filename) {
        removeMedia(itemToDelete.filename);
      }

      const filtered = history.filter(h => h.id !== id);
      writeJSON(HISTORY_PATH, filtered);

      res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ success: true }));
    } catch (err) {
      res.writeHead(500, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ error: err.message }));
    }
  });
}

module.exports = { register };
