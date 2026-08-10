from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from lib.technical_qa import TechnicalQAError, validate_dynamic_sample


def _make_video(path: Path, *, duration: float, width: int = 64, height: int = 112) -> None:
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi", "-i",
            f"testsrc2=size={width}x{height}:rate=24",
            "-f", "lavfi", "-i", f"sine=frequency=440:duration={duration}",
            "-t", str(duration), "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest", str(path),
        ],
        check=True,
        capture_output=True,
    )


def test_dynamic_sample_checks_real_media_properties(tmp_path: Path):
    sample = tmp_path / "sample.mp4"
    _make_video(sample, duration=10.2)
    report = validate_dynamic_sample(
        sample,
        {"width": 64, "height": 112, "fps": 24},
        min_seconds=10,
        max_seconds=15,
    )
    assert report["playable"] is True
    assert report["audio_present"] is True
    assert report["duration_seconds"] >= 10


def test_dynamic_sample_rejects_short_or_wrong_size_video(tmp_path: Path):
    sample = tmp_path / "short.mp4"
    _make_video(sample, duration=2)
    with pytest.raises(TechnicalQAError, match="duration"):
        validate_dynamic_sample(
            sample,
            {"width": 720, "height": 1280, "fps": 30},
            min_seconds=10,
            max_seconds=15,
        )
