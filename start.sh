#!/bin/bash
# Agnes AI Gateway · 启动脚本
# 端口范围 12301-12305

cd "$(dirname "$0")"
PORT=${PORT:-12301}
echo "  Agnes AI Gateway · 正在启动 (端口 ${PORT})"
echo "  ================="

if [ -d "frontend/dist" ] && [ -f "frontend/dist/index.html" ]; then
  echo "  生产模式：前端构建产物已就绪"
  PORT=$PORT NODE_ENV=production node server/index.js
else
  echo "  开发模式：请另开终端执行 cd frontend && npm run dev"
  echo ""
  PORT=$PORT node server/index.js
fi
