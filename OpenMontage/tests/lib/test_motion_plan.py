from __future__ import annotations

import pytest

from lib.motion_plan import MotionPlanError, build_motion_plan, validate_motion_plan


def test_motion_plan_is_derived_from_scene_plan_and_treatment():
    treatment = {
        "treatment_hash": "a" * 64,
        "pipeline": "cinematic",
        "style_id": "premium-minimalist",
        "render_runtime": "remotion",
        "delivery_promise": {"duration_seconds": 3, "width": 720, "height": 1280, "fps": 30},
        "asset_strategy": {"default": "generated", "allowed": ["generated"]},
        "motion_language": {"camera": "static", "transitions": ["cut"], "pace": "quick"},
        "typography_system": {"title_policy": "overlay"},
    }
    scene_plan = {
        "version": "1.0",
        "scenes": [
            {
                "id": "s1",
                "type": "generated",
                "description": "storm map",
                "start_seconds": 0,
                "end_seconds": 3,
                "movement": "slow push",
                "transition_out": "cut",
                "title_policy": "overlay",
                "required_assets": [{"type": "video", "description": "storm", "source": "generate"}],
            }
        ],
        "metadata": {"creative_treatment_hash": "a" * 64},
    }
    plan = build_motion_plan(scene_plan, treatment)
    validate_motion_plan(plan)
    assert plan["treatment_hash"] == "a" * 64
    assert plan["scenes"][0]["required_motion"] is True
    assert plan["scenes"][0]["title_policy"] == "overlay"


def test_motion_plan_rejects_hash_mismatch():
    with pytest.raises(MotionPlanError, match="treatment hash"):
        build_motion_plan(
            {"version": "1.0", "scenes": [], "metadata": {"creative_treatment_hash": "b" * 64}},
            {"treatment_hash": "a" * 64, "pipeline": "cinematic", "style_id": "x", "render_runtime": "ffmpeg"},
        )
