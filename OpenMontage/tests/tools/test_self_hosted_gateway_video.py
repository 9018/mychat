from __future__ import annotations

import json
from pathlib import Path

import pytest


class FakeResponse:
    def __init__(self, payload=None, *, content=b"", status_code=200):
        self._payload = payload
        self.content = content
        self.status_code = status_code
        self.text = json.dumps(payload) if payload is not None else content.decode(errors="replace")

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.text)

    def json(self):
        return self._payload

    def iter_content(self, chunk_size=1024):
        yield self.content


@pytest.fixture
def gateway_env(monkeypatch):
    monkeypatch.setenv("AGNES_API_KEY", "test-gateway-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "http://gateway.test/v1")


def test_gateway_video_resumes_existing_task_without_post(tmp_path, monkeypatch, gateway_env):
    import requests

    calls = []
    monkeypatch.setattr(
        requests,
        "get",
        lambda url, **kwargs: (calls.append(("GET", url)) or FakeResponse({
            "status": "completed", "video_url": "http://media.test/final.mp4"
        })),
    )
    monkeypatch.setattr(
        requests,
        "post",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("resume must not POST")),
    )
    monkeypatch.setattr(requests, "request", lambda *args, **kwargs: FakeResponse(content=b"mp4"))
    monkeypatch.setattr(
        requests,
        "get",
        lambda url, **kwargs: (
            calls.append(("GET", url)),
            FakeResponse(content=b"mp4") if url.endswith(".mp4") else FakeResponse({
                "status": "completed", "video_url": "http://media.test/final.mp4"
            }),
        )[1],
    )
    from tools.video.self_hosted_gateway_video import SelfHostedGatewayVideo

    output = tmp_path / "clip.mp4"
    result = SelfHostedGatewayVideo().execute({
        "prompt": "unused on resume",
        "request_id": "task-123",
        "output_path": str(output),
    })
    assert result.success
    assert output.read_bytes() == b"mp4"
    assert result.data["request_id"] == "task-123"
    assert not any(method == "POST" for method, _ in calls)


def test_gateway_video_submits_and_returns_request_id(tmp_path, monkeypatch, gateway_env):
    import requests

    calls = []
    monkeypatch.setattr(
        requests,
        "post",
        lambda url, **kwargs: (calls.append(("POST", url)) or FakeResponse({"task_id": "task-456"})),
    )
    monkeypatch.setattr(
        requests,
        "get",
        lambda url, **kwargs: (
            calls.append(("GET", url)),
            FakeResponse({"status": "completed", "video_url": "http://media.test/final.mp4"})
            if url.endswith("task-456")
            else FakeResponse(content=b"mp4"),
        )[1],
    )
    from tools.video.self_hosted_gateway_video import SelfHostedGatewayVideo

    result = SelfHostedGatewayVideo().execute({
        "prompt": "moving paper collage",
        "model": "agnes-video-v2.0",
        "duration": 3,
        "output_path": str(tmp_path / "clip.mp4"),
    })
    assert result.success
    assert result.data["request_id"] == "task-456"


def test_gateway_video_retries_signed_url_without_bearer(tmp_path, monkeypatch, gateway_env):
    from lib.gateway_http import GatewayHTTPError
    from tools.video.self_hosted_gateway_video import SelfHostedGatewayVideo

    class FakeClient:
        def post_json(self, path, payload, timeout):
            return {"task_id": "task-signed"}

        def get_json(self, path, timeout):
            return {"status": "completed", "video_url": "https://media.example.invalid/video.mp4"}

        def download_atomic(self, url, output_path, bearer=True, timeout=600):
            if bearer:
                raise GatewayHTTPError("gateway GET video.mp4 returned HTTP 401")
            Path(output_path).write_bytes(b"mp4")
            return Path(output_path)

    monkeypatch.setattr("tools.video.self_hosted_gateway_video.GatewayHTTP", FakeClient)
    result = SelfHostedGatewayVideo().execute({"prompt": "test", "output_path": str(tmp_path / "video.mp4")})
    assert result.success
    assert (tmp_path / "video.mp4").read_bytes() == b"mp4"
