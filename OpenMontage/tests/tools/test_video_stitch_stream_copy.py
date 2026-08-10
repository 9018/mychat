from tools.video.video_stitch import build_concat_plan


def test_concat_plan_allows_stream_copy_for_matching_signatures():
    sig = {"width": 1080, "height": 1920, "fps": 30, "video_codec": "h264", "pixel_format": "yuv420p", "audio_codec": "aac", "sample_rate": "48000", "audio_channels": 2}
    plan = build_concat_plan([sig, dict(sig)])
    assert plan.method == "stream_copy"
    assert plan.needs_normalization is False


def test_concat_plan_recommends_normalization_for_mismatch():
    a = {"width": 1080, "height": 1920, "fps": 30, "video_codec": "h264"}
    b = {"width": 720, "height": 1280, "fps": 24, "video_codec": "h264"}
    plan = build_concat_plan([a, b])
    assert plan.method == "normalize_then_stream_copy"
    assert plan.needs_normalization is True
