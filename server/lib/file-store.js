// ── JSON 文件读写 + 媒体下载/清理 ──────────────────────────────────
const fs = require('fs');
const path = require('path');
const https = require('https');
const http = require('http');
const { httpsKeepAliveAgent, httpKeepAliveAgent } = require('./keepalive-agent');

const OUTPUTS_DIR = path.join(__dirname, '..', '..', 'outputs');
if (!fs.existsSync(OUTPUTS_DIR)) {
  fs.mkdirSync(OUTPUTS_DIR, { recursive: true });
}

/** 读取并解析 JSON 文件，不存在或解析失败返回默认值 */
function readJSON(filePath, defaultValue = null) {
  if (fs.existsSync(filePath)) {
    try {
      return JSON.parse(fs.readFileSync(filePath, 'utf8'));
    } catch (e) {
      console.warn(`文件 ${path.basename(filePath)} 解析失败:`, e.message);
    }
  }
  return defaultValue;
}

/** 写入 JSON 文件 */
function writeJSON(filePath, data) {
  fs.writeFileSync(filePath, JSON.stringify(data, null, 2), 'utf8');
}

/**
 * 下载远程资源到本地 outputs/ 目录
 * @returns {string|null} 本地路径（/outputs/filename），失败返回 null
 */
function downloadMedia(rawUrl, kind = 'image') {
  const ext = kind === 'video' ? 'mp4' : 'png';
  const filename = `${Date.now()}_${Math.floor(Math.random() * 1000)}.${ext}`;
  const destPath = path.join(OUTPUTS_DIR, filename);

  if (rawUrl.startsWith('data:')) {
    const base64Data = rawUrl.replace(/^data:image\/\w+;base64,/, '');
    const buf = Buffer.from(base64Data, 'base64');
    fs.writeFileSync(destPath, buf);
    return `/outputs/${filename}`;
  }

  // 远程 URL 下载
  try {
    const client = rawUrl.startsWith('https') ? https : http;
    const agent = rawUrl.startsWith('https') ? httpsKeepAliveAgent : httpKeepAliveAgent;
    return new Promise((resolve) => {
      client.get(rawUrl, { agent }, (response) => {
        if (response.statusCode !== 200) {
          console.error(`下载媒体失败: HTTP ${response.statusCode}`);
          resolve(null);
          return;
        }
        const file = fs.createWriteStream(destPath);
        response.pipe(file);
        file.on('finish', () => {
          file.close();
          resolve(`/outputs/${filename}`);
        });
        file.on('error', () => resolve(null));
      }).on('error', (err) => {
        console.error('下载远程资源失败:', err.message);
        resolve(null);
      });
    });
  } catch (err) {
    console.error('下载远程资源失败:', err.message);
    return null;
  }
}

/** 删除本地媒体文件 */
function removeMedia(filename) {
  if (!filename) return;
  const remPath = path.join(OUTPUTS_DIR, filename);
  if (fs.existsSync(remPath)) {
    try {
      fs.unlinkSync(remPath);
    } catch (err) {
      console.error('物理文件删除失败:', err.message);
    }
  }
}

module.exports = { readJSON, writeJSON, downloadMedia, removeMedia, OUTPUTS_DIR };
