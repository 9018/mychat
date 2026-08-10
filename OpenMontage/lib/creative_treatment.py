"""Creative treatment loading, validation, locking, and hashing."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import jsonschema

from schemas.artifacts import load_schema


class DeliveryPromiseMismatch(ValueError):
    """Raised when rendering no longer matches the approved delivery."""


class TreatmentBindingError(ValueError):
    """Raised when a downstream artifact is not bound to the approved treatment."""


def ensure_hero_bakeoff_approval(
    project_dir: str | Path,
    stage: str,
    treatment: dict[str, Any],
) -> None:
    """Prevent atelier/hero assets from bypassing an approved dynamic sample."""
    if stage not in {"assets", "edit", "compose"}:
        return
    if treatment.get("composition_mode") != "atelier":
        return
    path = Path(project_dir) / "artifacts" / "style-bakeoff.json"
    if not path.is_file():
        raise TreatmentBindingError(f"{stage} requires an approved style-bakeoff")
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
        from lib.style_bakeoff import validate_bakeoff

        validate_bakeoff(record, current_treatment_hash=treatment.get("treatment_hash"))
    except Exception as exc:
        raise TreatmentBindingError(f"{stage} requires a current approved style-bakeoff: {exc}") from exc


def validate_treatment(data: dict[str, Any]) -> None:
    """Validate a treatment against the canonical artifact schema."""
    jsonschema.validate(instance=data, schema=load_schema("creative_treatment"))


def load_treatment(path: str | Path) -> dict[str, Any]:
    """Load and validate a JSON treatment from disk."""
    source = Path(path)
    data = json.loads(source.read_text(encoding="utf-8"))
    validate_treatment(data)
    return data


def _canonical_json(data: dict[str, Any]) -> bytes:
    return json.dumps(
        data,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def treatment_hash(
    data: dict[str, Any],
    *,
    exclude_keys: Iterable[str] = (),
) -> str:
    """Return a stable SHA-256 hash for a treatment."""
    excluded = set(exclude_keys)
    payload = {key: value for key, value in data.items() if key not in excluded}
    return hashlib.sha256(_canonical_json(payload)).hexdigest()


def lock_treatment(
    data: dict[str, Any],
    style_snapshot: dict[str, Any],
) -> dict[str, Any]:
    """Attach an immutable style snapshot and treatment hash."""
    locked = copy.deepcopy(data)
    locked["style_snapshot"] = copy.deepcopy(style_snapshot)
    locked.pop("treatment_hash", None)
    validate_treatment(locked)
    locked["treatment_hash"] = treatment_hash(locked)
    validate_treatment(locked)
    return locked


def ensure_delivery_promise(
    treatment: dict[str, Any],
    expected: dict[str, Any],
) -> None:
    """Ensure a render request matches the treatment's approved delivery."""
    approved = treatment.get("delivery_promise", {})
    fields = ("duration_seconds", "width", "height", "fps", "language", "quality_floor")
    mismatches = [
        field for field in fields
        if approved.get(field) != expected.get(field)
    ]
    if mismatches:
        raise DeliveryPromiseMismatch(
            "delivery promise mismatch: " + ", ".join(mismatches)
        )


def treatment_from_project(project_dir: str | Path) -> dict[str, Any] | None:
    """Load the project treatment if one exists, otherwise return ``None``."""
    path = Path(project_dir) / "artifacts" / "creative_treatment.json"
    if not path.exists():
        return None
    return load_treatment(path)


def _artifact_treatment_hash(stage: str, artifact: dict[str, Any]) -> str | None:
    if artifact.get("treatment_hash"):
        return str(artifact["treatment_hash"])
    metadata = artifact.get("metadata")
    if isinstance(metadata, dict) and metadata.get("creative_treatment_hash"):
        return str(metadata["creative_treatment_hash"])
    if stage == "proposal":
        plan = artifact.get("production_plan")
        if isinstance(plan, dict) and plan.get("creative_treatment_hash"):
            return str(plan["creative_treatment_hash"])
    return None


def ensure_artifact_treatment_binding(
    stage: str,
    artifact: dict[str, Any],
    treatment: dict[str, Any],
) -> None:
    """Require proposal and downstream creative artifacts to carry the hash."""
    if stage in {"research", "idea"}:
        return
    expected = treatment.get("treatment_hash")
    if not isinstance(expected, str) or len(expected) != 64:
        raise TreatmentBindingError("locked treatment has no valid treatment_hash")
    actual = _artifact_treatment_hash(stage, artifact)
    if actual != expected:
        raise TreatmentBindingError(
            f"{stage} artifact is not bound to the active creative treatment "
            f"(expected {expected}, got {actual})"
        )


def ensure_motion_plan_binding(
    stage: str,
    artifacts: dict[str, Any],
    treatment: dict[str, Any],
) -> None:
    """Require the executable motion plan once scene planning is complete."""
    if stage not in {"assets", "edit", "compose"}:
        return
    plan = artifacts.get("motion_plan")
    plan_hash = plan.get("treatment_hash") if isinstance(plan, dict) else None
    metadata = artifacts.get("metadata") if isinstance(artifacts.get("metadata"), dict) else {}
    plan_hash = plan_hash or metadata.get("motion_plan_treatment_hash")
    if plan_hash != treatment.get("treatment_hash"):
        raise TreatmentBindingError(
            f"{stage} requires a motion_plan bound to the active treatment"
        )
