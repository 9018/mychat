"""OpenAI-compatible gateway LLM client (scripting / agent fallback).

Reads the `llm:` block in config.yaml. With `provider: openai` plus a
self-hosted OpenAI-compatible gateway it routes chat to the in-house models
(e.g. deepseek-v4-flash-free, grok-4.5) instead of paying a cloud provider —
same explicit-configuration rules as the rest of the repo:

  base_url    = config.yaml llm.base_url  |  env OPENAI_BASE_URL
  api key     = env named by llm.api_key_env (default AGNES_API_KEY, alias OPENAI_API_KEY)
  proxy       = env UPSTREAM_PROXY (socks5) when the gateway subnet needs it

Usage:
  python3 -m lib.llm_client "write an 8-second news cold-open for a Henan policy story"
  python3 -m lib.llm_client --system "you are a beat planner" --model grok-4.5 "…"
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

try:
    from lib.config_model import OpenMontageConfig
except ImportError:  # allow running as script from repo root
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from lib.config_model import OpenMontageConfig

import requests


def gateway_config() -> dict[str, str]:
    llm = OpenMontageConfig.load().llm
    if not llm.model:
        return {"provider": "openai", "model": os.environ.get("LLM_MODEL", "deepseek-v4-flash-free")}
    for key in ("provider", "model", "base_url", "api_key_env", "temperature", "max_tokens"):
        if not hasattr(llm, key):
            raise RuntimeError(f"config.yaml llm.{key} missing")
    return {k: getattr(llm, k) for k in ("provider", "model", "base_url", "api_key_env")}


def _base_url(cfg: dict) -> str:
    return (
        (cfg.get("base_url") or os.environ.get("OPENAI_BASE_URL") or "")
        .rstrip("/")
    )


def _key(cfg: dict) -> str:
    env = cfg.get("api_key_env") or "AGNES_API_KEY"
    return os.environ.get(env) or os.environ.get("OPENAI_API_KEY")


def _proxies() -> dict | None:
    p = os.environ.get("UPSTREAM_PROXY")
    return {"http": p, "https": p} if p else None


def chat(
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> str:
    cfg = gateway_config()
    if cfg.get("provider") != "openai":
        raise RuntimeError(
            f"llm.provider={cfg.get('provider')} — this client only drives the "
            "OpenAI-compatible gateway"
        )
    base = _base_url(cfg)
    key = _key(cfg)
    if not base or not key:
        raise RuntimeError(
            "OpenAI-compatible gateway not configured: set config.yaml llm.base_url "
            "or env OPENAI_BASE_URL + AGNES_API_KEY"
        )
    body: dict[str, Any] = {
        "model": model or cfg.get("model") or "deepseek-v4-flash-free",
        "messages": messages,
        "temperature": temperature if temperature is not None else cfg.get("temperature", 0.7),
        "max_tokens": max_tokens or cfg.get("max_tokens", 4096),
    }
    r = requests.post(
        f"{base}/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json=body,
        proxies=_proxies(),
        timeout=300,
    )
    r.raise_for_status()
    msg = (r.json().get("choices") or [{}])[0].get("message", {}) or {}
    return msg.get("content") or ""


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="OpenAI-compatible gateway chat (scripting)")
    ap.add_argument("prompt", nargs="?", default="Say hello in one short line.")
    ap.add_argument("--system", default=None)
    ap.add_argument("--model", default=None)
    args = ap.parse_args()
    msgs = []
    if args.system:
        msgs.append({"role": "system", "content": args.system})
    msgs.append({"role": "user", "content": args.prompt})
    print(chat(msgs, model=args.model))