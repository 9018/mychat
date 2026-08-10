from schemas.artifacts import validate_artifact


def test_render_report_records_probe_and_segment_strategy():
    validate_artifact("render_report", {
        "version": "1.0",
        "outputs": [{
            "path": "renders/final.mp4", "format": "mp4", "resolution": "1080x1920",
            "duration_seconds": 5, "ffprobe": {"codec_name": "h264"},
            "segment_strategy": "bounded_segments", "stream_copy": False,
        }],
        "resource_policy": {"max_segment_seconds": 10, "concurrency": 2},
    })
