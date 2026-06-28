from __future__ import annotations

from pathlib import Path

import pytest

import main

ROOT = Path(__file__).resolve().parents[1]


def test_chat_gpt_final_only_cli_is_standalone_shortcut(monkeypatch) -> None:
    captured = {}

    def fake_run_jsonl_chat_bridge(**kwargs):
        captured.update(kwargs)
        return 0

    monkeypatch.setattr(main, "run_jsonl_chat_bridge", fake_run_jsonl_chat_bridge)

    assert main.main(["--root", str(ROOT), "--chat-gpt-final-only"]) == 0

    assert captured["command"] == "--chat-gpt"
    assert captured["require_openai_api_key"] is False
    assert captured["output_mode"] == "final_visible_text"


def test_final_only_alias_requires_chat_gpt_or_standalone_shortcut() -> None:
    with pytest.raises(SystemExit) as exc:
        main.main(["--final-only"])

    assert exc.value.code == 2


def test_chat_gpt_final_only_option_must_be_before_remainder_message(monkeypatch) -> None:
    captured = {}

    def fake_run_jsonl_chat_bridge(**kwargs):
        captured.update(kwargs)
        return 0

    monkeypatch.setattr(main, "run_jsonl_chat_bridge", fake_run_jsonl_chat_bridge)

    assert main.main(["--root", str(ROOT), "--chat-gpt", "--chat-gpt-final-only", "--", "hej"]) == 0
    assert captured["output_mode"] == "final_visible_text"


def test_final_only_alias_with_chat_gpt_passes_final_visible_output_mode(monkeypatch) -> None:
    captured = {}

    def fake_run_jsonl_chat_bridge(**kwargs):
        captured.update(kwargs)
        return 0

    monkeypatch.setattr(main, "run_jsonl_chat_bridge", fake_run_jsonl_chat_bridge)

    assert main.main(["--root", str(ROOT), "--chat-gpt", "--final-only", "--", "hej"]) == 0

    assert captured["command"] == "--chat-gpt"
    assert captured["output_mode"] == "final_visible_text"
