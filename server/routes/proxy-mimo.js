// ── /mimo/* → api.xiaomimimo.com 反向代理（MiMo TTS API） ───
const https = require('https');
const path = require('path');
const { httpsKeepAliveAgent } = require('../lib/keepalive-agent');

const UPSTREAM = 'api.xiaomimimo.com';
const agent = httpsKeepAliveAgent;

function getMimoApiKey() {
  try {
    const fs = require('fs');
    const envPath = path.join(__dirname, '..', '..', '.env');
    if (fs.existsSync(envPath)) {
      const content = fs.readFileSync(envPath, 'utf8');
      const match = content.match(/MIMO_API_KEY\s*=\s*([^\r\n]+)/);
      if (match) return match[1].trim();
    }
  } catch {}
  return process.env.MIMO_API_KEY || '';
}

function register(router) {
  router.all('/mimo/*', (req, res) => {
    const apiKey = getMimoApiKey();
    if (!apiKey) {
      res.writeHead(401, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ error: 'MIMO API key not configured. Set your MIMO_API_KEY in Settings or .env.' }));
      return;
    }

    // Rewrite path: /mimo/v1/chat/completions → /v1/chat/completions
    const incomingUrl = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
    const cleanPath = incomingUrl.pathname.replace(/^\/mimo/, '') + incomingUrl.search;

    const options = {
      hostname: UPSTREAM,
      path: cleanPath,
      method: req.method,
      headers: {
        'api-key': apiKey,
        'Content-Type': 'application/json',
      },
      agent,
    };

    const bodyLen = req.bodyRaw ? Buffer.byteLength(req.bodyRaw) : 0;
    if (bodyLen > 0) options.headers['Content-Length'] = bodyLen;

    const proxyReq = https.request(options, (proxyRes) => {
      const contentType = proxyRes.headers['content-type'] || '';
      const isStream = contentType.includes('text/event-stream');

      if (isStream && proxyRes.statusCode >= 200 && proxyRes.statusCode < 300) {
        res.writeHead(proxyRes.statusCode, {
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache, no-transform',
          'Connection': 'keep-alive',
          'X-Accel-Buffering': 'no',
        });
        proxyRes.pipe(res);
        return;
      }

      let body = '';
      proxyRes.on('data', chunk => { body += chunk; });
      proxyRes.on('end', () => {
        res.writeHead(proxyRes.statusCode, {
          'Content-Type': proxyRes.headers['content-type'] || 'application/json; charset=utf-8',
        });
        res.end(body);
      });
    });

    proxyReq.on('error', (e) => {
      console.error('MIMO proxy error:', e.message);
      if (!res.headersSent) {
        res.writeHead(502, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'MIMO upstream proxy error: ' + e.message }));
      }
    });

    if (req.bodyRaw) proxyReq.write(req.bodyRaw);
    proxyReq.end();
  });
}

module.exports = { register };
