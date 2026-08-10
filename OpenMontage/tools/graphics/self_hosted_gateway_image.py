"""Image generation through the project's OpenAI-compatible Agnes gateway."""

from __future__ import annotations

import base64
import os
import time
from pathlib import Path
from typing import Any

from lib.gateway_http import GatewayHTTP, GatewayHTTPError
from lib.workspace_config import load_workspace_config
from tools.base_tool import (
    BaseTool,
    Determinism,
    ExecutionMode,
    ResourceProfile,
    RetryPolicy,
    ToolResult,
    ToolRuntime,
    ToolStability,
    ToolStatus,
    ToolTier,
)


class SelfHostedGatewayImage(BaseTool):
    name = "self_hosted_gateway_image"
    version = "0.1.0"
    tier = ToolTier.GENERATE
    capability = "image_generation"
    provider = "self_hosted_gateway"
    stability = ToolStability.BETA
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.STOCHASTIC
    runtime = ToolRuntime.API
    dependencies = ["env:AGNES_API_KEY"]
    install_instructions = "Set AGNES_API_KEY (or OPENAI_API_KEY) and OPENAI_BASE_URL for the self-hosted gateway."
    agent_skills = ["flux-best-practices"]
    capabilities = ["generate_image", "text_to_image"]
    supports = {"aspect_ratio": True, "resolution": True, "multiple_outputs": False}
    best_for = ["Agnes gateway image generation", "OpenAI-compatible gpt-image-2 generation"]
    not_good_for = ["offline generation"]
    fallback_tools = ["grok_image", "openai_image"]
    input_schema = {
        "type": "object",
        "required": ["prompt"],
        "properties": {
            "prompt": {"type": "string"},
            "model": {"type": "string", "default": "agnes-image-2.1-flash"},
            "size": {"type": "string"},
            "aspect_ratio": {"type": "string"},
            "resolution": {"type": "string"},
            "n": {"type": "integer", "minimum": 1, "maximum": 1},
            "output_path": {"type": "string"},
        },
    }
    resource_profile = ResourceProfile(cpu_cores=1, ram_mb=512, disk_mb=100, network_required=True)
    retry_policy = RetryPolicy(max_retries=2, retryable_errors=["rate_limit", "timeout"])
    idempotency_key_fields = ["prompt", "model", "size", "aspect_ratio"]
    side_effects = ["writes image file to output_path", "calls self-hosted image gateway"]

    def get_status(self) -> ToolStatus:
        cfg = load_workspace_config(Path(__file__).resolve().parents[2])
        return ToolStatus.AVAILABLE if cfg.gateway_key and cfg.gateway_base else ToolStatus.UNAVAILABLE

    def estimate_cost(self, inputs: dict[str, Any]) -> float:
        return 0.0

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        start = time.time()
        try:
            client = GatewayHTTP()
            payload: dict[str, Any] = {
                "model": inputs.get("model") or "agnes-image-2.1-flash",
                "prompt": inputs["prompt"],
                "n": 1,
            }
            for key in ("size", "aspect_ratio", "resolution"):
                if inputs.get(key) is not None:
                    payload[key] = inputs[key]
            result = client.post_json("/images/generations", payload, timeout=300)
            item = (result.get("data") or [{}])[0]
            output_path = Path(inputs.get("output_path", "generated_gateway_image.png"))
            if item.get("b64_json"):
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(base64.b64decode(item["b64_json"]))
            elif item.get("url"):
                try:
                    client.download_atomic(str(item["url"]), output_path, bearer=True)
                except GatewayHTTPError as exc:
                    # Some gateways return a signed media URL that rejects the
                    # API bearer token. Retry once without auth; the URL itself
                    # remains opaque and is never emitted in the error.
                    if "HTTP 401" not in str(exc):
                        raise
                    client.download_atomic(str(item["url"]), output_path, bearer=False)
            else:
                return ToolResult(success=False, error="gateway image response has no usable output")
            model = payload["model"]
            return ToolResult(
                success=True,
                data={"provider": self.provider, "model": model, "output": str(output_path), "output_path": str(output_path)},
                artifacts=[str(output_path)],
                duration_seconds=round(time.time() - start, 2),
                model=model,
            )
        except (GatewayHTTPError, ValueError, OSError) as exc:
            return ToolResult(success=False, error=f"gateway image generation failed: {exc}", duration_seconds=round(time.time() - start, 2))
