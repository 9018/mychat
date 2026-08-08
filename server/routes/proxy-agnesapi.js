// ── /agnesapi/* → 上游反向代理 ──────────────────────────────────
const https = require('https');
const http = require('http');
const path = require('path');
const os = require('os');
const fs = require('fs');
const { spawn } = require('child_process');
const { readJSON } = require('../lib/file-store');
const { getApiKeyFromEnv } = require('../lib/env-store');
const { httpsKeepAliveAgent, httpKeepAliveAgent } = require('../lib/keepalive-agent');

function getUpstreamProxy() {
  const env = process.env.UPSTREAM_PROXY;
  if (env) return env.trim();
  const config = readJSON(path.join(__dirname, '..', '..', 'config.json'), {});
  return (config.upstreamProxy || '').trim();
}

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

    // 上游经显性 SOCKS5 代理访问时走 curl 转发
    const proxyUrl = getUpstreamProxy();
    if (proxyUrl) {
      const hdrFile = path.join(os.tmpdir(), `gw-agnes-hdr-${Date.now()}.txt`);
      const target = new URL(config.baseUrl || 'http://apihub.agnes-ai.com/agnesapi');
      const outgoing = `http://${target.hostname}${target.port ? ':' + target.port : ''}${upstreamPath === '/agnesapi' ? '/agnesapi' + urlObj.search : upstreamPath}`;
      const curl = spawn('curl', ['-sS', '--proxy', proxyUrl, '-D', hdrFile, '-X', req.method,
        '-H', `Authorization: Bearer ${apiKey}`, '-H', 'Content-Type: application/json',
        '--max-time', '300', outgoing], { stdio: ['ignore', 'pipe', 'inherit'] });
      let body = Buffer.alloc(0);
      curl.stdout.on('data', (c) => { body = Buffer.concat([body, c]); });
      curl.stdout.on('end', () => {
        let status = 502, ct = 'application/json';
        try {
          const txt = fs.readFileSync(hdrFile, 'utf8');
          const m = txt.match(/HTTP\/\d(?:\.\d)? (\d{3})/);
          if (m) status = parseInt(m[1], 10);
          const ctm = txt.match(/content-type:\s*([^\r\n]+)/i);
          if (ctm) ct = ctm[1].trim();
        } catch (e) {}
        fs.unlink(hdrFile, () => {});
        res.writeHead(status, { 'Content-Type': ct, 'Cache-Control': 'no-cache, no-store' });
        res.end(body);
      });
      curl.on('error', (err) => {
        if (!res.headersSent) {
          res.writeHead(502, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ error: { message: `代理执行失败: ${err.message}` } }));
        } else res.destroy();
      });
      return;
    }

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
