"""Canvas-aware typography measurement and collision checks."""

from __future__ import annotations

import math
from typing import Any


ROLE_RULES = {
    "title": {"min_size": 28, "max_size": 112, "line_height": 1.12, "weight": 0.92},
    "subtitle": {"min_size": 22, "max_size": 64, "line_height": 1.2, "weight": 0.9},
    "body": {"min_size": 18, "max_size": 46, "line_height": 1.35, "weight": 0.88},
    "caption": {"min_size": 14, "max_size": 32, "line_height": 1.25, "weight": 0.86},
}


def _glyph_width(character: str, font_size: float, weight: float) -> float:
    # CJK/full-width glyphs occupy one em; Latin and punctuation use a
    # narrower estimate. This remains deterministic when font files are not
    # installed, while the browser renderer performs final pixel measurement.
    if ord(character) > 0x2E80 or character in "，。！？：；“”‘’（）《》、":
        return font_size * weight
    return font_size * weight * 0.56


def measure_text_layout(
    text: str,
    *,
    canvas_width: int,
    canvas_height: int,
    role: str,
    max_width_ratio: float,
    safe_zone: dict[str, float],
    max_lines: int = 3,
) -> dict[str, Any]:
    if role not in ROLE_RULES:
        raise ValueError(f"unknown typography role: {role}")
    if not text:
        raise ValueError("text must not be empty")
    if not 0 < max_width_ratio <= 1:
        raise ValueError("max_width_ratio must be between 0 and 1")
    rule = ROLE_RULES[role]
    max_width = canvas_width * max_width_ratio
    zone = {
        "x": float(safe_zone["x"]) * canvas_width,
        "y": float(safe_zone["y"]) * canvas_height,
        "width": float(safe_zone["width"]) * canvas_width,
        "height": float(safe_zone["height"]) * canvas_height,
    }
    chosen: dict[str, Any] | None = None
    for size in range(int(rule["max_size"]), int(rule["min_size"]) - 1, -1):
        lines: list[str] = []
        current = ""
        current_width = 0.0
        for character in text:
            width = _glyph_width(character, size, rule["weight"])
            if current and current_width + width > max_width:
                lines.append(current)
                current = character
                current_width = width
            else:
                current += character
                current_width += width
        if current:
            lines.append(current)
        line_height = size * rule["line_height"]
        total_height = len(lines) * line_height
        if len(lines) <= max_lines and total_height <= zone["height"]:
            chosen = {
                "text": text,
                "role": role,
                "font_size": size,
                "line_height": line_height,
                "line_count": len(lines),
                "lines": lines,
                "box": {"x": zone["x"], "y": zone["y"], "width": max_width, "height": total_height},
                "canvas_width": canvas_width,
                "canvas_height": canvas_height,
                "fits": True,
            }
            break
    if chosen is None:
        size = int(rule["min_size"])
        chosen = {
            "text": text,
            "role": role,
            "font_size": size,
            "line_height": size * rule["line_height"],
            "line_count": max_lines + 1,
            "lines": [],
            "box": {"x": zone["x"], "y": zone["y"], "width": max_width, "height": zone["height"]},
            "canvas_width": canvas_width,
            "canvas_height": canvas_height,
            "fits": False,
        }
    return chosen


def _overlap(a: dict[str, float], b: dict[str, float]) -> bool:
    return not (
        a["x"] + a["width"] <= b["x"]
        or b["x"] + b["width"] <= a["x"]
        or a["y"] + a["height"] <= b["y"]
        or b["y"] + b["height"] <= a["y"]
    )


def validate_layout_collisions(layout: dict[str, Any], collision_regions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not layout.get("fits"):
        raise ValueError("typography layout does not fit its safe zone")
    collisions: list[dict[str, Any]] = []
    box = layout["box"]
    for region in collision_regions:
        target = {key: float(region[key]) for key in ("x", "y", "width", "height")}
        if max(target.values()) <= 1:
            target = {
                "x": target["x"] * layout["canvas_width"],
                "y": target["y"] * layout["canvas_height"],
                "width": target["width"] * layout["canvas_width"],
                "height": target["height"] * layout["canvas_height"],
            }
        if _overlap(box, target):
            collisions.append({"region": region.get("label", "unknown"), "box": box})
    return collisions
