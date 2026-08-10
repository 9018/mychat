from __future__ import annotations

from lib.pipeline_loader import list_pipelines, load_pipeline
from lib.pipeline_contracts import creative_contract
from styles.style_director import StyleDirector
from styles.style_registry import StyleRegistry


def test_every_production_pipeline_has_a_treatment_boundary_and_style_candidate():
    director = StyleDirector(StyleRegistry())
    for pipeline in list_pipelines():
        manifest = load_pipeline(pipeline)
        contract = creative_contract(manifest)
        if pipeline != "framework-smoke":
            assert contract["status"] == "ready"
        if pipeline == "framework-smoke":
            continue
        stages = [stage["name"] for stage in manifest["stages"]]
        treatment_stage = "proposal" if "proposal" in stages else "idea"
        assert treatment_stage in stages, pipeline
        if "scene_plan" in stages:
            assert stages.index(treatment_stage) < stages.index("scene_plan"), pipeline
        if "assets" in stages:
            assert stages.index("scene_plan") < stages.index("assets"), pipeline
        if "compose" in stages and "assets" in stages:
            assert stages.index("assets") < stages.index("compose"), pipeline
        candidates = director.propose(
            {
                "pipeline": pipeline,
                "aspect_ratio": "9:16",
                "available_runtimes": ["ffmpeg"],
                "available_providers": ["image", "video", "mimo_tts"],
            }
        )
        assert candidates, pipeline


def test_production_pipelines_declare_narration_visual_alignment():
    for pipeline in list_pipelines():
        manifest = load_pipeline(pipeline)
        if pipeline not in {"animated-explainer", "vox-collage"}:
            continue
        alignment = manifest.get("semantic_alignment")
        assert alignment, pipeline
        assert alignment["contract_artifact"] == "narration_visual_contract"
        assert alignment["report_artifact"] == "semantic_qa_report"
