from __future__ import annotations


def test_mimo_requires_gateway_base_and_key(monkeypatch):
    monkeypatch.delenv("AGNES_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    from tools.audio.mimo_tts import MiMoTTS
    from tools.base_tool import ToolStatus

    assert MiMoTTS().get_status() == ToolStatus.UNAVAILABLE


def test_mimo_is_available_when_gateway_base_and_key_exist(monkeypatch):
    monkeypatch.setenv("AGNES_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "http://gateway.test/v1")
    from tools.audio.mimo_tts import MiMoTTS
    from tools.base_tool import ToolStatus

    assert MiMoTTS().get_status() == ToolStatus.AVAILABLE
