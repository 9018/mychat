from __future__ import annotations

import json

from lib.single_entry_run import run_single_entry_offline


def test_single_entry_offline_writes_technical_preview_and_blocked_qa(tmp_path):
    result = run_single_entry_offline(
        project_id="offline-run",
        title="Offline run",
        pipeline="cinematic",
        brief={"topic": "Weather", "quality_mode": "standard"},
        project_root=tmp_path,
        available_runtimes=["ffmpeg"],
        available_providers=["image", "video"],
    )
    assert result["qa_report"]["status"] == "blocked"
    assert result["qa_report"]["technical_checks"]["status"] == "pass"
    assert result["qa_report"]["technical_checks"]["preview_kind"] == "technical_only"
    assert (tmp_path / "offline-run" / "renders" / "technical-preview.mp4").is_file()
    assert json.loads((tmp_path / "offline-run" / "artifacts" / "qa_report.json").read_text())["status"] == "blocked"
    semantic_path = tmp_path / "offline-run" / "artifacts" / "semantic_qa_report.json"
    assert semantic_path.is_file()
    qa = json.loads((tmp_path / "offline-run" / "artifacts" / "qa_report.json").read_text())
    assert qa["semantic_qa_report_ref"]["status"] == "blocked"
