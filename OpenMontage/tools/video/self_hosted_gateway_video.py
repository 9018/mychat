"""Asynchronous Agnes video generation through the OpenAI-compatible gateway."""

from __future__ import annotations

import time
import base64
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


class SelfHostedGatewayVideo(BaseTool):
    name = "self_hosted_gateway_video"
    version = "0.1.0"
    tier = ToolTier.GENERATE
    capability = "video_generation"
    provider = "self_hosted_gateway"
    stability = ToolStability.BETA
    execution_mode = ExecutionMode.ASYNC
    determinism = Determinism.STOCHASTIC
    runtime = ToolRuntime.API
    dependencies = ["env:AGNES_API_KEY"]
    install_instructions = "Set AGNES_API_KEY (or OPENAI_API_KEY) and OPENAI_BASE_URL for the self-hosted gateway."
    agent_skills = ["ai-video-gen"]
    capabilities = ["text_to_video", "image_to_video"]
    supports = {"text_to_video": True, "image_to_video": True, "reference_image": True, "native_audio": False}
    best_for = ["Agnes video generation through the local gateway"]
    not_good_for = ["offline generation", "native synchronized audio"]
    fallback_tools = ["grok_video", "veo_video", "kling_video"]
    input_schema = {
        "type": "object",
        "required": ["prompt"],
        "properties": {
            "prompt": {"type": "string"},
            "model": {"type": "string", "default": "agnes-video-v2.0"},
            "duration": {"type": "integer", "minimum": 1, "maximum": 15},
            "aspect_ratio": {"type": "string"},
            "image_url": {"type": "string"},
            "image_path": {"type": "string"},
            "request_id": {"type": "string"},
            "poll_interval_seconds": {"type": "number", "minimum": 0},
            "timeout_seconds": {"type": "number", "minimum": 1},
            "output_path": {"type": "string"},
        },
    }
    resource_profile = ResourceProfile(cpu_cores=1, ram_mb=512, disk_mb=500, network_required=True)
    retry_policy = RetryPolicy(max_retries=2, retryable_errors=["rate_limit", "timeout"])
    idempotency_key_fields = ["prompt", "model", "duration", "aspect_ratio", "image_url", "image_path"]
    side_effects = ["writes video file to output_path", "calls self-hosted video gateway"]

    def get_status(self) -> ToolStatus:
        cfg = load_workspace_config(Path(__file__).resolve().parents[2])
        return ToolStatus.AVAILABLE if cfg.gateway_key and cfg.gateway_base else ToolStatus.UNAVAILABLE

    def estimate_cost(self, inputs: dict[str, Any]) -> float:
        return 0.0

    def _payload(self, inputs: dict[str, Any]) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": inputs.get("model") or "agnes-video-v2.0",
            "prompt": inputs["prompt"],
        }
        for key in ("duration", "aspect_ratio", "image_url", "image_path"):
            if inputs.get(key) is not None:
                payload[key] = inputs[key]
        if inputs.get("image_path") and not inputs.get("image_url"):
            path = Path(inputs["image_path"])
            if not path.is_file():
                raise ValueError(f"image_path not found: {path}")
            mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
            encoded = base64.b64encode(path.read_bytes()).decode("ascii")
            payload["image"] = {"url": f"data:{mime};base64,{encoded}"}
            payload.pop("image_path", None)
        elif inputs.get("image_url"):
            payload["image"] = {"url": inputs["image_url"]}
            payload.pop("image_url", None)
        return payload

    @staticmethod
    def _status(data: dict[str, Any]) -> str:
        raw = str(data.get("status") or "").lower()
        return {"done": "completed", "success": "completed", "queued": "processing"}.get(raw, raw)

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        start = time.time()
        request_id = inputs.get("request_id")
        try:
            client = GatewayHTTP()
            if not request_id:
                submitted = client.post_json("/videos", self._payload(inputs), timeout=120)
                request_id = submitted.get("task_id") or submitted.get("id")
                if not request_id:
                    return ToolResult(success=False, error="gateway video response has no request id")

            deadline = time.time() + float(inputs.get("timeout_seconds", 900))
            interval = float(inputs.get("poll_interval_seconds", 2))
            latest: dict[str, Any] = {}
            while time.time() <= deadline:
                latest = client.get_json(f"/videos/{request_id}", timeout=60)
                status = self._status(latest)
                if status == "completed":
                    break
                if status in {"failed", "expired", "cancelled"}:
                    return ToolResult(success=False, error=f"gateway video task {status}; request_id={request_id}")
                time.sleep(interval)
            else:
                return ToolResult(success=False, error=f"gateway video task timed out; request_id={request_id}", data={"request_id": request_id})

            url = latest.get("video_url") or latest.get("url") or (latest.get("metadata") or {}).get("url")
            if not url:
                return ToolResult(success=False, error=f"gateway video completed without output; request_id={request_id}")
            output_path = Path(inputs.get("output_path", "generated_gateway_video.mp4"))
            try:
                client.download_atomic(str(url), output_path, bearer=True)
            except GatewayHTTPError as exc:
                if "HTTP 401" not in str(exc):
                    raise
                client.download_atomic(str(url), output_path, bearer=False)
            model = inputs.get("model") or "agnes-video-v2.0"
            return ToolResult(
                success=True,
                data={"provider": self.provider, "model": model, "request_id": request_id, "status": "completed", "output": str(output_path), "output_path": str(output_path)},
                artifacts=[str(output_path)],
                duration_seconds=round(time.time() - start, 2),
                model=model,
            )
        except (GatewayHTTPError, ValueError, OSError) as exc:
            data = {"request_id": request_id} if request_id else {}
            return ToolResult(success=False, data=data, error=f"gateway video generation failed: {exc}", duration_seconds=round(time.time() - start, 2))
