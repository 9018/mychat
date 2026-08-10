"""Small OpenAI-compatible HTTP client shared by gateway providers."""

from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path
from typing import Any

import requests

from lib.workspace_config import load_workspace_config


class GatewayHTTPError(RuntimeError):
    """Provider-safe error that never contains credentials or response bodies."""


class GatewayHTTP:
    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        cfg = load_workspace_config(Path(__file__).resolve().parent.parent)
        self.base_url = (base_url or cfg.gateway_base or "").rstrip("/")
        self.api_key = api_key or cfg.gateway_key
        if not self.base_url:
            raise GatewayHTTPError("gateway base URL is not configured")
        if not self.api_key:
            raise GatewayHTTPError("gateway API key is not configured")
        proxy = cfg.upstream_proxy
        self.proxies = {"http": proxy, "https": proxy} if proxy else None

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "OpenMontage/vox-integration",
        }

    def _raise(self, method: str, url: str, response: requests.Response) -> None:
        if response.status_code < 400:
            return
        path = url.split("/v1", 1)[-1] if "/v1" in url else url.rsplit("/", 1)[-1]
        raise GatewayHTTPError(f"gateway {method} {path} returned HTTP {response.status_code}")

    def post_json(self, path: str, payload: dict[str, Any], timeout: int = 240) -> dict[str, Any]:
        url = f"{self.base_url}/{path.lstrip('/')}"
        try:
            response = requests.post(url, headers=self.headers, json=payload, proxies=self.proxies, timeout=timeout)
            self._raise("POST", url, response)
            value = response.json()
        except GatewayHTTPError:
            raise
        except Exception as exc:
            raise GatewayHTTPError(f"gateway POST failed: {type(exc).__name__}") from exc
        if not isinstance(value, dict):
            raise GatewayHTTPError("gateway POST returned a non-object response")
        return value

    def get_json(self, path: str, timeout: int = 60) -> dict[str, Any]:
        url = f"{self.base_url}/{path.lstrip('/')}"
        try:
            response = requests.get(url, headers=self.headers, proxies=self.proxies, timeout=timeout)
            self._raise("GET", url, response)
            value = response.json()
        except GatewayHTTPError:
            raise
        except Exception as exc:
            raise GatewayHTTPError(f"gateway GET failed: {type(exc).__name__}") from exc
        if not isinstance(value, dict):
            raise GatewayHTTPError("gateway GET returned a non-object response")
        return value

    def download_atomic(self, url: str, output_path: Path, *, bearer: bool = True, timeout: int = 600) -> Path:
        headers = {"User-Agent": "OpenMontage/vox-integration"}
        if bearer:
            headers["Authorization"] = f"Bearer {self.api_key}"
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=f".{output_path.name}.", suffix=".part", dir=output_path.parent)
        os.close(fd)
        temp_path = Path(temp_name)
        try:
            response = requests.get(url, headers=headers, proxies=self.proxies, timeout=timeout, stream=True)
            self._raise("GET", url, response)
            with temp_path.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        handle.write(chunk)
            temp_path.replace(output_path)
            return output_path
        except GatewayHTTPError:
            temp_path.unlink(missing_ok=True)
            raise
        except Exception as exc:
            temp_path.unlink(missing_ok=True)
            raise GatewayHTTPError(f"gateway download failed: {type(exc).__name__}") from exc
