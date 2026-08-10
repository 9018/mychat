"""Cross-pipeline creative-kernel contract checks."""

from __future__ import annotations

from typing import Any


class PipelineContractError(ValueError):
    """Raised when a pipeline cannot participate in the unified workflow."""


def treatment_stage(manifest: dict[str, Any]) -> str | None:
    stages = [stage["name"] for stage in manifest.get("stages", [])]
    if "proposal" in stages:
        return "proposal"
    if "idea" in stages:
        return "idea"
    return None


def creative_contract(manifest: dict[str, Any]) -> dict[str, Any]:
    stages = [stage["name"] for stage in manifest.get("stages", [])]
    selected = treatment_stage(manifest)
    if selected is None:
        return {"status": "not_applicable", "pipeline": manifest.get("name"), "stages": stages}
    errors: list[str] = []
    kernel = manifest.get("creative_kernel")
    if not isinstance(kernel, dict):
        errors.append("creative_kernel declaration is required")
    else:
        expected_kernel = {
            "treatment_artifact": "creative_treatment",
            "motion_plan_artifact": "motion_plan",
            "style_registry": "styles/packages",
            "family_qa": "required",
            "hero_gate": "dynamic_sample_approval",
            "standard_gate": "technical_qa",
        }
        for key, expected in expected_kernel.items():
            if kernel.get(key) != expected:
                errors.append(f"creative_kernel.{key} must be {expected!r}")
    if "scene_plan" in stages and stages.index(selected) >= stages.index("scene_plan"):
        errors.append("treatment boundary must precede scene_plan")
    if "assets" in stages and "scene_plan" not in stages:
        errors.append("assets stage requires scene_plan for motion planning")
    if "edit" in stages and "assets" not in stages:
        errors.append("edit stage requires assets")
    if "compose" in stages and not {"edit", "assets"}.issubset(stages):
        errors.append("compose stage requires edit and assets")
    alignment = manifest.get("semantic_alignment")
    if alignment is not None:
        expected_alignment = {
            "contract_artifact": "narration_visual_contract",
            "report_artifact": "semantic_qa_report",
            "contract_required_from_stage": "script",
            "evidence_required_stage": "compose",
            "report_required_before_publish": True,
        }
        if not isinstance(alignment, dict):
            errors.append("semantic_alignment must be an object")
        else:
            for key, expected in expected_alignment.items():
                if alignment.get(key) != expected:
                    errors.append(f"semantic_alignment.{key} must be {expected!r}")
            if "script" not in stages:
                errors.append("semantic_alignment requires script stage")
            if "compose" not in stages:
                errors.append("semantic_alignment requires compose stage")
    if errors:
        raise PipelineContractError(f"{manifest.get('name')}: {'; '.join(errors)}")
    result = {
        "status": "ready",
        "pipeline": manifest.get("name"),
        "treatment_stage": selected,
        "motion_plan_stage": "scene_plan" if "scene_plan" in stages else None,
        "downstream_binding_stages": [stage for stage in ("assets", "edit", "compose", "publish") if stage in stages],
        "family_qa_required": bool("compose" in stages),
    }
    if alignment is not None:
        result["semantic_alignment"] = dict(alignment)
    return result
