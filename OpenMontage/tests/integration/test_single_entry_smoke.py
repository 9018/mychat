from pathlib import Path

from lib.checkpoint import get_next_stage, init_project, read_checkpoint, write_checkpoint
from lib.pipeline_loader import load_pipeline
from schemas.artifacts import validate_artifact
from tools.publishers.export_bundle import ExportBundle


def test_vox_collage_single_entry_offline_closes_over(tmp_path):
    manifest = load_pipeline("vox-collage")
    assert [stage["name"] for stage in manifest["stages"]] == [
        "research", "proposal", "script", "scene_plan", "assets", "edit", "compose", "publish"
    ]

    project_id = "offline-smoke"
    project_dir = init_project(
        project_id,
        title="Offline smoke",
        pipeline_type="vox-collage",
        pipeline_dir=tmp_path,
        style_id="vox-paper-collage",
    )
    write_checkpoint(
        tmp_path, project_id, "assets", "in_progress", {},
        metadata={"provider": "self_hosted_gateway", "request_id": "fixture-task-001"},
    )
    checkpoint = read_checkpoint(tmp_path, project_id, "assets")
    assert checkpoint["metadata"]["request_id"] == "fixture-task-001"
    assert get_next_stage(tmp_path, project_id, "vox-collage") == "research"

    video = project_dir / "renders" / "final.mp4"
    video.write_bytes(b"fixture-video")
    result = ExportBundle().execute({
        "video_path": str(video),
        "title": "Offline smoke",
        "project_name": project_id,
        "export_dir": str(project_dir / "exports"),
        "output_mirror_root": str(tmp_path / "outputs"),
        "timestamp": "2026-01-01T00:00:00Z",
    })
    assert result.success
    assert (tmp_path / "outputs" / project_id / "output.mp4").exists()
    validate_artifact("publish_log", result.data["publish_log"])
