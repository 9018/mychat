@echo off
rem Agnes AI Gateway · 启动脚本 (Windows)
rem 端口范围 12301-12305
set PORT=12301
if exist "frontend\dist\index.html" (
  echo 生产模式：前端构建产物已就绪
  set NODE_ENV=production
) else (
  echo 开发模式：请另开终端执行 cd frontend ^&^& npm run dev
)
node server/index.js
pause
