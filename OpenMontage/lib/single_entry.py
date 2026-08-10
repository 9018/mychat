"""Offline single-entry project planning for every registered style family."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from lib.checkpoint import init_project
from lib.creative_treatment import lock_treatment
from lib.motion_plan import build_motion_plan
from lib.semantic_qa import build_narration_visual_contract
from lib.style_bakeoff import create_bakeoff
from styles.style_director import StyleDirector
from styles.style_registry import StyleRegistry


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _treatment_from_candidate(
    *,
    project_id: str,
    pipeline: str,
    brief: dict[str, Any],
    candidate: dict[str, Any],
    package: dict[str, Any],
) -> dict[str, Any]:
    delivery = {
        "duration_seconds": brief.get("duration_seconds", 60),
        "width": brief.get("width", 720),
        "height": brief.get("height", 1280),
        "fps": brief.get("fps", 30),
        "language": brief.get("language", "zh-CN"),
        "quality_floor": brief.get("quality_floor", "presentable"),
    }
    return {
        "version": "1.0",
        "project_id": project_id,
        "production_family": brief.get("production_family", pipeline),
        "pipeline": pipeline,
        "style_family": package["family"],
        "style_id": package["id"],
        "style_package_version": package["version"],
        "taste_profile": {
            "design_read": brief.get("design_read", f"{package['id']} directed production"),
            "visual_variance": 4 if brief.get("quality_mode") == "hero" else 3,
            "motion_intensity": 4 if candidate["composition_modes"][0] != "graphics-led" else 3,
            "information_density": 4,
            "palette_discipline": "Use the locked style package palette.",
            "layout_variation": "Vary layout by narrative role, not by random templates.",
            "reference_strategy": "Use approved project references and package references.",
            "anti_patterns": ["generic template repetition", "unreviewed fallback"],
            "quality_gates": ["dynamic sample approved before batch generation"],
        },
        "reference_strategy": {
            "mode": "reference_derived" if brief.get("references") else "none",
            "references": list(brief.get("references", [])),
            "notes": "References inform the treatment and are not copied literally.",
        },
        "narrative_structure": {
            "type": brief.get("narrative_structure", "timeline"),
            "topic": brief.get("topic", ""),
        },
        "visual_language": {
            "palette": [package["id"]],
            "composition": candidate["composition_modes"][0],
            "texture": "Follow package director and prompt rules.",
        },
        "typography_system": {
            "title_font": brief.get("title_font", "package-defined"),
            "body_font": brief.get("body_font", "package-defined"),
            "title_policy": package["title_policy"][0],
            "safe_zone_policy": "scene-specific safe zones from scene_plan",
        },
        "motion_language": {
            "camera": "package-defined camera or graphic motion",
            "transitions": ["package-defined transition"],
            "pace": brief.get("pace", "narrative-led"),
        },
        "audio_language": {
            "narration": brief.get("narration", "optional approved voice"),
            "music": brief.get("music", "optional approved track"),
            "sfx": brief.get("sfx", "scene-specific restrained sound"),
        },
        "asset_strategy": {
            "default": candidate["asset_strategies"][0],
            "allowed": candidate["asset_strategies"],
        },
        "renderer_family": package["renderers"][0],
        "render_runtime": candidate["render_runtime"],
        "composition_mode": "atelier" if brief.get("quality_mode") == "hero" else "templated",
        "quality_rubric": {
            "primary_family": package["family"],
            "threshold": package["sample_gate"].get("min_score", 0.8),
            "secondary_families": list(brief.get("secondary_families", [])),
        },
        "fallback_policy": {
            "mode": "gate_required",
            "allowed": [runtime for runtime in package["runtimes"] if runtime != candidate["render_runtime"]],
            "requires_reapproval": True,
        },
        "delivery_promise": delivery,
    }


def _scene_plan_from_brief(brief: dict[str, Any], treatment: dict[str, Any]) -> dict[str, Any]:
    """Create a deterministic scene-plan scaffold bound to the treatment.

    Real providers can replace the descriptions and assets later, but the
    execution contract exists immediately: every scene has an explicit title
    policy, safe zone, movement and provenance source.
    """
    requested = brief.get("scenes") or [
        {"id": "s01", "type": "generated", "description": "Opening context", "duration": 4},
        {"id": "s02", "type": "generated", "description": "Main information beat", "duration": 8},
        {"id": "s03", "type": "text_card", "description": "Closing takeaway", "duration": 4},
    ]
    source = {"generated": "generate", "user_source": "source", "procedural": "provided", "screen": "record"}.get(
        treatment["asset_strategy"]["default"], "generate"
    )
    scenes: list[dict[str, Any]] = []
    cursor = 0.0
    for index, raw in enumerate(requested, start=1):
        item = dict(raw)
        duration = float(item.pop("duration", item.get("end_seconds", cursor + 4) - item.get("start_seconds", cursor)))
        duration = max(duration, 0.5)
        start = float(item.pop("start_seconds", cursor))
        end = float(item.pop("end_seconds", start + duration))
        scene_id = str(item.pop("id", f"s{index:02d}"))
        scene_type = str(item.pop("type", "generated"))
        scene = {
            "id": scene_id,
            "type": scene_type,
            "description": str(item.pop("description", f"Scene {index}")),
            "start_seconds": start,
            "end_seconds": end,
            "movement": item.pop("movement", treatment["motion_language"]["camera"]),
            "transition_out": item.pop("transition_out", treatment["motion_language"]["transitions"][0]),
            "title_policy": item.pop("title_policy", treatment["typography_system"]["title_policy"]),
            "safe_zones": item.pop("safe_zones", [{"x": 0.08, "y": 0.08, "width": 0.84, "height": 0.84}]),
            "required_assets": item.pop(
                "required_assets",
                [{"type": "image", "description": str(item.get("description", "scene visual")), "source": source}],
            ),
        }
        script_section_id = item.pop("script_section_id", None)
        if script_section_id:
            scene["script_section_id"] = str(script_section_id)
        if "claim_ids" in item:
            scene["claim_ids"] = [str(value) for value in item.pop("claim_ids")]
        if item:
            scene["extensions"] = item
        scenes.append(scene)
        cursor = end
    return {
        "version": "1.0",
        "style_id": treatment["style_id"],
        "scenes": scenes,
        "metadata": {
            "creative_treatment_hash": treatment["treatment_hash"],
            "delivery_promise": treatment["delivery_promise"],
        },
    }
def create_single_entry_plan(
    *,
    project_id: str,
    title: str,
    pipeline: str,
    brief: dict[str, Any],
    project_root: str | Path,
    available_runtimes: list[str],
    available_providers: list[str],
    primary_style: str | None = None,
) -> dict[str, Any]:
    """Create an offline project plan and locked treatment.

    This intentionally stops before provider calls. It is the single entry
    proposal boundary: candidates and the treatment are written to the
    canonical project directory for human approval.
    """
    root = Path(project_root)
    registry = StyleRegistry()
    director = StyleDirector(registry)
    candidates = director.propose(
        {
            **brief,
            "pipeline": pipeline,
            "available_runtimes": available_runtimes,
            "available_providers": available_providers,
        }
    )
    if primary_style:
        candidates = [item for item in candidates if item["style_id"] == primary_style] + [
            item for item in candidates if item["style_id"] != primary_style
        ]
    if not candidates:
        raise ValueError(f"no executable style candidates for pipeline {pipeline}")
    selected = candidates[0]
    package = registry.get(selected["style_id"], selected["style_package_version"])
    project_dir = init_project(
        project_id,
        title=title,
        pipeline_type=pipeline,
        pipeline_dir=root,
        style_id=selected["style_id"],
    )
    registry.snapshot_for_project(project_dir / "treatments", selected["style_id"])
    treatment = lock_treatment(
        _treatment_from_candidate(
            project_id=project_id,
            pipeline=pipeline,
            brief=brief,
            candidate=selected,
            package=package,
        ),
        {
            "id": package["id"],
            "version": package["version"],
            "maturity": package["maturity"],
        },
    )
    _write_json(project_dir / "artifacts" / "style-candidates.json", {"candidates": candidates})
    _write_json(project_dir / "artifacts" / "creative_treatment.json", treatment)
    scene_plan = _scene_plan_from_brief(brief, treatment)
    contract, scene_plan = build_narration_visual_contract(
        project_id=project_id,
        brief=brief,
        scene_plan=scene_plan,
        delivery_promise=treatment["delivery_promise"],
    )
    motion_plan = build_motion_plan(scene_plan, treatment)
    _write_json(project_dir / "artifacts" / "scene_plan.json", scene_plan)
    _write_json(project_dir / "artifacts" / "narration_visual_contract.json", contract)
    _write_json(project_dir / "artifacts" / "motion_plan.json", motion_plan)
    bakeoff = create_bakeoff(
        project_dir=project_dir,
        treatment_hash=treatment["treatment_hash"],
        style_id=selected["style_id"],
        candidates=[
            {
                "id": f"candidate-{index + 1}",
                "style_id": item["style_id"],
                "prompt": brief.get("design_read", item["style_id"]),
                "seed": index + 1,
                "render_runtime": item["render_runtime"],
            }
            for index, item in enumerate(candidates[: max(2, min(4, len(candidates)))])
        ],
        quality_mode=brief.get("quality_mode", "standard"),
        delivery_promise=treatment["delivery_promise"],
        artifact_path=project_dir / "artifacts" / "scene_plan.json",
    )
    return {
        "status": selected["status"],
        "project_dir": str(project_dir),
        "selected_style_id": selected["style_id"],
        "selected_style_package_version": selected["style_package_version"],
        "candidates": candidates,
        "treatment": treatment,
        "scene_plan": scene_plan,
        "narration_visual_contract": contract,
        "motion_plan": motion_plan,
        "bakeoff": bakeoff,
    }
