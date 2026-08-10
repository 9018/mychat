from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from lib.creative_treatment import (
    DeliveryPromiseMismatch,
    TreatmentBindingError,
    ensure_artifact_treatment_binding,
    ensure_motion_plan_binding,
    ensure_delivery_promise,
    lock_treatment,
    load_treatment,
    treatment_hash,
    validate_treatment,
)
from schemas.artifacts import validate_artifact


def valid_treatment() -> dict:
    return {
        "version": "1.0",
        "project_id": "typhoon-13",
        "production_family": "hybrid",
        "pipeline": "hybrid",
        "style_family": "cinematic-generative",
        "style_id": "premium-minimalist",
        "style_package_version": "1.0.0",
        "taste_profile": {
            "design_read": "Editorial weather alert with controlled tension.",
            "visual_variance": 4,
            "motion_intensity": 4,
            "information_density": 4,
            "palette_discipline": "Deep blue, warning amber, restrained red.",
            "layout_variation": "Map, atmospheric detail, and typography-led alert frames.",
            "reference_strategy": "Use approved weather-map and editorial references.",
            "anti_patterns": ["generic stock montage"],
            "quality_gates": ["Weather facts remain legible in every hero frame."],
        },
        "reference_strategy": {
            "mode": "reference_derived",
            "references": ["references/weather-editorial.jpg"],
            "notes": "Reference informs composition, not literal copying.",
        },
        "narrative_structure": {"type": "timeline", "beats": ["arrival", "impact", "temperature"]},
        "visual_language": {
            "palette": ["#0B1F3A", "#F59E0B", "#E11D48"],
            "composition": "editorial weather desk with atmospheric inserts",
            "texture": "fine grain and restrained paper map overlays",
        },
        "typography_system": {
            "title_font": "Noto Sans CJK SC",
            "body_font": "Noto Sans CJK SC",
            "title_policy": "overlay",
            "safe_zone_policy": "top-third or lower-third, scene-specific",
        },
        "motion_language": {
            "camera": "slow push and controlled map drift",
            "transitions": ["match_cut", "map_wipe", "dissolve"],
            "pace": "measured escalation",
        },
        "audio_language": {
            "narration": "calm authoritative Chinese news voice",
            "music": "low atmospheric pulse",
            "sfx": "subtle wind and weather texture",
        },
        "asset_strategy": {
            "default": "hybrid",
            "allowed": ["archival", "user_source", "generated", "reconstructed", "procedural"],
            "per_scene": {
                "scene-01": {"source": "generated", "labeling": "illustrative"},
                "scene-02": {"source": "archival", "labeling": "source-credit"},
            },
        },
        "renderer_family": "cinematic-trailer",
        "render_runtime": "remotion",
        "composition_mode": "atelier",
        "quality_rubric": {
            "primary_family": "cinematic-generative",
            "threshold": 0.8,
            "secondary_families": ["documentary-archive"],
        },
        "fallback_policy": {
            "mode": "gate_required",
            "allowed": ["ffmpeg"],
            "requires_reapproval": True,
        },
        "delivery_promise": {
            "duration_seconds": 60,
            "width": 720,
            "height": 1280,
            "fps": 30,
            "language": "zh-CN",
            "quality_floor": "presentable",
        },
        "extensions": {"weather": {"alert_level": "high"}},
    }


def test_valid_treatment_is_schema_valid_and_round_trips(tmp_path: Path):
    treatment = valid_treatment()
    validate_treatment(treatment)
    validate_artifact("creative_treatment", treatment)

    path = tmp_path / "creative_treatment.json"
    path.write_text(json.dumps(treatment, ensure_ascii=False), encoding="utf-8")
    assert load_treatment(path)["project_id"] == "typhoon-13"
    assert treatment_hash(treatment) == treatment_hash(json.loads(path.read_text(encoding="utf-8")))


def test_treatment_requires_style_package_version():
    treatment = valid_treatment()
    del treatment["style_package_version"]
    with pytest.raises(jsonschema.ValidationError):
        validate_treatment(treatment)


def test_treatment_rejects_silent_fallback():
    treatment = valid_treatment()
    treatment["fallback_policy"] = {
        "mode": "automatic",
        "allowed": ["ffmpeg"],
        "requires_reapproval": False,
    }
    with pytest.raises(jsonschema.ValidationError):
        validate_treatment(treatment)


def test_treatment_allows_mixed_families_and_generated_documentary_support():
    treatment = valid_treatment()
    treatment["production_family"] = "documentary"
    treatment["pipeline"] = "documentary-montage"
    treatment["style_family"] = "documentary-archive"
    treatment["asset_strategy"]["allowed"] = ["archival", "generated", "reconstructed", "procedural"]
    treatment["quality_rubric"] = {
        "primary_family": "documentary-archive",
        "threshold": 0.8,
        "secondary_families": ["cinematic-generative"],
    }
    validate_treatment(treatment)


def test_lock_treatment_adds_style_snapshot_and_hash():
    treatment = valid_treatment()
    locked = lock_treatment(
        treatment,
        {
            "id": "premium-minimalist",
            "version": "1.0.0",
            "maturity": "quality_verified",
        },
    )
    assert locked["style_snapshot"] == {
        "id": "premium-minimalist",
        "version": "1.0.0",
        "maturity": "quality_verified",
    }
    assert locked["treatment_hash"] == treatment_hash(locked, exclude_keys={"treatment_hash"})


def test_treatment_delivery_promise_is_hard_bound():
    treatment = valid_treatment()
    ensure_delivery_promise(
        treatment,
        {
            "duration_seconds": 60,
            "width": 720,
            "height": 1280,
            "fps": 30,
            "language": "zh-CN",
            "quality_floor": "presentable",
        },
    )
    with pytest.raises(DeliveryPromiseMismatch):
        ensure_delivery_promise(
            treatment,
            {
                "duration_seconds": 60,
                "width": 1920,
                "height": 1080,
                "fps": 30,
                "language": "zh-CN",
                "quality_floor": "presentable",
            },
        )


def test_downstream_artifact_must_reference_locked_treatment():
    locked = lock_treatment(
        valid_treatment(),
        {"id": "premium-minimalist", "version": "1.0.0", "maturity": "quality_verified"},
    )
    ensure_artifact_treatment_binding(
        "scene_plan",
        {"metadata": {"creative_treatment_hash": locked["treatment_hash"]}},
        locked,
    )
    with pytest.raises(TreatmentBindingError):
        ensure_artifact_treatment_binding(
            "scene_plan",
            {"metadata": {"creative_treatment_hash": "0" * 64}},
            locked,
        )


def test_assets_edit_and_compose_require_motion_plan():
    locked = lock_treatment(
        valid_treatment(),
        {"id": "premium-minimalist", "version": "1.0.0", "maturity": "quality_verified"},
    )
    with pytest.raises(TreatmentBindingError, match="motion_plan"):
        ensure_motion_plan_binding("assets", {}, locked)
    ensure_motion_plan_binding("assets", {"motion_plan": {"treatment_hash": locked["treatment_hash"]}}, locked)
