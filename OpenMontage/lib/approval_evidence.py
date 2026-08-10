"""Version-bound evidence for human approval gates."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ApprovalEvidenceError(ValueError):
    """Raised when an approval no longer points at real evidence."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create_approval(
    *,
    artifact_path: str | Path,
    artifact_hash: str,
    preview_path: str | Path,
    decision: str,
    reviewer: str,
    notes: str,
    treatment_hash: str,
) -> dict[str, Any]:
    preview = Path(preview_path)
    if not preview.is_file():
        raise ApprovalEvidenceError(f"preview does not exist: {preview}")
    if decision not in {"approved", "rejected", "changes_requested"}:
        raise ApprovalEvidenceError(f"invalid approval decision: {decision}")
    return {
        "version": "1.0",
        "artifact_path": str(Path(artifact_path)),
        "artifact_hash": artifact_hash,
        "preview_path": str(preview),
        "preview_sha256": _sha256(preview),
        "decision": decision,
        "reviewer": reviewer,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "notes": notes,
        "treatment_hash": treatment_hash,
    }


def validate_approval(
    approval: dict[str, Any],
    *,
    strict: bool = False,
    expected_artifact_path: str | Path | None = None,
    expected_artifact_hash: str | None = None,
    expected_treatment_hash: str | None = None,
) -> dict[str, Any]:
    required = (
        "artifact_hash",
        "preview_path",
        "preview_sha256",
        "decision",
        "reviewer",
        "treatment_hash",
    )
    missing = [field for field in required if not approval.get(field)]
    if missing:
        raise ApprovalEvidenceError(f"missing approval evidence fields: {', '.join(missing)}")
    preview = Path(approval["preview_path"])
    if not preview.is_file():
        raise ApprovalEvidenceError(f"preview does not exist: {preview}")
    actual = _sha256(preview)
    if actual != approval["preview_sha256"]:
        raise ApprovalEvidenceError(
            f"preview hash mismatch: expected {approval['preview_sha256']}, got {actual}"
        )
    if strict:
        artifact_path = Path(expected_artifact_path or approval.get("artifact_path", ""))
        if not artifact_path.is_file():
            raise ApprovalEvidenceError(f"artifact does not exist: {artifact_path}")
        artifact_actual = _sha256(artifact_path)
        recorded_hash = approval.get("artifact_hash")
        if recorded_hash != artifact_actual:
            raise ApprovalEvidenceError(
                f"artifact hash mismatch: expected {recorded_hash}, got {artifact_actual}"
            )
        if expected_artifact_hash and artifact_actual != expected_artifact_hash:
            raise ApprovalEvidenceError(
                f"artifact hash mismatch: expected current {expected_artifact_hash}, got {artifact_actual}"
            )
        if expected_treatment_hash and approval.get("treatment_hash") != expected_treatment_hash:
            raise ApprovalEvidenceError(
                f"treatment hash mismatch: expected {expected_treatment_hash}, got {approval.get('treatment_hash')}"
            )
        return {
            "valid": True,
            "preview_path": str(preview),
            "preview_sha256": actual,
            "artifact_path": str(artifact_path),
            "artifact_sha256": artifact_actual,
        }
    return {"valid": True, "preview_path": str(preview), "preview_sha256": actual}
