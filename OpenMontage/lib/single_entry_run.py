"""Offline execution of the single-entry plan through a technical QA gate."""

from __future__ import annotations

import json
import hashlib
import subprocess
from pathlib import Path
from typing import Any

from lib.family_qa import build_qa_report
from lib.semantic_qa import build_semantic_qa_report
from lib.single_entry import create_single_entry_plan
from lib.technical_qa import validate_dynamic_sample


def run_single_entry_offline(
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
    """Create the canonical plan, render a local technical sample and write QA.

    The generated test-pattern media is deliberately labeled technical-only;
    the report remains ``blocked`` until real creative evidence and reviewer
    scores are supplied.
    """
    result = create_single_entry_plan(
        project_id=project_id,
        title=title,
        pipeline=pipeline,
        brief=brief,
        project_root=project_root,
        available_runtimes=available_runtimes,
        available_providers=available_providers,
        primary_style=primary_style,
    )
    project_dir = Path(result["project_dir"])
    delivery = result["treatment"]["delivery_promise"]
    preview = project_dir / "renders" / "technical-preview.mp4"
    preview.parent.mkdir(parents=True, exist_ok=True)
    duration = min(max(float(delivery.get("duration_seconds", 60)), 10.2), 15.0)
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi", "-i",
            f"testsrc2=size={delivery['width']}x{delivery['height']}:rate={delivery['fps']}",
            "-f", "lavfi", "-i", f"sine=frequency=440:duration={duration}",
            "-t", str(duration), "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest", str(preview),
        ],
        check=True,
        capture_output=True,
    )
    technical = validate_dynamic_sample(preview, delivery, min_seconds=10, max_seconds=15)
    semantic = build_semantic_qa_report(
        result["narration_visual_contract"],
        result["scene_plan"],
        evidence_by_claim={},
        asset_checks={"status": "blocked", "reason": "technical-only preview is not creative evidence"},
    )
    semantic_path = project_dir / "artifacts" / "semantic_qa_report.json"
    semantic_payload = json.dumps(semantic, ensure_ascii=False, indent=2) + "\n"
    semantic_path.write_text(semantic_payload, encoding="utf-8")
    semantic_hash = hashlib.sha256(semantic_payload.encode("utf-8")).hexdigest()
    report = build_qa_report(
        project_id=project_id,
        primary_family=result["treatment"]["quality_rubric"]["primary_family"],
        secondary_families=result["treatment"]["quality_rubric"].get("secondary_families", []),
        evidence_scores={},
        evidence_paths=[preview],
        technical_checks={"status": "pass", "preview_kind": "technical_only", **technical},
        require_score_provenance=True,
        semantic_qa_report_ref={
            "artifact_id": "semantic_qa_report",
            "artifact_path": str(semantic_path),
            "artifact_hash": semantic_hash,
            "contract_hash": semantic["contract_hash"],
            "status": semantic["status"],
        },
    )
    report["status"] = "blocked"
    report.setdefault("failed_checks", {})["creative_review"] = [
        "technical preview is not creative evidence; real dynamic sample and reviewer scores required"
    ]
    qa_path = project_dir / "artifacts" / "qa_report.json"
    qa_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result.update({
        "technical_preview_path": str(preview),
        "semantic_qa_report_path": str(semantic_path),
        "qa_report_path": str(qa_path),
        "qa_report": report,
        "semantic_qa_report": semantic,
    })
    return result
