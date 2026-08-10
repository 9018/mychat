"""Registry for the ten migrated vox-director visual themes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from styles.style_registry import StyleRegistry


class VoxThemeRegistry:
    THEME_LANGUAGE = {
        "vox-american-retro": {"palette": ["cream", "cobalt", "signal-red"], "typography": "condensed display sans with utility labels"},
        "vox-swiss-modern": {"palette": ["white", "black", "signal-red"], "typography": "neutral grotesk on a strict modular grid"},
        "vox-punk-zine": {"palette": ["black", "acid-yellow", "magenta"], "typography": "rough cutout type with ransom-note contrast"},
        "vox-soviet-constructivist": {"palette": ["paper", "black", "construction-red"], "typography": "bold block display with diagonal hierarchy"},
        "vox-wpa-propaganda": {"palette": ["ink-blue", "warm-cream", "brick-red"], "typography": "painted public-information headline system"},
        "vox-70s-groovy": {"palette": ["avocado", "orange", "brown"], "typography": "rounded display with elastic rhythm"},
        "vox-chinese-ink": {"palette": ["ink", "rice-paper", "vermillion"], "typography": "brush headline with restrained modern captions"},
        "vox-atomic-age": {"palette": ["turquoise", "atomic-orange", "charcoal"], "typography": "mid-century geometric display with orbit motifs"},
        "vox-newsprint-editorial": {"palette": ["newsprint", "ink", "editorial-red"], "typography": "newspaper display serif with compact sans metadata"},
        "vox-gilded-deco": {"palette": ["midnight", "gold", "ivory"], "typography": "geometric deco caps with elegant small text"},
    }

    def __init__(self, registry: StyleRegistry | None = None):
        self.registry = registry or StyleRegistry()

    def discover(self) -> list[str]:
        return sorted(
            style_id
            for style_id in self.registry.discover()
            if style_id.startswith("vox-") and style_id != "vox-paper-collage"
        )

    def get(self, theme_id: str, version: str | None = None) -> dict[str, Any]:
        if theme_id not in self.discover():
            raise KeyError(f"unknown vox theme: {theme_id}")
        package = self.registry.get(theme_id, version)
        # The registry profile is canonical. These aliases make the theme
        # vocabulary explicit for beats and prompt builders.
        language = self.THEME_LANGUAGE[theme_id]
        motion_path = Path(package["_package_dir"]) / "motion.md"
        motion = motion_path.read_text(encoding="utf-8").strip()
        return {
            **package,
            "palette": language["palette"],
            "typography": language["typography"],
            "motion": motion,
            "layout_grammar": package["composition_modes"],
        }
