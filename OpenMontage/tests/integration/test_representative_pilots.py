from __future__ import annotations

from pathlib import Path

from backlot.state import load_board_state
from lib.representative_pilots import (
    load_pilot_scenarios,
    materialize_pilot_projects,
    plan_pilot,
    run_pilot_matrix,
)


def test_seven_representative_scenarios_cover_all_families():
    root = Path(__file__).parents[2]
    scenarios = load_pilot_scenarios(root / "tests" / "eval" / "golden_scenarios")
    names = {item["name"] for item in scenarios}
    assert {
        "vox_editorial_collage", "clean_professional_data", "illustration_character",
        "cinematic_mixed_media", "documentary_hybrid", "screen_or_presenter",
        "reference_derived_custom",
    } <= names
    assert len(scenarios) >= 7


def test_representative_pilot_matrix_produces_playable_technical_previews(tmp_path):
    root = Path(__file__).parents[2]
    report = run_pilot_matrix(root / "tests" / "eval" / "golden_scenarios", tmp_path)
    assert report["count"] >= 7
    assert all(item["technical_status"] == "passed" for item in report["reports"])
    assert all(Path(item["preview_path"]).is_file() for item in report["reports"])
    assert all(item["preview_kind"] == "creative_dynamic_local" for item in report["reports"])
    assert all(item["creative_status"] == "awaiting_human_review" for item in report["reports"])
    assert all(Path(item["provenance_path"]).is_file() for item in report["reports"])
    assert all(Path(item["review_packet_path"]).is_file() for item in report["reports"])


def test_representative_pilots_materialize_as_backlot_review_projects(tmp_path):
    root = Path(__file__).parents[2]
    output = tmp_path / "pilot-evidence"
    run_pilot_matrix(root / "tests" / "eval" / "golden_scenarios", output)
    projects = materialize_pilot_projects(output, tmp_path / "projects")
    assert len(projects) >= 7
    for raw_project in projects:
        project = Path(raw_project)
        state = load_board_state(project)
        assert state["creative_review"]["status"] == "awaiting_human_review"
        assert len(state["creative_review"]["candidates"]["candidates"]) == 2
        assert state["creative_review"]["review_packet_path"] == "artifacts/review-packet.json"
        assert len(state["media"]["renders"]) == 1
        assert (project / "verify" / "frame_01.jpg").is_file()
