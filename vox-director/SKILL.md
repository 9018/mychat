---
name: vox-director
description: >
  Turn ONE topic into a finished Vox-style paper-collage explainer / ad video, end to end
  on a self-hosted OpenAI-compatible aggregator gateway (newapi) + local ffmpeg — script,
  collage keyframes, motion, voice-over, captions, all automated. Use this whenever the
  user wants a "Vox style" video, a paper/torn-paper collage animation, a "motion collage",
  a narrated explainer or short ad built from AI-generated collage posters, a
  scrapbook-style tribute, or wants to turn a topic / product / person into a punchy
  narrated collage video — even if they don't say the word "Vox".
  Triggers: "vox video", "collage video", "motion collage", "paper collage
  explainer", "make a collage ad", "turn this topic into a collage video".
---

# Vox Director

Turn a one-line topic into a finished **Vox-style paper-collage video**: a bold, punchy,
narrated explainer/ad where each beat is a torn-paper collage poster that comes alive, with
voice-over and captions. Runs on **one OpenAI-compatible gateway key** + local **ffmpeg**.

The look is the modern editorial paper-collage popularized by Vox explainers and creators
like Stav Zilber / rom1trs: hand-cut paper cut-outs, torn edges, tape, halftone dots,
newspaper clippings, bold flat color per beat, big cut-out headlines.

## Backend (this deployment)

All media calls go to a **self-hosted OpenAI-compatible aggregator** (newapi style) — not
Atlas Cloud. The gateway models validated for this pipeline (2026-08-08):

| Job | Model (on the gateway) | Note |
|---|---|---|
| Script / beat map (chat) | `deepseek-v4-flash-free`, `agnes-2.0-flash` | `mimo-v2.5-free` works (reasoning-y) |
| Collage keyframes | `agnes-image-2.1-flash` | takes `size`; outputs PUBLIC urls (downloadable) |
| Keyframes (alt) | `gpt-image-2` / `grok-imagine-image` / `-quality` | gpt-image-2 returns `b64_json` directly (no URL needed); grok-* return localhost asset URLs, fetched via `GROK2API_BASE`+`GROK2API_KEY` (explicit env) → base64 data URI (see models-and-gotchas.md) |
| Motion (image→video) | `agnes-video-v2.0` (default) / `grok-imagine-video` | agnes: `duration` s, public url or **base64** input. grok-imagine-video: routed **directly to Grok2API** `POST /v1/videos/generations` (v3.1.1: `request_id`, poll `pending/done/failed`, `image` as `{"url"}` — base64 data URI works; needs `GROK2API_BASE`+`GROK2API_KEY`), aspect_ratio + resolution passed explicitly |
| Narration TTS | `mimo-v2.5-tts` | chat/completions audio protocol |
| Voice design | `mimo-v2.5-tts-voicedesign` | free-form design brief |
| Voice clone | `mimo-v2.5-tts-voiceclone` | reference sample (data URI) |
| Music | **none** | supply `bgm_file` or run without BGM |

Everything else in this document is identical: the pipeline stages, decision gates, prompts
and quality bar come from the original Vox Director skill.

## The core idea (read this first)

The Vox collage look and the collage motion are **two different steps**:

1. **The look is born in the IMAGE step.** Each beat is a finished collage *poster* made by a
   text-to-image model. All the collage DNA (torn paper, cut-outs, halftone, bold color,
   headline text) lives in that image. If the image isn't a rich collage, nothing downstream
   will save it.
2. **The motion is added after.** By default the video model animates the whole poster (the
   "living poster" path — simple, automated). For dramatic *piece-by-piece* assembly you cut
   the poster into parts and drive them with the local keyframe engine (advanced path).

Everything hinges on the prompts. **Before writing any image or video prompt, read
`references/prompt-guide.md`** — it has the exact prompt structures that make the difference
between "a real Vox collage" and "a moving PowerPoint".

## Prerequisites (check, don't skip)

- `echo "${OPENAI_API_KEY:+set}"` — if empty, tell the user to set it and stop:
  `export OPENAI_API_KEY="sk-..."`.
- `OPENAI_BASE_URL` — optional; default `http://10.0.1.108:18901/v1`.
- `UPSTREAM_PROXY` — **required in this network**: the 10.0.1.108 hosts are reachable
  only through `socks5h://192.168.99.3:1080` (explicit config, also used by the
  dashboard backend `config.json: upstreamProxy`).
- `GROK2API_BASE` — grok-imagine-* assets are served by the Grok2API media service
  (`http://10.0.1.108:8000`; explicit, no default).
- `GROK2API_KEY` — Client Key minted on the Grok2API console (explicit, no default).
- `command -v ffmpeg ffprobe` — required for assembly (`brew install ffmpeg` on macOS).
- `python3 -c "import PIL"` — Pillow, for captions/watermark overlays.

## Standard workflow (topic → film)

This is the default, most-automated path. Every stage is one script, all driven by a single
`beats.json` per project under `out/<project>/`.

1. **Topic → beat map.** First **read `references/beat-layer.md`** (the story layer) and pick a
   narrative `arc` that fits the topic (`timeline` for history, `pas`/`bab` for ads,
   `how_it_works` for explainers, `man_in_hole` for transformations, …). Then write
   `out/<project>/beats.json` following that arc: **beat-1 headline must be a ≤3s hook**; beat
   count per duration (30s→6–8, 60s→10–12); split each beat into **2 shots** (wide+detail) with
   **per-shot `camera_move` VARIED across adjacent beats** (never repeat; `static` on the payoff)
   and **rich `element_motion`** (see step 4). Each beat: `narration`, `title_cn`/`title_en`,
   `scene`, `bg`, `feel`, `hook`. This draft is the **first mandatory approval gate** — show the
   user the beat map before generating (the aspect-routing approximation is the other gate, and
   on this gateway it never fires — agnes-video follows the keyframe's aspect). Examples in `examples/`.

2. **Pick the visual style (hybrid — do this BEFORE keyframes).** Do not reuse one house style
   for every topic. Read `references/prompt-guide.md` (§5 theme presets); pick 3–4 **theme presets**
   (`styles.THEME_PRESETS`: `american-retro`, `swiss-modern`, `punk-zine`,
   `soviet-constructivist`, `wpa-propaganda`, `70s-groovy`, `chinese-ink`, `atomic-age`,
   `newsprint-editorial`) that fit the topic's era/culture/tone — or compose a custom theme by
   mixing the prompt-guide dimensions. Match the topic, **not** the language. Run a bake-off
   and let the user pick by eye:
   `python3 scripts/style_bakeoff.py out/<project> american-retro,swiss-modern,punk-zine,atomic-age`
   Set the chosen name as `"collage_style"` (or `"theme"`) in beats.json.

3. **Keyframes (the collage look).** `python3 scripts/keyframes.py out/<project>`
   Generates one collage poster per beat/shot with **agnes-image-2.1-flash** (override via
   `image_model`), headline text baked in. Compose prompts with the 5-part structure in
   `references/prompt-guide.md`. Verify each poster looks like a *real layered collage*
   before animating — re-roll here rather than paying to animate a weak image.

4. **Motion.** `python3 scripts/clips.py out/<project>`
   Animates each poster with **agnes-video-v2.0** (image reference is sent as base64 — the
   gateway rejects private/localhost URLs but accepts base64 image data). Two independent axes:
   • **`camera_move`** — ONE move per shot. Safe/default: `{static, push_in, pull_out, pan, tilt,
     parallax}`. **Bold/experimental** `{orbit, dolly_zoom, roll, whip}` are available — pair with
     `constraints: loose` and re-roll.
   • **`element_motion`** — where the energy lives; **write it per beat to fit that scene**. A
     hero element flying across the frame is a great **occasional** punch, not every shot.
   `motion_style` = `calm | punchy | max`; `constraints` = `strict` (default) | `loose`.
   agnes-video **follows the input keyframe's aspect** — no aspect routing needed on this backend.

5. **Voice (+ optional music).** `python3 scripts/audio.py out/<project>`
   One consistent narrator via **mimo-v2.5-tts**. **Pick `voice_id` to fit the topic + language** —
   see `references/voices.md` (MiMo roster: `mimo_default`, `冰糖`, `茉莉`, `苏打`, `白桦`, `Mia`,
   `Chloe`, `Milo`, `Dean`). For a designed voice set `voice.voice_desc` (e.g. "an elderly
   northern-Chinese storyteller, slow and gravelly"); for a REAL person's voice set
   `voice.clone_ref` to a local audio sample → narrates via **mimo-v2.5-tts-voiceclone**.
   **Music:** the gateway has no music model. Set `bgm_file` to a local track, or accept no BGM.

6. **Assemble.** `python3 scripts/assemble.py out/<project>`
   ffmpeg: normalize + concat all shots, lay the narration (ducked under the BGM when present),
   burn captions timed per beat, add the watermark. Output `out/<project>/final.mp4`.

7. **Verify.** Extract frames to jpg and look:
   `ffmpeg -ss <t> -i final.mp4 -vf "scale=640:-1,format=yuvj420p" -frames:v 1 f.jpg`

### Cadence — how long shots should be

A common mistake is one long shot per beat. Aim for a **cut every ~4–6 seconds**:

- **Shots run 3–6s; never exceed ~7s** — beyond that the AI motion has nowhere to go.
- **A beat's narration is ~8–10s, so give each beat 2 shots** (wide with headline + detail
  cut-in without it). The narration plays across both; the visual cuts mid-sentence.
- A ~60s film is typically **~6 beats × 2 shots × ~5s = 12 shots**, not 6 × 10s.
- Reuse the wide keyframe as shot `a`; generate a tighter detail for shot `b`
  (`keyframes.py` skips shots that already have a `keyframe_url`).

Add a `shots` array to each beat (see schema). Give each shot its own short `scene` and
`motion`; set `"title": true` only on the wide shot.

## A-roll mode (talking-head → collage)

**UNAVAILABLE on this gateway** (no STT model for `asr_beats.py` transcription, and no
`video-edit` class model to re-style real footage). The scripts remain for when the gateway
provisions STT + video-edit; today they fail with a clear error. Use B-roll instead.

## C-roll mode (one photo → collage)

**UNAVAILABLE on this gateway** (needs an image-*edit* model + background-removal, neither is
provisioned). `croll_keyframes.py` falls back to plain text-to-image, which cannot anchor a
photo. Use B-roll instead.

## beats.json schema

```json
{
  "project": "my-film", "topic": "...", "language": "en",
  "aspect": "9:16",                       // 16:9 | 9:16 | 1:1 | 3:4
  "style": "collage",
  "provider": "openai",                   // media backend — the self-hosted gateway (default)
  "theme": "american-retro",              // THEME_PRESET (styles.THEME_PRESETS) — the LOOK layer
  "arc": "timeline",                      // narrative arc (beat-layer.md) — the STORY skeleton
  "video_model": "agnes-video-v2.0",      // image-to-video (follows keyframe aspect)
  "image_model": "agnes-image-2.1-flash", // keyframes (public urls; grok-imagine-* is NOT usable)
  "image_resolution": "1k",               // 1k (default) | 2k | 4k
  "motion_style": "punchy",               // amplitude: calm | punchy | max (theme sets a default)
  "constraints": "strict",                // strict = defect guards on | loose = let AI explore + re-roll
  "voice": {"voice_id": "mimo_default", "language": "zh", "speed": 1.0},
                                          // + "voice_desc": "elderly grandfather, slow, warm" (voicedesign)
                                          // + "clone_ref": "path/to/sample.mp3" (clone that voice)
  "bgm_file": "/path/to/track.mp3",       // OPTIONAL local music (gateway has no music model)
  "mix": {"music": 0.6, "voice": 1.25},   // audio balance — optional (used when BGM present)
  "caption_style": "white",               // white | paper
  "captions": true,                       // false = no burned-in captions
  "watermark": "agent skill · vox-director",
  "beats": [
    {
      "id": 1, "title_cn": "", "title_en": "BEFORE MONEY",
      "bg": "earthy clay tan", "feel": "ancient, humble", "hook": "surprising_stat",
      "narration": "For most of history, there was no money...",
      "shots": [
        {"id": "a", "dur": 5, "title": true,  "shot_size": "WIDE", "camera_move": "push_in",
         "scene": "...wide establishing collage...",
         "element_motion": "traders gesture, goat bobs, a paper bird flaps across the frame"},
        {"id": "b", "dur": 5, "title": false, "shot_size": "CLOSE", "camera_move": "parallax",
         "scene": "...close cut-in detail...",
         "element_motion": "the exchanged goods slide together, halftone pulses"}
      ]
    }
  ]
}
```

## Backends are pluggable

Every API call goes through a **provider** (`scripts/provider.py`); the OpenAI-compatible
gateway is the default backend (`"provider": "openai"`). `run_jobs()` does submit/poll with
**auto-resubmit on stalled or failed jobs**.

## Advanced: element-level motion collage (local-only)

The traditional path animates the *whole* poster. For **pieces-fly-in-and-assemble**, read
`references/local-engine.md`. **Note:** `extract_elements.py` needs a background-removal
model for `cutout` mode — unavailable on the gateway; use `"mode": "crop"` (plain crops work
locally) or skip the advanced path.

## Editions

- **Auto edition** (this skill): topic in, film out, all on the self-hosted gateway.
- **Manual prompt-pack**: if no gateway is reachable, just produce the beat map + the
  per-beat image prompts + the per-clip motion prompts + the narration script for the user
  to paste into any generator. The creative engine (the prompts) is identical.