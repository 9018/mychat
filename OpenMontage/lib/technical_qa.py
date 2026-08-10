"""Evidence-backed media validation for previews and final renders."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


class TechnicalQAError(ValueError):
    """Raised when a media artifact cannot satisfy its delivery contract."""


def probe_media(path: str | Path) -> dict[str, Any]:
    media = Path(path)
    if not media.is_file():
        raise TechnicalQAError(f"media file does not exist: {media}")
    try:
        completed = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=index,codec_type,codec_name,width,height,r_frame_rate", "-of", "json", str(media)],
            check=True,
            capture_output=True,
            text=True,
        )
        raw = json.loads(completed.stdout)
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        raise TechnicalQAError(f"media is not decodable: {media}") from exc
    streams = raw.get("streams") or []
    video = next((item for item in streams if item.get("codec_type") == "video"), None)
    audio = next((item for item in streams if item.get("codec_type") == "audio"), None)
    if video is None:
        raise TechnicalQAError("media has no video stream")
    duration = float((raw.get("format") or {}).get("duration") or 0.0)
    fps_text = str(video.get("r_frame_rate") or "0/1")
    try:
        numerator, denominator = fps_text.split("/", 1)
        fps = float(numerator) / float(denominator)
    except (ValueError, ZeroDivisionError):
        fps = 0.0
    return {
        "path": str(media),
        "duration_seconds": duration,
        "width": int(video.get("width") or 0),
        "height": int(video.get("height") or 0),
        "fps": fps,
        "video_codec": video.get("codec_name"),
        "audio_codec": audio.get("codec_name") if audio else None,
        "audio_present": audio is not None,
        "playable": True,
    }


def validate_dynamic_sample(
    path: str | Path,
    delivery_promise: dict[str, Any],
    *,
    min_seconds: float = 10.0,
    max_seconds: float = 15.0,
) -> dict[str, Any]:
    report = probe_media(path)
    issues: list[str] = []
    duration = report["duration_seconds"]
    if duration < min_seconds or duration > max_seconds:
        issues.append(f"duration {duration:.3f}s outside {min_seconds:.3f}-{max_seconds:.3f}s")
    for key in ("width", "height"):
        expected = delivery_promise.get(key)
        if expected is not None and int(expected) != report[key]:
            issues.append(f"{key} {report[key]} != expected {expected}")
    expected_fps = delivery_promise.get("fps")
    if expected_fps is not None and abs(float(expected_fps) - report["fps"]) > 0.5:
        issues.append(f"fps {report['fps']:.3f} != expected {expected_fps}")
    if not report["audio_present"]:
        issues.append("sample has no audio stream")
    report["issues"] = issues
    report["playable"] = not issues
    if issues:
        raise TechnicalQAError("technical sample validation failed: " + "; ".join(issues))
    return report
