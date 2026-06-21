// ── 上游耗时打点工具 ────────────────────────────────────────────────
/**
 * 创建延迟打点器
 * 对所有 /v1/* 请求都打点，让用户一眼看出瓶颈在「连接」「上游处理」还是「下游传输」。
 * 对 /v1/chat/completions 还会额外计算「首字节延迟 TTFB」与「首 chunk 延迟 TTFT」。
 */
function createLatencyTracker(upstreamHost, isChatCompletion = false) {
  return {
    t0: Date.now(),
    tSocketConnect: null,
    tFirstByte: null,
    tFirstChunk: null,
    socketReused: false,
    upstreamHost,
    isChatCompletion,

    onSocket(socket) {
      if (socket.connecting === false || socket.writable) {
        this.tSocketConnect = Date.now();
        this.socketReused = true;
      } else {
        socket.once('connect', () => {
          this.tSocketConnect = Date.now();
          this.socketReused = false;
        });
      }
    },

    onFirstByte(statusCode) {
      this.tFirstByte = Date.now();
      const ttfbMs = this.tFirstByte - this.t0;
      const connMs = this.tSocketConnect != null ? (this.tSocketConnect - this.t0) : null;
      const reuseTag = this.socketReused ? '(socket 复用)' : '(新建连接)';
      console.log(
        `[${new Date().toLocaleTimeString()}] ← 上游 ${this.upstreamHost} 响应 HTTP ${statusCode} · ` +
        `TTFB ${ttfbMs}ms · 连接 ${connMs != null ? connMs + 'ms' : 'N/A'} ${reuseTag}`
      );
    },

    onFirstChunk() {
      if (this.tFirstChunk == null) {
        this.tFirstChunk = Date.now();
        const ttftMs = this.tFirstChunk - this.t0;
        const headerToChunkMs = this.tFirstChunk - (this.tFirstByte || this.t0);
        if (this.isChatCompletion) {
          console.log(
            `  ⏱ 聊天 TTFT ${ttftMs}ms (header→chunk ${headerToChunkMs}ms)`
          );
        }
      }
    },

    onEnd() {
      const totalMs = Date.now() - this.t0;
      const ttft = this.tFirstChunk != null ? (this.tFirstChunk - this.t0) : null;
      const gen = this.tFirstChunk != null ? (Date.now() - this.tFirstChunk) : null;
      console.log(
        `  ⏱ 上游总耗时 ${totalMs}ms` +
        (ttft != null ? ` · TTFT ${ttft}ms · 生成阶段 ${gen}ms` : '')
      );
    }
  };
}

module.exports = { createLatencyTracker };
