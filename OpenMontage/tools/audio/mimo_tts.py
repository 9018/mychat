"""MiMo TTS through the self-hosted gateway (chat/completions audio protocol).

Same protocol vox-director uses (`ai_cloud.tts`): the gateway exposes MiMo
voices via `POST {OPENAI_BASE_URL}/chat/completions` with an `audio` field,
and the reply's `choices[0].message.audio.data` carries base64-encoded audio.

Explicit configuration only (no guessing):
  OPENAI_BASE_URL = http://10.0.1.108:18901/v1   (self-hosted gateway)
  AGNES_API_KEY   = the gateway sk- key (alias: OPENAI_API_KEY)
  UPSTREAM_PROXY  = socks5h://192.168.99.3:1080  (required for that network)

Voices: Chinese voices use their Chinese names (冰糖 / 茉莉 / 苏打 / 白桦),
English voices their English names (Mia / Chloe / Milo / Dean),
default `mimo_default`.
"""

from __future__ import annotations

import base64
import os
import time
from pathlib import Path
from typing import Any

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


def _gateway_base() -> str:
    base = os.environ.get("OPENAI_BASE_URL")
    if not base:
        raise RuntimeError(
            "OPENAI_BASE_URL not set (self-hosted gateway, e.g. "
            "http://10.0.1.108:18901/v1)"
        )
    return base.rstrip("/")


def _gateway_key() -> str:
    key = os.environ.get("AGNES_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("AGNES_API_KEY / OPENAI_API_KEY not set")
    return key


def _proxies() -> dict | None:
    p = os.environ.get("UPSTREAM_PROXY")
    return {"http": p, "https": p} if p else None


VOICES = {
    "mimo_default": "MiMo 默认",
    "bingtang": "冰糖",
    "moli": "茉莉",
    "soda": "苏打",
    "baihua": "白桦",
    "Mia": "Mia",
    "Chloe": "Chloe",
    "Milo": "Milo",
    "Dean": "Dean",
}


class MiMoTTS(BaseTool):
    name = "mimo_tts"
    version = "0.1.0"
    tier = ToolTier.VOICE
    capability = "tts"
    provider = "mimo"
    stability = ToolStability.EXPERIMENTAL
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.STOCHASTIC
    runtime = ToolRuntime.API

    dependencies = []
    install_instructions = (
        "Set OPENAI_BASE_URL + AGNES_API_KEY (self-hosted gateway) and "
        "UPSTREAM_PROXY when on the 10.0.1.108 network."
    )
    fallback = "piper_tts"
    fallback_tools = ["piper_tts", "openai_tts"]
    agent_skills = ["ai-voice"]

    capabilities = ["text_to_speech", "voice_selection"]
    supports = {
        "voice_cloning": True,          # mimo-v2.5-tts-voiceclone
        "multilingual": True,           # zh + en named voices
        "offline": False,
        "native_audio": True,
    }
    best_for = [
        "Chinese narration (strong zh voices: 冰糖/白桦)",
        "production via the in-house gateway",
    ]
    not_good_for = ["offline generation", "music"]

    quality_score = 0.85

    input_schema = {
        "type": "object",
        "required": ["text"],
        "properties": {
            "text": {"type": "string"},
            "model": {
                "type": "string",
                "enum": [
                    "mimo-v2.5-tts",
                    "mimo-v2.5-tts-voicedesign",
                    "mimo-v2.5-tts-voiceclone",
                ],
                "default": "mimo-v2.5-tts",
            },
            "voice": {
                "type": "string",
                "enum": list(VOICES),
                "default": "mimo_default",
            },
            "voice_desc": {
                "type": "string",
                "description": "Free-form voice design brief (voicedesign model)",
            },
            "clone_sample_path": {
                "type": "string",
                "description": "Local audio sample for voice clone (voiceclone model)",
            },
            "speed": {"type": "number", "minimum": 0.5, "maximum": 2.0},
            "output_path": {"type": "string", "default": "mimo_tts_output.mp3"},
        },
    }

    resource_profile = ResourceProfile(
        cpu_cores=0, ram_mb=64, vram_mb=0, disk_mb=50, network_required=True
    )
    retry_policy = RetryPolicy(max_retries=2, retryable_errors=["timeout"])
    idempotency_key_fields = ["text", "model", "voice", "voice_desc"]
    side_effects = ["writes audio file to output_path"]

    def get_status(self) -> ToolStatus:
        if (os.environ.get("AGNES_API_KEY") or os.environ.get("OPENAI_API_KEY")) and os.environ.get("OPENAI_BASE_URL"):
            return ToolStatus.AVAILABLE
        return ToolStatus.UNAVAILABLE

    def estimate_cost(self, inputs: dict[str, Any]) -> float:
        return round(len(str(inputs.get("text", ""))) / 1000 * 0.001, 4)

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        import requests

        try:
            base = _gateway_base()
            key = _gateway_key()
        except RuntimeError as e:
            return ToolResult(success=False, error=str(e))

        text = inputs["text"]
        model = inputs.get("model", "mimo-v2.5-tts")
        voice_key = str(inputs.get("voice", "mimo_default"))
        voice = VOICES.get(voice_key, voice_key)

        messages: list[dict] = []
        if inputs.get("voice_desc"):
            messages.append({"role": "user", "content": inputs["voice_desc"]})
        messages.append({"role": "assistant", "content": text})

        audio: dict[str, Any] = {"format": "mp3"}
        if model.endswith("voiceclone") and inputs.get("clone_sample_path"):
            # voiceclone: the audio sample goes in the `voice` slot (data URI)
            path = Path(inputs["clone_sample_path"])
            if not path.exists():
                return ToolResult(success=False, error=f"clone sample missing: {path}")
            audio["voice"] = "data:audio/wav;base64," + base64.b64encode(
                path.read_bytes()
            ).decode()
        elif model.endswith("voicedesign"):
            # voicedesign: the design brief already rides in the user message;
            # no named voice may accompany it (gateway 400s otherwise)
            pass
        elif voice:
            audio["voice"] = voice

        body: dict[str, Any] = {"model": model, "messages": messages, "audio": audio}
        if inputs.get("speed"):
            body["speed"] = inputs["speed"]

        start = time.time()
        try:
            r = requests.post(
                f"{base}/chat/completions",
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                json=body,
                proxies=_proxies(),
                timeout=240,
            )
            r.raise_for_status()
            data = (r.json().get("choices") or [{}])[0].get("message", {}).get(
                "audio", {}
            ).get("data")
            if not data:
                return ToolResult(
                    success=False, error=f"gateway returned no audio data: {r.text[:200]}"
                )
            audio_bytes = base64.b64decode(data)
        except Exception as e:
            return ToolResult(success=False, error=f"MiMo TTS failed: {e}")

        output_path = Path(inputs.get("output_path", "mimo_tts_output.mp3"))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(audio_bytes)

        return ToolResult(
            success=True,
            data={
                "provider": "mimo",
                "model": model,
                "voice": voice,
                "output": str(output_path),
                "output_path": str(output_path),
                "format": "mp3",
                "duration_seconds": round(time.time() - start, 2),
            },
            artifacts=[str(output_path)],
            cost_usd=self.estimate_cost(inputs),
        )
