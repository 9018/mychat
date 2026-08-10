"""Executable Style Package registry.

Legacy styles/*.yaml remain readable through playbook_loader. New production
plans use this registry so style identity, version, runtime, and QA contract
are explicit and project-lockable.
"""

from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path
from typing import Any

import jsonschema
import yaml


REQUIRED_FILES = (
    "profile.yaml",
    "director.md",
    "prompting.md",
    "motion.md",
    "typography.md",
    "quality-rubric.yaml",
    "sample-rubric.yaml",
)
SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "styles" / "style_package.schema.json"


class StylePackageError(ValueError):
    """Raised when a style package is missing or incompatible."""


def _schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def validate_profile(profile: dict[str, Any]) -> None:
    """Validate a style package profile."""
    jsonschema.validate(instance=profile, schema=_schema())


class StyleRegistry:
    def __init__(self, styles_root: str | Path | None = None):
        self.styles_root = Path(styles_root or Path(__file__).resolve().parent / "packages")
        self._packages: dict[str, dict[str, Any]] = {}
        self._cache_signature: tuple[tuple[str, int], ...] | None = None

    def _signature(self) -> tuple[tuple[str, int], ...]:
        if not self.styles_root.exists():
            return ()
        entries: list[tuple[str, int]] = []
        for package_dir in sorted(p for p in self.styles_root.iterdir() if p.is_dir()):
            profile_path = package_dir / "profile.yaml"
            entries.append((package_dir.name, profile_path.stat().st_mtime_ns if profile_path.exists() else -1))
        return tuple(entries)

    def discover(self) -> dict[str, dict[str, Any]]:
        signature = self._signature()
        if self._packages and signature == self._cache_signature:
            return copy.deepcopy(self._packages)
        self._packages = {}
        if not self.styles_root.exists():
            return {}
        for package_dir in sorted(p for p in self.styles_root.iterdir() if p.is_dir()):
            profile_path = package_dir / "profile.yaml"
            if not profile_path.exists():
                raise StylePackageError(f"{package_dir.name}: missing profile.yaml")
            profile = yaml.safe_load(profile_path.read_text(encoding="utf-8")) or {}
            validate_profile(profile)
            missing = [name for name in REQUIRED_FILES if not (package_dir / name).is_file()]
            if missing:
                raise StylePackageError(f"{profile.get('id', package_dir.name)}: missing {', '.join(missing)}")
            if profile["id"] in self._packages:
                raise StylePackageError(f"duplicate style package id: {profile['id']}")
            profile = copy.deepcopy(profile)
            profile["_package_dir"] = str(package_dir)
            self._packages[profile["id"]] = profile
        self._cache_signature = signature
        return copy.deepcopy(self._packages)

    def _ensure_discovered(self) -> None:
        if not self._packages:
            self.discover()

    def get(self, style_id: str, version: str | None = None) -> dict[str, Any]:
        # Re-read profiles so a long-running Backlot process sees an explicit
        # package upgrade. Project snapshots remain immutable on disk.
        self.discover()
        try:
            package = self._packages[style_id]
        except KeyError as exc:
            raise StylePackageError(f"style package not found: {style_id}") from exc
        if version is not None and package["version"] != version:
            raise StylePackageError(
                f"style package {style_id} version {version} not found; current is {package['version']}"
            )
        return copy.deepcopy(package)

    def list_by_family(self, family: str) -> list[str]:
        self._ensure_discovered()
        return sorted(style_id for style_id, package in self._packages.items() if package["family"] == family)

    def resolve_inheritance(self, style_id: str) -> dict[str, Any]:
        self._ensure_discovered()
        visiting: set[str] = set()

        def resolve(current_id: str) -> dict[str, Any]:
            if current_id in visiting:
                raise StylePackageError(f"cyclic style inheritance at {current_id}")
            profile = self.get(current_id)
            parent_id = profile.get("extends")
            if not parent_id:
                return profile
            visiting.add(current_id)
            parent = resolve(parent_id)
            visiting.remove(current_id)
            merged = copy.deepcopy(parent)
            merged.update(profile)
            merged["_package_dir"] = profile["_package_dir"]
            return merged

        return resolve(style_id)

    def compose(self, primary: str, supporting: str) -> dict[str, Any]:
        self._ensure_discovered()
        primary_profile = self._packages.get(primary)
        primary_family = primary_profile["family"] if primary_profile else primary
        supporting_profile = self._packages.get(supporting)
        supporting_family = supporting_profile["family"] if supporting_profile else supporting
        if primary_profile:
            conflicts = set(primary_profile["combinability"].get("conflicts", []))
            if supporting in conflicts or supporting_family in conflicts:
                raise StylePackageError(f"{primary} conflicts with {supporting_family}")
            supports = set(primary_profile["combinability"].get("supports", []))
            if supports and supporting not in supports and supporting_family not in supports:
                return {
                    "status": "atelier_required",
                    "families": [primary_family, supporting_family],
                    "reason": f"{primary} has no verified combination rule for {supporting_family}",
                }
        if supporting_profile:
            conflicts = set(supporting_profile["combinability"].get("conflicts", []))
            if primary in conflicts or primary_family in conflicts:
                raise StylePackageError(f"{supporting} conflicts with {primary_family}")
        return {"status": "ready", "families": [primary_family, supporting_family]}

    def snapshot_for_project(self, project_dir: str | Path, style_id: str) -> dict[str, Any]:
        package = self.get(style_id)
        snapshot = {
            "style_id": package["id"],
            "version": package["version"],
            "family": package["family"],
            "maturity": package["maturity"],
            "provenance": package["provenance"],
        }
        target = Path(project_dir)
        target.mkdir(parents=True, exist_ok=True)
        source_dir = Path(package["_package_dir"])
        package_snapshot_dir = target / "style-package" / package["id"] / str(package["version"])
        if package_snapshot_dir.exists():
            # Never mutate an existing project lock. A rerun must use the
            # already locked package or fail visibly if it is incomplete.
            missing = [name for name in REQUIRED_FILES if not (package_snapshot_dir / name).is_file()]
            if missing:
                raise StylePackageError(
                    f"incomplete immutable snapshot for {style_id}: missing {', '.join(missing)}"
                )
        else:
            package_snapshot_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source_dir, package_snapshot_dir)
        snapshot["snapshot_path"] = str(package_snapshot_dir)
        (target / "style-package.snapshot.yaml").write_text(
            yaml.safe_dump(snapshot, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        return snapshot
