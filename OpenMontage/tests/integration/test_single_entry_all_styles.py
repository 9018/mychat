from __future__ import annotations

from pathlib import Path

from lib.family_qa import evaluate_project
from lib.creative_treatment import ensure_delivery_promise, lock_treatment
from styles.style_director import StyleDirector
from styles.style_registry import StyleRegistry


ROOT = Path(__file__).resolve().parents[2]


def test_single_entry_discovers_all_openmontage_and_vox_style_packages():
    registry = StyleRegistry(ROOT / "styles" / "packages")
    packages = registry.discover()
    expected = {
        "anime-ghibli",
        "clean-professional",
        "flat-motion-graphics",
        "minimalist-diagram",
        "premium-minimalist",
        "vox-paper-collage",
        "vox-american-retro",
        "vox-swiss-modern",
        "vox-punk-zine",
        "vox-soviet-constructivist",
        "vox-wpa-propaganda",
        "vox-70s-groovy",
        "vox-chinese-ink",
        "vox-atomic-age",
        "vox-newsprint-editorial",
        "vox-gilded-deco",
    }
    assert set(packages) == expected


def test_single_entry_can_propose_cinematic_collage_and_documentary_hybrid():
    director = StyleDirector(StyleRegistry(ROOT / "styles" / "packages"))
    cinematic = director.propose(
        {
            "pipeline": "cinematic",
            "aspect_ratio": "9:16",
            "quality_mode": "hero",
            "available_runtimes": ["remotion", "ffmpeg"],
            "available_providers": ["image", "video"],
        }
    )
    documentary = director.propose(
        {
            "pipeline": "documentary-montage",
            "aspect_ratio": "16:9",
            "quality_mode": "hero",
            "available_runtimes": ["remotion", "ffmpeg"],
            "available_providers": ["image", "video"],
        }
    )
    assert any(item["style_family"] == "editorial-collage" for item in cinematic)
    assert any(item["style_family"] == "editorial-collage" for item in documentary)


def test_single_entry_locks_treatment_and_runs_composed_family_qa():
    treatment = {
        "version": "1.0",
        "project_id": "offline-pilot",
        "production_family": "cinematic",
        "pipeline": "cinematic",
        "style_family": "cinematic-generative",
        "style_id": "premium-minimalist",
        "style_package_version": "1.0.0",
        "taste_profile": {
            "design_read": "Measured editorial weather film.",
            "visual_variance": 4,
            "motion_intensity": 4,
            "information_density": 3,
            "palette_discipline": "navy and amber",
            "layout_variation": "map and hero frame",
            "reference_strategy": "approved references",
            "anti_patterns": ["generic montage"],
            "quality_gates": ["hero frame reads"],
        },
        "reference_strategy": {"mode": "none", "references": [], "notes": "No external reference."},
        "narrative_structure": {"type": "timeline"},
        "visual_language": {"palette": ["#0B1F3A"], "composition": "hero-led", "texture": "fine grain"},
        "typography_system": {
            "title_font": "Noto Sans CJK SC",
            "body_font": "Noto Sans CJK SC",
            "title_policy": "overlay",
            "safe_zone_policy": "top-third",
        },
        "motion_language": {"camera": "slow push", "transitions": ["dissolve"], "pace": "measured"},
        "audio_language": {"narration": "calm", "music": "atmospheric", "sfx": "wind"},
        "asset_strategy": {"default": "hybrid", "allowed": ["generated", "archival"]},
        "renderer_family": "cinematic-trailer",
        "render_runtime": "remotion",
        "composition_mode": "atelier",
        "quality_rubric": {
            "primary_family": "cinematic-generative",
            "threshold": 0.8,
            "secondary_families": ["editorial-collage"],
        },
        "fallback_policy": {"mode": "gate_required", "allowed": ["ffmpeg"], "requires_reapproval": True},
        "delivery_promise": {
            "duration_seconds": 60,
            "width": 720,
            "height": 1280,
            "fps": 30,
            "language": "zh-CN",
            "quality_floor": "presentable",
        },
    }
    locked = lock_treatment(treatment, {"id": "premium-minimalist", "version": "1.0.0", "maturity": "atelier_required"})
    ensure_delivery_promise(locked, locked["delivery_promise"])
    qa = evaluate_project(
        primary_family="cinematic-generative",
        secondary_families=["editorial-collage"],
        evidence={
            "hero_moment": 0.9,
            "lighting": 0.9,
            "camera_motivation": 0.9,
            "audio_arc": 0.9,
            "material_layering": 0.9,
            "typography_hierarchy": 0.9,
            "transition_intent": 0.9,
        },
    )
    assert locked["treatment_hash"]
    assert qa["status"] == "pass"
