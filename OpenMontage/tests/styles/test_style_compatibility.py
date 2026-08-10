from __future__ import annotations

from pathlib import Path

import pytest

from styles.style_compatibility import CompatibilityResolver, CompatibilityError
from styles.style_registry import StyleRegistry


ROOT = Path(__file__).resolve().parents[2]


def resolver() -> CompatibilityResolver:
    return CompatibilityResolver(StyleRegistry(ROOT / "styles" / "packages"))


def test_cinematic_collage_is_a_valid_composition():
    result = resolver().resolve(
        pipeline="cinematic",
        primary_style="premium-minimalist",
        supporting_styles=["vox-newsprint-editorial"],
        asset_strategies=["generated", "archival"],
        aspect_ratio="9:16",
        render_runtime="remotion",
        available_runtimes=["remotion", "ffmpeg"],
        available_providers=["image", "video", "mimo_tts"],
        quality_mode="hero",
    )
    assert result["status"] in {"ready", "atelier_required"}
    assert result["status"] != "blocked"
    assert "editorial-collage" in result["style_families"]


def test_documentary_generated_reconstruction_is_not_globally_rejected():
    result = resolver().resolve(
        pipeline="documentary-montage",
        primary_style="vox-newsprint-editorial",
        supporting_styles=[],
        asset_strategies=["archival", "generated", "reconstructed"],
        aspect_ratio="16:9",
        render_runtime="remotion",
        available_runtimes=["remotion"],
        available_providers=["image", "video"],
        quality_mode="hero",
    )
    assert result["status"] in {"ready", "atelier_required"}
    assert not any("AI" in reason or "generated" in reason.lower() and "forbidden" in reason.lower()
                   for reason in result["reasons"])


def test_missing_runtime_is_blocked_with_explicit_reason():
    result = resolver().resolve(
        pipeline="cinematic",
        primary_style="premium-minimalist",
        supporting_styles=[],
        asset_strategies=["generated"],
        aspect_ratio="9:16",
        render_runtime="blender",
        available_runtimes=["remotion"],
        available_providers=["image"],
        quality_mode="hero",
    )
    assert result["status"] == "blocked"
    assert any("runtime" in reason.lower() for reason in result["reasons"])


def test_unsupported_style_combination_requires_atelier_or_reports_conflict():
    with pytest.raises(CompatibilityError):
        resolver().resolve(
            pipeline="screen-demo",
            primary_style="premium-minimalist",
            supporting_styles=["vox-punk-zine"],
            asset_strategies=["screen"],
            aspect_ratio="9:16",
            render_runtime="remotion",
            available_runtimes=["remotion"],
            available_providers=["capture"],
            quality_mode="standard",
        )
