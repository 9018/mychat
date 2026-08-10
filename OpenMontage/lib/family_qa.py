"""Family-aware creative QA.

Rubrics emphasize different qualities, but they do not ban a material type or
cross-family composition. A project is evaluated against its approved primary
family and any approved supporting families.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from pathlib import Path
from typing import Any

from lib.technical_qa import TechnicalQAError, validate_dynamic_sample


FAMILY_CHECKS: dict[str, tuple[str, ...]] = {
    "editorial-collage": (
        "material_layering",
        "typography_hierarchy",
        "transition_intent",
    ),
    "professional-motion": (
        "information_hierarchy",
        "typography_legibility",
        "motion_intent",
    ),
    "illustration-animation": (
        "character_continuity",
        "action_readability",
        "visual_consistency",
    ),
    "cinematic-generative": (
        "hero_moment",
        "lighting",
        "camera_motivation",
        "audio_arc",
    ),
    "documentary-archive": (
        "narrative_truth",
        "source_context",
        "labeling_strategy",
        "fact_consistency",
    ),
    "presenter-screen": (
        "ui_legibility",
        "operation_correctness",
        "speech_sync",
    ),
    "hybrid-mixed-media": (
        "transition_intent",
        "visual_consistency",
        "narrative_fit",
    ),
}


def evaluate_style_family(
    family: str,
    evidence: dict[str, float],
    *,
    threshold: float = 0.7,
) -> dict[str, Any]:
    checks = FAMILY_CHECKS.get(family, ("narrative_fit", "visual_consistency", "typography_legibility"))
    failed = [
        check for check in checks
        if float(evidence.get(check, 0.0)) < threshold
    ]
    return {
        "family": family,
        "status": "pass" if not failed else "fail",
        "threshold": threshold,
        "checks": {check: float(evidence.get(check, 0.0)) for check in checks},
        "failed_checks": failed,
    }


def evaluate_project(
    *,
    primary_family: str,
    secondary_families: list[str] | tuple[str, ...],
    evidence: dict[str, float],
    threshold: float = 0.7,
) -> dict[str, Any]:
    families = [primary_family, *secondary_families]
    reports = {
        family: evaluate_style_family(family, evidence, threshold=threshold)
        for family in dict.fromkeys(families)
    }
    return {
        "status": "pass" if all(item["status"] == "pass" for item in reports.values()) else "fail",
        "primary_family": primary_family,
        "families_checked": list(reports),
        "checks": {family: report["checks"] for family, report in reports.items()},
        "failed_checks": {
            family: report["failed_checks"]
            for family, report in reports.items()
            if report["failed_checks"]
        },
        "reports": reports,
    }


def build_qa_report(
    *,
    project_id: str,
    primary_family: str,
    secondary_families: list[str] | tuple[str, ...],
    evidence_scores: dict[str, float],
    evidence_paths: list[str | Path] | tuple[str | Path, ...],
    approvals: list[dict[str, Any]] | None = None,
    threshold: float = 0.7,
    technical_checks: dict[str, Any] | None = None,
    require_approval: bool = False,
    score_provenance: dict[str, list[str] | tuple[str, ...]] | None = None,
    require_score_provenance: bool = False,
    semantic_qa_report_ref: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a schema-valid, evidence-backed family QA artifact.

    Creative scores and real preview/evidence files are both required. Missing
    evidence is represented as ``blocked`` rather than silently passing QA.
    ``technical_checks`` is intentionally orthogonal to family scores so a
    render can be technically playable while still failing creative review.
    """
    if not project_id:
        raise ValueError("project_id is required")
    paths = [Path(path) for path in evidence_paths]
    evidence = []
    timestamp = datetime.now(timezone.utc).isoformat()
    missing = []
    for path in paths:
        if not path.is_file():
            missing.append(str(path))
            continue
        suffix = path.suffix.lower()
        kind = "frame" if suffix in {".png", ".jpg", ".jpeg", ".webp"} else "metric"
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        evidence.append({"path": str(path), "timestamp": timestamp, "kind": kind, "sha256": digest})

    creative = evaluate_project(
        primary_family=primary_family,
        secondary_families=secondary_families,
        evidence=evidence_scores,
        threshold=threshold,
    )
    failed_checks = dict(creative["failed_checks"])
    if missing:
        failed_checks["evidence"] = [f"missing:{path}" for path in missing]
    normalized_technical = dict(technical_checks or {})
    if normalized_technical.get("media_path"):
        try:
            normalized_technical.update(
                validate_dynamic_sample(
                    normalized_technical["media_path"],
                    normalized_technical.get("delivery_promise") or {},
                )
            )
            normalized_technical["status"] = "pass"
        except (TechnicalQAError, OSError, ValueError) as exc:
            normalized_technical["status"] = "fail"
            normalized_technical["error"] = str(exc)
            failed_checks["technical"] = [str(exc)]
    if require_approval and not any(item.get("decision") == "approved" for item in (approvals or [])):
        failed_checks["approval"] = ["approved human decision is required before pass"]
    if require_score_provenance:
        evidence_paths_set = {str(path) for path in paths if path.is_file()}
        missing_score_provenance = [
            check for family_checks in creative["checks"].values()
            for check in family_checks
            if not (score_provenance or {}).get(check)
            or not set(str(item) for item in (score_provenance or {}).get(check, [])).intersection(evidence_paths_set)
        ]
        if missing_score_provenance:
            failed_checks["score_provenance"] = sorted(set(missing_score_provenance))
    technical_failed = normalized_technical.get("status") == "fail"
    status = "blocked" if (
        missing
        or not evidence
        or technical_failed
        or (require_approval and "approval" in failed_checks)
        or (require_score_provenance and "score_provenance" in failed_checks)
    ) else creative["status"]
    report: dict[str, Any] = {
        "version": "1.0",
        "project_id": project_id,
        "status": status,
        "primary_family": creative["primary_family"],
        "families_checked": creative["families_checked"],
        "checks": creative["checks"],
        "evidence": evidence,
    }
    if failed_checks:
        report["failed_checks"] = failed_checks
    if approvals:
        report["approvals"] = approvals
    if technical_checks is not None:
        report["technical_checks"] = normalized_technical
    if score_provenance is not None:
        report["score_provenance"] = score_provenance
    if semantic_qa_report_ref is not None:
        report["semantic_qa_report_ref"] = dict(semantic_qa_report_ref)
    return report
