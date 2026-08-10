from __future__ import annotations

from pathlib import Path

import pytest

from lib.approval_evidence import ApprovalEvidenceError, create_approval, validate_approval


def test_approval_binds_preview_and_artifact_hash(tmp_path: Path):
    preview = tmp_path / "sample.mp4"
    preview.write_bytes(b"preview-v1")
    approval = create_approval(
        artifact_path=tmp_path / "scene_plan.json",
        artifact_hash="artifact-hash",
        preview_path=preview,
        decision="approved",
        reviewer="user",
        notes="Approved dynamic sample.",
        treatment_hash="treatment-hash",
    )
    assert approval["preview_path"] == str(preview)
    assert approval["preview_sha256"]
    assert validate_approval(approval)["valid"] is True


def test_missing_preview_invalidates_approval(tmp_path: Path):
    approval = {
        "decision": "approved",
        "reviewer": "user",
        "preview_path": str(tmp_path / "missing.mp4"),
        "preview_sha256": "abc",
        "artifact_hash": "artifact-hash",
        "treatment_hash": "treatment-hash",
    }
    with pytest.raises(ApprovalEvidenceError, match="preview"):
        validate_approval(approval)


def test_changed_preview_invalidates_old_approval(tmp_path: Path):
    preview = tmp_path / "sample.mp4"
    preview.write_bytes(b"preview-v1")
    approval = create_approval(
        artifact_path=tmp_path / "scene_plan.json",
        artifact_hash="artifact-hash",
        preview_path=preview,
        decision="approved",
        reviewer="user",
        notes="Approved.",
        treatment_hash="treatment-hash",
    )
    preview.write_bytes(b"preview-v2")
    with pytest.raises(ApprovalEvidenceError, match="hash"):
        validate_approval(approval)


def test_strict_approval_rejects_changed_artifact_and_treatment(tmp_path: Path):
    artifact = tmp_path / "scene_plan.json"
    artifact.write_text('{"version":"1.0"}', encoding="utf-8")
    preview = tmp_path / "sample.mp4"
    preview.write_bytes(b"preview-v1")
    import hashlib
    artifact_hash = hashlib.sha256(artifact.read_bytes()).hexdigest()
    approval = create_approval(
        artifact_path=artifact,
        artifact_hash=artifact_hash,
        preview_path=preview,
        decision="approved",
        reviewer="user",
        notes="Approved.",
        treatment_hash="treatment-v1",
    )
    artifact.write_text('{"version":"2.0"}', encoding="utf-8")
    with pytest.raises(ApprovalEvidenceError, match="artifact hash"):
        validate_approval(approval, strict=True, expected_treatment_hash="treatment-v1")
