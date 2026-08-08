#!/usr/bin/env python3
"""assemble_lite.py — zero-re-encode assembly for same-spec grok clips.

Videos are concatenated with `-c copy` (no x264 re-encode), narration mp3s are
concatenated with `-c copy`, then muxed. CPU stays near idle — safe on fragile
hosts that hard-reboot under ffmpeg encoding load spikes.

Requires: every clip has the same resolution/fps and its duration equals its
beat duration (grok-imagine-video output guarantees this).
"""
import json
import os
import subprocess
import sys


def ff(args):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-threads", "2", *args],
                   check=True)


def run(project_dir):
    with open(os.path.join(project_dir, "beats.json")) as f:
        doc = json.load(f)
    tmp = os.path.join(project_dir, "_lite")
    os.makedirs(tmp, exist_ok=True)

    # ---- 1) exact-duration clips in order (copy concat, no re-encode) ----
    segs = []
    for b in doc["beats"]:
        for s in (b.get("shots") or [b]):
            cp = s.get("clip_path")
            if not cp or not os.path.exists(cp):
                raise SystemExit(f"missing clip: {cp}")
            segs.append(cp)
    vlist = os.path.join(tmp, "vlist.txt")
    with open(vlist, "w") as f:
        for p in segs:
            f.write(f"file '{os.path.abspath(p)}'\n")
    body = os.path.join(tmp, "body.mp4")
    ff(["-f", "concat", "-safe", "0", "-i", vlist, "-c", "copy", body])

    # ---- 2+3) single mux pass: filter-concat the narration (light aac encode),
    # video untouched with `-c copy`. NO -shortest: video timeline is the
    # master, narration leads then silence until total.
    narr = []
    for b in doc["beats"]:
        na = b.get("narration_audio")
        if na and os.path.exists(na):
            narr.append(na)
    if not narr:
        raise SystemExit("no narration_audio found")
    fc = "".join(f"[{i}:a]" for i in range(1, len(narr) + 1))
    fc += f"concat=n={len(narr)}:v=0:a=1[a]"
    inputs = ["-i", body]
    for n in narr:
        inputs += ["-i", n]
    final = os.path.join(project_dir, "final.mp4")
    ff([*inputs, "-filter_complex", fc, "-map", "0:v", "-map", "[a]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", final])
    print("FINAL:", final)


if __name__ == "__main__":
    proj = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(__file__), "..", "out", "tang-30s")
    run(os.path.abspath(proj))