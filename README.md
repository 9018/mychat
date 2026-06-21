# Agnes AI Gateway · 控制台

前后端分离的 AI 网关管理面板，调用 AI API 提供**视频/图像/对话**生成能力，专为国内网络环境优化（自带视频反向代理）。

---

## 快速启动

```bash
# 生产模式（后端托管前端）
cd frontend && npm run build && cd ..
./start.sh

# 开发模式（前后端分别启动）
node server/index.js                    # 终端 1：后端 (端口 12301)
cd frontend && npm install && npm run dev  # 终端 2：前端 (端口 5173)
```

> 生产模式默认端口 **12301**，可通过 `PORT` 环境变量修改。

---

## 功能

| 功能 | 说明 |
|------|------|
| **视频生成** | 文生视频 / 图生视频 / 多图视频 / 关键帧动画（异步 + 轮询） |
| **图像生成** | 文生图 / 图生图 / 构图保留 / 高密度优化（同步） |
| **对话** | 多模型 SSE 流式对话，支持图片/音频/视频/通用文件上传 |
| **素材分析** | ChatGPT 联动工作流：分析素材 → 生成 Prompt → 批量生图 |
| **历史记录** | 最近生成记录，含缩略图预览，单条删除 |
| **外观微调** | 暗色/亮色主题、密度、缩放、6 种强调色 |

---

## 项目结构

```
├── server/                     # 后端（零依赖 Node.js）
│   ├── index.js               # 入口 — HTTP 服务 + 路由挂载
│   ├── router.js              # 轻量路由分发器
│   ├── middleware/             # body-parser, cors, logger
│   ├── routes/                 # 8 个功能路由
│   │   ├── api-key.js          # API Key 读写
│   │   ├── config.js           # 配置读写
│   │   ├── history.js          # 历史记录 CRUD + 媒体缓存
│   │   ├── material.js         # 素材分析配置/Prompt
│   │   ├── video-proxy.js      # 视频代理（破除中国防火墙）
│   │   ├── proxy-v1.js         # /v1/* → 上游 AI API 反向代理
│   │   ├── proxy-agnesapi.js   # /agnesapi/* → 上游查询代理
│   │   └── static.js           # outputs/ 静态文件服务
│   └── lib/                    # 工具库
│       ├── keepalive-agent.js   # HTTPS 连接复用
│       ├── env-store.js         # .env 读写
│       ├── file-store.js        # JSON 文件 + 媒体下载
│       └── latency.js           # TTFB/TTFT 打点
├── frontend/                   # React SPA（Vite + TypeScript）
│   ├── src/
│   │   ├── api/                # HTTP 客户端 + 类型定义
│   │   ├── contexts/           # Config, Key, Tweaks, History
│   │   ├── hooks/              # usePolling, useSSEChat, useLocalStorage
│   │   ├── components/         # Layout / common / History
│   │   ├── pages/              # Video / Image / Chat / Admin / Material
│   │   └── styles/             # 全局 CSS（OKLCH 主题 + 响应式）
│   └── vite.config.ts          # 开发代理 → localhost:12301
├── config.json                 # 模型列表、默认模型、baseUrl
├── .env                        # API Key（AGNES_API_KEY）
├── outputs/                    # 本地缓存媒体文件
├── start.sh                    # Linux/macOS 启动脚本
└── start.bat                   # Windows 启动脚本
```

---

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 控制台页面（SPA） |
| GET/POST | `/api/key` | 读写 API Key |
| GET/POST | `/api/config` | 读写用户配置 |
| GET/POST/DELETE | `/api/history` | 历史记录 |
| GET/POST | `/api/material/config` | 素材分析模板 |
| GET/POST/DELETE | `/api/material/prompts` | 素材分析 Prompt |
| GET | `/video-proxy?url=` | 视频代理中转 |
| * | `/v1/*` | AI API 反向代理 |
| * | `/agnesapi/*` | 视频状态查询代理 |
| GET | `/outputs/*` | 本地缓存媒体 |

---

## 技术要点

- **后端零依赖**：纯 Node.js `http` 模块，无需 `npm install`
- **连接复用**：自定义 `keepAliveAgent`（30s timeout、32 sockets、LIFO）
- **延迟打点**：每个上游请求自动记录 TTFB、TTFT、连接复用、总耗时
- **错误分类**：401（Key 无效）、服务端临时错误（自动重试）、网络错误
- **SSE 透传**：聊天流式响应直接透传，前端增量接收 token
- **移动端适配**：`@media (max-width: 768px)` 隐藏导航栏，显示底部导航
- **主题系统**：OKLCH 色彩空间、6 种强调色、密度/缩放调节

---

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `PORT` | `12301` | 监听端口 |
| `HOST` | `0.0.0.0` | 监听地址 |
