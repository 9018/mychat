# Vox Director — Agent Guide

This repository is an **agent skill**: a self-contained workflow that turns one
topic into a finished Vox-style paper-collage video (script → collage keyframes →
motion → voice-over → music → captions). Media generation runs on a
**self-hosted OpenAI-compatible gateway** (newapi style); composition is local ffmpeg.

## How to use it (for the agent)

1. Read **`SKILL.md`** — the full workflow and the two human approval gates.
   (`SKILL.zh.md` is the same in Chinese.)
2. Before writing any prompt, read **`references/`** (prompt structures, the
   vocabulary/theme bank, and the narrative-beat library).
3. Work one project at a time under `out/<project>/`, driven by a single
   `beats.json`. Run the stages in **`scripts/`** in order:
   `style_bakeoff.py → keyframes.py → clips.py → audio.py → assemble.py`.

## Requirements

- `OPENAI_API_KEY` in the environment — from the self-hosted gateway admin
- `OPENAI_BASE_URL` (default `http://10.0.1.108:18901/v1`)
- `UPSTREAM_PROXY` — required in this network: `socks5h://192.168.99.3:1080` (reach 10.0.1.108)
- `GROK2API_BASE` + `GROK2API_KEY` — only if using grok-imagine-* keyframes (media fetch)
- `ffmpeg` + `ffprobe`
- Python 3 with `pillow`

## Agent notes

- **Claude Code** auto-loads this as a skill from `SKILL.md`'s frontmatter — just
  ask for a "vox video".
- **Models validated on the gateway (2026-08-08):**
  - chat/script: `deepseek-v4-flash-free`, `agnes-2.0-flash`, `mimo-v2.5-free`
  - image keyframes: `agnes-image-2.1-flash` (`grok-imagine-image` exists but
    returns localhost asset URLs — not usable today)
  - video motion: `agnes-video-v2.0` (base64 image refs, `duration` seconds)
  - TTS: `mimo-v2.5-tts` / `mimo-v2.5-tts-voicedesign` / `mimo-v2.5-tts-voiceclone`
  - **No** STT, no music model, no background-removal, no image-edit → A-roll /
    C-roll / cutout paths are unavailable on this gateway.