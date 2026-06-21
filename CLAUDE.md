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
