from __future__ import annotations

import io
import json
import time
from types import SimpleNamespace

import main
import latka_jazn.core.chat_command_contract as chat_command_module
from latka_jazn.config import JaznConfig
from latka_jazn.core.chat_command_contract import apply_chat_cli_settings, run_jsonl_chat_bridge
from latka_jazn.core.runtime_chat import run_persistent_chat
from latka_jazn.model_adapters.factory import build_model_adapter, build_model_adapter_status


def test_chat_cli_settings_select_terminal_adapter_without_openai_key(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("JAZN_MODEL_ADAPTER", raising=False)
    cfg = apply_chat_cli_settings(JaznConfig())

    status = build_model_adapter(cfg).describe()

    assert cfg.model_adapter == "terminal_runtime_adapter"
    assert status["adapter_id"] == "terminal_runtime_adapter"
    assert status["provider"] == "terminal_host"
    assert status["status"] == "terminal_bridge_available"
    assert status["requires_api_key"] is False
    assert status["can_generate_model_guided_speech"] is False


def test_model_adapter_status_cli_respects_chat_loop(monkeypatch, capsys) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("JAZN_MODEL_ADAPTER", raising=False)

    assert main.main(["--chat", "--model-adapter-status"]) == 0
    payload = json.loads(capsys.readouterr().out)

    status = payload["model_adapter_status"]
    assert status["adapter_id"] == "terminal_runtime_adapter"
    assert status["provider"] == "terminal_host"
    assert status["status"] == "terminal_bridge_available"
    assert status["selected_adapter"] == "terminal_runtime_adapter"
    assert status["requires_api_key"] is False


def test_chatgpt_bridge_timeout_returns_controlled_jsonl_error(monkeypatch) -> None:
    monkeypatch.setenv("JAZN_RUNTIME_TURN_TIMEOUT_SECONDS", "0.01")

    class HangingRuntimeSession:
        def __init__(self, config, session_id=None, no_carryover=False, source_client="test") -> None:
            self.config = config
            self.state = SimpleNamespace(session_id=session_id or "hang")

        def process_user_text(self, *args, **kwargs):
            time.sleep(5)
            return {"final_visible_text": "too late"}

        def close(self) -> None:
            pass

    monkeypatch.setattr(chat_command_module, "JaznRuntimeSession", HangingRuntimeSession)
    stdout = io.StringIO()

    rc = run_jsonl_chat_bridge(
        config=JaznConfig(),
        session_id="timeout-test",
        no_carryover=True,
        command="--chat-gpt",
        stdin=io.StringIO("hej\n"),
        stdout=stdout,
    )

    assert rc == 0
    payload = json.loads(stdout.getvalue())
    assert payload["ok"] is False
    assert payload["error_code"] == "runtime_turn_timeout"
    assert payload["chat_bridge"]["command"] == "--chat-gpt"


def test_chat_loop_timeout_closes_without_fake_latka_reply(monkeypatch) -> None:
    monkeypatch.setenv("JAZN_RUNTIME_TURN_TIMEOUT_SECONDS", "0.01")

    class HangingRuntime:
        config = JaznConfig()
        state = SimpleNamespace(session_id="chat-hang")

        def process_user_text(self, *args, **kwargs):
            time.sleep(5)
            return {"final_visible_text": "too late"}

    stdout = io.StringIO()
    lifecycle = run_persistent_chat(
        HangingRuntime(),
        stdin=io.StringIO("hej\n"),
        stdout=stdout,
        session_id="chat-hang",
        no_carryover=True,
    )

    assert lifecycle.exit_reason == "runtime_turn_timeout"
    out = stdout.getvalue()
    assert "[runtime_turn_timeout]" in out
    assert "too late" not in out


def test_status_builders_distinguish_null_chatgpt_and_chat(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("JAZN_MODEL_ADAPTER", raising=False)

    default_status = build_model_adapter_status(JaznConfig())
    chat_status = build_model_adapter_status(apply_chat_cli_settings(JaznConfig()))
    chatgpt_cfg = chat_command_module.apply_chatgpt_cli_settings(JaznConfig())
    chatgpt_status = build_model_adapter_status(chatgpt_cfg)

    assert default_status["adapter_id"] == "null_model_adapter"
    assert chat_status["adapter_id"] == "terminal_runtime_adapter"
    assert chatgpt_status["adapter_id"] == "chatgpt_runtime_adapter"
