from tools.publishers.export_bundle import ExportBundle


def test_export_bundle_can_mirror_final_video(tmp_path):
    source = tmp_path / "final.mp4"
    source.write_bytes(b"video")
    mirror = tmp_path / "mirror"
    result = ExportBundle().execute({
        "video_path": str(source), "title": "Demo", "export_dir": str(tmp_path / "exports"),
        "output_mirror_root": str(mirror), "project_name": "demo", "timestamp": "2026-01-01T00:00:00Z",
    })
    assert result.success
    assert (mirror / "demo" / "output.mp4").read_bytes() == b"video"
