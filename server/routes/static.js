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
      const stat = fs.statSync(filePath);
      const range = req.headers.range;
      if (range) {
        // HTTP Range (浏览器/播放器拖动与分段加载必需)
        const m = /bytes=(\d*)-(\d*)/.exec(range);
        let start = m && m[1] !== '' ? parseInt(m[1], 10) : 0;
        let end = m && m[2] !== '' ? parseInt(m[2], 10) : stat.size - 1;
        if (isNaN(start) || start < 0) start = 0;
        if (isNaN(end) || end >= stat.size) end = stat.size - 1;
        if (start > end) {
          res.writeHead(416, { 'Content-Range': `bytes */${stat.size}` });
          return res.end();
        }
        res.writeHead(206, {
          'Content-Type': contentType,
          'Content-Range': `bytes ${start}-${end}/${stat.size}`,
          'Accept-Ranges': 'bytes',
          'Content-Length': end - start + 1,
        });
        fs.createReadStream(filePath, { start, end }).pipe(res);
      } else {
        res.writeHead(200, {
          'Content-Type': contentType,
          'Accept-Ranges': 'bytes',
          'Content-Length': stat.size,
        });
        fs.createReadStream(filePath).pipe(res);
      }
    } else {
      res.writeHead(404);
      res.end('Not found');
    }
  });
}

module.exports = { register };
