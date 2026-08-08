// ── /v1/* → 上游反向代理 ───────────────────────────────────────
// 核心代理逻辑：动态 baseUrl、keepAlive、打点、流式 SSE 透传、错误分类处理
const https = require('https');
const http = require('http');
const path = require('path');
const os = require('os');
const { spawn } = require('child_process');
const fs = require('fs');
const { readJSON } = require('../lib/file-store');
const { getApiKeyFromEnv } = require('../lib/env-store');
const { httpsKeepAliveAgent, httpKeepAliveAgent } = require('../lib/keepalive-agent');
const { createLatencyTracker } = require('../lib/latency');

function getUpstreamProxy() {
  // 显性配置:env UPSTREAM_PROXY 优先,其次 config.json 的 upstreamProxy 字段
  const env = process.env.UPSTREAM_PROXY;
  if (env) return env.trim();
  const config = readJSON(path.join(__dirname, '..', '..', 'config.json'), {});
  return (config.upstreamProxy || '').trim();
}

// 有显式代理(本网络 10.0.1.108 只能经 socks5h://192.168.99.3:1080 访问)时,
// 转发交给 curl,保持流式 SSE 透传。
function proxyViaCurl(req, res, targetUrl, apiKey, bodyByteLen) {
  const proxyUrl = getUpstreamProxy();
  const hdrFile = path.join(os.tmpdir(), `gw-hdr-${Date.now()}-${Math.random().toString(36).slice(2)}.txt`);
  const args = ['-sS', '-N', '--proxy', proxyUrl, '-D', hdrFile, '-X', req.method,
    '-H', `Authorization: Bearer ${apiKey}`,
    '-H', 'Content-Type: application/json',
    '-H', `User-Agent: agnes-gateway/socks5-proxy`, '--max-time', '1100'];
  if (bodyByteLen > 0) args.push('--data-binary', '@-');
  args.push(targetUrl.href);

  const curl = spawn('curl', args, { stdio: ['pipe', 'pipe', 'inherit'] });
  let responded = false;
  const finish = (code, headers, stream) => {
    if (responded) return;
    responded = true;
    res.writeHead(code, headers);
    if (stream) stream.pipe(res);
  };
  curl.on('error', (err) => {
    if (!responded) {
      responded = true;
      res.writeHead(502, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: { message: `代理执行失败: ${err.message}` } }));
    }
  });
  curl.stdout.on('data', (chunk) => {
    if (responded) return;
    let status = 502;
    let ct = 'application/json';
    try {
      const txt = fs.readFileSync(hdrFile, 'utf8');
      const m = txt.match(/HTTP\/\d(?:\.\d)? (\d{3})/);
      if (m) status = parseInt(m[1], 10);
      const ctm = txt.match(/content-type:\s*([^\r\n]+)/i);
      if (ctm) ct = ctm[1].trim();
    } catch (e) {}
    const isStream = ct.includes('text/event-stream');
    if (isStream) {
      finish(status, { 'Content-Type': ct, 'Cache-Control': 'no-cache, no-transform', 'Connection': 'keep-alive', 'X-Accel-Buffering': 'no' }, null);
      res.write(chunk);
      curl.stdout.on('data', (c) => res.write(c));
      curl.stdout.on('end', () => res.end());
    } else {
      curl.stdout.pause();
      let body = chunk;
      const collect = (c) => { body = Buffer.concat([body, c]); };
      curl.stdout.on('data', collect);
      curl.stdout.on('end', () => {
        const text = body.toString('utf8');
        let out;
        if (status >= 400) {
          let parsed = null;
          try { parsed = JSON.parse(text); } catch (e) {}
          const msg = (parsed && (parsed.error?.message || parsed.message)) || text.slice(0, 300) || `(空响应) 上游 HTTP ${status}`;
          out = JSON.stringify({ error: { message: `上游错误: ${msg}` } });
        } else {
          out = text;
        }
        finish(status, { 'Content-Type': ct, 'Cache-Control': 'no-cache, no-store' }, null);
        res.end(out);
      });
      curl.stdout.resume();
    }
  });
  if (req.bodyRaw) curl.stdin.write(req.bodyRaw);
  curl.stdin.end();
  fs.unlink(hdrFile, () => {});
}

function register(router) {
  router.all('/v1/*', (req, res) => {
    let apiKey = req.headers['x-api-key'] || '';
    if (!apiKey) {
      apiKey = getApiKeyFromEnv();
    }

    const incomingUrl = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
    incomingUrl.searchParams.delete('_t');
    const cleanPath = incomingUrl.pathname + incomingUrl.search;

    let targetUrlStr = 'http://10.0.1.108:18901/v1';
    const config = readJSON(path.join(__dirname, '..', '..', 'config.json'), {});
    if (config.baseUrl) {
      targetUrlStr = config.baseUrl;
    }

    let targetUrl;
    try {
      targetUrl = new URL(targetUrlStr);
    } catch (err) {
      targetUrl = new URL('http://10.0.1.108:18901/v1');
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
      console.log(`[${new Date().toLocaleTimeString()}] → 上游 ${req.method} ${cleanPath} · 请求体 ${sizeKB} KB (${sizeMB} MB)`);
      if (bodyByteLen > 4 * 1024 * 1024) {
        console.warn(`  ⚠ 请求体超过 4 MB，可能触发上游网关的 body size 限制`);
      }
    }

    // 上游需经 SOCKS5 代理时才可用(10.0.1.108 网段) → 走 curl 转发(流式 SSE 兼容)
    if (getUpstreamProxy()) {
      targetUrl.pathname = targetUrl.pathname.replace(/\/$/, '') || '/v1';
      let up = targetUrl.href;
      const cleanPath2 = incomingUrl.pathname + incomingUrl.search;
      const cfgPath = targetUrl.pathname.replace(/\/$/, '');
      const uPath = (cfgPath && cfgPath !== '/v1')
        ? cfgPath + cleanPath2.replace(/^\/v1/, '')
        : cleanPath2;
      targetUrl.pathname = '/v1';
      up = new URL(uPath, targetUrl.href).href;
      proxyViaCurl(req, res, new URL(up), apiKey, bodyByteLen);
      return;
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
