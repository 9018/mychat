#!/usr/bin/env python3
"""upscale.py — optional post-production upscale / reformat of the assembled film.

grok-imagine-video tops out at 720p (server-enforced) and outputs 16:9. To
deliver larger and/or vertical (9:16), run this AFTER assemble (assemble_lite
auto-runs it when configured).

Explicit configuration only — opt-in, never guessed:
  1. beats.json  `"video_scale": "1080p"`, `"video_aspect": "9:16"` (project)
  2. env         `VIDEO_SCALE=1080p`, `VIDEO_ASPECT=9:16`           (global)
When video_aspect differs from the source, the film is pillar-boxed onto a
blurred-fill canvas of that aspect (nothing is cropped). Same aspect = pure
upscale. Supported scales: 480p|720p (passthrough) | 1080p | 1440p | 4k
Threads: `FFMPEG_THREADS` env (default 4 — this VM hard-reboots on encode
spikes).

Usage:
  python3 scripts/upscale.py <project_dir> [SCALE] [ASPECT]   e.g. 1080p 9:16
Output: <project_dir>/final_<aspect?>_<scale>.mp4 — final.mp4 never touched.
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


def parse_aspect(a):
    """'9:16' / '16:9' / '1:1' -> (w, h) tuple or None (keep source)."""
    if not a:
        return None
    w, h = (float(x) for x in str(a).lower().split(":"))
    return (w, h)


def upscale_aspect(src, dest, target_wh, aspect):
    """Blurred-fill reformat: canvas = target_wh at the requested aspect;
    bg = scaled+cropped blur, fg = full source centered. Nothing cropped."""
    W, H = target_wh
    threads = os.environ.get("FFMPEG_THREADS", "4")
    vf = (f"[0:v]split=2[bg][fg];"
          f"[bg]scale={W}:{H}:force_original_aspect_ratio=increase,"
          f"crop={W}:{H},boxblur=30:2[bg0];"
          f"[fg]scale={W}:{H}:force_original_aspect_ratio=decrease[fg0];"
          f"[bg0][fg0]overlay=(W-w)/2:(H-h)/2,setsar=1,format=yuv420p[v]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-threads", threads,
                    "-i", src, "-filter_complex", vf, "-map", "[v]",
                    "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                    "-c:a", "copy", "-movflags", "+faststart", dest], check=True)
    print(f"upscale: {os.path.basename(src)} -> {W}x{H} ({aspect}) -> {dest}")


def run(project_dir, scale=None, aspect=None):
    bpath = os.path.join(project_dir, "beats.json")
    if os.path.exists(bpath):
        with open(bpath) as f:
            doc = json.load(f)
        scale = scale or doc.get("video_scale")
        aspect = aspect or doc.get("video_aspect")
    scale = scale or os.environ.get("VIDEO_SCALE")
    aspect = aspect or os.environ.get("VIDEO_ASPECT")
    if not scale:
        print("upscale: no video_scale / VIDEO_SCALE — passthrough")
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
    w, h = probe(src)
    aw, ah = parse_aspect(aspect or os.environ.get("VIDEO_ASPECT"))
    src_ratio = w / h
    tag = ""
    if aw and abs(aw / ah - src_ratio) > 0.01:      # different aspect → blur-pad
        target = SCALES[scale]
        if aw / ah > 1:                              # landscape target
            H, W = target, round(target * aw / ah)
        else:                                        # portrait target (9:16…)
            W, H = target, round(target * ah / aw)
        dest = os.path.join(project_dir, f"final_{int(aw)}x{int(ah)}_{scale}.mp4")
        upscale_aspect(src, dest, (W, H), f"{int(aw)}:{int(ah)}")
        return dest
    dest = os.path.join(project_dir, f"final_{scale}.mp4")
    upscale(src, dest, scale)
    return dest


if __name__ == "__main__":
    proj = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(__file__), "..", "out", "henan-60s")
    arg = sys.argv[2] if len(sys.argv) > 2 else None
    arg2 = sys.argv[3] if len(sys.argv) > 3 else None
    run(os.path.abspath(proj), arg, arg2)