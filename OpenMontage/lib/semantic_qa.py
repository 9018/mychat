"""Claim-level semantic QA for narration, scene plans and final evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from schemas.artifacts import validate_artifact


EXACT_DETERMINISTIC_MODES = {
    "source_media", "deterministic_graphic", "overlay_text", "diagram",
    "character_action", "screen_action",
}


def _canonical_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def contract_hash(contract: dict[str, Any]) -> str:
    payload = json.dumps(contract, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def validate_contract(contract: dict[str, Any]) -> None:
    validate_artifact("narration_visual_contract", contract)
    claims = contract["claims"]
    ids = [claim["id"] for claim in claims]
    if len(ids) != len(set(ids)):
        raise ValueError("claim IDs must be unique")
    policy = contract["coverage_policy"]
    for claim in claims:
        if claim["end_seconds_target"] < claim["start_seconds_target"]:
            raise ValueError(f"claim {claim['id']} has reversed target interval")
        if claim["must_show"] and claim["representation_mode"] == "approved_narration_only":
            raise ValueError(f"must_show claim {claim['id']} cannot be narration-only")
        if (
            policy.get("exact_requires_deterministic_support", True)
            and claim["precision"] == "exact"
            and claim["representation_mode"] not in EXACT_DETERMINISTIC_MODES
        ):
            raise ValueError(f"exact claim {claim['id']} requires deterministic or verified source support")


def build_narration_visual_contract(
    *,
    project_id: str,
    brief: dict[str, Any],
    scene_plan: dict[str, Any],
    delivery_promise: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Create a contract and bind claims to scenes by section or explicit IDs.

    Existing briefs may not have claim atoms yet. In that compatibility case a
    non-must-show atmospheric claim is generated per scene so every new
    single-entry project still has a durable contract artifact.
    """
    raw_claims = brief.get("claims") or []
    claims: list[dict[str, Any]] = []
    if raw_claims:
        claims = [dict(item) for item in raw_claims]
    else:
        for scene in scene_plan.get("scenes", []):
            scene_id = str(scene["id"])
            claims.append({
                "id": f"claim-{scene_id}",
                "section_id": str(scene.get("script_section_id") or scene_id),
                "narration_text": str(scene.get("description", scene_id)),
                "claim_type": "summary",
                "start_seconds_target": float(scene.get("start_seconds", 0)),
                "end_seconds_target": float(scene.get("end_seconds", 0)),
                "must_show": False,
                "precision": "atmospheric",
                "representation_mode": "approved_narration_only",
                "required_visual_tokens": [str(scene.get("description", scene_id))],
                "forbidden_substitutions": [],
                "source_ref": f"brief:{brief.get('topic', project_id)}",
            })
    claims_by_section = {str(claim.get("section_id")): claim["id"] for claim in claims}
    bound_scene_plan = json.loads(json.dumps(scene_plan, ensure_ascii=False))
    for scene in bound_scene_plan.get("scenes", []):
        explicit = [str(item) for item in scene.get("claim_ids", [])]
        section_id = str(scene.get("script_section_id") or scene.get("extensions", {}).get("script_section_id", ""))
        if not explicit and section_id in claims_by_section:
            explicit = [claims_by_section[section_id]]
        if explicit:
            scene["claim_ids"] = explicit
            scene.setdefault("semantic_risk", "high" if any(
                claim.get("id") in explicit and claim.get("precision") == "exact" for claim in claims
            ) else "medium")
    script_source = brief.get("script_sections") or brief.get("script") or {
        "title": brief.get("title", project_id),
        "topic": brief.get("topic", ""),
        "claims": claims,
    }
    script_hash = str(brief.get("script_hash") or _canonical_hash(script_source))
    contract = {
        "version": "1.0",
        "project_id": project_id,
        "script_hash": script_hash,
        "delivery_promise": dict(delivery_promise),
        "claims": claims,
        "coverage_policy": {
            "must_show_requires_evidence": True,
            "exact_requires_deterministic_support": True,
            "max_unplanned_narration_boundary_deviation_seconds": 0.25,
            "max_unapproved_speed_change_ratio": 0.03,
        },
        "metadata": {"generated_by": "single_entry", "source": "brief"},
    }
    validate_contract(contract)
    return contract, bound_scene_plan


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _scene_ids_by_claim(scene_plan: dict[str, Any]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for scene in scene_plan.get("scenes", []):
        scene_id = str(scene.get("id", ""))
        for claim_id in scene.get("claim_ids", []):
            result.setdefault(str(claim_id), []).append(scene_id)
    return result


def _narration_by_claim(segments: Iterable[dict[str, Any]]) -> dict[str, dict[str, float]]:
    result: dict[str, dict[str, float]] = {}
    for segment in segments:
        claim_id = str(segment.get("claim_id", ""))
        if claim_id:
            result[claim_id] = {"start": float(segment.get("start", 0.0)), "end": float(segment.get("end", 0.0))}
    return result


def build_semantic_qa_report(
    contract: dict[str, Any],
    scene_plan: dict[str, Any],
    *,
    evidence_by_claim: dict[str, list[dict[str, Any]]] | None = None,
    narration_segments: list[dict[str, Any]] | None = None,
    speed_change_ratio: float = 0.0,
    asset_checks: dict[str, Any] | None = None,
    final_checks: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the semantic report and apply claim, timing and evidence gates."""
    validate_contract(contract)
    evidence_by_claim = evidence_by_claim or {}
    narration_by_claim = _narration_by_claim(narration_segments or [])
    scenes_by_claim = _scene_ids_by_claim(scene_plan)
    policy = contract["coverage_policy"]
    tolerance = float(policy.get("max_unplanned_narration_boundary_deviation_seconds", 0.25))
    speed_limit = float(policy.get("max_unapproved_speed_change_ratio", 0.03))
    evidence: list[dict[str, Any]] = []
    claim_results: list[dict[str, Any]] = []
    missing_must_show: list[str] = []
    exact_total = 0
    exact_accurate = 0
    has_missing_file = False

    for claim in contract["claims"]:
        claim_id = claim["id"]
        scene_ids = scenes_by_claim.get(claim_id, [])
        records = list(evidence_by_claim.get(claim_id, []))
        timestamps: list[Any] = []
        paths: list[str] = []
        notes: list[str] = []
        status = "pass"
        for record in records:
            timestamp = record.get("timestamp", 0.0)
            path = str(record.get("path", ""))
            timestamps.append(timestamp)
            paths.append(path)
            file_path = Path(path)
            if not file_path.is_file():
                has_missing_file = True
                notes.append(f"missing evidence file: {path}")
                continue
            evidence.append({
                "claim_id": claim_id,
                "path": path,
                "timestamp": timestamp,
                "kind": str(record.get("kind", "frame")),
                "sha256": _sha256(file_path),
            })
        if claim["must_show"]:
            covered = bool(scene_ids) and bool(records) and not any("missing evidence file" in note for note in notes)
            if not covered:
                status = "fail"
                missing_must_show.append(claim_id)
                if not scene_ids:
                    notes.append("must_show claim is not referenced by any scene")
                if not records:
                    notes.append("must_show claim has no evidence")
        elif not scene_ids and claim["representation_mode"] != "approved_narration_only":
            status = "fail"
            notes.append("supporting claim is not referenced by any scene")
        if claim["precision"] == "exact":
            exact_total += 1
            if status == "pass":
                exact_accurate += 1
        actual = narration_by_claim.get(claim_id)
        claim_results.append({
            "claim_id": claim_id,
            "status": status,
            "scene_ids": scene_ids,
            "actual_narration_start": actual["start"] if actual else None,
            "actual_narration_end": actual["end"] if actual else None,
            "evidence_timestamps": timestamps,
            "evidence_paths": paths,
            "observed_visual": "evidence frame supplied" if paths else "",
            "missing_tokens": [],
            "unexpected_assertions": [],
            "reviewer_note": notes,
        })

    deviations: list[float] = []
    for claim in contract["claims"]:
        actual = narration_by_claim.get(claim["id"])
        if actual:
            deviations.extend([
                abs(actual["start"] - float(claim["start_seconds_target"])),
                abs(actual["end"] - float(claim["end_seconds_target"])),
            ])
    max_deviation = max(deviations, default=0.0)
    speed_changed = float(speed_change_ratio) > speed_limit
    timeline_checks = {
        "status": "fail" if max_deviation > tolerance or speed_changed else "pass",
        "max_boundary_deviation_seconds": max_deviation,
        "boundary_tolerance_seconds": tolerance,
        "unapproved_speed_change_ratio": float(speed_change_ratio),
        "unapproved_speed_change": speed_changed,
    }
    final_checks = dict(final_checks or {})
    final_checks.setdefault("unexpected_assertions", [])
    final_checks.setdefault("status", "fail" if final_checks["unexpected_assertions"] else "pass")
    must_show_total = sum(1 for claim in contract["claims"] if claim["must_show"])
    covered = must_show_total - len(set(missing_must_show))
    coverage_metrics = {
        "must_show_total": must_show_total,
        "must_show_covered": covered,
        "must_show_coverage_ratio": covered / must_show_total if must_show_total else 1.0,
        "exact_total": exact_total,
        "exact_accurate": exact_accurate,
        "missing_must_show_claim_ids": sorted(set(missing_must_show)),
    }
    if (asset_checks or {}).get("status") == "blocked" or has_missing_file:
        status = "blocked"
    elif any(item["status"] != "pass" for item in claim_results):
        status = "fail"
    elif timeline_checks["status"] != "pass" or final_checks["status"] != "pass":
        status = "fail"
    else:
        status = "pass"
    report = {
        "version": "1.0",
        "project_id": contract["project_id"],
        "contract_hash": contract_hash(contract),
        "status": status,
        "asset_checks": dict(asset_checks or {}),
        "timeline_checks": timeline_checks,
        "final_checks": final_checks,
        "claim_results": claim_results,
        "coverage_metrics": coverage_metrics,
        "evidence": evidence,
    }
    validate_artifact("semantic_qa_report", report)
    return report
