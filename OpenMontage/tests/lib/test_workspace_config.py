from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def clear_workspace_environment(monkeypatch):
    for key in (
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
    ):
        monkeypatch.delenv(key, raising=False)


def test_process_env_wins_over_env_file_and_config(tmp_path, monkeypatch):
    root = tmp_path / "workspace"
    app = root / "OpenMontage"
    app.mkdir(parents=True)
    (root / ".env").write_text(
        "AGNES_API_KEY=file-key\nOPENAI_BASE_URL=http://file.test/v1\n",
        encoding="utf-8",
    )
    (root / "config.json").write_text(
        json.dumps({"baseUrl": "http://config.test/v1"}), encoding="utf-8"
    )
    monkeypatch.setenv("AGNES_API_KEY", "process-key")

    from lib.workspace_config import load_workspace_config

    cfg = load_workspace_config(app)
    assert cfg.gateway_key == "process-key"
    assert cfg.gateway_base == "http://file.test/v1"


def test_aliases_and_safe_view_do_not_expose_secrets(tmp_path, monkeypatch):
    monkeypatch.setenv("GROK2API_KEY", "secret-grok")
    monkeypatch.setenv("GROK2API_BASE", "http://grok.test:8000")

    from lib.workspace_config import load_workspace_config

    cfg = load_workspace_config(tmp_path)
    assert cfg.grok_key == "secret-grok"
    assert cfg.safe_view()["grok_key"] == "set"
    assert "secret-grok" not in repr(cfg.safe_view())
    assert cfg.safe_view()["grok_base"] == "grok.test:8000"


def test_explicit_env_file_is_loaded_without_overriding_process_env(tmp_path, monkeypatch):
    env_file = tmp_path / "custom.env"
    env_file.write_text(
        "AGNES_API_KEY=custom-key\nGROK2API_BASE=http://custom.test/v1\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("OPENMONTAGE_ENV_FILE", str(env_file))
    monkeypatch.setenv("AGNES_API_KEY", "process-key")

    from lib.workspace_config import load_workspace_config

    cfg = load_workspace_config(tmp_path)
    assert cfg.gateway_key == "process-key"
    assert cfg.grok_base == "http://custom.test/v1"


def test_config_json_defaults_are_used_for_non_secret_values(tmp_path, monkeypatch):
    (tmp_path / "config.json").write_text(
        json.dumps(
            {
                "baseUrl": "http://config.test/v1",
                "models": {
                    "image": "agnes-image-2.1-flash",
                    "video": "agnes-video-v2.0",
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("AGNES_API_KEY", raising=False)

    from lib.workspace_config import load_workspace_config

    cfg = load_workspace_config(tmp_path)
    assert cfg.gateway_base == "http://config.test/v1"
    assert cfg.image_model == "agnes-image-2.1-flash"
    assert cfg.video_model == "agnes-video-v2.0"
