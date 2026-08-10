from __future__ import annotations

from lib.vox_collage_artifacts import export_beats, import_beats


def test_vox_roundtrip_preserves_claim_and_fact_layer_fields():
    scene_plan = {
        "version": "1.0",
        "scenes": [
            {
                "id": "beat-01-shot-01",
                "type": "generated",
                "description": "date",
                "start_seconds": 0,
                "end_seconds": 5,
                "claim_ids": ["claim-01"],
                "must_show": True,
                "fact_layer_policy": "deterministic",
                "semantic_evidence_points": [{"timestamp": 2.0, "tokens": ["8月10日"]}],
                "semantic_risk": "high",
            }
        ],
        "metadata": {"aspect_ratio": "9:16"},
    }
    restored = import_beats(export_beats(scene_plan))["scenes"][0]
    assert restored["claim_ids"] == ["claim-01"]
    assert restored["must_show"] is True
    assert restored["fact_layer_policy"] == "deterministic"
    assert restored["semantic_evidence_points"][0]["tokens"] == ["8月10日"]
    assert restored["semantic_risk"] == "high"
