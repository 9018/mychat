from __future__ import annotations

from styles.vox_theme_registry import VoxThemeRegistry


def test_all_vox_themes_are_discoverable_and_distinct():
    registry = VoxThemeRegistry()
    themes = registry.discover()
    assert len(themes) == 10
    assert all(theme.startswith("vox-") for theme in themes)
    palettes = {tuple(registry.get(theme)["palette"]) for theme in themes}
    assert len(palettes) == 10


def test_theme_profile_is_versioned_and_has_scene_rules():
    profile = VoxThemeRegistry().get("vox-newsprint-editorial")
    assert profile["version"]
    assert profile["typography"]
    assert profile["motion"]
