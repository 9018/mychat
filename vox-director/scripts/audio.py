#!/usr/bin/env python3
"""
Audio stage: per-beat narration (one consistent voice) + optional BGM.

Narration uses the gateway's MiMo TTS models via chat/completions:
  - mimo-v2.5-tts             named voices (Chinese names for zh, English IDs for en)
  - mimo-v2.5-tts-voicedesign free-form voice design (a brief in the user message)
  - mimo-v2.5-tts-voiceclone  clone a reference sample (voice.clone_ref)

MUSIC: this gateway has NO music model. Provide a local track with
beats.json `"bgm_file": "/path/to/track.mp3"` to score the film; otherwise the
pipeline runs without BGM (assemble.py handles both).

Usage: python3 audio.py <project_dir>   (default: out/tang-30s)
"""
import base64
import json
import os
import subprocess
import sys

from provider import get_provider

VOICE_MODEL = os.environ.get("VOICE_MODEL", "mimo-v2.5-tts")  # .env 全局默认;normal narration
VOICEDESIGN_MODEL = os.environ.get("VOICEDESIGN_MODEL", "mimo-v2.5-tts-voicedesign")  # .env 全局默认
CLONE_MODEL = os.environ.get("CLONE_MODEL", "mimo-v2.5-tts-voiceclone")  # .env 全局默认
MUSIC_MODEL = None                            # gateway has no music model

# MiMo named voices — zh voices use their Chinese names on the API.
VOICE_ALIASES = {
    # xai-tts legacy names -> MiMo default (keeps old beats.json working)
    "leo": "mimo_default", "rex": "mimo_default", "sal": "mimo_default",
    "ara": "mimo_default", "eve": "mimo_default",
    # MiMo voices (see frontend PRESET_VOICES / tts.ts)
    "mimo_default": "mimo_default",
    "bingtang": "冰糖", "moli": "茉莉", "soda": "苏打", "baihua": "白桦",
    "mia": "Mia", "chloe": "Chloe", "milo": "Milo", "dean": "Dean",
}

# Voicedesign brief template (keeps delivery on-brand for explainers).
VOICEDESIGN_TEMPLATE = ("{desc} They narrate a documentary-style explainer with "
                        "crisp articulation, clean studio vocal only — no music, no SFX.")

LANG_NAMES = {"en": "English", "zh": "Mandarin Chinese", "ja": "Japanese",
              "ko": "Korean", "es": "Spanish", "fr": "French", "de": "German"}


def probe_dur(path: str) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", path], capture_output=True, text=True).stdout
    try:
        return float(out.strip())
    except ValueError:
        return 0.0


def run(project_dir: str):
    bpath = os.path.join(project_dir, "beats.json")
    with open(bpath) as f:
        doc = json.load(f)
    adir = os.path.join(project_dir, "audio")
    os.makedirs(adir, exist_ok=True)

    prov = get_provider(doc.get("provider"))
    voice = doc.get("voice", {})
    voice_id = voice.get("voice_id", "mimo_default")
    voice_alias = VOICE_ALIASES.get(str(voice_id).lower(), voice_id)
    voice_desc = voice.get("voice_desc")          # voicedesign brief
    clone_ref = voice.get("clone_ref")            # local audio sample -> clone

    # ---- narration: synchronous TTS per beat (fast, ~1-3s each) ----
    for beat in doc["beats"]:
        if beat.get("narration_audio"):
            print(f"[narr {beat['id']}] reuse {beat['narration_audio']}")
            continue
        text = beat["narration"]
        if clone_ref:
            with open(clone_ref, "rb") as f:
                ref_b64 = "data:audio/wav;base64," + base64.b64encode(f.read()).decode()
            audio = prov.tts(CLONE_MODEL, text, clone_sample_b64=ref_b64,
                             audio_format="mp3")
        elif voice_desc:
            desc = VOICEDESIGN_TEMPLATE.format(desc=voice_desc)
            audio = prov.tts(VOICEDESIGN_MODEL, text, voice_desc=desc,
                             audio_format="mp3")
        else:
            audio = prov.tts(VOICE_MODEL, text, voice=voice_alias,
                             audio_format="mp3")
        dest = os.path.join(adir, f"narr_{beat['id']}.mp3")
        with open(dest, "wb") as f:
            f.write(audio)
        beat["narration_audio"] = dest
        beat["narration_dur"] = round(probe_dur(dest), 2)
        print(f"[narr {beat['id']}] {beat['narration_dur']}s -> {dest}")

    # ---- BGM: local file only (no music model on the gateway) ----
    bgm_path = os.path.join(adir, "bgm.mp3")
    if os.path.exists(bgm_path):
        doc["bgm_path"] = bgm_path
        print(f"[bgm] reuse existing {bgm_path}")
    elif doc.get("bgm_file") and os.path.exists(doc["bgm_file"]):
        import shutil
        shutil.copyfile(doc["bgm_file"], bgm_path)
        doc["bgm_path"] = bgm_path
        doc["bgm_dur"] = round(probe_dur(bgm_path), 2)
        print(f"[bgm] copied {doc['bgm_file']} -> {bgm_path}")
    else:
        doc["bgm_path"] = None
        print("[bgm] no music model on gateway and no bgm_file set — "
              "running without BGM (supply beats.json bgm_file to score the film)")

    with open(bpath, "w") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    print("updated", bpath)


if __name__ == "__main__":
    proj = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(__file__), "..", "out", "tang-30s")
    run(os.path.abspath(proj))