// ── /v1/* → 上游反向代理 ───────────────────────────────────────
// 核心代理逻辑：动态 baseUrl、keepAlive、打点、流式 SSE 透传、错误分类处理
const https = require('https');
const http = require('http');
const path = require('path');
const { readJSON } = require('../lib/file-store');
const { getApiKeyFromEnv } = require('../lib/env-store');
const { httpsKeepAliveAgent, httpKeepAliveAgent } = require('../lib/keepalive-agent');
const { createLatencyTracker } = require('../lib/latency');

function register(router) {
  router.all('/v1/*', (req, res) => {
    let apiKey = req.headers['x-api-key'] || '';
    if (!apiKey) {
      apiKey = getApiKeyFromEnv();
    }

    const incomingUrl = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
    incomingUrl.searchParams.delete('_t');
    const cleanPath = incomingUrl.pathname + incomingUrl.search;

    let targetUrlStr = 'https://apihub.agnes-ai.com/v1';
    const config = readJSON(path.join(__dirname, '..', '..', 'config.json'), {});
    if (config.baseUrl) {
      targetUrlStr = config.baseUrl;
    }

    let targetUrl;
    try {
      targetUrl = new URL(targetUrlStr);
    } catch (err) {
      targetUrl = new URL('https://apihub.agnes-ai.com/v1');
    }

    let upstreamPath = cleanPath;
    const configPathName = targetUrl.pathname.replace(/\/$/, '');
    if (configPathName && configPathName !== '/v1') {
      upstreamPath = configPathName + cleanPath.replace(/^\/v1/, '');
    }

    const bodyByteLen = req.bodyRaw ? Buffer.byteLength(req.bodyRaw) : 0;

    if (req.method === 'POST' && bodyByteLen > 0) {
      const sizeKB = (bodyByteLen / 1024).toFixed(1);
      const sizeMB = (bodyByteLen / 1024 / 1024).toFixed(2);
      console.log(`[${new Date().toLocaleTimeString()}] → 上游 ${req.method} ${upstreamPath} · 请求体 ${sizeKB} KB (${sizeMB} MB)`);
      if (bodyByteLen > 4 * 1024 * 1024) {
        console.warn(`  ⚠ 请求体超过 4 MB，可能触发上游网关的 body size 限制`);
      }
    }

    const options = {
      hostname: targetUrl.hostname,
      port: targetUrl.port || (targetUrl.protocol === 'https:' ? 443 : 80),
      path: upstreamPath,
      method: req.method,
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
      },
    };
    if (bodyByteLen > 0) options.headers['Content-Length'] = bodyByteLen;

    const client = targetUrl.protocol === 'https:' ? https : http;
    options.agent = targetUrl.protocol === 'https:' ? httpsKeepAliveAgent : httpKeepAliveAgent;

    const isChatCompletion = upstreamPath.includes('/chat/completions');
    const tracker = createLatencyTracker(targetUrl.hostname, isChatCompletion);

    const proxy = client.request(options, (upstream) => {
      tracker.onFirstByte(upstream.statusCode);

      const upstreamCT = (upstream.headers['content-type'] || '').toLowerCase();
      const isStream = upstreamCT.includes('text/event-stream');

      upstream.once('data', () => tracker.onFirstChunk());
      upstream.once('end', () => tracker.onEnd());

      if (isStream && upstream.statusCode >= 200 && upstream.statusCode < 300) {
        res.writeHead(upstream.statusCode, {
          'Content-Type': upstream.headers['content-type'],
          'Cache-Control': 'no-cache, no-transform',
          'Connection': 'keep-alive',
          'X-Accel-Buffering': 'no',
        });
        upstream.pipe(res);
        return;
      }

      let respBody = '';
      upstream.on('data', chunk => { respBody += chunk; });

      if (upstream.statusCode < 200 || upstream.statusCode >= 300) {
        upstream.on('end', () => {
          console.log(`[${new Date().toLocaleTimeString()}] 上游接口返回数据:`, respBody.slice(0, 500));
          let parsed;
          try { parsed = JSON.parse(respBody); } catch { parsed = null; }

          res.writeHead(upstream.statusCode, {
            'Content-Type': 'application/json; charset=utf-8',
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
          });

          if (upstream.statusCode === 401) {
            res.end(JSON.stringify({ error: { message: 'API Key 无效或已过期，请检查并重新输入。' } }));
          } else if (parsed && parsed.error) {
            const msg = parsed.error.message || parsed.error;
            res.end(JSON.stringify({ error: { message: `上游错误: ${msg}` } }));
          } else if (parsed && parsed.message) {
            res.end(JSON.stringify({ error: { message: `上游错误: ${parsed.message}` } }));
          } else {
            const isEmpty = !respBody;
            const isOverloaded = upstream.statusCode === 503 || upstream.statusCode === 413 || upstream.statusCode === 502;
            let summary = respBody ? respBody.slice(0, 300) : `(空响应)`;
            if (isEmpty && isOverloaded && bodyByteLen > 1024 * 1024) {
              const sizeMB = (bodyByteLen / 1024 / 1024).toFixed(2);
              summary = `(空响应，请求体 ${sizeMB} MB) — 上游网关可能因请求体过大而中断，建议改用图片 URL 或更小尺寸的参考图`;
            } else if (isEmpty && isOverloaded) {
              summary = `(空响应) — 上游服务暂时繁忙，稍后将自动重试`;
            }
            res.end(JSON.stringify({ error: { message: `上游返回 HTTP ${upstream.statusCode}: ${summary}` } }));
          }
        });
        return;
      }

      upstream.on('end', () => {
        console.log(`[${new Date().toLocaleTimeString()}] 上游接口返回数据:`, respBody.slice(0, 500));
      });

      res.writeHead(upstream.statusCode, {
        'Content-Type': upstream.headers['content-type'] || 'application/json',
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
      });
      upstream.pipe(res);
    });

    proxy.on('error', (err) => {
      console.error('代理请求失败:', err.message);
      try {
        const fs = require('fs');
        const errorLogPath = path.join(__dirname, '..', '..', 'outputs', 'error.log');
        fs.writeFileSync(errorLogPath, `${new Date().toISOString()} [Proxy Error] ${err.stack}\n`, { flag: 'a' });
      } catch (e) {}
      if (res.headersSent) {
        res.destroy();
        return;
      }
      res.writeHead(502, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: { message: `上游请求失败: ${err.message}` } }));
    });

    proxy.on('socket', (socket) => tracker.onSocket(socket));

    if (req.bodyRaw) proxy.write(req.bodyRaw);
    proxy.end();
  });
}

module.exports = { register };
