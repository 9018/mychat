// ── 上游连接复用 ──────────────────────────────────────────────────
// 默认 https.globalAgent 每次请求都会新建 socket（TLS 握手 ~150-400 ms）。
// 用自定义 Agent 开启 keepAlive，多轮对话/轮询能复用同一条连接，省下握手时间。
const https = require('https');
const http = require('http');

const httpsKeepAliveAgent = new https.Agent({
  keepAlive: true,
  keepAliveMsecs: 30 * 1000,  // 30s 内复用 socket
  maxSockets: 32,             // 单主机最大并发
  scheduling: 'lifo',         // 偏好最近使用的连接（命中缓存几率更高）
});

const httpKeepAliveAgent = new http.Agent({
  keepAlive: true,
  keepAliveMsecs: 30 * 1000,
  maxSockets: 32,
  scheduling: 'lifo',
});

module.exports = { httpsKeepAliveAgent, httpKeepAliveAgent };
