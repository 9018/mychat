from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from styles.style_registry import StyleRegistry, StylePackageError


REQUIRED_FILES = [
    "profile.yaml",
    "director.md",
    "prompting.md",
    "motion.md",
    "typography.md",
    "quality-rubric.yaml",
    "sample-rubric.yaml",
]


def write_package(root: Path, style_id: str = "test-editorial", version: str = "1.0.0", **overrides):
    package = root / style_id
    package.mkdir(parents=True, exist_ok=True)
    profile = {
        "id": style_id,
        "version": version,
        "family": "editorial-collage",
        "maturity": "atelier_required",
        "provenance": "test",
        "pipelines": ["hybrid"],
        "composition_modes": ["collage-led", "hybrid"],
        "asset_strategies": ["generated", "archival", "hybrid"],
        "renderers": ["cinematic-trailer"],
        "runtimes": ["remotion", "ffmpeg"],
        "aspect_ratios": ["9:16", "16:9"],
        "title_policy": ["overlay", "embedded", "hybrid"],
        "subtitle_policy": ["caption"],
        "providers": ["fixture-image"],
        "sample_gate": {"required": True, "duration_seconds": 10},
        "combinability": {"supports": ["cinematic-generative"], "conflicts": []},
        **overrides,
    }
    (package / "profile.yaml").write_text(yaml.safe_dump(profile), encoding="utf-8")
    for filename in REQUIRED_FILES[1:]:
        (package / filename).write_text(f"# {style_id} {filename}\n", encoding="utf-8")
    (package / "references").mkdir(exist_ok=True)
    (package / "fixtures").mkdir(exist_ok=True)
    return package


def test_registry_discovers_and_validates_complete_package(tmp_path: Path):
    write_package(tmp_path)
    registry = StyleRegistry(tmp_path)
    packages = registry.discover()
    assert packages["test-editorial"]["id"] == "test-editorial"
    assert registry.get("test-editorial")["version"] == "1.0.0"
    assert registry.list_by_family("editorial-collage") == ["test-editorial"]


def test_registry_rejects_package_missing_executable_director_file(tmp_path: Path):
    package = write_package(tmp_path)
    (package / "motion.md").unlink()
    registry = StyleRegistry(tmp_path)
    with pytest.raises(StylePackageError, match="motion.md"):
        registry.discover()


def test_registry_locks_snapshot_to_project(tmp_path: Path):
    package = write_package(tmp_path / "styles")
    registry = StyleRegistry(tmp_path / "styles")
    registry.discover()
    snapshot = registry.snapshot_for_project(tmp_path / "project", "test-editorial")
    assert snapshot["style_id"] == "test-editorial"
    assert snapshot["version"] == "1.0.0"
    assert (tmp_path / "project" / "style-package.snapshot.yaml").exists()
    locked = tmp_path / "project" / "style-package" / "test-editorial" / "1.0.0"
    assert (locked / "director.md").exists()
    assert (locked / "fixtures").is_dir()


def test_registry_composes_supported_styles_and_reports_conflict(tmp_path: Path):
    write_package(tmp_path, "cinematic", family="cinematic-generative", combinability={
        "supports": ["editorial-collage"], "conflicts": ["screen-led"]
    })
    write_package(tmp_path, "collage", family="editorial-collage", combinability={
        "supports": ["cinematic-generative"], "conflicts": []
    })
    registry = StyleRegistry(tmp_path)
    registry.discover()
    composed = registry.compose("cinematic", "collage")
    assert composed["status"] == "ready"
    assert composed["families"] == ["cinematic-generative", "editorial-collage"]

    with pytest.raises(StylePackageError, match="screen-led"):
        registry.compose("cinematic", "screen-led")


def test_registry_keeps_project_snapshot_after_global_package_update(tmp_path: Path):
    styles = tmp_path / "styles"
    write_package(styles, version="1.0.0")
    registry = StyleRegistry(styles)
    registry.discover()
    snapshot = registry.snapshot_for_project(tmp_path / "project", "test-editorial")
    write_package(styles, version="2.0.0")
    assert snapshot["version"] == "1.0.0"
    assert registry.get("test-editorial")["version"] == "2.0.0"
