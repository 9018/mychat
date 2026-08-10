"""Resolve render runtime availability without making silent substitutions."""

from __future__ import annotations

from typing import Any, Iterable


class RuntimeResolutionError(ValueError):
    """Raised for malformed runtime requests."""


class RuntimeResolver:
    VALID_RUNTIMES = {"ffmpeg", "remotion", "hyperframes", "canvas", "svg", "lottie", "blender"}

    def resolve(
        self,
        *,
        style_package: dict[str, Any],
        requested_runtime: str,
        available_runtimes: Iterable[str],
        quality_mode: str = "standard",
    ) -> dict[str, Any]:
        if requested_runtime not in self.VALID_RUNTIMES:
            raise RuntimeResolutionError(f"unknown runtime: {requested_runtime}")
        declared = set(style_package.get("runtimes", []))
        available = set(available_runtimes)
        fallback_options = sorted(declared & available - {requested_runtime})
        result = {
            "runtime": requested_runtime,
            "style_id": style_package.get("id"),
            "quality_mode": quality_mode,
            "status": "ready",
            "reasons": [],
            "fallback_options": fallback_options,
            "requires_reapproval": False,
            "gate_requirements": ["technical_qa"],
        }
        if requested_runtime not in declared:
            result.update(
                status="blocked",
                reasons=[f"runtime {requested_runtime} is not declared by the style package"],
                requires_reapproval=True,
                gate_requirements=["style_compatibility", "human_approval"],
            )
        elif requested_runtime not in available:
            result.update(
                status="blocked",
                reasons=[f"runtime {requested_runtime} is not available on this machine"],
                requires_reapproval=True,
                gate_requirements=["runtime_install_or_manual_swap", "human_approval"],
            )
        elif quality_mode == "hero":
            result["gate_requirements"] = ["dynamic_sample", "technical_qa"]
        return result
