from __future__ import annotations

import json
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[2]


def test_qa_report_schema_requires_evidence_and_family_context():
    schema = json.loads(
        (ROOT / "schemas" / "artifacts" / "qa_report.schema.json").read_text(encoding="utf-8")
    )
    report = {
        "version": "1.0",
        "project_id": "sample",
        "status": "pass",
        "primary_family": "cinematic-generative",
        "families_checked": ["cinematic-generative", "editorial-collage"],
        "checks": {"cinematic-generative": {"hero_moment": 0.9}},
        "evidence": [{"path": "previews/sample.mp4", "timestamp": "00:00:02", "kind": "frame"}],
    }
    jsonschema.validate(report, schema)
