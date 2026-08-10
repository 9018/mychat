"""Offline representative-pilot matrix and technical preview runner."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from lib.creative_preview import render_creative_preview
from lib.family_qa import FAMILY_CHECKS, build_qa_report
from styles.style_compatibility import CompatibilityResolver
from styles.style_registry import StyleRegistry
from lib.technical_qa import validate_dynamic_sample
from lib.checkpoint import init_project
from lib.creative_treatment import lock_treatment
from lib.motion_plan import build_motion_plan
from lib.single_entry import _scene_plan_from_brief, _treatment_from_candidate


def load_pilot_scenarios(directory: str | Path) -> list[dict[str, Any]]:
    paths = sorted(Path(directory).glob("*.json"))
    scenarios = []
    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        if "primary_style" in data and "delivery" in data:
            scenarios.append(data)
    return scenarios


def plan_pilot(scenario: dict[str, Any], registry: StyleRegistry | None = None) -> dict[str, Any]:
    registry = registry or StyleRegistry()
    package = registry.get(scenario["primary_style"])
    result = CompatibilityResolver(registry).resolve(
        pipeline=scenario["pipeline_type"],
        primary_style=scenario["primary_style"],
        supporting_styles=scenario.get("supporting_styles", []),
        asset_strategies=scenario["asset_strategies"],
        aspect_ratio=scenario["aspect_ratio"],
        render_runtime=next(iter(package["runtimes"])),
        available_runtimes=package["runtimes"],
        available_providers=package["providers"],
        quality_mode=scenario["quality_mode"],
    )
    return {
        "name": scenario["name"],
        "pipeline_type": scenario["pipeline_type"],
        "style_id": package["id"],
        "style_package_version": package["version"],
        "status": result["status"],
        "family": scenario["style_family"],
        "delivery": scenario["delivery"],
        "compatibility": result,
        "source_labeling": scenario.get("source_labeling"),
    }


def render_technical_preview(
    scenario: dict[str, Any], output_path: str | Path, duration_seconds: float | None = None
) -> Path:
    """Backward-compatible entry point; new pilots are creative, not testsrc."""
    return Path(render_creative_preview(scenario, output_path, duration_seconds=duration_seconds)["path"])


def _extract_review_frames(video_path: Path, output_dir: Path, duration: float) -> list[str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamps = [max(0.2, min(duration - 0.2, value)) for value in (1.0, duration * 0.35, duration * 0.7, duration - 1.0)]
    frames: list[str] = []
    for index, timestamp in enumerate(timestamps):
        frame = output_dir / f"frame_{index:02d}.jpg"
        subprocess.run(
            ["ffmpeg", "-y", "-ss", str(timestamp), "-i", str(video_path), "-frames:v", "1", "-q:v", "2", str(frame)],
            check=True,
            capture_output=True,
        )
        frames.append(str(frame))
    return frames


def run_pilot_matrix(scenarios_dir: str | Path, output_dir: str | Path) -> dict[str, Any]:
    registry = StyleRegistry()
    reports: list[dict[str, Any]] = []
    output_dir = Path(output_dir)
    for scenario in load_pilot_scenarios(scenarios_dir):
        plan = plan_pilot(scenario, registry)
        creative = render_creative_preview(
            {**scenario, "style_package_version": plan["style_package_version"]},
            output_dir / f"{scenario['name']}.mp4",
        )
        preview = Path(creative["path"])
        technical = validate_dynamic_sample(preview, scenario["delivery"])
        frames = _extract_review_frames(preview, output_dir / f"{scenario['name']}.review", technical["duration_seconds"])
        review_packet = {
            "version": "1.0",
            "scenario": scenario["name"],
            "preview_path": str(preview),
            "provenance_path": creative["provenance_path"],
            "frame_paths": frames,
            "family": plan["family"],
            "source_labeling": plan.get("source_labeling"),
            "rubric_checks": list(FAMILY_CHECKS.get(plan["family"], ("narrative_fit", "visual_consistency", "typography_legibility"))),
            "human_review_required": True,
            "instructions": "Score each rubric check against the review frames, attach evidence paths, then record an approval.",
        }
        review_packet_path = output_dir / f"{scenario['name']}.review-packet.json"
        review_packet_path.write_text(json.dumps(review_packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        qa_report = build_qa_report(
            project_id=f"pilot-{scenario['name']}",
            primary_family=plan["family"],
            secondary_families=[],
            evidence_scores={},
            evidence_paths=[preview, *[Path(item) for item in frames], Path(creative["provenance_path"]), review_packet_path],
            technical_checks={"media_path": str(preview), "delivery_promise": scenario["delivery"], **technical},
            require_approval=True,
            require_score_provenance=True,
        )
        qa_report.update({
            "preview_kind": "creative_dynamic_local",
            "creative_status": "awaiting_human_review",
            "provenance_path": creative["provenance_path"],
            "review_packet_path": str(review_packet_path),
        })
        if plan.get("source_labeling"):
            qa_report["source_labeling"] = plan["source_labeling"]
        qa_report_path = output_dir / f"{scenario['name']}.qa_report.json"
        qa_report_path.write_text(json.dumps(qa_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        report = {
            "scenario": scenario["name"],
            "plan": plan,
            "preview_path": str(preview),
            "preview_kind": "creative_dynamic_local",
            "technical_status": "passed",
            "technical_checks": technical,
            "creative_status": "awaiting_human_review",
            "creative_block_reason": "local creative sample is ready; rubric scores and approval must be recorded from review frames",
            "provenance_path": creative["provenance_path"],
            "review_packet_path": str(review_packet_path),
            "qa_report_path": str(qa_report_path),
        }
        (output_dir / f"{scenario['name']}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        reports.append(report)
    return {"version": "1.0", "count": len(reports), "reports": reports}


def materialize_pilot_projects(
    pilot_output_dir: str | Path,
    project_root: str | Path,
) -> list[str]:
    """Materialize pilot evidence into canonical Backlot project folders.

    This deliberately preserves the creative gate: each project is visible,
    playable, and technically checked, but remains ``awaiting_human`` until a
    reviewer scores the supplied frames and records an approval.
    """
    pilot_output_dir = Path(pilot_output_dir)
    project_root = Path(project_root)
    materialized: list[str] = []
    registry = StyleRegistry()
    for report_path in sorted(pilot_output_dir.glob("*.json")):
        if report_path.name.endswith((".qa_report.json", ".review-packet.json")):
            continue
        report = json.loads(report_path.read_text(encoding="utf-8"))
        if not isinstance(report, dict) or not report.get("scenario") or not report.get("plan"):
            continue
        scenario = report["scenario"]
        plan = report["plan"]
        project_id = f"pilot-{scenario}"
        project_dir = init_project(
            project_id,
            title=f"Representative pilot · {scenario}",
            pipeline_type=plan["pipeline_type"],
            pipeline_dir=project_root,
            style_id=plan["style_id"],
        )
        (project_dir / "verify").mkdir(parents=True, exist_ok=True)

        preview_src = Path(report["preview_path"])
        preview_dst = project_dir / "renders" / "creative-preview.mp4"
        shutil.copy2(preview_src, preview_dst)
        provenance_src = Path(report["provenance_path"])
        provenance_dst = project_dir / "artifacts" / "provenance.json"
        shutil.copy2(provenance_src, provenance_dst)
        packet_src = Path(report["review_packet_path"])
        packet = json.loads(packet_src.read_text(encoding="utf-8"))
        frame_paths: list[str] = []
        for index, raw_frame in enumerate(packet.get("frame_paths", []), start=1):
            frame_dst = project_dir / "verify" / f"frame_{index:02d}.jpg"
            shutil.copy2(Path(raw_frame), frame_dst)
            frame_paths.append(frame_dst.relative_to(project_dir).as_posix())

        package = registry.get(plan["style_id"], plan["style_package_version"])
        candidate = {
            "style_id": plan["style_id"],
            "style_package_version": plan["style_package_version"],
            "style_family": plan["family"],
            "composition_modes": package["composition_modes"],
            "asset_strategies": package["asset_strategies"][:2],
            "render_runtime": plan["compatibility"]["render_runtime"],
        }
        brief = {
            **plan["delivery"],
            "pipeline": plan["pipeline_type"],
            "production_family": plan["family"],
            "style_family": plan["family"],
            "quality_mode": "hero",
            "topic": scenario,
            "design_read": f"{plan['style_id']} representative creative pilot",
        }
        treatment = lock_treatment(
            _treatment_from_candidate(
                project_id=project_id,
                pipeline=plan["pipeline_type"],
                brief=brief,
                candidate=candidate,
                package=package,
            ),
            {"id": package["id"], "version": package["version"], "maturity": package["maturity"]},
        )
        scene_plan = _scene_plan_from_brief(brief, treatment)
        motion_plan = build_motion_plan(scene_plan, treatment)
        artifacts = project_dir / "artifacts"
        artifacts.joinpath("creative_treatment.json").write_text(
            json.dumps(treatment, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        artifacts.joinpath("scene_plan.json").write_text(
            json.dumps(scene_plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        artifacts.joinpath("motion_plan.json").write_text(
            json.dumps(motion_plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        candidates = [
            {"id": "pilot-candidate-1", "style_id": plan["style_id"], "prompt": f"{scenario}: editorial opening", "seed": 101},
            {"id": "pilot-candidate-2", "style_id": plan["style_id"], "prompt": f"{scenario}: data-led alternate", "seed": 202},
        ]
        artifacts.joinpath("style-candidates.json").write_text(
            json.dumps({"candidates": candidates, "compatibility": plan["compatibility"]}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        bakeoff = {
            "version": "1.0",
            "treatment_hash": treatment["treatment_hash"],
            "style_id": plan["style_id"],
            "quality_mode": "hero",
            "candidates": candidates,
            "status": "awaiting_approval",
            "selected_candidate": None,
            "delivery_promise": plan["delivery"],
            "preview_path": "renders/creative-preview.mp4",
            "review_packet_path": "artifacts/review-packet.json",
        }
        artifacts.joinpath("style-bakeoff.json").write_text(
            json.dumps(bakeoff, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

        packet["preview_path"] = "renders/creative-preview.mp4"
        packet["provenance_path"] = "artifacts/provenance.json"
        packet["frame_paths"] = frame_paths
        packet["review_status"] = "awaiting_human_review"
        packet_dst = artifacts / "review-packet.json"
        packet_dst.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        qa = json.loads(Path(report["qa_report_path"]).read_text(encoding="utf-8"))
        qa["project_id"] = project_id
        qa["provenance_path"] = "artifacts/provenance.json"
        qa["review_packet_path"] = "artifacts/review-packet.json"
        qa["evidence"] = [
            {**item, "path": "renders/creative-preview.mp4" if Path(item["path"]).suffix == ".mp4" else item["path"]}
            for item in qa.get("evidence", [])
        ]
        for item in qa["evidence"]:
            source_name = Path(item["path"]).name
            if source_name.startswith("frame_") and source_name.endswith(".jpg"):
                item["path"] = f"verify/{source_name}"
            elif source_name.endswith(".provenance.json"):
                item["path"] = "artifacts/provenance.json"
            elif source_name.endswith(".review-packet.json"):
                item["path"] = "artifacts/review-packet.json"
        artifacts.joinpath("qa_report.json").write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        asset_manifest = {
            "version": "1.0",
            "assets": [{"id": "pilot-preview", "type": "video", "path": "renders/creative-preview.mp4", "scene_id": "s01", "source_tool": "creative_preview", "provider": "local-procedural"}],
            "total_cost_usd": 0,
        }
        artifacts.joinpath("asset_manifest.json").write_text(json.dumps(asset_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        checkpoint = {
            "version": "1.0",
            "project_id": project_id,
            "pipeline_type": plan["pipeline_type"],
            "stage": "assets",
            "status": "awaiting_human",
            "timestamp": "2026-08-10T00:00:00+00:00",
            "style_id": plan["style_id"],
            "human_approval_required": True,
            "human_approved": False,
            "artifacts": {"asset_manifest": "artifacts/asset_manifest.json", "qa_report": "artifacts/qa_report.json", "style_bakeoff": "artifacts/style-bakeoff.json"},
            "review": {"status": "awaiting_human_review", "packet": "artifacts/review-packet.json", "instruction": "Score the family rubric from verify/*.jpg and record approval before provider/final render."},
        }
        (project_dir / "checkpoint_assets.json").write_text(json.dumps(checkpoint, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        materialized.append(str(project_dir))
    return materialized
