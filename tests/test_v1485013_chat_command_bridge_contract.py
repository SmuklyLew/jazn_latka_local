from __future__ import annotations

import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from latka_jazn.config import JaznConfig
from latka_jazn.core.chat_command_contract import (
    apply_openai_cli_settings,
    chat_gpt_contract,
    chat_open_ai_contract,
    extract_user_text_from_payload,
    run_jsonl_chat_bridge,
)
from latka_jazn.model_adapters.factory import build_model_adapter

ROOT = Path(__file__).resolve().parents[1]


def test_chat_command_contracts_separate_chatgpt_and_openai() -> None:
    chatgpt = chat_gpt_contract().to_dict()
    openai = chat_open_ai_contract().to_dict()
    assert chatgpt["command"] == "--chat-gpt"
    assert chatgpt["requires_api_key"] is False
    assert chatgpt["uses_openai_api"] is False
    assert openai["command"] == "--chat-open-ai"
    assert openai["requires_api_key"] is True
    assert openai["uses_openai_api"] is True


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
        text=True,
        capture_output=True,
        timeout=15,
    )
    assert proc.returncode == 2
    assert "--chat-gpt" in proc.stderr


def test_bridge_discovery_cli_lists_three_modes() -> None:
    proc = subprocess.run(
        [sys.executable, "main.py", "--bridge-discovery", "--root", str(ROOT)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=20,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["local_chat"]["command"].startswith("python main.py --chat")
    assert payload["chatgpt_bridge"]["requires_api_key"] is False
    assert payload["openai_bridge"]["requires_api_key"] is True
