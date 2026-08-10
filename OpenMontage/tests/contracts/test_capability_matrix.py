from __future__ import annotations

from pathlib import Path

from lib.capability_matrix import load_capability_matrix, validate_capability_matrix


def test_capability_matrix_has_complete_evidence_and_real_sources():
    root = Path(__file__).parents[2]
    matrix = load_capability_matrix(root / "docs" / "migration" / "all-style-capability-matrix.yaml")
    validate_capability_matrix(matrix, root)
    assert len(matrix["capabilities"]) >= 30
    assert {item["kind"] for item in matrix["capabilities"]} >= {
        "pipeline", "style", "tool", "runtime", "vox_capability"
    }


def test_quality_verified_entries_reference_actual_evidence():
    root = Path(__file__).parents[2]
    matrix = load_capability_matrix(root / "docs" / "migration" / "all-style-capability-matrix.yaml")
    validate_capability_matrix(matrix, root)
    for item in matrix["capabilities"]:
        if item["quality_status"] == "quality_verified":
            assert item["evidence"], item["id"]
            assert any((root / evidence).exists() for evidence in item["evidence"]), item["id"]
