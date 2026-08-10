"""Explicit xAI-compatible endpoint overrides for OpenMontage Grok tools.

Lets the Grok tools talk to the SELF-HOSTED Grok2API gateway instead of
api.x.ai — no Atlas/magic guesses, everything explicit:

  XAI_BASE       → http://10.0.1.108:8000   (or shared GROK2API_BASE from .env)
  UPSTREAM_PROXY → socks5h://192.168.99.3:1080  (when 10.0.1.108 needs a proxy)

Media links returned by Grok2API point at 127.0.0.1 — `media_url()` rewrites
them onto the configured base and flags whether the Bearer key must be sent.
When unset, everything falls back to the original api.x.ai behaviour.
"""
from __future__ import annotations

import os
from urllib.parse import urlsplit, urlunsplit


def api_base() -> str:
    return (
        os.environ.get("XAI_BASE")
        or os.environ.get("GROK2API_BASE")
        or "https://api.x.ai"
    ).rstrip("/")


def proxies() -> dict | None:
    p = os.environ.get("UPSTREAM_PROXY")
    return {"http": p, "https": p} if p else None


def api_key() -> str | None:
    """Return the shared Grok2API key, accepting the legacy xAI alias."""
    return os.environ.get("GROK2API_KEY") or os.environ.get("XAI_API_KEY")


def media_url(url: str) -> tuple[str, bool]:
    """Return (download_url, needs_bearer). Grok2API media hosts are
    127.0.0.1/localhost and require the client key on the media endpoints."""
    if not url or url.startswith("https://api.x.ai"):
        return url, False
    u = urlsplit(url)
    if u.hostname in ("127.0.0.1", "localhost"):
        b = urlsplit(api_base())
        return urlunsplit((b.scheme, b.netloc, u.path, u.query, u.fragment)), True
    return url, False
