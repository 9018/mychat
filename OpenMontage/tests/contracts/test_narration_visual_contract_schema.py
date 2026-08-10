from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from lib.semantic_qa import validate_contract
from schemas.artifacts import validate_artifact


ROOT = Path(__file__).resolve().parents[2]


def _contract() -> dict:
    return {
        "version": "1.0",
        "project_id": "white-dolphin",
        "script_hash": "a" * 64,
        "delivery_promise": {
            "duration_seconds": 60,
            "width": 720,
            "height": 1280,
            "fps": 30,
            "language": "zh-CN",
        },
        "claims": [
            {
                "id": "claim-01",
                "section_id": "s01",
                "narration_text": "8月10日起河南风雨增强",
                "claim_type": "time",
                "start_seconds_target": 0,
                "end_seconds_target": 5,
                "must_show": True,
                "precision": "exact",
                "representation_mode": "deterministic_graphic",
                "required_visual_tokens": ["8月10日", "河南", "风雨增强"],
                "forbidden_substitutions": ["抽象乌云"],
                "source_ref": "user-brief",
            }
        ],
        "coverage_policy": {
            "must_show_requires_evidence": True,
            "exact_requires_deterministic_support": True,
            "max_unplanned_narration_boundary_deviation_seconds": 0.25,
            "max_unapproved_speed_change_ratio": 0.03,
        },
        "metadata": {},
    }


def test_contract_schema_is_registered_and_validates():
    contract = _contract()
    validate_artifact("narration_visual_contract", contract)
    validate_contract(contract)


def test_contract_rejects_must_show_claim_that_is_narration_only():
    contract = _contract()
    contract["claims"][0]["representation_mode"] = "approved_narration_only"
    with pytest.raises(ValueError, match="must_show"):
        validate_contract(contract)


def test_contract_schema_is_strict_about_claim_fields():
    schema = json.loads(
        (ROOT / "schemas" / "artifacts" / "narration_visual_contract.schema.json").read_text(
            encoding="utf-8"
        )
    )
    contract = _contract()
    contract["claims"][0]["unexpected"] = True
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(contract, schema)
