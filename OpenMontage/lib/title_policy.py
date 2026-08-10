"""Pure title/layout decisions shared by scene planning and composition."""

from __future__ import annotations

from dataclasses import dataclass
from math import isclose
from typing import Any


@dataclass(frozen=True)
class TitleDecision:
    policy: str
    should_overlay: bool
    max_width_ratio: float
    canvas_orientation: str


def _ratio(value: str) -> float:
    try:
        width, height = (float(part) for part in value.split(":", 1))
        if width <= 0 or height <= 0:
            raise ValueError
        return width / height
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError(f"invalid aspect ratio: {value!r}") from exc


def resolve_title_policy(scene: dict[str, Any], *, aspect_ratio: str) -> TitleDecision:
    ratio = _ratio(aspect_ratio)
    orientation = "portrait" if ratio < 1 else "landscape"
    default_width = 0.82 if orientation == "portrait" else 0.75
    requested = scene.get("title_policy") or "none"
    if scene.get("text_in_image") is True or requested == "embedded":
        policy = "embedded"
    elif requested in {"overlay", "none"}:
        policy = requested
    else:
        raise ValueError(f"invalid title policy: {requested!r}")
    width = float(scene.get("title_max_width_ratio", default_width))
    if not 0 < width <= 1:
        raise ValueError("title max width ratio must be between 0 and 1")
    return TitleDecision(
        policy=policy,
        should_overlay=policy == "overlay",
        max_width_ratio=width,
        canvas_orientation=orientation,
    )


def validate_safe_zones(safe_zones: list[dict[str, Any]]) -> bool:
    for zone in safe_zones:
        values = [float(zone[key]) for key in ("x", "y", "width", "height")]
        x, y, width, height = values
        if width <= 0 or height <= 0 or x < 0 or y < 0 or x + width > 1 or y + height > 1:
            raise ValueError(f"safe zone is outside normalized canvas: {zone!r}")
    return True


def validate_reference_aspect(width: int | float, height: int | float, target_aspect_ratio: str, *, tolerance: float = 0.03) -> bool:
    if width <= 0 or height <= 0:
        raise ValueError("reference width and height must be positive")
    actual = float(width) / float(height)
    expected = _ratio(target_aspect_ratio)
    if not isclose(actual, expected, rel_tol=tolerance, abs_tol=0.0):
        raise ValueError(
            f"reference aspect ratio {actual:.4f} does not match target {target_aspect_ratio}"
        )
    return True
