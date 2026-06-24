#!/usr/bin/env node
// ── 服务器入口 ──────────────────────────────────────────────────
// 聚合中间件、注册路由、启动 HTTP 服务

const http = require('http');
const https = require('https');
const fs = require('fs');
const path = require('path');

const Router = require('./router');
const { parseBody } = require('./middleware/body-parser');
const { setCorsHeaders, handlePreflight } = require('./middleware/cors');
const { logger } = require('./middleware/logger');

// ── 注册路由 ──────────────────────────────────────────────────────
const router = new Router();

require('./routes/api-key').register(router);
require('./routes/config').register(router);
require('./routes/history').register(router);
require('./routes/material').register(router);
require('./routes/chat').register(router);
require('./routes/static').register(router);
require('./routes/video-proxy').register(router);
require('./routes/proxy-agnesapi').register(router);
require('./routes/proxy-v1').register(router);
// MiMo TTS routes
require('./routes/mimo-key').register(router);
require('./routes/proxy-mimo').register(router);

// ── 生产模式：托管前端构建产物 ──────────────────────────────────
const DIST_DIR = path.join(__dirname, '..', 'frontend', 'dist');
function serveFrontend(req, res) {
  // 只对 GET 请求托管 SPA
  if (req.method !== 'GET') return false;

  // 跳过 API 和静态文件路径
  if (req.url.startsWith('/api/') || req.url.startsWith('/v1/') ||
      req.url.startsWith('/mimo/') || req.url.startsWith('/agnesapi') ||
      req.url.startsWith('/video-proxy') || req.url.startsWith('/outputs/')) {
    return false;
  }

  if (!fs.existsSync(DIST_DIR)) return false;

  // SPA fallback：对于非文件请求，返回 index.html
  let filePath = path.join(DIST_DIR, req.url === '/' ? 'index.html' : req.url);
  if (!fs.existsSync(filePath)) {
    filePath = path.join(DIST_DIR, 'index.html');
  }

  const ext = path.extname(filePath).toLowerCase();
  const contentTypeMap = {
    '.html': 'text/html; charset=utf-8',
    '.js': 'application/javascript; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.json': 'application/json',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.svg': 'image/svg+xml',
    '.ico': 'image/x-icon',
    '.woff': 'font/woff',
    '.woff2': 'font/woff2',
  };

  if (fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
    res.writeHead(200, { 'Content-Type': contentTypeMap[ext] || 'application/octet-stream', 'Cache-Control': 'public, max-age=0, must-revalidate' });
    fs.createReadStream(filePath).pipe(res);
    return true;
  }
  return false;
}

// ── 创建 HTTP 服务 ──────────────────────────────────────────────
const SSL_PORT = process.env.SSL_PORT || 12300;
const PORT = process.env.PORT || 12301;
const HOST = process.env.HOST || '0.0.0.0';
const sslOptions = {
  key: fs.readFileSync(path.join(__dirname, 'ssl', 'key.pem')),
  cert: fs.readFileSync(path.join(__dirname, 'ssl', 'cert.pem')),
};

const server = http.createServer(async (req, res) => {
  // 1. 请求日志
  logger(req, res);

  // 2. CORS
  setCorsHeaders(res);
  if (handlePreflight(req, res)) return;

  // 3. 解析请求体
  try {
    await parseBody(req);
  } catch (err) {
    res.writeHead(400, { 'Content-Type': 'application/json; charset=utf-8' });
    res.end(JSON.stringify({ error: `请求体解析失败: ${err.message}` }));
    return;
  }

  // 4. 收集原始 body（给代理路由用）
  let bodyRaw = '';
  if (req.method === 'POST' || req.method === 'PUT' || req.method === 'PATCH') {
    bodyRaw = JSON.stringify(req.body);
  }

  // 5. 尝试匹配 API 路由
  const matched = await router.handle(req, res, bodyRaw);
  if (matched) return;

  // 6. 尝试托管前端 SPA（仅生产模式）
  if (serveFrontend(req, res)) return;

  // 7. 404
  res.writeHead(404);
  res.end('Not found');
});

server.on('error', (err) => {
  if (err.code === 'EADDRINUSE') {
    console.error(`\n[提示] 端口 ${PORT} 已被占用，服务器似乎已经在运行中。`);
    console.error(`请直接在浏览器中打开: http://localhost:${PORT}`);
    console.error(`如果需要重新启动，请先关闭正在运行的终端或杀死占用该端口的 Node 进程。\n`);
    process.exit(1);
  } else {
    console.error('服务器启动失败:', err);
  }
});

server.listen(PORT, HOST, () => {
  const mode = process.env.NODE_ENV === 'production' ? '生产模式' : '开发模式';
  console.log(`\n  Agnes AI Gateway · 后端服务已启动 (${mode})`);
  console.log(`  监听地址: http://localhost:${PORT}\n`);
});


// ── HTTPS 服务（自签名证书，用于麦克风录音） ──────────────────
try {
  https.createServer(sslOptions, async (req, res) => {
    logger(req, res);
    setCorsHeaders(res);
    if (handlePreflight(req, res)) return;
    try { await parseBody(req); } catch (err) {
      res.writeHead(400, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ error: `请求体解析失败: ${err.message}` }));
      return;
    }
    let bodyRaw = "";
    if (req.method === 'POST' || req.method === 'PUT' || req.method === 'PATCH') {
      bodyRaw = JSON.stringify(req.body);
    }
    const matched = await router.handle(req, res, bodyRaw);
    if (matched) return;
    if (serveFrontend(req, res)) return;
    res.writeHead(404);
    res.end('Not found');
  }).listen(SSL_PORT, HOST, () => {
    console.log(`  HTTPS:  https://localhost:${SSL_PORT}/`);
  });
} catch (err) {
  console.error('[警告] HTTPS 服务启动失败（不影响 HTTP）:', err.message);
}

module.exports = server;
