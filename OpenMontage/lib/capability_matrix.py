"""Load and validate the auditable OpenMontage/vox capability matrix."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


ALLOWED_STATUSES = {
    "absent",
    "present",
    "configured",
    "live_verified",
    "quality_verified",
    "blocked",
    "degraded",
    "experimental",
}
REQUIRED_FIELDS = {
    "id",
    "kind",
    "owner",
    "source_path",
    "implementation_status",
    "configured_status",
    "live_status",
    "quality_status",
    "evidence",
}
VALID_KINDS = {"pipeline", "style", "tool", "runtime", "vox_capability"}


class CapabilityMatrixError(ValueError):
    """Raised when a capability matrix is incomplete or unverifiable."""


def load_capability_matrix(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    with source.open(encoding="utf-8") as handle:
        matrix = yaml.safe_load(handle)
    if not isinstance(matrix, dict):
        raise CapabilityMatrixError("capability matrix must be a mapping")
    return matrix


def validate_capability_matrix(matrix: dict[str, Any], root: str | Path) -> None:
    root = Path(root)
    capabilities = matrix.get("capabilities")
    if not isinstance(capabilities, list) or not capabilities:
        raise CapabilityMatrixError("capabilities must be a non-empty list")
    seen: set[str] = set()
    for item in capabilities:
        if not isinstance(item, dict):
            raise CapabilityMatrixError("each capability must be an object")
        missing = REQUIRED_FIELDS - set(item)
        if missing:
            raise CapabilityMatrixError(f"{item.get('id', '<unknown>')} missing {sorted(missing)}")
        identifier = item["id"]
        if not isinstance(identifier, str) or not identifier or identifier in seen:
            raise CapabilityMatrixError(f"duplicate or invalid capability id: {identifier!r}")
        seen.add(identifier)
        if item["kind"] not in VALID_KINDS:
            raise CapabilityMatrixError(f"{identifier}: invalid kind {item['kind']!r}")
        for field in ("implementation_status", "configured_status", "live_status", "quality_status"):
            if item[field] not in ALLOWED_STATUSES:
                raise CapabilityMatrixError(f"{identifier}: invalid {field} {item[field]!r}")
        source = root / item["source_path"]
        if not source.exists():
            raise CapabilityMatrixError(f"{identifier}: source_path does not exist: {item['source_path']}")
        if not isinstance(item["evidence"], list):
            raise CapabilityMatrixError(f"{identifier}: evidence must be a list")
        if item["quality_status"] == "quality_verified" and not item["evidence"]:
            raise CapabilityMatrixError(f"{identifier}: quality_verified requires evidence")
