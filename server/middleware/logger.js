// ── 请求日志中间件 ───────────────────────────────────────────
function logger(req, res) {
  console.log(`[${new Date().toLocaleTimeString()}] ${req.method} ${req.url}`);
}

module.exports = { logger };
