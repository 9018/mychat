// ── 视频代理中转 ─────────────────────────────────────────────
// 解决国内 storage.googleapis.com 被墙无法加载视频的问题
const https = require('https');
const { httpsKeepAliveAgent } = require('../lib/keepalive-agent');

function register(router) {
  router.get('/video-proxy', (req, res) => {
    try {
      const targetUrl = req.query.url;
      if (!targetUrl) {
        res.writeHead(400);
        res.end('Missing url parameter');
        return;
      }

      const parsedTarget = new URL(targetUrl);

      const proxyHeaders = {
        'Host': parsedTarget.hostname,
        'User-Agent': req.headers['user-agent'] || 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
      };
      if (req.headers['range']) {
        proxyHeaders['Range'] = req.headers['range'];
      }
      if (req.headers['accept']) {
        proxyHeaders['Accept'] = req.headers['accept'];
      }

      const proxyReq = https.request({
        hostname: parsedTarget.hostname,
        port: 443,
        path: parsedTarget.pathname + parsedTarget.search,
        method: 'GET',
        headers: proxyHeaders,
        timeout: 20000,
        agent: httpsKeepAliveAgent,
      }, (upstream) => {
        res.writeHead(upstream.statusCode, upstream.headers);
        upstream.pipe(res);
      });

      proxyReq.on('timeout', () => {
        proxyReq.destroy(new Error('Connection timeout to upstream storage'));
      });

      proxyReq.on('error', (err) => {
        console.error(`视频中转失败 [URL: ${targetUrl}]:`, err.message);
        if (!res.headersSent) {
          res.writeHead(502, { 'Content-Type': 'text/plain; charset=utf-8' });
          res.end(`Failed to proxy video: ${err.message}`);
        }
      });

      proxyReq.end();
    } catch (err) {
      res.writeHead(400);
      res.end('Invalid url');
    }
  });
}

module.exports = { register };
