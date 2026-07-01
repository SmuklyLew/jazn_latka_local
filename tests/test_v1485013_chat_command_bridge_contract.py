from __future__ import annotations

import io
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import main
import latka_jazn.core.chat_command_contract as chat_command_module
from latka_jazn.config import JaznConfig
from latka_jazn.core.chat_command_contract import (
    apply_chatgpt_cli_settings,
    apply_openai_cli_settings,
    chat_gpt_contract,
    chat_lm_studio_contract,
    chat_open_ai_contract,
    extract_user_text_from_payload,
    run_jsonl_chat_bridge,
)
from latka_jazn.model_adapters.factory import build_model_adapter

ROOT = Path(__file__).resolve().parents[1]
LMSTUDIO_TRUTH_BOUNDARY = (
    "LM Studio jest lokalnym backendem językowym przez OpenAI-compatible API. "
    "Nie wymaga OPENAI_API_KEY i nie jest źródłem tożsamości, pamięci, stanu ani prawdy runtime Jaźni. "
    "Widoczna odpowiedź przechodzi przez istniejący runtime, walidację i truthful fallback."
)


def test_chat_command_contracts_separate_chatgpt_and_openai() -> None:
    chatgpt = chat_gpt_contract().to_dict()
    openai = chat_open_ai_contract().to_dict()
    lmstudio = chat_lm_studio_contract().to_dict()
    assert chatgpt["command"] == "--chat-gpt"
    assert chatgpt["requires_api_key"] is False
    assert chatgpt["uses_openai_api"] is False
    assert openai["command"] == "--chat-open-ai"
    assert openai["requires_api_key"] is True
    assert openai["uses_openai_api"] is True
    assert lmstudio["command"] == "--chat-lm-studio"
    assert lmstudio["requires_api_key"] is False
    assert lmstudio["uses_openai_api"] is False
    assert lmstudio["keeps_process_alive"] is True
    assert lmstudio["engine_reused_between_turns"] is True
    assert lmstudio["truth_boundary"] == LMSTUDIO_TRUTH_BOUNDARY
    assert "final_visible_text" in chatgpt["output_modes"]
    assert "jedyną kanoniczną flagą" in chatgpt["truth_boundary"]
    assert "Legacy aliasy" in chatgpt["truth_boundary"]
    assert "--chat-gpt--final-only" not in chatgpt["truth_boundary"]


@pytest.mark.parametrize(
    "payload,expected",
    [
        ({"message": "a"}, ("a", "json", "message")),
        ({"text": "b"}, ("b", "json", "text")),
        ({"user_text": "c"}, ("c", "json", "user_text")),
        ({"content": "d"}, ("d", "json", "content")),
        ({"prompt": "e"}, ("e", "json", "prompt")),
        ({"messages": [{"role": "assistant", "content": "old"}, {"role": "user", "content": "new"}]}, ("new", "json_chat_messages", "messages[user].content")),
        ({"messages": [{"role": "user", "content": [{"text": "he"}, {"text": "j"}]}]}, ("hej", "json_chat_messages", "messages[user].content")),
    ],
)
def test_extract_user_text_from_supported_chatgpt_shapes(payload, expected) -> None:
    assert extract_user_text_from_payload(payload) == expected


def test_chat_open_ai_without_key_fails_truthfully(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    cfg = JaznConfig(root=ROOT)
    stdout = io.StringIO()
    rc = run_jsonl_chat_bridge(
        config=cfg,
        session_id="unit",
        no_carryover=True,
        command="--chat-open-ai",
        stdin=io.StringIO('{"message":"hej"}\n'),
        stdout=stdout,
        require_openai_api_key=True,
    )
    assert rc == 3
    payload = json.loads(stdout.getvalue())
    assert payload["ok"] is False
    assert payload["error_code"] == "missing_openai_api_key"
    assert payload["chat_command_contract"]["uses_openai_api"] is True


@pytest.mark.parametrize("flag", ["--chat-open-ai", "--chat-openai"])
def test_chat_openai_cli_flags_without_key_fail_truthfully(monkeypatch, capsys, flag: str) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    assert main.main([flag]) == 3
    payload = json.loads(capsys.readouterr().out)

    assert payload["ok"] is False
    assert payload["error_code"] == "missing_openai_api_key"
    assert payload["chat_command_contract"]["requires_api_key"] is True


def test_chat_gpt_contract_still_does_not_require_openai_api_key(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    contract = chat_gpt_contract().to_dict()

    assert contract["requires_api_key"] is False
    assert contract["uses_openai_api"] is False


def test_apply_chatgpt_cli_settings_selects_chatgpt_host_adapter(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    cfg = JaznConfig(root=ROOT)
    apply_chatgpt_cli_settings(cfg)
    status = build_model_adapter(cfg).describe()

    assert cfg.model_adapter == "chatgpt_runtime_adapter"
    assert status["name"] == "chatgpt_runtime_adapter"
    assert status["provider"] == "chatgpt_host"
    assert status["status"] == "host_bridge_available"
    assert status["model"] == "chatgpt_host_model"
    assert status["requires_api_key"] is False
    assert status["can_generate_model_guided_speech"] is False


def test_apply_openai_cli_settings_selects_openai_adapter(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-used-by-this-test")
    cfg = JaznConfig(root=ROOT)
    apply_openai_cli_settings(cfg, model="gpt-test", api_base="https://api.openai.com/v1/", timeout_seconds=7, max_output_tokens=123)
    status = build_model_adapter(cfg).describe()
    assert status["name"] == "openai_responses_adapter"
    assert status["status"] == "configured"
    assert status["model"] == "gpt-test"
    assert status["api_base"] == "https://api.openai.com/v1"


def test_chat_jsonl_removed_exit_code_and_message() -> None:
    proc = subprocess.run(
        [sys.executable, "main.py", "--chat-jsonl"],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=15,
    )
    assert proc.returncode == 2
    assert "--chat-gpt" in proc.stderr


def test_bridge_discovery_cli_lists_aliases_and_lmstudio_contract() -> None:
    proc = subprocess.run(
        [sys.executable, "main.py", "--bridge-discovery", "--root", str(ROOT)],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=20,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["local_chat"]["command"].startswith("python main.py --chat")
    assert payload["chatgpt_bridge"]["requires_api_key"] is False
    assert payload["chatgpt_bridge"]["canonical_command"] == "--chat-gpt"
    assert payload["chatgpt_bridge"]["one_shot_command"].startswith("python main.py --chat-gpt --")
    assert payload["chatgpt_bridge"]["one_shot_prefers_live_daemon"] is True
    assert payload["chatgpt_bridge"]["daemon_fast_path_env"].startswith("JAZN_CHATGPT_PREFER_DAEMON=0")
    assert "--chat-gpt-final-only" in payload["chatgpt_bridge"]["legacy_aliases"]
    assert payload["openai_bridge"]["requires_api_key"] is True
    assert "--chat-openai" in payload["openai_bridge"]["aliases"]
    assert payload["lmstudio_bridge"]["command"].startswith("python main.py --chat-lm-studio")
    assert payload["lmstudio_bridge"]["requires_api_key"] is False
    assert payload["lmstudio_bridge"]["truth_boundary"] == LMSTUDIO_TRUTH_BOUNDARY


def _install_fake_runtime_session(monkeypatch, final_text: str = "[czas] Widoczna odpowiedź Łatki.") -> None:
    class FakeRuntimeSession:
        def __init__(self, config, session_id=None, no_carryover=False, source_client="test") -> None:
            self.config = config
            self.state = SimpleNamespace(session_id=session_id or "fake-session")
            self.closed = False

        def process_user_text(self, user_text: str, *, client: str, lifecycle: str, session_id_source: str, process_reused: bool) -> dict:
            return {
                "ok": True,
                "final_visible_text": final_text,
                "final_response_contract": {"final_visible_text": final_text},
                "exact_runtime_text": final_text,
            }

        def close(self) -> None:
            self.closed = True

    monkeypatch.setattr(chat_command_module, "JaznRuntimeSession", FakeRuntimeSession)


def test_chat_gpt_default_output_stays_jsonl(monkeypatch) -> None:
    _install_fake_runtime_session(monkeypatch)
    stdout = io.StringIO()

    rc = chat_command_module.run_jsonl_chat_bridge(
        config=JaznConfig(root=ROOT),
        session_id="unit-jsonl",
        no_carryover=True,
        command="--chat-gpt",
        stdin=io.StringIO("hej\n"),
        stdout=stdout,
    )

    assert rc == 0
    payload = json.loads(stdout.getvalue())
    assert payload["final_visible_text"] == "[czas] Widoczna odpowiedź Łatki."
    assert payload["chat_bridge"]["command"] == "--chat-gpt"




def test_chat_gpt_cli_one_shot_uses_canonical_flag_and_final_text(monkeypatch, capsys) -> None:
    monkeypatch.setenv("JAZN_CHATGPT_PREFER_DAEMON", "0")
    _install_fake_runtime_session(monkeypatch, final_text="[czas] Jedna kanoniczna flaga działa.")

    assert main.main(["--chat-gpt", "--", "hej"]) == 0

    out = capsys.readouterr().out
    assert out == "[czas] Jedna kanoniczna flaga działa.\n"
    assert not out.lstrip().startswith("{")


def test_chat_gpt_one_shot_uses_live_daemon_when_env_enabled(monkeypatch, tmp_path, capsys) -> None:
    marker_dir = tmp_path / "workspace_runtime"
    marker_dir.mkdir(parents=True)
    (marker_dir / "JAZN_ACTIVE_RUNTIME.json").write_text("{}\n", encoding="utf-8")
    calls: list[str] = []

    def fake_status_daemon(cfg, *, host="127.0.0.1", port=8787, marker_output=None):
        calls.append("status")
        return {"active_state": "active_degraded", "endpoint_reachable": True, "pid_alive": True}

    def fake_chat_daemon(cfg, user_text, **kwargs):
        calls.append(f"chat:{user_text}")
        return {"ok": True, "final_visible_text": "[czas] daemon fast path działa."}

    def fail_local_bridge(*args, **kwargs):
        raise AssertionError("local JSONL bridge should not run when daemon fast path is healthy")

    monkeypatch.setattr(main, "status_daemon", fake_status_daemon)
    monkeypatch.setattr(main, "chat_daemon", fake_chat_daemon)
    monkeypatch.setattr(main, "run_jsonl_chat_bridge", fail_local_bridge)
    monkeypatch.setenv("JAZN_CHATGPT_PREFER_DAEMON", "1")

    assert main.main(["--root", str(tmp_path), "--chat-gpt", "--", "hej"]) == 0

    assert calls == ["status", "chat:hej"]
    assert capsys.readouterr().out == "[czas] daemon fast path działa.\n"

def test_chat_gpt_final_only_outputs_only_final_visible_text(monkeypatch) -> None:
    _install_fake_runtime_session(monkeypatch)
    stdout = io.StringIO()

    rc = chat_command_module.run_jsonl_chat_bridge(
        config=JaznConfig(root=ROOT),
        session_id="unit-final-only",
        no_carryover=True,
        command="--chat-gpt",
        stdin=io.StringIO("hej\n"),
        stdout=stdout,
        output_mode="final_visible_text",
    )

    assert rc == 0
    assert stdout.getvalue() == "[czas] Widoczna odpowiedź Łatki.\n"
    assert not stdout.getvalue().lstrip().startswith("{")


def test_chat_lm_studio_one_shot_uses_same_runtime_and_final_text(monkeypatch, capsys) -> None:
    _install_fake_runtime_session(monkeypatch, final_text="[czas] Wspólna neurologia działa.")

    assert main.main(["--chat-lm-studio", "--", "hej"]) == 0

    out = capsys.readouterr().out
    assert out == "[czas] Wspólna neurologia działa.\n"
    assert not out.lstrip().startswith("{")


def test_chat_terminal_one_shot_uses_same_runtime_and_final_text(monkeypatch, capsys) -> None:
    class FakeWorker:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs
        def process_user_text(self, user_text: str, **kwargs) -> dict:
            assert self.kwargs["command"] == "--chat"
            assert kwargs["client"] == "terminal_chat_one_shot"
            return {
                "ok": True,
                "final_visible_text": "[czas] Terminal używa tej samej sesji.",
                "final_response_contract": {"final_visible_text": "[czas] Terminal używa tej samej sesji."},
            }
        def close(self) -> None:
            pass

    monkeypatch.setattr(main, "RuntimeSessionWorker", FakeWorker)

    assert main.main(["--chat", "--", "hej"]) == 0

    out = capsys.readouterr().out
    assert out == "[czas] Terminal używa tej samej sesji.\n"
    assert not out.lstrip().startswith("{")

def test_chat_gpt_one_shot_uses_local_bridge_by_default(monkeypatch, tmp_path) -> None:
    calls: list[str] = []

    def fail_status_daemon(*args, **kwargs):
        raise AssertionError("daemon status should not run by default for local --chat-gpt one-shot")

    def fake_run_jsonl_chat_bridge(**kwargs):
        calls.append("local")
        assert kwargs["command"] == "--chat-gpt"
        assert kwargs["output_mode"] == "final_visible_text"
        return 0

    monkeypatch.delenv("JAZN_CHATGPT_PREFER_DAEMON", raising=False)
    monkeypatch.setattr(main, "status_daemon", fail_status_daemon)
    monkeypatch.setattr(main, "run_jsonl_chat_bridge", fake_run_jsonl_chat_bridge)

    assert main.main(["--root", str(tmp_path), "--chat-gpt", "--", "hej"]) == 0
    assert calls == ["local"]
