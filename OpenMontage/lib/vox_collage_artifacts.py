"""Deterministic adapter from canonical scene plans to Vox beats exports."""

from __future__ import annotations

from collections import OrderedDict
from typing import Any


def _beat_id(scene_id: str) -> str:
    return scene_id.split("-shot-", 1)[0]


def export_beats(scene_plan: dict[str, Any]) -> dict[str, Any]:
    scenes = sorted(
        scene_plan.get("scenes", []),
        key=lambda scene: (float(scene.get("start_seconds", 0)), str(scene.get("id", ""))),
    )
    grouped: OrderedDict[str, dict[str, Any]] = OrderedDict()
    for scene in scenes:
        scene_id = str(scene["id"])
        beat_id = _beat_id(scene_id)
        start = float(scene.get("start_seconds", 0))
        end = float(scene.get("end_seconds", start))
        beat = grouped.setdefault(
            beat_id,
            {"id": beat_id, "start": start, "end": end, "duration": 0.0, "shots": []},
        )
        beat["start"] = min(beat["start"], start)
        beat["end"] = max(beat["end"], end)
        beat["duration"] = round(beat["end"] - beat["start"], 6)
        shot: dict[str, Any] = {
            "scene_id": scene_id,
            "duration": round(end - start, 6),
            "description": scene.get("description", ""),
        }
        for key in (
            "prompt", "provider", "model", "image_path", "clip_path", "narration_audio",
            "title_policy", "safe_zones", "arc_id", "beat_role", "shot_id", "narration",
            "visual_prompt", "motion_prompt", "transition_intent", "theme_id", "texture",
            "palette", "type_rules", "image", "video", "audio", "timing", "aspect_strategy",
            "claim_ids", "must_show", "fact_layer_policy", "semantic_evidence_points", "semantic_risk",
        ):
            if key in scene:
                shot[key] = scene[key]
        if scene.get("extensions"):
            shot["extensions"] = scene["extensions"]
        beat["shots"].append(shot)

    for beat in grouped.values():
        beat["start"] = round(beat["start"], 6)
        beat["end"] = round(beat["end"], 6)
        beat["duration"] = round(beat["duration"], 6)
        beat["shots"].sort(key=lambda shot: str(shot["scene_id"]))

    metadata = scene_plan.get("metadata") or {}
    return {
        "version": "1.0",
        "aspect_ratio": metadata.get("aspect_ratio", "16:9"),
        "beats": list(grouped.values()),
    }


def import_beats(beats: dict[str, Any]) -> dict[str, Any]:
    """Convert Vox beats back into a canonical scene plan without losing extensions."""
    scenes: list[dict[str, Any]] = []
    for beat in beats.get("beats", []):
        for index, shot in enumerate(beat.get("shots", []), start=1):
            scene_id = str(shot.get("scene_id") or shot.get("shot_id") or f"{beat['id']}-shot-{index:02d}")
            duration = float(shot.get("duration", beat.get("duration", 0)))
            start = float(beat.get("start", 0))
            scene: dict[str, Any] = {
                "id": scene_id,
                "type": "generated",
                "description": shot.get("description", ""),
                "start_seconds": start,
                "end_seconds": start + duration,
            }
            for key in (
                "prompt", "provider", "model", "image_path", "clip_path", "narration_audio",
                "title_policy", "safe_zones", "arc_id", "beat_role", "shot_id", "narration",
                "visual_prompt", "motion_prompt", "transition_intent", "theme_id", "texture",
                "palette", "type_rules", "image", "video", "audio", "timing", "aspect_strategy",
                "claim_ids", "must_show", "fact_layer_policy", "semantic_evidence_points", "semantic_risk",
            ):
                if key in shot:
                    scene[key] = shot[key]
            if shot.get("extensions"):
                scene["extensions"] = shot["extensions"]
            scenes.append(scene)
    return {
        "version": "1.0",
        "style_id": "vox-paper-collage",
        "scenes": scenes,
        "metadata": {"aspect_ratio": beats.get("aspect_ratio", "16:9")},
    }
