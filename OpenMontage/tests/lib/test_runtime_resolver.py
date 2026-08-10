from __future__ import annotations

from lib.runtime_resolver import RuntimeResolver


def test_runtime_resolver_selects_requested_available_runtime():
    result = RuntimeResolver().resolve(
        style_package={"id": "clean-professional", "runtimes": ["remotion", "ffmpeg"]},
        requested_runtime="remotion",
        available_runtimes=["remotion", "ffmpeg"],
        quality_mode="hero",
    )
    assert result["status"] == "ready"
    assert result["runtime"] == "remotion"


def test_runtime_resolver_never_silently_falls_back():
    result = RuntimeResolver().resolve(
        style_package={"id": "vox-newsprint-editorial", "runtimes": ["remotion", "ffmpeg"]},
        requested_runtime="remotion",
        available_runtimes=["ffmpeg"],
        quality_mode="hero",
    )
    assert result["status"] == "blocked"
    assert result["requires_reapproval"] is True
    assert "ffmpeg" in result["fallback_options"]
