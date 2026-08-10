"""Static/dynamic style bakeoff records used before batch generation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class BakeoffError(ValueError):
    """Raised when a bakeoff lacks evidence or candidate diversity."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def create_bakeoff(
    *,
    project_dir: str | Path,
    treatment_hash: str,
    style_id: str,
    candidates: list[dict[str, Any]],
    quality_mode: str = "standard",
    delivery_promise: dict[str, Any] | None = None,
    artifact_path: str | Path | None = None,
) -> dict[str, Any]:
    if not treatment_hash or len(treatment_hash) != 64:
        raise BakeoffError("bakeoff requires a locked treatment hash")
    if quality_mode == "hero" and len(candidates) < 2:
        raise BakeoffError("hero bakeoff requires at least 2 candidates")
    ids = [item.get("id") for item in candidates]
    if len(ids) != len(set(ids)):
        raise BakeoffError("bakeoff candidate IDs must be unique")
    if len({(item.get("prompt"), item.get("seed")) for item in candidates}) != len(candidates):
        raise BakeoffError("bakeoff candidates must have distinct prompt/seed pairs")
    record = {
        "version": "1.0",
        "treatment_hash": treatment_hash,
        "style_id": style_id,
        "quality_mode": quality_mode,
        "candidates": candidates,
        "status": "awaiting_dynamic_sample" if quality_mode == "hero" else "awaiting_approval",
        "selected_candidate": None,
    }
    if delivery_promise is not None:
        record["delivery_promise"] = delivery_promise
    if artifact_path is not None:
        artifact = Path(artifact_path)
        if artifact.is_file():
            record["artifact_path"] = str(artifact)
            record["artifact_hash"] = _sha256(artifact)
    target = Path(project_dir) / "artifacts" / "style-bakeoff.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return record


def approve_bakeoff(
    record: dict[str, Any],
    *,
    preview_path: str | Path,
    selected_candidate: str,
    reviewer: str,
    notes: str = "",
    delivery_promise: dict[str, Any] | None = None,
) -> dict[str, Any]:
    preview = Path(preview_path)
    if not preview.is_file():
        raise BakeoffError(f"dynamic sample does not exist: {preview}")
    if selected_candidate not in {item.get("id") for item in record.get("candidates", [])}:
        raise BakeoffError(f"unknown bakeoff candidate: {selected_candidate}")
    delivery_promise = delivery_promise or record.get("delivery_promise")
    if delivery_promise is not None:
        from lib.technical_qa import TechnicalQAError, validate_dynamic_sample

        try:
            technical = validate_dynamic_sample(preview, delivery_promise)
        except TechnicalQAError as exc:
            raise BakeoffError(f"technical sample validation failed: {exc}") from exc
        record["technical_checks"] = technical
    record.update(
        {
            "status": "approved",
            "selected_candidate": selected_candidate,
            "preview_path": str(preview),
            "preview_sha256": _sha256(preview),
            "reviewer": reviewer,
            "notes": notes,
        }
    )
    if record.get("artifact_path") and record.get("artifact_hash"):
        record["approval"] = {
            "artifact_path": record["artifact_path"],
            "artifact_hash": record["artifact_hash"],
            "treatment_hash": record["treatment_hash"],
            "preview_path": str(preview),
            "preview_sha256": record["preview_sha256"],
            "decision": "approved",
            "reviewer": reviewer,
            "notes": notes,
        }
    return record


def validate_bakeoff(
    record: dict[str, Any],
    *,
    current_artifact_path: str | Path | None = None,
    current_treatment_hash: str | None = None,
) -> dict[str, Any]:
    """Revalidate an approval against current files before a downstream gate."""
    if record.get("status") != "approved":
        raise BakeoffError("bakeoff is not approved")
    preview = Path(record.get("preview_path", ""))
    if not preview.is_file():
        raise BakeoffError(f"approved preview does not exist: {preview}")
    if _sha256(preview) != record.get("preview_sha256"):
        raise BakeoffError("approved preview hash mismatch")
    if current_treatment_hash and record.get("treatment_hash") != current_treatment_hash:
        raise BakeoffError("approved bakeoff treatment hash is stale")
    artifact_path = Path(current_artifact_path or record.get("artifact_path", ""))
    if record.get("artifact_path") or current_artifact_path:
        if not artifact_path.is_file():
            raise BakeoffError(f"approved artifact does not exist: {artifact_path}")
        if record.get("artifact_hash") != _sha256(artifact_path):
            raise BakeoffError("approved artifact hash mismatch")
    return {"valid": True, "preview_path": str(preview), "artifact_path": str(artifact_path) if artifact_path else None}
