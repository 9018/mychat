from __future__ import annotations

from pathlib import Path

from styles.style_registry import StyleRegistry


ROOT = Path(__file__).resolve().parents[2]


def test_all_migrated_style_packages_have_distinct_executable_director_content():
    registry = StyleRegistry(ROOT / "styles" / "packages")
    packages = registry.discover()
    assert len(packages) == 16
    director_contents = {
        Path(profile["_package_dir"], "director.md").read_text(encoding="utf-8")
        for profile in packages.values()
    }
    motion_contents = {
        Path(profile["_package_dir"], "motion.md").read_text(encoding="utf-8")
        for profile in packages.values()
    }
    typography_contents = {
        Path(profile["_package_dir"], "typography.md").read_text(encoding="utf-8")
        for profile in packages.values()
    }
    assert len(director_contents) == 16
    assert len(motion_contents) == 16
    assert len(typography_contents) == 16


def test_every_package_has_family_specific_quality_language():
    registry = StyleRegistry(ROOT / "styles" / "packages")
    for profile in registry.discover().values():
        rubric = Path(profile["_package_dir"], "quality-rubric.yaml").read_text(encoding="utf-8")
        assert profile["family"] in rubric or profile["id"] in rubric
        assert "narrative_fit" in rubric
        assert "typography_legibility" in rubric


def test_every_package_has_a_non_placeholder_static_fixture():
    registry = StyleRegistry(ROOT / "styles" / "packages")
    for profile in registry.discover().values():
        fixture_dir = Path(profile["_package_dir"]) / "fixtures"
        fixtures = [path for path in fixture_dir.iterdir() if path.is_file() and path.name != ".gitkeep"]
        assert fixtures, profile["id"]
        assert any(path.stat().st_size > 100 for path in fixtures), profile["id"]


def test_every_package_has_a_provenance_labeled_reference_board():
    registry = StyleRegistry(ROOT / "styles" / "packages")
    for profile in registry.discover().values():
        references = Path(profile["_package_dir"]) / "references"
        boards = [path for path in references.glob("*.json") if path.is_file()]
        assert boards, profile["id"]
        assert any("provenance" in path.read_text(encoding="utf-8") for path in boards), profile["id"]
