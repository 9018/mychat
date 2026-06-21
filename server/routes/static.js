// ── 静态文件服务路由 ──────────────────────────────────────────
const fs = require('fs');
const path = require('path');
const { OUTPUTS_DIR } = require('../lib/file-store');

function register(router) {
  // GET /outputs/* — 提供 outputs 目录中的生成结果
  router.get('/outputs/*', (req, res) => {
    const safeFilename = path.basename(req.url);
    const filePath = path.join(OUTPUTS_DIR, safeFilename);
    if (fs.existsSync(filePath)) {
      const ext = path.extname(filePath).toLowerCase();
      const contentTypeMap = {
        '.mp4': 'video/mp4',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.webp': 'image/webp',
        '.gif': 'image/gif',
      };
      const contentType = contentTypeMap[ext] || 'application/octet-stream';
      res.writeHead(200, { 'Content-Type': contentType });
      fs.createReadStream(filePath).pipe(res);
    } else {
      res.writeHead(404);
      res.end('Not found');
    }
  });
}

module.exports = { register };
