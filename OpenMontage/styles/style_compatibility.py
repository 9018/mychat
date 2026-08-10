"""Resolve whether a pipeline/style/asset/runtime combination is executable."""

from __future__ import annotations

from typing import Any, Iterable

from styles.style_registry import StylePackageError, StyleRegistry


class CompatibilityError(ValueError):
    """Raised for an explicit incompatible production request."""


class CompatibilityResolver:
    STATUSES = {"ready", "atelier_required", "degraded", "experimental", "blocked"}

    def __init__(self, registry: StyleRegistry):
        self.registry = registry

    def resolve(
        self,
        *,
        pipeline: str,
        primary_style: str,
        supporting_styles: Iterable[str] = (),
        asset_strategies: Iterable[str] = (),
        aspect_ratio: str,
        render_runtime: str,
        available_runtimes: Iterable[str],
        available_providers: Iterable[str],
        quality_mode: str = "standard",
    ) -> dict[str, Any]:
        primary = self.registry.get(primary_style)
        supporting = list(supporting_styles)
        asset_strategies = list(asset_strategies)
        available_runtimes = set(available_runtimes)
        available_providers = set(available_providers)
        reasons: list[str] = []
        missing_requirements: list[str] = []
        fallback_options: list[str] = []
        status = "ready"

        if pipeline not in primary["pipelines"]:
            reasons.append(f"style {primary_style} is not verified for pipeline {pipeline}")
            status = "atelier_required"

        unsupported_assets = [
            strategy for strategy in asset_strategies
            if strategy not in primary["asset_strategies"]
        ]
        if unsupported_assets:
            raise CompatibilityError(
                f"{primary_style} cannot execute asset strategies: {', '.join(unsupported_assets)}"
            )

        if aspect_ratio not in primary["aspect_ratios"]:
            reasons.append(f"aspect ratio {aspect_ratio} requires a style-specific adaptation")
            status = "atelier_required"

        if render_runtime not in primary["runtimes"]:
            reason = f"runtime {render_runtime} is not supported by {primary_style}"
            missing_requirements.append(reason)
            reasons.append(reason)
            status = "blocked"
        elif render_runtime not in available_runtimes:
            reason = f"runtime {render_runtime} is not available on this machine"
            missing_requirements.append(reason)
            reasons.append(reason)
            alternatives = sorted(set(primary["runtimes"]) & available_runtimes)
            fallback_options.extend(alternatives)
            status = "degraded" if alternatives else "blocked"

        # Package providers are the available option set, not all mandatory
        # dependencies. A package may render without TTS when the treatment
        # intentionally has no narration. Profiles can opt into strict
        # requirements with required_providers.
        required_providers = set(primary.get("required_providers", []))
        missing_providers = sorted(required_providers - available_providers)
        if missing_providers:
            missing_requirements.append(
                f"providers unavailable: {', '.join(missing_providers)}"
            )
            status = "degraded" if status != "blocked" else status

        for support in supporting:
            try:
                composed = self.registry.compose(primary_style, support)
            except StylePackageError as exc:
                raise CompatibilityError(str(exc)) from exc
            support_families = composed["families"][1:]
            if composed["status"] == "atelier_required":
                status = "atelier_required" if status == "ready" else status
                reasons.append(composed["reason"])
            else:
                reasons.append(f"composed with {', '.join(support_families)}")

        if quality_mode == "hero" and primary["maturity"] != "quality_verified":
            status = "atelier_required" if status not in {"blocked", "degraded"} else status
            reasons.append("hero production requires a dynamic sample gate for this package")

        if status == "ready" and not reasons:
            reasons.append("all requested style, asset, runtime, and provider constraints are verified")
        if status not in self.STATUSES:
            raise AssertionError(f"unknown compatibility status: {status}")

        return {
            "status": status,
            "pipeline": pipeline,
            "style_id": primary["id"],
            "style_package_version": primary["version"],
            "style_families": [primary["family"]]
            + [
                self.registry.get(style)["family"] if style in self.registry.discover() else style
                for style in supporting
            ],
            "render_runtime": render_runtime,
            "aspect_ratio": aspect_ratio,
            "asset_strategies": asset_strategies,
            "quality_mode": quality_mode,
            "reasons": reasons,
            "missing_requirements": missing_requirements,
            "fallback_options": fallback_options,
            "gate_requirements": [
                "dynamic_sample" if quality_mode == "hero" or status == "atelier_required" else "technical_qa"
            ],
        }
