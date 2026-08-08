# CLAUDE.md

This file provides guidance to Claude when working with code in this repository.

## Project Overview

A frontend-backend separated AI Gateway dashboard for the **Agnes AI** platform, exposing video generation, image generation, and chat capabilities through a modular, zero-dependency Node.js backend and a React SPA frontend.

## Structure

```
├── server/                   # Backend (zero-dependency Node.js)
│   ├── index.js              # Entry point — creates HTTP server, mounts router
│   ├── router.js             # Lightweight route dispatcher (GET/POST/DELETE/ALL + wildcards)
│   ├── middleware/
│   │   ├── logger.js         # Request logging
│   │   ├── body-parser.js    # JSON body parsing
│   │   └── cors.js           # CORS headers + preflight
│   ├── routes/
│   │   ├── api-key.js        # GET/POST /api/key
│   │   ├── config.js         # GET/POST /api/config
│   │   ├── history.js        # GET/POST/DELETE /api/history
│   │   ├── material.js       # Material analysis config/prompts/history
│   │   ├── video-proxy.js    # GET /video-proxy?url= (bypasses firewall)
│   │   ├── proxy-v1.js       # * /v1/* → upstream reverse proxy (with keepAlive, latency, SSE)
│   │   ├── proxy-agnesapi.js # * /agnesapi/* → upstream reverse proxy
│   │   └── static.js         # GET /outputs/* — serve generated media
│   └── lib/
│       ├── keepalive-agent.js   # httpsKeepAliveAgent / httpKeepAliveAgent
│       ├── env-store.js         # .env read/write (API Key)
│       ├── file-store.js        # JSON file read/write + media download/cleanup
│       └── latency.js           # TTFB / TTFT / connection time tracking
├── frontend/                 # React SPA (Vite + TypeScript)
│   ├── src/
│   │   ├── api/              # HTTP client + per-domain API modules (client, key, config, history, material, types)
│   │   ├── contexts/         # React Contexts (Config, Key, Tweaks, History)
│   │   ├── hooks/            # Custom hooks (usePolling, useSSEChat, useLocalStorage)
│   │   ├── components/
│   │   │   ├── Layout/       # NavRail, TopBar, TweaksPanel
│   │   │   ├── common/       # AspectPicker, StatusCard, Toast, ModelSelect, ImageUploader, Spinner
│   │   │   └── History/      # HistoryStrip
│   │   ├── pages/            # VideoPage, ImagePage, ChatPage, AdminPage, MaterialPage
│   │   └── styles/           # global.css (theme variables, base styles)
│   ├── vite.config.ts        # Dev proxy: /api → localhost:3000
│   └── package.json
├── config.json               # App config (model list, baseUrl, defaults)
├── .env                      # AGNES_API_KEY
├── outputs/                  # Locally cached generated media
├── index.html                # (legacy monolith, kept for reference)
├── server.js                 # (legacy monolith, kept for reference)
├── start.sh                  # Production mode launcher
└── start.bat                 # Windows launcher
```

## How to Run

### Production (backend serves built frontend)

```bash
cd frontend && npm run build && cd ..
NODE_ENV=production node server/index.js
# Open http://localhost:3000
```

Or simply `./start.sh` (auto-detects dist/).

### Development (Vite dev server + backend)

```bash
# Terminal 1: Backend
node server/index.js

# Terminal 2: Frontend dev server
cd frontend && npm install && npm run dev
# Open http://localhost:5173 (Vite proxies /api to backend)
```

## Architecture Overview

### Backend — Modular Route Handlers

The `server/router.js` implements a lightweight dispatcher supporting GET/POST/DELETE/ALL methods with wildcard path matching. Routes are registered in `server/index.js`:

```
require('./routes/api-key').register(router)
require('./routes/config').register(router)
// ... etc.
```

Key features preserved from the original monolith:
- Custom keepAlive agents (30s timeout, 32 max sockets, LIFO) for upstream connection reuse
- Full latency instrumentation (connection time, TTFB, TTFT, generation phase)
- SSE streaming passthrough for chat completions
- Automatic body-size warnings (>4MB triggers upstream 413/503 risk)
- Error classification (401 auth, server temp errors, network errors)
- Video proxy bypasses `storage.googleapis.com` firewall restrictions

### Frontend — React SPA with Context + Hooks

Component hierarchy:
- `App.tsx` wraps providers (Tweaks > Config > Key > History)
- `AppContent` renders NavRail + TopBar + content area based on active tab
- Pages are conditionally rendered (no router library needed): `{activeTab === 'video' && <VideoPage />}`
- State management via React Context: `ConfigContext`, `KeyContext`, `TweaksContext`, `HistoryContext`
- Custom hooks encapsulate complex logic:
  - `usePolling` — async video task polling with retry/backoff
  - `useSSEChat` — SSE streaming chat with TTFT metrics
  - `useLocalStorage` — typed localStorage wrapper

### API Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/api/key` | Read API Key from .env |
| POST | `/api/key` | Save API Key to .env |
| GET/POST | `/api/config` | Config.json CRUD |
| GET/POST/DELETE | `/api/history` | Generation history with media caching |
| * | `/api/material/*` | Material analysis CRUD |
| GET | `/video-proxy?url=` | Video proxy for Google Cloud Storage (firewall bypass) |
| * | `/v1/*` | Reverse proxy to AI API (with Bearer token + keepAlive) |
| * | `/agnesapi/*` | Reverse proxy for video status queries |
| GET | `/outputs/*` | Static file serving for cached media |

In **production mode** (`NODE_ENV=production`), the backend also serves `frontend/dist/` as static SPA.

### Key Design Decisions

- **Zero-dependency backend**: Pure Node.js `http` module, avoiding npm install for the server
- **React + Vite frontend**: Modern development experience with TypeScript, HMR, and fast builds
- **No router library**: Tab switching via conditional rendering (`activeTab === 'x' && <Page />`)
- **No state management library**: React Context + useReducer sufficient for this complexity level
- **TypeScript interfaces** in `src/api/types.ts` shared across all frontend modules
- **Vite proxy** in development: all `/api/*`, `/v1/*`, `/agnesapi/*` requests forwarded to backend

---

## Vox Director 自有 AI 视频导演流水线(2026-08-08 改造标准)

`vox-director/` 是从 [9018/vox-director](https://github.com/9018/vox-director)(fork 自 Alisa0808,Atlas Cloud 版)改造而来的**自有流水线**:不做 Atlas 兼容,媒体调用全部改为走本项目的 **自托管 OpenAI 兼容网关**(newapi)。

### 网关连接(与网关面板共用;网络均为显性配置,无硬编码猜测)

```
OPENAI_API_KEY  = AGNES_API_KEY(见 .env,即网关 sk- 密钥;新网关 10.0.1.108:18901 与该 key 互通)
OPENAI_BASE_URL = http://10.0.1.108:18901/v1   (ai_cloud.py 默认值)
UPSTREAM_PROXY  = socks5h://192.168.99.3:1080  (必需:10.0.1.108 网段只能经此 SOCKS5 访问;
                   后端读 config.json 的 upstreamProxy 或 env,转发走 curl)
GROK2API_BASE   = http://10.0.1.108:8000       (grok-imagine-* 媒体服务,无默认)
GROK2API_KEY    = g2a_...(Grok2API 控制台签发的 Client Key,无默认)
```

> 注:192.168.99.4:18901 网关已弃用。Grok2API 管理端点(经 login 会话)从 JS bundle
> 反查得 `/api/admin/v1/auth/login`、`/api/admin/v1/client-keys`;媒体下载为
> `/v1/media/images/<id>` + `Authorization: Bearer <client-key>`。

### 模型映射(2026-08-08 对网关逐 endpoint 实测)

| 流水线阶段 | 模型 | 实测状态 |
|---|---|---|
| 剧本 / beats 规划 | `deepseek-v4-flash-free` / `agnes-2.0-flash` | ✅(mimo-v2.5-free 可用,内容在 reasoning) |
| 拼贴海报关键帧 | `agnes-image-2.1-flash` | ✅ 参数 `size`;输出公网可下载 URL |
| 海报动效(图生视频) | `agnes-video-v2.0` | ✅ `duration` 秒、`image` 支持 base64、跟随输入比例,`GET /videos/{id}` 轮询 |
| 旁白 | `mimo-v2.5-tts` | ✅ chat/completions 音频协议(同步返回 base64) |
| 音色设计 | `mimo-v2.5-tts-voicedesign` | ✅ `voice.voice_desc` 描述 |
| 声音克隆 | `mimo-v2.5-tts-voiceclone` | ✅ `voice.clone_ref` 本地样本 → data URI |
| 配乐 | ❌ 无 | 用 `bgm_file`(本地曲)或无 BGM |
| STT(A-roll) / 抠图 / image-edit(C-roll) | ❌ 无 | A-roll、C-roll 模式已禁用(脚本报错提示) |
| `grok-imagine-image(-quality)` | ✅ **已打通** | 生成 → Grok2API 取回 base64 data URI;实测可喂视频模型 |
| `grok-imagine-video` | ✅ **已打通**(Grok2API 直连) | 网关 18901 的 /v1/videos 仍 404,故客户端直连 Grok2API `/v1/videos/generations`(v3.1.1 协议:request_id 轮询 pending/done/failed,image 需 `{"url"}` 对象,data URI 实测可用);实测 720p 4s 出片 |
| `grok-4.5` | ✅ chat | 新网关实测可用 |
| `gpt-image-2` | ✅ **已打通** | 返回 b64_json 直接可用;实测:关键帧 → base64 → agnes-video-v2.0 图生视频 mp4 |
| `gpt-5.5` / `gpt-5.6-luna` | ✅ chat | codex 渠道修复后实测可用 |
| `xiaomi/mimo-v2.5` | ❌ | provider 返回 empty response content |
| `deepseek/deepseek-v4-flash` | ❌ | 403(Cline 专用) |

### 代码改动(相对上游)

- 新增 `scripts/ai_cloud.py`(OpenAI 兼容客户端:chat / images / videos / TTS / 下载),删除 `atlas_cloud.py`。
- `scripts/provider.py` 重写:`OpenAIProvider`(beats.json `"provider": "openai"`),图片改为**同步提交下载**(网关无异步任务),视频仍走 `submit + run_jobs 轮询`(失败自动重试)。
- `scripts/keyframes.py` / `style_bakeoff.py`:同步生成;`clips.py`:默认 `agnes-video-v2.0`(base64 图 + duration);`audio.py`:MiMo TTS 三模型 + 无 BGM 降级;`assemble.py`:无 BGM 分支;`asr_beats.py` / `croll_keyframes.py`: 网关不可用,明确报错。
- 文档:`SKILL.md`(zh/en)、`AGENTS.md`、`references/`(models-and-gotchas 全量重写、voices 换 MiMo 表)、README(zh/en)、示例 beats 音色改 `mimo_default`;`vox-director.skill` 已重新打包(含全部改动)。
- `ai_cloud.py` 的 HTTP 层统一走 `_http_request()`:有 `UPSTREAM_PROXY` 时经 curl 走 SOCKS5(流式 SSE 也兼容),无代理时 urllib 零依赖。

### 端到端已验证(2026-08-08)

- 基础: `style_bakeoff → keyframes → clips → audio → assemble` 跑通(1 拍 3s 成片,无 BGM),输出 `out/<project>/final.mp4`。
- **默认 grok 链实测(全默认走 grok)**: `grok-imagine-image`(直连 Grok2API)关键帧 → `grok-imagine-video`(直连 `/v1/videos/generations`,data URI 图生视频)→ 720p mp4 → `mimo-v2.5-tts` 旁白 → assemble → **final.mp4(1920×1080, 4s)** ✓
- **grok 视频出口节点注意**: 图生视频任务完成需 Grok2API 的 `grok_console` 出口节点(`no grok_console 出口节点` 报错 = 该节点不可用,任务会 failed/卡 99%;用户侧恢复后任务会自动补完)。大视频下载经 socks5 代理较慢,`download()` 超时已放宽到 600s。

### 全局默认模型(.env 显式配置,2026-08-08 新增)

```
IMAGE_MODEL=grok-imagine-image-quality   # keyframes / style_bakeoff 默认
VIDEO_MODEL=grok-imagine-video           # clips 默认
VOICE_MODEL=mimo-v2.5-tts                # audio 旁白默认
```

优先级:**beats.json 项目级字段(image_model/video_model/voice)> .env(全局默认)> 脚本常量(fallback)**。
改全局默认只动 `.env`;单项目覆盖写 `beats.json`;脚本常量是最后兜底。

### 环境变量

```bash
cd vox-director
export OPENAI_API_KEY="sk-..."                       # 网关密钥(与 .env 同款)
export UPSTREAM_PROXY="socks5h://192.168.99.3:1080"  # 本网络必需(显式)
python3 scripts/keyframes.py out/<project>           # 即可逐个 stage 跑
```
