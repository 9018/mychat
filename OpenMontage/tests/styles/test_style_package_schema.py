from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest
import yaml

from styles.style_registry import validate_profile


ROOT = Path(__file__).resolve().parents[2]


def test_style_package_schema_has_executable_compatibility_contract():
    schema = json.loads(
        (ROOT / "schemas" / "styles" / "style_package.schema.json").read_text(encoding="utf-8")
    )
    for field in (
        "id",
        "version",
        "family",
        "maturity",
        "pipelines",
        "composition_modes",
        "asset_strategies",
        "renderers",
        "runtimes",
        "sample_gate",
        "combinability",
    ):
        assert field in schema["required"]


def test_invalid_maturity_is_rejected():
    with pytest.raises(jsonschema.ValidationError):
        validate_profile({"id": "bad", "version": "1.0.0", "family": "x", "maturity": "done"})


def test_migrated_packages_are_real_directories():
    packages = ROOT / "styles" / "packages"
    assert packages.is_dir()
    assert any(p.is_dir() for p in packages.iterdir())
