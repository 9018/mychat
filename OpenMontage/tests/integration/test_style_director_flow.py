from __future__ import annotations

from pathlib import Path

from styles.style_director import StyleDirector
from styles.style_registry import StyleRegistry


ROOT = Path(__file__).resolve().parents[2]


def test_style_director_proposes_multiple_real_style_candidates():
    director = StyleDirector(StyleRegistry(ROOT / "styles" / "packages"))
    candidates = director.propose(
        {
            "pipeline": "cinematic",
            "topic": "weather warning",
            "aspect_ratio": "9:16",
            "quality_mode": "hero",
            "available_runtimes": ["remotion", "ffmpeg"],
            "available_providers": ["image", "video", "mimo_tts"],
        }
    )
    assert len(candidates) >= 3
    assert len({candidate["style_id"] for candidate in candidates}) == len(candidates)
    assert all(candidate["style_package_version"] for candidate in candidates)
    assert all(candidate["status"] in {"ready", "atelier_required", "degraded"} for candidate in candidates)
