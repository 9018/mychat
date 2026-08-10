from __future__ import annotations

from pathlib import Path


def test_vox_collage_manifest_has_canonical_stage_order():
    from lib.pipeline_loader import load_pipeline

    manifest = load_pipeline("vox-collage")
    assert [stage["name"] for stage in manifest["stages"]] == [
        "research", "proposal", "script", "scene_plan", "assets", "edit", "compose", "publish"
    ]
    assert manifest["stages"][4]["human_approval_default"] is True
    assert "video_compose" in manifest["stages"][6]["required_tools"]


def test_vox_collage_manifest_declares_semantic_alignment_artifacts():
    from lib.pipeline_loader import load_pipeline

    manifest = load_pipeline("vox-collage")
    alignment = manifest["semantic_alignment"]
    assert alignment["contract_artifact"] == "narration_visual_contract"
    assert alignment["report_artifact"] == "semantic_qa_report"
    assert alignment["contract_required_from_stage"] == "script"
    assert alignment["report_required_before_publish"] is True


def test_vox_collage_creative_contract_exposes_semantic_alignment():
    from lib.pipeline_loader import load_pipeline
    from lib.pipeline_contracts import creative_contract

    contract = creative_contract(load_pipeline("vox-collage"))
    assert contract["semantic_alignment"]["contract_artifact"] == "narration_visual_contract"
    assert contract["semantic_alignment"]["report_artifact"] == "semantic_qa_report"


def test_vox_collage_required_skills_exist():
    from lib.pipeline_loader import load_pipeline

    root = Path(__file__).parents[2]
    manifest = load_pipeline("vox-collage")
    for skill in manifest["required_skills"]:
        assert (root / "skills" / f"{skill}.md").is_file(), skill


def test_vox_paper_style_is_schema_valid():
    import json
    import yaml
    import jsonschema

    root = Path(__file__).parents[2]
    style = yaml.safe_load((root / "styles/vox-paper-collage.yaml").read_text(encoding="utf-8"))
    schema = json.loads((root / "schemas/styles/playbook.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(style, schema)
