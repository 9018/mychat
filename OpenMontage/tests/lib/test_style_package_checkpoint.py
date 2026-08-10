from __future__ import annotations

from lib.checkpoint import init_project


def test_init_project_accepts_executable_style_package_id(tmp_path):
    project = init_project(
        "package-style",
        title="Package style",
        pipeline_type="cinematic",
        pipeline_dir=tmp_path,
        style_id="vox-newsprint-editorial",
    )
    assert (project / "project.json").exists()
