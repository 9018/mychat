# Models & gotchas — self-hosted OpenAI-compatible gateway

All media calls go through one OpenAI-compatible gateway (`OPENAI_BASE_URL`,
default `http://10.0.1.108:18901/v1`). Verify the live list first:
`GET {base}/models` (with `Authorization: Bearer $OPENAI_API_KEY`).

## Network (explicit config, nothing guessed)

- The `10.0.1.108` hosts (gateway `:18901`, Grok2API `:8000`) are reachable
  **only through a SOCKS5 hop**. Set `UPSTREAM_PROXY=socks5h://192.168.99.3:1080`
  (env or dashboard `config.json: upstreamProxy`). `ai_cloud.py` routes every
  request (gateway + grok asset fetch) through it via curl when set.
- grok-imagine-* image assets come back as `http://127.0.0.1:8000/v1/media/images/<id>`
  — served by the **Grok2API media service**. Configure
  `GROK2API_BASE=http://10.0.1.108:8000` and `GROK2API_KEY=<client key>` (mint a
  Client Key in the Grok2API console). The skill then rewrites the origin, fetches
  the asset with the key, and returns a **base64 data URI** usable everywhere.
  Missing either env var -> a clear error naming exactly what to set.

## Model map (validated 2026-08-08, re-validated after Grok2API 直连开通)

| Job | Model | Note |
|---|---|---|
| Script / beat planning (chat) | `deepseek-v4-flash-free` | free; replies fine |
| Chat (alt) | `agnes-2.0-flash` | fast |
| Chat (alt, reasoning-y) | `mimo-v2.5-free` | content comes in `reasoning` |
| Chat (alt) | `grok-4.5` | works (tier beyond free-flash) |
| Keyframes / posters | `agnes-image-2.1-flash` | `size` param (e.g. `1024x1024`); outputs a **public** https URL |
| Keyframes (alt) | `gpt-image-2` | returns **`b64_json`** directly (`1024x1024`+); feeds image-to-video as data URI — validated |
| Chat (alt) | `gpt-5.5` / `gpt-5.6-luna` | codex channel; both answer (re-validated) |
| Animate (image→video) | `agnes-video-v2.0` | `duration` seconds; accepts public URL or **base64** for `image`; 256→480p automatically; poll `GET /videos/{id}` |
| Animate (alt, xAI 协议) | `grok-imagine-video` | **Grok2API 直连**(非网关):`POST /v1/videos/generations`;字段 `duration`/`aspect_ratio`/`resolution`/`image`(`{"url": ...}`,字符串自动包装,base64 data URI 实测可用);`request_id` 轮询 `GET /v1/videos/{id}` → `pending|done|failed`,完成后 `video.url`(重写为 GROK2API_BASE 后带 Bearer 下载);实测 1280x720 4s 出片 |
| Narration TTS | `mimo-v2.5-tts` | chat/completions audio protocol; zh voices use Chinese names |
| Voice design | `mimo-v2.5-tts-voicedesign` | brief in the user message |
| Voice clone | `mimo-v2.5-tts-voiceclone` | `audio.voice` = data-URI sample |
| Music | ❌ none | use `bgm_file` (local) or no BGM |
| STT (A-roll) | ❌ none | A-roll unavailable |
| Background removal | ❌ none | `extract_elements.py` cutout mode unavailable |
| Image edit | ❌ none | C-roll unavailable |

Models listed in `/models` but NOT usable (validated):

- ~~`grok-imagine-video`~~ — **NOW WORKS** (Grok2API 直连, see model map). The old
  gateway route (`POST /v1/videos` on 18901) still 404s, which is why the client
  routes grok-* video submissions to Grok2API `/v1/videos/generations` directly
  with the Client Key.
- ~~`gpt-5.5` / `gpt-5.6-luna` / `gpt-image-2`~~ — **NOW WORKS** (2026-08-08, after the
  channel was fixed). gpt-5.5/gpt-5.6-luna answer chat (codex channel); gpt-image-2
  returns **`b64_json`** (no URL needed, 1024→1254px PNG, usable directly as data
  URI for image-to-video). Validated end-to-end: gpt-image-2 keyframe → base64 →
  agnes-video-v2.0 → mp4. ✓
- `gpt-image-1.5` — intentionally **not used** (user decision); also the token
  lacks access to it.
- `deepseek/deepseek-v4-flash` — 403 "only available via Cline product surfaces".
- `xiaomi/mimo-v2.5` — `empty response content` from the provider.

**Validated end-to-end 2026-08-08**: `grok-imagine-image` keyframe → base64 data
URI (via GROK2API) → `agnes-video-v2.0` image-to-video → public mp4. ✓

## beats.json authoring

- Each **shot** may carry user-authored `image_prompt` (keyframes pass it straight
  to the image model, bypassing the auto collage/painterly composer) and
  `motion_prompt` (clips uses it verbatim as the video prompt). Omit either to
  fall back to automatic composition. Converted from a flat `scenes[]` plan:
  1 scene → 1 beat (narration=voice, title on first beat) + 1 shot
  (`dur=scenes.duration`, `scene=scenes.visual`, prompts preserved verbatim).

## Request gotchas (all inside `scripts/ai_cloud.py`)

1. **User-Agent header is mandatory** — the gateway's WAF blocks default urllib UAs.
2. **Video image param**: localhost/private URLs are rejected upstream — send **base64
   data URIs** (the skill's `upload()` returns them).
3. **num_frames** (if you pass it for video) must be `8*n+1`; prefer `duration` seconds.
4. **Image params differ per model**: agnes-image-* takes `size`; grok-imagine-* takes
   `aspect_ratio` and **rejects `size`** (`styles.image_params` handles both).
5. **TTS is synchronous** — no submit/poll; bytes come back in
   `choices[0].message.audio.data` (base64). `audio.format` wav/mp3.
6. **Asset urls can be `data:` URIs or public https**; `download()` handles both
   (urllib with UA, curl fallback — both via the socks5 proxy when set, timeout 600s
   for big videos).
7. Video completion: `GET /videos/{id}` → `status: queued|processing|completed|failed`,
   `progress`, `video_url` (https://platform-outputs.agnes-ai.space/...) — public.

## ffmpeg gotchas (unchanged)

- No libass/drawtext in this ffmpeg — captions are Pillow PNGs composited with
  `overlay` (see `text_overlay.py`).
- Clip shorter than its segment gets slowed (`setpts`) instead of frozen.
- Off-aspect clips get a blurred-fill background (`split/scale/crop/boxblur/overlay`).
- BGM is ducked under narration with `sidechaincompress` — skipped entirely when no
  `bgm_path` exists (gateway has no music model).

## Content / budget notes

- Costs are per-generation; `run_jobs()` auto-resubmits stalled/failed jobs up to
  `max_retries` — a resubmit is a NEW billed task.
- Chat (deepseek-v4-flash-free / mimo-v2.5-free / agnes-2.0-flash) is effectively
  free — use it to plan beats and enrich `element_motion`.
## Host stability (this VM hard-reboots under ffmpeg encode spikes)

2026-08-08: three near-instant hard reboots (16:59 / 16:08 / 16:19, no shutdown
log, no panic, no OOM — KVM guest died mid `assemble.py`) — all within ~1-2 min
of starting the x264 re-encode pass. The host kills the VM on sustained CPU
bursts. Workarounds shipped:

- `scripts/assemble_lite.py` — **zero-re-encode** assembly: `-c copy` concat of
  same-spec clips + light aac narration mux. 60s film in ~1.3s, CPU idle.
  Prereq: every clip shares resolution/fps and duration == beat dur
  (grok-imagine-video guarantees this). Use it instead of assemble.py on this
  host. `-shortest` avoided: video timeline is master, narration leads.
- `assemble.py` `ff()` honours `FFMPEG_THREADS` env (default 8) when a
  re-encode is unavoidable.

## Global model defaults via .env (explicit, no magic)

`IMAGE_MODEL` / `VIDEO_MODEL` / `VOICE_MODEL` env vars override the script-level
fallback constants (`keyframes.py`, `style_bakeoff.py`, `clips.py`, `audio.py`).
Priority: beats.json per-project (`image_model`/`video_model`/`voice`) >
env global > script constant. Set them in the repo root `.env`.
