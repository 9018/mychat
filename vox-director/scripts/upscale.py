#!/usr/bin/env python3
"""upscale.py — optional post-production upscale of the assembled final film.

grok-imagine-video tops out at 720p (server-enforced). To deliver larger, run
this AFTER assemble (or let assemble_lite auto-run it when configured).

Explicit configuration only — opt-in, never guessed:
  1. beats.json  `"video_scale": "1080p"`   (per-project)
  2. env         `VIDEO_SCALE=1080p`        (global default in .env)
Supported values: 480p (no-op passthrough) | 720p | 1080p | 1440p | 4k
Threads: `FFMPEG_THREADS` env, default 4 (this host hard-reboots on encode
spikes — keep the encode headroom small).

Usage:
  python3 scripts/upscale.py <project_dir> [SCALE]
Output: <project_dir>/final_<scale>.mp4 (final.mp4 itself is never touched).
"""
import json
import os
import subprocess
import sys

SCALES = {  # height of the short edge in pixels
    "480p": 480, "720p": 720, "1080p": 1080, "1440p": 1440, "4k": 2160,
}


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                          "-show_entries", "stream=width,height",
                          "-of", "csv=p=0", path],
                         capture_output=True, text=True).stdout.strip()
    w, h = (int(x) for x in out.split(","))
    return w, h


def upscale(src, dest, scale):
    w, h = probe(src)
    short = min(w, h)
    if short >= SCALES[scale]:
        print(f"upscale: input already ≥ {scale} ({w}x{h}) — copying")
        subprocess.run(["cp", src, dest], check=True)
        return
    target = SCALES[scale]
    # keep the portrait/landscape geometry
    if h > w:            # portrait (e.g. 9:16) — short edge is the width
        W, H = target, round(target * h / w)
    else:                # landscape (e.g. 16:9) — short edge is the height
        W, H = round(target * w / h), target
    threads = os.environ.get("FFMPEG_THREADS", "4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-threads", threads,
                    "-i", src, "-vf", f"scale={W}:{H}:flags=lanczos",
                    "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                    "-pix_fmt", "yuv420p", "-c:a", "copy",
                    "-movflags", "+faststart", dest], check=True)
    print(f"upscale: {w}x{h} -> {W}x{H} ({scale}) -> {dest}")


def run(project_dir, scale=None):
    bpath = os.path.join(project_dir, "beats.json")
    if os.path.exists(bpath):
        with open(bpath) as f:
            doc = json.load(f)
        scale = scale or doc.get("video_scale")
    scale = scale or os.environ.get("VIDEO_SCALE")
    if not scale:
        print("upscale: no `video_scale` in beats.json and no VIDEO_SCALE env — passthrough")
        return None
    scale = str(scale).lower().strip()
    if scale not in SCALES:
        raise SystemExit(f"upscale: unsupported scale {scale!r} — use {sorted(SCALES)}")
    if scale in ("480p", "720p"):
        print(f"upscale: {scale} is native — skipping")
        return None
    src = os.path.join(project_dir, "final.mp4")
    if not os.path.exists(src):
        raise SystemExit(f"upscale: missing {src} — run assemble first")
    dest = os.path.join(project_dir, f"final_{scale}.mp4")
    upscale(src, dest, scale)
    return dest


if __name__ == "__main__":
    proj = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(__file__), "..", "out", "henan-60s")
    arg = sys.argv[2] if len(sys.argv) > 2 else None
    run(os.path.abspath(proj), arg)