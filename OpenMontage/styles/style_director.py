"""Generate executable style candidates for a brief."""

from __future__ import annotations

from typing import Any

from styles.style_compatibility import CompatibilityResolver
from styles.style_registry import StyleRegistry


class StyleDirector:
    def __init__(self, registry: StyleRegistry):
        self.registry = registry
        self.resolver = CompatibilityResolver(registry)

    def propose(self, brief: dict[str, Any]) -> list[dict[str, Any]]:
        pipeline = brief["pipeline"]
        aspect_ratio = brief.get("aspect_ratio", "9:16")
        quality_mode = brief.get("quality_mode", "standard")
        runtimes = brief.get("available_runtimes", ["ffmpeg"])
        providers = brief.get("available_providers", [])
        requested_family = brief.get("style_family")
        candidates: list[dict[str, Any]] = []

        for style_id, package in sorted(self.registry.discover().items()):
            verified_for_pipeline = pipeline in package["pipelines"]
            if requested_family and package["family"] != requested_family:
                continue
            strategies = list(package["asset_strategies"][:2])
            runtime = next((item for item in package["runtimes"] if item in runtimes), package["runtimes"][0])
            result = self.resolver.resolve(
                pipeline=pipeline,
                primary_style=style_id,
                asset_strategies=strategies,
                aspect_ratio=aspect_ratio,
                render_runtime=runtime,
                available_runtimes=runtimes,
                available_providers=providers or package["providers"],
                quality_mode=quality_mode,
            )
            if result["status"] == "blocked":
                continue
            candidates.append(
                {
                    "style_id": style_id,
                    "style_package_version": package["version"],
                    "style_family": package["family"],
                    "composition_modes": package["composition_modes"],
                    "asset_strategies": strategies,
                    "render_runtime": runtime,
                    **result,
                }
            )
            if not verified_for_pipeline:
                candidates[-1]["status"] = "atelier_required" if candidates[-1]["status"] == "ready" else candidates[-1]["status"]
                candidates[-1]["reasons"] = list(candidates[-1].get("reasons", [])) + [
                    f"style package {style_id} is not pipeline-verified; atelier adaptation required"
                ]
        candidates.sort(key=lambda item: (item["status"] != "ready", item["style_id"]))
        return candidates
