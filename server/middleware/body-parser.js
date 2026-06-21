// ── JSON 请求体解析中间件 ─────────────────────────────────────
const { Writable } = require('stream');

/**
 * 解析 JSON body，挂载到 req.body
 * 仅在 Content-Type 为 application/json 时生效
 */
function parseBody(req) {
  return new Promise((resolve, reject) => {
    if (req.method === 'GET' || req.method === 'DELETE') {
      req.body = {};
      return resolve();
    }

    const contentType = req.headers['content-type'] || '';
    if (!contentType.includes('application/json')) {
      req.body = {};
      return resolve();
    }

    let body = '';
    req.on('data', chunk => { body += chunk; });
    req.on('end', () => {
      try {
        req.body = body ? JSON.parse(body) : {};
        resolve();
      } catch (err) {
        reject(err);
      }
    });
    req.on('error', reject);
  });
}

module.exports = { parseBody };
