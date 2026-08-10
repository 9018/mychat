from __future__ import annotations

from lib.family_qa import build_qa_report, evaluate_project, evaluate_style_family
from schemas.artifacts import validate_artifact


def test_cinematic_collage_uses_both_rubrics_without_automatic_failure():
    result = evaluate_project(
        primary_family="cinematic-generative",
        secondary_families=["editorial-collage"],
        evidence={
            "hero_moment": 1.0,
            "lighting": 0.9,
            "camera_motivation": 0.9,
            "audio_arc": 0.85,
            "material_layering": 0.9,
            "typography_hierarchy": 0.85,
            "transition_intent": 0.9,
        },
    )
    assert result["status"] == "pass"
    assert set(result["families_checked"]) == {"cinematic-generative", "editorial-collage"}


def test_documentary_generated_reconstruction_uses_context_and_labeling_checks():
    result = evaluate_project(
        primary_family="documentary-archive",
        secondary_families=["cinematic-generative"],
        evidence={
            "narrative_truth": 0.9,
            "source_context": 0.9,
            "labeling_strategy": 0.85,
            "fact_consistency": 0.95,
            "camera_motivation": 0.8,
            "lighting": 0.8,
            "audio_arc": 0.8,
            "hero_moment": 0.8,
        },
    )
    assert result["status"] == "pass"
    assert result["checks"]["documentary-archive"]["labeling_strategy"] == 0.85


def test_family_qa_reports_failures_with_reasons():
    result = evaluate_style_family(
        "professional-motion",
        {"typography_legibility": 0.4, "information_hierarchy": 0.5},
    )
    assert result["status"] == "fail"
    assert result["failed_checks"]


def test_build_qa_report_requires_real_evidence(tmp_path):
    preview = tmp_path / "preview.mp4"
    preview.write_bytes(b"technical-preview")
    report = build_qa_report(
        project_id="storm-13",
        primary_family="cinematic-generative",
        secondary_families=["editorial-collage"],
        evidence_scores={
            "hero_moment": 0.9,
            "lighting": 0.9,
            "camera_motivation": 0.9,
            "audio_arc": 0.9,
            "material_layering": 0.9,
            "typography_hierarchy": 0.9,
            "transition_intent": 0.9,
        },
        evidence_paths=[preview],
        technical_checks={"playable": True, "duration_seconds": 60},
    )
    validate_artifact("qa_report", report)
    assert report["status"] == "pass"
    assert report["technical_checks"]["playable"] is True


def test_build_qa_report_blocks_missing_preview(tmp_path):
    report = build_qa_report(
        project_id="missing-preview",
        primary_family="documentary-archive",
        secondary_families=[],
        evidence_scores={
            "narrative_truth": 0.9,
            "source_context": 0.9,
            "labeling_strategy": 0.9,
            "fact_consistency": 0.9,
        },
        evidence_paths=[tmp_path / "does-not-exist.mp4"],
    )
    assert report["status"] == "blocked"
    assert "evidence" in report["failed_checks"]


def test_build_qa_report_references_semantic_report(tmp_path):
    evidence = tmp_path / "frame.png"
    evidence.write_bytes(b"frame")
    semantic = {
        "artifact_id": "semantic-qa-report",
        "artifact_path": str(tmp_path / "semantic_qa_report.json"),
        "artifact_hash": "a" * 64,
        "contract_hash": "b" * 64,
        "status": "pass",
    }
    report = build_qa_report(
        project_id="semantic-ref",
        primary_family="professional-motion",
        secondary_families=[],
        evidence_scores={"information_hierarchy": 0.9, "typography_legibility": 0.9, "motion_intent": 0.9},
        evidence_paths=[evidence],
        semantic_qa_report_ref=semantic,
    )
    assert report["semantic_qa_report_ref"]["status"] == "pass"
    validate_artifact("qa_report", report)


def test_build_qa_report_technical_media_is_validated_and_approval_is_required(tmp_path):
    preview = tmp_path / "preview.mp4"
    import subprocess
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc2=size=320x576:rate=30",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=10.2", "-t", "10.2",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(preview),
    ], check=True, capture_output=True)
    report = build_qa_report(
        project_id="approval-gate",
        primary_family="professional-motion",
        secondary_families=[],
        evidence_scores={"information_hierarchy": 0.9, "typography_legibility": 0.9, "motion_intent": 0.9},
        evidence_paths=[preview],
        approvals=[],
        require_approval=True,
        technical_checks={
            "media_path": str(preview),
            "delivery_promise": {"width": 320, "height": 576, "fps": 30, "duration_seconds": 10.2},
        },
    )
    assert report["status"] == "blocked"
    assert report["technical_checks"]["status"] == "pass"
    assert "approval" in report["failed_checks"]


def test_strict_family_qa_rejects_unproven_caller_scores(tmp_path):
    preview = tmp_path / "preview.png"
    preview.write_bytes(b"frame evidence")
    report = build_qa_report(
        project_id="strict-score-gate",
        primary_family="professional-motion",
        secondary_families=[],
        evidence_scores={"information_hierarchy": 0.95, "typography_legibility": 0.95, "motion_intent": 0.95},
        evidence_paths=[preview],
        require_score_provenance=True,
    )
    assert report["status"] == "blocked"
    assert "score_provenance" in report["failed_checks"]
