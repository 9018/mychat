import subprocess

from tools.video.video_compose import build_render_report
from schemas.artifacts import validate_artifact


def test_build_render_report_from_real_mp4(tmp_path):
    output = tmp_path / "tiny.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=black:s=320x568:r=30", "-t", "0.5",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(output),
    ], check=True, capture_output=True)
    report = build_render_report(output, resource_policy={"max_segment_seconds": 10, "concurrency": 2})
    validate_artifact("render_report", report)
    assert report["outputs"][0]["resolution"] == "320x568"
