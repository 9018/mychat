<p align="right"><b>English</b> · <a href="README.zh.md">简体中文</a></p>

# 🎬 Vox Director

**Turn one topic into a finished Vox-style paper-collage explainer / ad video — script, collage keyframes, motion, voice-over, music and captions, all automated.**

An **agent skill** that runs end to end on a **self-hosted OpenAI-compatible gateway** (`OPENAI_API_KEY` / `OPENAI_BASE_URL`) + local `ffmpeg`, usable by any coding agent (Claude Code, Codex, etc.). You give it a one-line topic; it gives you an `mp4`.

![License: MIT](https://img.shields.io/badge/License-MIT-black.svg) ![Agent Skill](https://img.shields.io/badge/Agent-Skill-d97757.svg)

<div align="center">

https://github.com/user-attachments/assets/ed08d230-7bcb-4b48-a17d-23c079208f9f

<b>▶ "The evolution of Chinese civilization" · 30s</b>

</div>

<table>
  <tr>
    <td width="25%"><a href="https://github.com/user-attachments/assets/216cd62f-6314-456c-94cf-1090b8559a22"><img src="assets/thumbs/football.jpg" width="100%" alt="How football conquered the world"></a></td>
    <td width="25%"><a href="https://github.com/user-attachments/assets/561788b1-5615-4828-b3f8-b24ae5ad7bcd"><img src="assets/thumbs/mexican.jpg" width="100%" alt="Mexican street food"></a></td>
    <td width="25%"><a href="https://github.com/user-attachments/assets/f69f072f-f50a-41ba-9e66-7ed0aae4ddc0"><img src="assets/thumbs/money.jpg" width="100%" alt="A brief history of money"></a></td>
    <td width="25%"><a href="https://github.com/user-attachments/assets/b9ff526f-577f-4acb-aafe-a2519a9b7c1c"><img src="assets/thumbs/silicon-valley.jpg" width="100%" alt="A brief history of Silicon Valley"></a></td>
  </tr>
  <tr>
    <td align="center"><sub>Football history · 60s</sub></td>
    <td align="center"><sub>Mexican street food · 60s</sub></td>
    <td align="center"><sub>A brief history of money · 60s</sub></td>
    <td align="center"><sub>Silicon Valley history · 60s</sub></td>
  </tr>
</table>

<p align="center"><sub><em>▶ more films — click any thumbnail to play</em></sub></p>

---

## What it is

The look is the modern editorial **paper-collage** popularized by Vox explainers: hand-cut paper cut-outs, torn edges, tape, halftone dots, newspaper clippings, bold flat color per beat, big cut-out headlines — brought to life with motion, a narrator, music and captions.

## How it works

One topic flows through one script per stage, all driven by a single `beats.json` per project:

```
topic
  │
  ├─ 1. beat map        pick a narrative arc → write beats.json      ◀── GATE 1: you approve the beat map
  ├─ 2. style bake-off  render the same beat in 3–4 themes           ◀── GATE 2: you pick the look by eye
  ├─ 3. keyframes       one collage poster per beat  (nano-banana-2)
  ├─ 4. motion          animate each poster          (gemini-omni-flash i2v)
  ├─ 5. voice + music   one narrator (xai/tts) + BGM (minimax/music)
  ├─ 6. assemble        ffmpeg: concat, duck music under VO, burn captions + watermark
  └─ final.mp4
```

That flow is **B-roll** — a topic in, everything generated. Two more input modalities reuse the same engine:

- **A-roll — you already have a talking-head video.** It is ASR-segmented into beats and re-styled into the collage look, keeping the real face, lip-sync and gestures frame-for-frame (`gemini-omni-flash/video-edit`, auto-retrying on `seedance-2.0/reference-to-video`).
- **C-roll — you have one still photo** (a selfie, a product shot). The subject is cut out as a photographic sticker — never redrawn — and each beat's poster is generated around it (`nano-banana-2/edit`). The narration can be cloned into the subject's own voice.

Two ideas make or break the result, and the skill is built around both:

1. **The look is born in the image step.** Each beat is a finished collage *poster*. All the collage DNA (torn paper, cut-outs, halftone, headline text) lives in that image — if the poster isn't a rich collage, nothing downstream saves it.
2. **The motion is added after.** By default an AI video model animates the whole poster (the "living poster" path). For dramatic *piece-by-piece* assembly, an optional local keyframe engine cuts the poster into parts and drives them frame-by-frame (no content filters, pixel-exact — great for real people).

Two human decision gates keep you in control (approve the beat map; pick the style); everything else is automated.

## Models (verified on the self-hosted gateway, 2026-08-08)

| Job | Model |
|---|---|
| Script / beatmap | `deepseek-v4-flash-free`, `agnes-2.0-flash`, `mimo-v2.5-free` |
| Collage keyframes | `agnes-image-2.1-flash` |
| Motion (image→video) | `agnes-video-v2.0` |
| Narration TTS | `mimo-v2.5-tts` |
| Voice design | `mimo-v2.5-tts-voicedesign` |
| Voice clone | `mimo-v2.5-tts-voiceclone` |
| Music | not available (use a local `bgm_file`) |

A-roll (STT + video-edit) and C-roll (image-edit + background removal) models are **not**
provisioned on the gateway — those modes are disabled in this fork.

## Install

Clone the repo, then:

```bash
export OPENAI_API_KEY="sk-..."
export OPENAI_BASE_URL="http://10.0.1.108:18901/v1"   # optional; this is the default
# 10.0.1.108 需经 SOCKS5 才能访问(显性配置),以及可选的 grok 图片媒体取回:
export UPSTREAM_PROXY="socks5h://192.168.99.3:1080"
export GROK2API_BASE="http://10.0.1.108:8000"    # grok-imagine-* 媒体服务
export GROK2API_KEY="g2a_..."                     # Grok2API 控制台签发的 Client Key
brew install ffmpeg          # or apt install ffmpeg
pip install pillow
```

Tell your coding agent: "make a Vox-style collage video about <topic>, <language>, <ratio>."

## Install

This is an **agent skill** — it works with any coding agent that can read a workflow and run scripts (Claude Code, Codex, …). Claude Code auto-discovers it as a skill; other agents read [`AGENTS.md`](AGENTS.md) → [`SKILL.md`](SKILL.md).

**Option A — from this repo:**
```bash
git clone <your-fork> ~/.claude/skills/vox-director
```

**Option B — from the packaged skill:** download [`vox-director.skill`](vox-director.skill) and install it via your Claude skills UI.

Then set your gateway key:
```bash
export OPENAI_API_KEY="sk-..."
export OPENAI_BASE_URL="http://10.0.1.108:18901/v1"
```

## Quick start

Just ask your coding agent, with the skill installed:

> *"Make me a Vox-style collage video introducing Mexican street food — English, 16:9, 15 seconds."*

The agent will draft a beat map for your approval, run a style bake-off for you to pick from, then generate keyframes → motion → voice → music and assemble `out/<project>/final.mp4`.

## Requirements

- A **coding agent** — Claude Code, Codex, or similar
- **OpenAI-compatible gateway** key (`OPENAI_API_KEY`)
- **ffmpeg** + **ffprobe** (`brew install ffmpeg`)
- **Python 3** with **Pillow** (`pip install pillow`) — for caption/watermark overlays

## What's in the box

```
SKILL.md              the skill (English) — the workflow the agent follows
SKILL.zh.md           the same skill in Chinese
AGENTS.md             entry point for non-Claude agents (Codex, …)
references/           the creative engine
  prompt-guide.md       the LOOK layer — prompt structures, vocab & 9 theme presets
  beat-layer.md         14 narrative arcs + hook/pacing + shot patterns
  voices.md             xai/tts voice roster — pick a voice_id per language/tone
  models-and-gotchas.md every API / ffmpeg gotcha, already solved
  local-engine.md       the advanced element-level motion engine
scripts/              one script per pipeline stage
examples/             ready-to-run beats.json examples
assets/               the showcase film
```

## Credits

Forked from [@alisaqqt](https://x.com/alisaqqt)'s vox-director and re-pointed from Atlas Cloud to a self-hosted OpenAI-compatible gateway.

Inspired by the collage-ad workflows of **[Stav Zilber](https://x.com/StavZilber)**, **[rom1trs](https://x.com/rom1trs)** and **[Higgsfield](https://x.com/higgsfield_ai)**, and by **[Vox](https://www.vox.com)**'s explainer visual language.


## License

[MIT](LICENSE) © 2026 Alisa Qian

## Friends

**[LINUX DO](https://linux.do)** — an open, friendly community where developers share and learn together.
