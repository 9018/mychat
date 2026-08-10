from __future__ import annotations

import json
from pathlib import Path

from lib.semantic_qa import build_semantic_qa_report, contract_hash
from schemas.artifacts import validate_artifact


def _contract() -> dict:
    return {
        "version": "1.0",
        "project_id": "pilot",
        "script_hash": "b" * 64,
        "delivery_promise": {"duration_seconds": 10, "width": 720, "height": 1280, "fps": 30, "language": "zh-CN"},
        "claims": [
            {
                "id": "claim-a",
                "section_id": "s1",
                "narration_text": "8月10日",
                "claim_type": "time",
                "start_seconds_target": 0,
                "end_seconds_target": 5,
                "must_show": True,
                "precision": "exact",
                "representation_mode": "deterministic_graphic",
                "required_visual_tokens": ["8月10日"],
                "forbidden_substitutions": [],
                "source_ref": "brief",
            },
            {
                "id": "claim-b",
                "section_id": "s2",
                "narration_text": "雨势增强",
                "claim_type": "warning",
                "start_seconds_target": 5,
                "end_seconds_target": 10,
                "must_show": True,
                "precision": "literal",
                "representation_mode": "diagram",
                "required_visual_tokens": ["雨势增强"],
                "forbidden_substitutions": [],
                "source_ref": "brief",
            },
        ],
        "coverage_policy": {
            "must_show_requires_evidence": True,
            "exact_requires_deterministic_support": True,
            "max_unplanned_narration_boundary_deviation_seconds": 0.25,
            "max_unapproved_speed_change_ratio": 0.03,
        },
        "metadata": {},
    }


def _scene_plan() -> dict:
    return {
        "version": "1.0",
        "scenes": [
            {"id": "s1-shot-01", "type": "generated", "description": "date", "start_seconds": 0, "end_seconds": 5, "claim_ids": ["claim-a"], "semantic_risk": "high"},
            {"id": "s2-shot-01", "type": "diagram", "description": "rain", "start_seconds": 5, "end_seconds": 10, "claim_ids": ["claim-b"], "semantic_risk": "high"},
        ],
    }


def test_semantic_qa_passes_with_evidence_and_aligned_narration(tmp_path):
    evidence_a = tmp_path / "claim-a.png"
    evidence_b = tmp_path / "claim-b.png"
    evidence_a.write_bytes(b"date evidence")
    evidence_b.write_bytes(b"rain evidence")
    report = build_semantic_qa_report(
        _contract(),
        _scene_plan(),
        evidence_by_claim={
            "claim-a": [{"timestamp": 2.0, "path": str(evidence_a), "kind": "frame"}],
            "claim-b": [{"timestamp": 7.0, "path": str(evidence_b), "kind": "frame"}],
        },
        narration_segments=[
            {"claim_id": "claim-a", "start": 0.1, "end": 4.9},
            {"claim_id": "claim-b", "start": 5.1, "end": 9.9},
        ],
    )
    assert report["status"] == "pass"
    assert report["coverage_metrics"]["must_show_coverage_ratio"] == 1.0
    assert report["claim_results"][0]["evidence_paths"] == [str(evidence_a)]
    assert report["contract_hash"] == contract_hash(_contract())
    validate_artifact("semantic_qa_report", report)


def test_semantic_qa_fails_when_must_show_claim_has_no_scene_evidence(tmp_path):
    evidence_a = tmp_path / "claim-a.png"
    evidence_a.write_bytes(b"date evidence")
    scene_plan = _scene_plan()
    scene_plan["scenes"][1]["claim_ids"] = []
    report = build_semantic_qa_report(
        _contract(),
        scene_plan,
        evidence_by_claim={"claim-a": [{"timestamp": 2.0, "path": str(evidence_a), "kind": "frame"}]},
    )
    assert report["status"] == "fail"
    assert report["coverage_metrics"]["must_show_coverage_ratio"] == 0.5
    assert "claim-b" in report["coverage_metrics"]["missing_must_show_claim_ids"]


def test_semantic_qa_blocks_missing_evidence_and_unapproved_speed_change(tmp_path):
    missing = tmp_path / "not-created.png"
    report = build_semantic_qa_report(
        _contract(),
        _scene_plan(),
        evidence_by_claim={
            "claim-a": [{"timestamp": 2.0, "path": str(missing), "kind": "frame"}],
            "claim-b": [],
        },
        speed_change_ratio=0.031,
    )
    assert report["status"] == "blocked"
    assert report["timeline_checks"]["status"] == "fail"
    assert report["timeline_checks"]["unapproved_speed_change"] is True
    assert any("missing" in item for item in report["claim_results"][0]["reviewer_note"])
