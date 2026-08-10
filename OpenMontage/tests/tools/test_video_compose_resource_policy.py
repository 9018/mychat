from tools.video.video_compose import normalize_resource_policy, split_cut_windows


def test_resource_policy_is_bounded_for_local_rendering():
    policy = normalize_resource_policy({"max_segment_seconds": 30, "concurrency": 8})
    assert policy == {"max_segment_seconds": 10, "concurrency": 2}


def test_resource_policy_has_safe_defaults():
    assert normalize_resource_policy({}) == {"max_segment_seconds": 10, "concurrency": 2}


def test_long_cut_is_split_without_timeline_drift():
    parts = split_cut_windows({"source": "a.mp4", "in_seconds": 0, "out_seconds": 25}, 10)
    assert [(p["in_seconds"], p["out_seconds"]) for p in parts] == [(0, 10), (10, 20), (20, 25)]
