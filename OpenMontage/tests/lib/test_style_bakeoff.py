from __future__ import annotations

import json
import subprocess

import pytest

from lib.style_bakeoff import BakeoffError, approve_bakeoff, create_bakeoff, validate_bakeoff


def test_hero_bakeoff_requires_multiple_distinct_candidates_and_dynamic_sample(tmp_path):
    bakeoff = create_bakeoff(
        project_dir=tmp_path,
        treatment_hash="a" * 64,
        style_id="vox-newsprint-editorial",
        candidates=[
            {"id": "c1", "prompt": "newspaper collage", "seed": 1},
            {"id": "c2", "prompt": "editorial cutout", "seed": 2},
            {"id": "c3", "prompt": "ink archive", "seed": 3},
        ],
        quality_mode="hero",
        delivery_promise={"width": 64, "height": 112, "fps": 24},
    )
    assert bakeoff["status"] == "awaiting_dynamic_sample"
    preview = tmp_path / "sample.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc2=size=64x112:rate=24",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=10.2", "-t", "10.2",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
            str(preview),
        ], check=True, capture_output=True,
    )
    approve_bakeoff(bakeoff, preview_path=preview, selected_candidate="c2", reviewer="tester")
    assert bakeoff["status"] == "approved"
    assert bakeoff["preview_sha256"]


def test_approved_bakeoff_becomes_stale_when_bound_artifact_changes(tmp_path):
    artifact = tmp_path / "scene_plan.json"
    artifact.write_text('{"version":"1.0"}', encoding="utf-8")
    bakeoff = create_bakeoff(
        project_dir=tmp_path,
        treatment_hash="a" * 64,
        style_id="clean-professional",
        candidates=[{"id": "c1", "prompt": "one", "seed": 1}, {"id": "c2", "prompt": "two", "seed": 2}],
        quality_mode="standard",
        artifact_path=artifact,
    )
    preview = tmp_path / "sample.mp4"
    preview.write_bytes(b"sample")
    approve_bakeoff(bakeoff, preview_path=preview, selected_candidate="c1", reviewer="tester")
    validate_bakeoff(bakeoff, current_artifact_path=artifact, current_treatment_hash="a" * 64)
    artifact.write_text('{"version":"2.0"}', encoding="utf-8")
    with pytest.raises(BakeoffError, match="artifact hash"):
        validate_bakeoff(bakeoff, current_artifact_path=artifact, current_treatment_hash="a" * 64)


def test_hero_bakeoff_rejects_single_candidate(tmp_path):
    with pytest.raises(BakeoffError, match="at least 2"):
        create_bakeoff(
            project_dir=tmp_path,
            treatment_hash="a" * 64,
            style_id="clean-professional",
            candidates=[{"id": "c1", "prompt": "clean", "seed": 1}],
            quality_mode="hero",
        )


def test_hero_bakeoff_rejects_a_non_playable_short_preview(tmp_path):
    bakeoff = create_bakeoff(
        project_dir=tmp_path,
        treatment_hash="a" * 64,
        style_id="vox-newsprint-editorial",
        candidates=[
            {"id": "c1", "prompt": "one", "seed": 1},
            {"id": "c2", "prompt": "two", "seed": 2},
        ],
        quality_mode="hero",
    )
    preview = tmp_path / "short.mp4"
    preview.write_bytes(b"not-a-video")
    with pytest.raises(BakeoffError, match="technical"):
        approve_bakeoff(
            bakeoff,
            preview_path=preview,
            selected_candidate="c1",
            reviewer="tester",
            delivery_promise={"width": 720, "height": 1280, "fps": 30},
        )
