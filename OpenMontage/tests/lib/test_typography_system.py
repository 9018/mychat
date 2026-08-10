from __future__ import annotations

from lib.typography_system import measure_text_layout, validate_layout_collisions


def test_portrait_long_title_is_measured_inside_safe_zone():
    layout = measure_text_layout(
        "第13号台风白海豚即将影响河南全省风雨增强",
        canvas_width=720,
        canvas_height=1280,
        role="title",
        max_width_ratio=0.82,
        safe_zone={"x": 0.08, "y": 0.08, "width": 0.84, "height": 0.23},
    )
    assert layout["font_size"] < 100
    assert layout["line_count"] <= 3
    assert layout["fits"] is True
    validate_layout_collisions(layout, [])


def test_title_collision_is_reported_against_face_region():
    layout = measure_text_layout(
        "台风预警",
        canvas_width=720,
        canvas_height=1280,
        role="title",
        max_width_ratio=0.82,
        safe_zone={"x": 0.08, "y": 0.08, "width": 0.84, "height": 0.23},
    )
    collisions = validate_layout_collisions(
        layout,
        [{"x": 0.1, "y": 0.1, "width": 0.7, "height": 0.2, "label": "face"}],
    )
    assert collisions
