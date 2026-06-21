// ── .env 读写（API Key 持久化） ─────────────────────────────────────
const fs = require('fs');
const path = require('path');

const ENV_PATH = path.join(__dirname, '..', '..', '.env');

function getApiKeyFromEnv() {
  let apiKey = '';
  if (fs.existsSync(ENV_PATH)) {
    const content = fs.readFileSync(ENV_PATH, 'utf8');
    const match = content.match(/AGNES_API_KEY\s*=\s*([^\r\n]+)/);
    if (match) {
      apiKey = match[1].trim();
    }
  }
  // 兼容旧版 key.txt 并迁移
  if (!apiKey) {
    const keyPath = path.join(__dirname, '..', '..', 'key.txt');
    if (fs.existsSync(keyPath)) {
      apiKey = fs.readFileSync(keyPath, 'utf8').trim();
      if (apiKey) {
        saveApiKeyToEnv(apiKey);
      }
    }
  }
  return apiKey;
}

function saveApiKeyToEnv(apiKey) {
  let content = '';
  if (fs.existsSync(ENV_PATH)) {
    content = fs.readFileSync(ENV_PATH, 'utf8');
  }

  if (content.includes('AGNES_API_KEY=')) {
    content = content.replace(/AGNES_API_KEY\s*=\s*[^\r\n]*/, `AGNES_API_KEY=${apiKey}`);
  } else {
    content += (content.endsWith('\n') || content === '' ? '' : '\n') + `AGNES_API_KEY=${apiKey}\n`;
  }
  fs.writeFileSync(ENV_PATH, content, 'utf8');

  // 删除 key.txt
  const keyPath = path.join(__dirname, '..', '..', 'key.txt');
  if (fs.existsSync(keyPath)) {
    try {
      fs.unlinkSync(keyPath);
    } catch (e) {
      console.error('删除 key.txt 失败:', e.message);
    }
  }
}

module.exports = { getApiKeyFromEnv, saveApiKeyToEnv, ENV_PATH };
