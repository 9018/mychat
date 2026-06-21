// ── 轻量路由分发器（零依赖） ─────────────────────────────────────
// 支持 GET/POST/DELETE/ALL + 通配符匹配 + query string 解析

class Router {
  constructor() {
    this.routes = [];
  }

  _add(methods, pattern, handler) {
    // 特殊字符转义（wildcard * 除外）
    const escRE = (s) => s.replace(/[.+?^${}()|[\]\\]/g, '\\$&');

    let regexStr;
    if (pattern.endsWith('/*')) {
      // /v1/*  →  ^/v1/.*$  匹配前缀 + 任意子路径
      regexStr = '^' + escRE(pattern.slice(0, -2)) + '/.*$';
    } else if (pattern.endsWith('*')) {
      // /agnesapi*  →  ^/agnesapi.*$  匹配前缀 + 任意后续字符
      regexStr = '^' + escRE(pattern.slice(0, -1)) + '.*$';
    } else {
      // 精确匹配
      regexStr = '^' + escRE(pattern) + '$';
    }

    const regex = new RegExp(regexStr);
    this.routes.push({ methods, pattern, regex, handler });
  }

  get(pattern, handler) { this._add(['GET'], pattern, handler); }
  post(pattern, handler) { this._add(['POST'], pattern, handler); }
  delete(pattern, handler) { this._add(['DELETE'], pattern, handler); }
  all(pattern, handler) {
    this._add(['GET', 'POST', 'DELETE', 'PUT', 'PATCH', 'OPTIONS'], pattern, handler);
  }

  /**
   * 解析 URL query string
   */
  _parseQuery(url) {
    const idx = url.indexOf('?');
    if (idx === -1) return {};
    const qs = url.slice(idx + 1);
    const params = {};
    qs.split('&').forEach(pair => {
      if (!pair) return;
      const [key, ...valParts] = pair.split('=');
      params[decodeURIComponent(key)] = decodeURIComponent(valParts.join('=') || '');
    });
    return params;
  }

  /**
   * 处理请求
   * @returns {boolean} 是否匹配到路由
   */
  async handle(req, res, bodyRaw) {
    const method = req.method;
    const fullPath = req.url;

    const qIdx = fullPath.indexOf('?');
    const pathname = qIdx >= 0 ? fullPath.slice(0, qIdx) : fullPath;
    const query = this._parseQuery(fullPath);

    for (const route of this.routes) {
      if (!route.methods.includes(method)) continue;

      const match = pathname.match(route.regex);
      if (match) {
        req.query = query;
        req.pathname = pathname;
        req.bodyRaw = bodyRaw;
        try {
          await route.handler(req, res);
        } catch (err) {
          console.error(`路由错误 [${method} ${pathname}]:`, err);
          if (!res.headersSent) {
            res.writeHead(500, { 'Content-Type': 'application/json; charset=utf-8' });
            res.end(JSON.stringify({ error: `服务器内部错误: ${err.message}` }));
          }
        }
        return true;
      }
    }
    return false;
  }
}

module.exports = Router;
