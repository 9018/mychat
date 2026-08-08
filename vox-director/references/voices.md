# Voice roster — MiMo TTS (`mimo-v2.5-tts`)

Set `voice.voice_id` in beats.json. **Pick by the film's LANGUAGE first, then match
gender/tone to the topic** — don't just leave the default.

- Chinese voices use their **Chinese names** on the API (`冰糖`, not `bingtang`).
- English voices use their English names directly.
- Legacy xai-tts ids (`leo`/`rex`/`ara`/…) map to `mimo_default` for back-compat.
- Skill default: **`mimo_default`**. Override per film.

## Named voices

| id | name | lang | gender |
|---|---|---|---|
| `mimo_default` | MiMo 默认 | mixed | mixed |
| `bingtang` | 冰糖 | zh | F |
| `moli` | 茉莉 | zh | F |
| `soda` | 苏打 | zh | M |
| `baihua` | 白桦 | zh | M |
| `Mia` | Mia | en | F |
| `Chloe` | Chloe | en | F |
| `Milo` | Milo | en | M |
| `Dean` | Dean | en | M |

## Designing a voice (no fixed id needed)

`mimo-v2.5-tts-voicedesign` synthesizes a voice from a free-form brief. Put the
brief in `voice.voice_desc`, e.g.:

- "Heavy Russian accent, gruff middle-aged male, blunt and matter-of-fact."
- "一位年迈的老先生,说带北方口音的普通话,语速缓慢而沉稳,嗓音略带沙哑和沧桑感。"
- "1940s film-noir narrator, deep and smoky, deliberate pacing."

Delivery template (helps timing beat-stability): the skill appends
"narrate a documentary-style explainer with crisp, clean studio delivery — no music, no SFX."

## Cloning a real voice

`mimo-v2.5-tts-voiceclone` narrates in the exact voice of a local audio sample:
set `voice.clone_ref` to the sample path (wav/mp3). Use it for a C-roll presenter,
a brand voice, or a recurring narrator IP.