"""Shared workspace configuration for all OpenMontage providers.

The workspace root owns the only secret-bearing ``.env`` file.  Providers use
this module for aliases and non-secret defaults instead of parsing their own
copy of the environment.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlsplit

from dotenv import dotenv_values


_ENV_KEYS = (
    "AGNES_API_KEY",
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "GROK2API_KEY",
    "XAI_API_KEY",
    "GROK2API_BASE",
    "XAI_BASE",
    "UPSTREAM_PROXY",
    "IMAGE_MODEL",
    "VIDEO_MODEL",
    "VIDEO_MODEL_PORTRAIT",
    "VIDEO_MODEL_LANDSCAPE",
    "VOICE_MODEL",
)


@dataclass(frozen=True)
class WorkspaceConfig:
    workspace_root: Path
    gateway_base: str | None = None
    gateway_key: str | None = None
    grok_base: str | None = None
    grok_key: str | None = None
    upstream_proxy: str | None = None
    image_model: str | None = None
    video_model: str | None = None
    video_model_portrait: str | None = None
    video_model_landscape: str | None = None
    voice_model: str | None = None

    def safe_view(self) -> dict[str, str | None]:
        """Return a log-safe view with values replaced by status/host only."""
        return {
            "workspace_root": str(self.workspace_root),
            "gateway_base": _host_only(self.gateway_base),
            "gateway_key": "set" if self.gateway_key else "missing",
            "grok_base": _host_only(self.grok_base),
            "grok_key": "set" if self.grok_key else "missing",
            "upstream_proxy": _host_only(self.upstream_proxy),
            "image_model": self.image_model,
            "video_model": self.video_model,
            "video_model_portrait": self.video_model_portrait,
            "video_model_landscape": self.video_model_landscape,
            "voice_model": self.voice_model,
        }


def _host_only(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlsplit(value if "://" in value else f"//{value}")
    return parsed.netloc or parsed.path.split("/", 1)[0]


def _as_root(start: Path | str | None) -> Path:
    path = Path(start or Path.cwd()).expanduser().resolve()
    return path if path.is_dir() else path.parent


def _find_workspace_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / ".env").is_file() or (candidate / "config.json").is_file():
            return candidate
    return start


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _first(mapping: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = mapping.get(key)
        if value not in (None, ""):
            return str(value)
    return None


def _file_values(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    return {key: value for key, value in dotenv_values(path).items() if value is not None}


def _merge_process_env(file_values: dict[str, str]) -> dict[str, str]:
    merged = dict(file_values)
    for key in _ENV_KEYS:
        if key in os.environ:
            merged[key] = os.environ[key]
    return merged


def _load_env_values(root: Path) -> dict[str, str]:
    """Load explicit env-file values without overriding process variables."""
    explicit = os.environ.get("OPENMONTAGE_ENV_FILE")
    if explicit:
        return _merge_process_env(_file_values(Path(explicit).expanduser()))
    return _merge_process_env(_file_values(root / ".env"))


def load_workspace_config(start: Path | str | None = None) -> WorkspaceConfig:
    """Resolve config using process env > explicit env file > root env > JSON."""
    root = _find_workspace_root(_as_root(start))
    env = _load_env_values(root)
    config = _load_json(root / "config.json")
    models = config.get("models") if isinstance(config.get("models"), dict) else {}

    gateway_base = env.get("OPENAI_BASE_URL") or _first(config, "baseUrl", "base_url")
    gateway_key = env.get("AGNES_API_KEY") or env.get("OPENAI_API_KEY")
    grok_base = env.get("GROK2API_BASE") or env.get("XAI_BASE")
    grok_key = env.get("GROK2API_KEY") or env.get("XAI_API_KEY")

    return WorkspaceConfig(
        workspace_root=root,
        gateway_base=gateway_base,
        gateway_key=gateway_key,
        grok_base=grok_base,
        grok_key=grok_key,
        upstream_proxy=env.get("UPSTREAM_PROXY") or _first(config, "upstreamProxy", "upstream_proxy"),
        image_model=env.get("IMAGE_MODEL") or _first(models, "image") or _first(config, "imageModel"),
        video_model=env.get("VIDEO_MODEL") or _first(models, "video") or _first(config, "videoModel"),
        video_model_portrait=env.get("VIDEO_MODEL_PORTRAIT"),
        video_model_landscape=env.get("VIDEO_MODEL_LANDSCAPE"),
        voice_model=env.get("VOICE_MODEL") or _first(models, "voice") or _first(config, "voiceModel"),
    )


def configure_process_environment(start: Path | str | None = None) -> WorkspaceConfig:
    """Populate only missing compatibility aliases and return the config."""
    cfg = load_workspace_config(start)
    aliases = {
        "AGNES_API_KEY": cfg.gateway_key,
        "OPENAI_API_KEY": cfg.gateway_key,
        "OPENAI_BASE_URL": cfg.gateway_base,
        "GROK2API_KEY": cfg.grok_key,
        "XAI_API_KEY": cfg.grok_key,
        "GROK2API_BASE": cfg.grok_base,
        "XAI_BASE": cfg.grok_base,
        "UPSTREAM_PROXY": cfg.upstream_proxy,
    }
    for key, value in aliases.items():
        if value and key not in os.environ:
            os.environ[key] = value
    return cfg
