from __future__ import annotations

import json

import pytest

from lib.single_entry import create_single_entry_plan
from lib.checkpoint import CheckpointValidationError, write_checkpoint


def test_single_entry_creates_project_treatment_and_candidate_artifacts(tmp_path):
    result = create_single_entry_plan(
        project_id="weather-pilot",
        title="Weather pilot",
        pipeline="cinematic",
        brief={"topic": "Typhoon warning", "aspect_ratio": "9:16", "quality_mode": "hero"},
        project_root=tmp_path,
        available_runtimes=["ffmpeg"],
        available_providers=["image", "video"],
    )
    project = tmp_path / "weather-pilot"
    assert result["status"] == "atelier_required"
    assert result["selected_style_id"]
    assert (project / "project.json").exists()
    treatment_path = project / "artifacts" / "creative_treatment.json"
    candidates_path = project / "artifacts" / "style-candidates.json"
    assert treatment_path.exists()
    assert candidates_path.exists()
    assert (project / "artifacts" / "style-bakeoff.json").exists()
    assert (project / "artifacts" / "scene_plan.json").exists()
    assert (project / "artifacts" / "motion_plan.json").exists()
    treatment = json.loads(treatment_path.read_text(encoding="utf-8"))
    assert treatment["delivery_promise"]["width"] == 720
    assert treatment["delivery_promise"]["height"] == 1280
    assert result["motion_plan"]["treatment_hash"] == treatment["treatment_hash"]


def test_single_entry_writes_narration_visual_contract_and_binds_scene_claims(tmp_path):
    result = create_single_entry_plan(
        project_id="contract-pilot",
        title="Contract pilot",
        pipeline="animated-explainer",
        brief={
            "topic": "Typhoon warning",
            "quality_mode": "standard",
            "claims": [
                {
                    "id": "claim-date",
                    "section_id": "s1",
                    "narration_text": "8月10日起风雨增强",
                    "claim_type": "time",
                    "start_seconds_target": 0,
                    "end_seconds_target": 4,
                    "must_show": True,
                    "precision": "exact",
                    "representation_mode": "deterministic_graphic",
                    "required_visual_tokens": ["8月10日"],
                    "forbidden_substitutions": [],
                    "source_ref": "brief",
                }
            ],
            "scenes": [
                {"id": "s1", "type": "text_card", "description": "Date", "duration": 4, "script_section_id": "s1"}
            ],
        },
        project_root=tmp_path,
        available_runtimes=["ffmpeg"],
        available_providers=["image"],
    )
    project = tmp_path / "contract-pilot"
    contract_path = project / "artifacts" / "narration_visual_contract.json"
    assert contract_path.exists()
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    assert result["narration_visual_contract"]["claims"][0]["id"] == "claim-date"
    assert contract["claims"][0]["id"] == "claim-date"
    scene_plan = json.loads((project / "artifacts" / "scene_plan.json").read_text(encoding="utf-8"))
    assert scene_plan["scenes"][0]["claim_ids"] == ["claim-date"]


def test_locked_treatment_is_required_by_downstream_checkpoints(tmp_path):
    result = create_single_entry_plan(
        project_id="binding-pilot",
        title="Binding pilot",
        pipeline="cinematic",
        brief={"topic": "Binding", "quality_mode": "standard"},
        project_root=tmp_path,
        available_runtimes=["ffmpeg"],
        available_providers=["image", "video"],
    )
    project = tmp_path / "binding-pilot"
    with pytest.raises(CheckpointValidationError, match="not bound"):
        write_checkpoint(
            tmp_path,
            "binding-pilot",
            "scene_plan",
            "in_progress",
            {"scene_plan": {"version": "1.0", "scenes": [{"id": "s1", "type": "generated", "description": "x", "start_seconds": 0, "end_seconds": 1}]}},
            pipeline_type="cinematic",
        )

    treatment = json.loads((project / "artifacts" / "creative_treatment.json").read_text(encoding="utf-8"))
    scene_plan = {
        "version": "1.0",
        "scenes": [{"id": "s1", "type": "generated", "description": "x", "start_seconds": 0, "end_seconds": 1}],
        "metadata": {"creative_treatment_hash": treatment["treatment_hash"]},
    }
    write_checkpoint(
        tmp_path,
        "binding-pilot",
        "scene_plan",
        "in_progress",
        {"scene_plan": scene_plan},
        pipeline_type="cinematic",
    )


def test_hero_assets_cannot_bypass_dynamic_bakeoff(tmp_path):
    create_single_entry_plan(
        project_id="hero-gate",
        title="Hero gate",
        pipeline="cinematic",
        brief={"topic": "Gate", "quality_mode": "hero"},
        project_root=tmp_path,
        available_runtimes=["ffmpeg"],
        available_providers=["image", "video"],
    )
    import json
    treatment = json.loads((tmp_path / "hero-gate" / "artifacts" / "creative_treatment.json").read_text())
    with pytest.raises(CheckpointValidationError, match="approved style-bakeoff"):
        write_checkpoint(
            tmp_path,
            "hero-gate",
            "assets",
            "in_progress",
            {
                "asset_manifest": {
                    "version": "1.0", "assets": [], "total_cost_usd": 0.0,
                    "metadata": {"creative_treatment_hash": treatment["treatment_hash"]},
                },
                "motion_plan": {
                    "version": "1.0", "pipeline": treatment["pipeline"],
                    "style_id": treatment["style_id"], "render_runtime": treatment["render_runtime"],
                    "treatment_hash": treatment["treatment_hash"],
                    "scenes": [{"scene_id": "s1", "start_seconds": 0, "end_seconds": 1,
                                "movement": "static", "transition": "cut", "asset_strategy": "procedural",
                                "required_motion": False, "title_policy": "overlay"}],
                },
            },
            pipeline_type="cinematic",
        )
