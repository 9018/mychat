// ── /agnesapi/* → 上游反向代理 ──────────────────────────────────
const https = require('https');
const http = require('http');
const path = require('path');
const { readJSON } = require('../lib/file-store');
const { getApiKeyFromEnv } = require('../lib/env-store');
const { httpsKeepAliveAgent, httpKeepAliveAgent } = require('../lib/keepalive-agent');

function register(router) {
  router.all('/agnesapi*', (req, res) => {
    let apiKey = req.headers['x-api-key'] || '';
    if (!apiKey) {
      apiKey = getApiKeyFromEnv();
    }

    // 动态读取 baseUrl
    let targetHost = 'apihub.agnes-ai.com';
    let targetProtocol = 'https:';
    let targetPort = 443;
    let targetPathname = '/agnesapi';

    const configPath = path.join(__dirname, '..', '..', 'config.json');
    const config = readJSON(configPath, {});
    if (config.baseUrl) {
      try {
        const parsedBase = new URL(config.baseUrl);
        targetHost = parsedBase.hostname;
        targetProtocol = parsedBase.protocol;
        targetPort = parsedBase.port || (parsedBase.protocol === 'https:' ? 443 : 80);
      } catch (e) {}
    }

    const urlObj = new URL(req.url, `http://${req.headers.host}`);
    const upstreamPath = targetPathname + urlObj.search;

    const options = {
      hostname: targetHost,
      port: targetPort,
      path: upstreamPath,
      method: req.method,
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
      },
    };

    const body = req.bodyRaw || '';
    if (body) options.headers['Content-Length'] = Buffer.byteLength(body);

    const client = targetProtocol === 'https:' ? https : http;
    options.agent = targetProtocol === 'https:' ? httpsKeepAliveAgent : httpKeepAliveAgent;

    const proxy = client.request(options, (upstream) => {
      console.log(`[${new Date().toLocaleTimeString()}] ← 上游查询 ${targetHost} 响应 HTTP ${upstream.statusCode}`);
      res.writeHead(upstream.statusCode, {
        'Content-Type': upstream.headers['content-type'] || 'application/json',
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
      });
      upstream.pipe(res);
    });

    proxy.on('error', (err) => {
      console.error('查询代理请求失败:', err.message);
      if (!res.headersSent) {
        res.writeHead(502, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: { message: `上游查询请求失败: ${err.message}` } }));
      }
    });

    if (body) proxy.write(body);
    proxy.end();
  });
}

module.exports = { register };
