from __future__ import annotations

import json
import subprocess
import sys


def test_single_entry_cli_writes_offline_plan(tmp_path):
    brief = tmp_path / "brief.json"
    brief.write_text(
        json.dumps({"topic": "Typhoon warning", "quality_mode": "hero"}),
        encoding="utf-8",
    )
    root = tmp_path / "projects"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/plan_single_entry.py",
            "--project-id",
            "cli-pilot",
            "--title",
            "CLI pilot",
            "--pipeline",
            "cinematic",
            "--brief-json",
            str(brief),
            "--project-root",
            str(root),
            "--runtime",
            "remotion",
            "--provider",
            "image",
            "--provider",
            "video",
        ],
        cwd=".",
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    assert payload["selected_style_id"]
    assert (root / "cli-pilot" / "artifacts" / "creative_treatment.json").exists()
