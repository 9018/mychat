from pathlib import Path

from tools.graphics.self_hosted_gateway_image import SelfHostedGatewayImage


def test_gateway_image_b64_response(monkeypatch, tmp_path):
    import base64

    class FakeClient:
        def post_json(self, path, payload, timeout):
            return {"data": [{"b64_json": base64.b64encode(b"png").decode()}]}

    monkeypatch.setattr("tools.graphics.self_hosted_gateway_image.GatewayHTTP", FakeClient)
    result = SelfHostedGatewayImage().execute({"prompt": "test", "output_path": str(tmp_path / "image.png")})
    assert result.success
    assert (tmp_path / "image.png").read_bytes() == b"png"


def test_gateway_image_payload_forwards_aspect_ratio(monkeypatch, tmp_path):
    seen = {}

    class FakeClient:
        def post_json(self, path, payload, timeout):
            seen.update(payload)
            return {"data": [{"b64_json": "cG5n"}]}

    monkeypatch.setattr("tools.graphics.self_hosted_gateway_image.GatewayHTTP", FakeClient)
    SelfHostedGatewayImage().execute({"prompt": "test", "aspect_ratio": "9:16", "output_path": str(tmp_path / "image.png")})
    assert seen["aspect_ratio"] == "9:16"


def test_gateway_image_retries_signed_url_without_bearer(monkeypatch, tmp_path):
    tool = SelfHostedGatewayImage()
    monkeypatch.setattr(tool, "get_status", lambda: "available")

    class FakeClient:
        def post_json(self, path, payload, timeout):
            return {"data": [{"url": "https://media.example.invalid/image.png"}]}

        def download_atomic(self, url, output_path, bearer=True, timeout=600):
            if bearer:
                from lib.gateway_http import GatewayHTTPError
                raise GatewayHTTPError("gateway GET image.png returned HTTP 401")
            Path(output_path).write_bytes(b"png")
            return Path(output_path)

    monkeypatch.setattr("tools.graphics.self_hosted_gateway_image.GatewayHTTP", FakeClient)
    result = tool.execute({"prompt": "test", "output_path": str(tmp_path / "image.png")})
    assert result.success
    assert (tmp_path / "image.png").read_bytes() == b"png"
