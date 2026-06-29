from __future__ import annotations

import json

import main
import pytest
from latka_jazn.config import JaznConfig
from latka_jazn.core.runtime_environment import detect_runtime_environment
from latka_jazn.model_adapters.factory import build_model_adapter_status


def _clear_host_env(monkeypatch) -> None:
    for key in list(__import__("os").environ):
        if key.startswith("CUA_DD_"):
            monkeypatch.delenv(key, raising=False)
    for key in [
        "JUPYTER_SERVER_OAI_PATH",
        "JAZN_ASSUME_CHATGPT_HOST",
        "JAZN_HOST_RUNTIME",
        "JAZN_VISIBLE_CHANNEL",
        "JAZN_MODEL_ADAPTER",
        "OPENAI_API_KEY",
    ]:
        monkeypatch.delenv(key, raising=False)


def test_environment_status_keeps_backend_and_effective_channel_separate(monkeypatch) -> None:
    _clear_host_env(monkeypatch)
    status = build_model_adapter_status(JaznConfig(), command="--chat-gpt-final-only")

    assert status["adapter_id"] == "chatgpt_runtime_adapter"
    assert status["selected_backend_adapter"] == "null_model_adapter"
    assert status["visible_channel_adapter"] == "chatgpt_runtime_adapter"
    assert status["effective_runtime_adapter"] == "chatgpt_runtime_adapter"
    assert status["base_backend_adapter_status"]["adapter_id"] == "null_model_adapter"
    assert status["runtime_environment"]["explicit_command"] == "--chat-gpt-final-only"
    assert status["runtime_environment"]["is_chatgpt_host_bridge"] is True
    assert status["requires_api_key"] is False


def test_environment_status_uses_terminal_adapter_for_chat_command(monkeypatch) -> None:
    _clear_host_env(monkeypatch)
    status = build_model_adapter_status(JaznConfig(), command="--chat")

    assert status["adapter_id"] == "terminal_runtime_adapter"
    assert status["selected_backend_adapter"] == "null_model_adapter"
    assert status["visible_channel_adapter"] == "terminal_runtime_adapter"
    assert status["runtime_environment"]["is_terminal_chat_loop"] is True


def test_model_adapter_status_detects_chatgpt_tool_container(monkeypatch, capsys) -> None:
    _clear_host_env(monkeypatch)
    monkeypatch.setenv("CUA_DD_PYTHON_TOOL", "true")

    assert main.main(["--model-adapter-status"]) == 0
    payload = json.loads(capsys.readouterr().out)
    status = payload["model_adapter_status"]

    assert status["adapter_id"] == "chatgpt_runtime_adapter"
    assert status["selected_backend_adapter"] == "null_model_adapter"
    assert status["effective_runtime_adapter"] == "chatgpt_runtime_adapter"
    assert status["runtime_environment"]["environment_host"] == "openai_chatgpt_tool_container"
    assert "detected_openai_chatgpt_tool_container" in status["runtime_environment"]["detection_basis"]


def test_default_builder_without_host_inference_stays_null(monkeypatch) -> None:
    _clear_host_env(monkeypatch)
    monkeypatch.setenv("CUA_DD_PYTHON_TOOL", "true")

    status = build_model_adapter_status(JaznConfig())

    assert status["adapter_id"] == "null_model_adapter"
    assert status["effective_runtime_adapter"] == "null_model_adapter"


def test_runtime_environment_env_marker_can_select_chatgpt(monkeypatch) -> None:
    _clear_host_env(monkeypatch)
    monkeypatch.setenv("JAZN_VISIBLE_CHANNEL", "chatgpt")

    env = detect_runtime_environment(JaznConfig())

    assert env.selected_backend_adapter == "null_model_adapter"
    assert env.visible_channel_adapter == "chatgpt_runtime_adapter"
    assert env.effective_runtime_adapter == "chatgpt_runtime_adapter"
    assert env.environment_host == "chatgpt_env_marker"


def test_startup_status_exposes_runtime_environment(monkeypatch, capsys) -> None:
    _clear_host_env(monkeypatch)
    monkeypatch.setenv("JAZN_HOST_RUNTIME", "chatgpt")

    assert main.main(["--startup-status-fast"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["runtime_environment"]["effective_runtime_adapter"] == "chatgpt_runtime_adapter"
    assert payload["model_adapter_status"]["selected_backend_adapter"] == "null_model_adapter"
    assert payload["model_adapter_status"]["adapter_id"] == "chatgpt_runtime_adapter"


@pytest.mark.parametrize(
    ("args", "expected_command", "expected_adapter"),
    [
        (["--chat-gpt", "--startup-status-fast"], "--chat-gpt", "chatgpt_runtime_adapter"),
        (["--chat-gpt-final-only", "--startup-status-fast"], "--chat-gpt-final-only", "chatgpt_runtime_adapter"),
        (["--chat", "--startup-status-fast"], "--chat", "terminal_runtime_adapter"),
    ],
)
def test_startup_status_combined_cli_mode_reports_effective_adapter(
    monkeypatch,
    capsys,
    args: list[str],
    expected_command: str,
    expected_adapter: str,
) -> None:
    _clear_host_env(monkeypatch)

    assert main.main(args) == 0
    payload = json.loads(capsys.readouterr().out)
    runtime_environment = payload["runtime_environment"]
    model_adapter_status = payload["model_adapter_status"]

    assert runtime_environment["explicit_command"] == expected_command
    assert runtime_environment["effective_runtime_adapter"] == expected_adapter
    assert runtime_environment["visible_channel_adapter"] == expected_adapter
    assert model_adapter_status["selected_backend_adapter"] == "null_model_adapter"
    assert model_adapter_status["effective_runtime_adapter"] == expected_adapter
