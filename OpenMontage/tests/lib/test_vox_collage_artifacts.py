from __future__ import annotations

import json
from pathlib import Path


def _fixture():
    path = Path(__file__).parents[1] / "fixtures" / "vox_collage" / "minimal_scene_plan.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_scene_plan_exports_grouped_beats():
    from lib.vox_collage_artifacts import export_beats

    beats = export_beats(_fixture())
    assert beats["version"] == "1.0"
    assert beats["aspect_ratio"] == "9:16"
    assert beats["beats"][0]["shots"][0]["scene_id"] == "beat-01-shot-01"
    assert beats["beats"][0]["duration"] == 2


def test_scene_plan_export_is_deterministic():
    from lib.vox_collage_artifacts import export_beats

    first = json.dumps(export_beats(_fixture()), ensure_ascii=False, sort_keys=True)
    second = json.dumps(export_beats(_fixture()), ensure_ascii=False, sort_keys=True)
    assert first == second


def test_export_does_not_copy_checkpoint_state():
    from lib.vox_collage_artifacts import export_beats

    scene_plan = _fixture()
    scene_plan["metadata"]["checkpoint_status"] = "completed"
    beats = export_beats(scene_plan)
    assert "checkpoint_status" not in beats


def test_beats_round_trip_preserves_motion_and_unknown_extensions():
    from lib.vox_collage_artifacts import export_beats, import_beats

    scene_plan = _fixture()
    scene_plan["scenes"][0].update(
        {
            "arc_id": "arrival",
            "beat_role": "hook",
            "motion_prompt": "paper layers breathe",
            "transition_intent": "hard reveal",
            "theme_id": "vox-newsprint-editorial",
            "extensions": {"custom_provider_seed": 41},
        }
    )
    beats = export_beats(scene_plan)
    restored = import_beats(beats)
    shot = restored["scenes"][0]
    assert shot["arc_id"] == "arrival"
    assert shot["motion_prompt"] == "paper layers breathe"
    assert shot["extensions"]["custom_provider_seed"] == 41
