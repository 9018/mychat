from __future__ import annotations

import pytest


def test_embedded_title_disables_overlay():
    from lib.title_policy import resolve_title_policy

    decision = resolve_title_policy({"text_in_image": True, "title_policy": "overlay"}, aspect_ratio="9:16")
    assert decision.policy == "embedded"
    assert decision.should_overlay is False


def test_vertical_default_width_ratio():
    from lib.title_policy import resolve_title_policy

    decision = resolve_title_policy({"title_policy": "overlay"}, aspect_ratio="9:16")
    assert decision.max_width_ratio == 0.82
    assert decision.canvas_orientation == "portrait"


def test_landscape_default_width_ratio():
    from lib.title_policy import resolve_title_policy

    decision = resolve_title_policy({"title_policy": "overlay"}, aspect_ratio="16:9")
    assert decision.max_width_ratio == 0.75
    assert decision.canvas_orientation == "landscape"


def test_safe_zone_out_of_bounds_is_rejected():
    from lib.title_policy import validate_safe_zones

    with pytest.raises(ValueError, match="safe zone"):
        validate_safe_zones([{"x": 0.8, "y": 0, "width": 0.4, "height": 0.2}])


def test_reference_aspect_ratio_must_be_close():
    from lib.title_policy import validate_reference_aspect

    assert validate_reference_aspect(1080, 1920, "9:16") is True
    with pytest.raises(ValueError, match="aspect ratio"):
        validate_reference_aspect(1920, 1080, "9:16")
