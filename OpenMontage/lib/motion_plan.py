"""Build and validate the executable scene-level motion contract."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import jsonschema

from schemas.artifacts import load_schema


class MotionPlanError(ValueError):
    """Raised when a motion plan cannot honor the locked treatment."""


def validate_motion_plan(plan: dict[str, Any]) -> None:
    jsonschema.validate(instance=plan, schema=load_schema("motion_plan"))


def build_motion_plan(scene_plan: dict[str, Any], treatment: dict[str, Any]) -> dict[str, Any]:
    expected_hash = treatment.get("treatment_hash")
    actual_hash = (scene_plan.get("metadata") or {}).get("creative_treatment_hash")
    if not expected_hash or actual_hash != expected_hash:
        raise MotionPlanError("scene plan treatment hash does not match locked treatment hash")

    default_strategy = treatment["asset_strategy"]["default"]
    allowed_strategies = set(treatment["asset_strategy"].get("allowed", []))
    scenes: list[dict[str, Any]] = []
    for scene in scene_plan.get("scenes", []):
        required_assets = scene.get("required_assets", [])
        strategies = [asset.get("source") for asset in required_assets if asset.get("source")]
        strategy = strategies[0] if strategies else default_strategy
        strategy = {
            "generate": "generated",
            "source": "user_source",
            "record": "user_source",
            "provided": "procedural",
        }.get(strategy, strategy)
        if allowed_strategies and strategy not in allowed_strategies:
            raise MotionPlanError(f"scene {scene.get('id')} uses unsupported asset strategy {strategy!r}")
        asset_types = {str(asset.get("type")) for asset in required_assets}
        required_motion = bool(asset_types & {"video", "animation", "avatar", "screen_recording"})
        scenes.append(
            {
                "scene_id": str(scene["id"]),
                "start_seconds": float(scene.get("start_seconds", 0)),
                "end_seconds": float(scene.get("end_seconds", 0)),
                "movement": str(scene.get("movement") or treatment["motion_language"]["camera"]),
                "transition": str(scene.get("transition_out") or treatment["motion_language"]["transitions"][0]),
                "asset_strategy": strategy,
                "required_motion": required_motion,
                "title_policy": str(scene.get("title_policy") or treatment["typography_system"]["title_policy"]),
                "safe_zones": deepcopy(scene.get("safe_zones", [])),
                "shot_language": deepcopy(scene.get("shot_language", {})),
            }
        )
    if not scenes:
        raise MotionPlanError("scene plan must contain at least one scene")
    plan = {
        "version": "1.0",
        "pipeline": treatment["pipeline"],
        "style_id": treatment["style_id"],
        "render_runtime": treatment["render_runtime"],
        "treatment_hash": expected_hash,
        "scenes": scenes,
    }
    validate_motion_plan(plan)
    return plan
