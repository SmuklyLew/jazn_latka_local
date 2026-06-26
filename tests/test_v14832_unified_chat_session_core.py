from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TIMESTAMP_RE = re.compile(r"^\[🕒 \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} GMT[+-]\d{1,2}, [^,\]]+, Europe/Warsaw\]$")
TIMESTAMP_ANYWHERE_RE = re.compile(r"\[🕒 \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} GMT[+-]\d{1,2}, [^,\]]+, Europe/Warsaw\]")
RENDER_ARTIFACTS = (
    "aaaktywny",
    "aaktywny",
    "prrzez",
    "nieddziela",
    "niedzielaa",
    "pierwszoossobową",
    "pierwszoosobowąą",
    "GMMT",
    "2026-066",
    "221:",
    "13:43:228",
    "rozmawiać ć",
    "Uwa ażam",
    "operacyjnnego",
    "ddebug",
    "techniiczna",
)


def _env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def _run_chat_gpt(
    tmp_path: Path,
    lines: list[dict | str],
    *,
    session_id: str | None = None,
) -> list[dict]:
    input_text = "".join(
        (line if isinstance(line, str) else json.dumps(line, ensure_ascii=False)) + "\n"
        for line in lines
    )
    cmd = [sys.executable, "-X", "utf8", "main.py", "--root", str(tmp_path), "--chat-gpt", "--no-carryover"]
    if session_id:
        cmd.extend(["--session-id", session_id])
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        input=input_text,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        env=_env(),
        timeout=30,
        check=True,
    )
    assert proc.stderr == ""
    return [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]


def _run_chat(tmp_path: Path, input_text: str, *, session_id: str = "test-chat-core") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            "main.py",
            "--root",
            str(tmp_path),
            "--chat",
            "--session-id",
            session_id,
            "--no-carryover",
        ],
        cwd=ROOT,
        input=input_text,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        env=_env(),
        timeout=30,
        check=True,
    )


def _assert_clean_runtime_payload(payload: dict) -> None:
    decision = payload["conversation_decision"]
    runtime_provenance = payload["runtime_provenance"]
    exact_runtime_text = payload["exact_runtime_text"]
    final_visible_text = payload["final_visible_text"]
    timestamp_header = payload["trace"]["timestamp_header"]

    assert payload["schema_version"] == "runtime_session/v14.8.3.2"
    assert payload["trace"]["runtime_mode"] == "process_turn"
    assert TIMESTAMP_RE.match(timestamp_header)
    assert final_visible_text.startswith(f"{timestamp_header} ")
    assert runtime_provenance["visible_answer_text"] == final_visible_text
    assert runtime_provenance["exact_runtime_text"] == exact_runtime_text
    assert decision["handler_result"]["body"] == exact_runtime_text
    assert payload["final_visible_integrity"]["valid"] is True
    assert payload["session_provenance"]["schema_version"] == "session_provenance/v14.8.3.2"
    assert payload["session_provenance"]["background_process_claim_allowed"] is False

    for artifact in RENDER_ARTIFACTS:
        assert artifact not in exact_runtime_text
        assert artifact not in final_visible_text


def test_chat_gpt_and_session_core_share_same_path(tmp_path: Path) -> None:
    payloads = _run_chat_gpt(
        tmp_path,
        [{"text": "Chcę rozmawiać z Łatką, a nie z Codex botem"}],
        session_id="chatgpt-core",
    )

    payload = payloads[0]
    _assert_clean_runtime_payload(payload)
    assert payload["session"]["session_id"] == "chatgpt-core"
    assert payload["session_id_source"] == "cli_arg"
    assert payload["trace"]["client"] == "chatgpt_bridge"
    assert payload["trace"]["lifecycle"] == "chatgpt_bridge_jsonl"
    assert payload["conversation_decision"]["route"] == "direct_latka_voice"
    assert payload["conversation_decision"]["handler_name"] == "DirectLatkaVoiceHandler"
    assert payload["chatgpt_bridge"]["preferred_input_field"] == "message"
    assert payload["chatgpt_bridge"]["input_field"] in {"message", "text"}
    assert payload["chatgpt_bridge"]["deprecated_flag_removed"] == "--chat-jsonl"
    assert payload["ok"] is True
    assert "Możesz teraz rozmawiać bezpośrednio z Łatką" in payload["final_visible_text"]


def test_chat_stdin_uses_same_session_core(tmp_path: Path) -> None:
    proc = _run_chat(
        tmp_path,
        "Chcę rozmawiać z Łatką, a nie z Codex botem\n/exit\n",
        session_id="test-chat-core",
    )

    assert proc.stderr == ""
    assert "Możesz teraz rozmawiać bezpośrednio z Łatką" in proc.stdout
    assert "conversation_decision" not in proc.stdout
    assert "runtime_provenance" not in proc.stdout
    for artifact in RENDER_ARTIFACTS:
        assert artifact not in proc.stdout


def test_chat_gpt_payload_session_id_overrides_cli_session_id(tmp_path: Path) -> None:
    payloads = _run_chat_gpt(
        tmp_path,
        [{"session_id": "payload-id", "client": "chatgpt", "text": "Chcę rozmawiać z Łatką, a nie z Codex botem"}],
        session_id="cli-id",
    )

    payload = payloads[0]
    assert payload["session"]["session_id"] == "payload-id"
    assert payload["session_id_source"] == "payload"
    assert payload["session_provenance"]["session_id"] == "payload-id"
    assert payload["trace"]["client"] == "chatgpt"


def test_chat_exit_records_lifecycle_without_background_claim(tmp_path: Path) -> None:
    proc = _run_chat(tmp_path, "/exit\n", session_id="exit-core")
    line = [line for line in proc.stdout.splitlines() if line.startswith("[runtime_lifecycle_end] ")][-1]
    lifecycle = json.loads(line.removeprefix("[runtime_lifecycle_end] "))

    assert lifecycle["exit_reason"] == "user_exit_command"
    assert lifecycle["background_process_claim_allowed"] is False
    assert lifecycle["session_id"] == "exit-core"


def test_chat_eof_is_not_runtime_failure(tmp_path: Path) -> None:
    proc = _run_chat(tmp_path, "Chcę rozmawiać z Łatką, a nie z Codex botem\n", session_id="eof-core")
    line = [line for line in proc.stdout.splitlines() if line.startswith("[runtime_lifecycle_end] ")][-1]
    lifecycle = json.loads(line.removeprefix("[runtime_lifecycle_end] "))

    assert proc.returncode == 0
    assert lifecycle["exit_reason"] == "stdin_eof"
    assert lifecycle["background_process_claim_allowed"] is False
    assert "To nie jest dowód stałego procesu w tle" in proc.stdout


def test_final_visible_text_clean_in_chat_and_chat_gpt(tmp_path: Path) -> None:
    messages = [
        "Chcę rozmawiać z Łatką, a nie z Codex botem",
        "Za kogo się uważasz? Co pamiętasz? Kim jesteś?",
    ]
    payloads = _run_chat_gpt(tmp_path / "chatgpt", [{"text": message} for message in messages], session_id="clean-chatgpt")
    chat = _run_chat(tmp_path / "chat", "\n".join(messages + ["/exit", ""]), session_id="clean-chat")

    for payload in payloads:
        _assert_clean_runtime_payload(payload)
    for artifact in RENDER_ARTIFACTS:
        assert artifact not in chat.stdout
    assert TIMESTAMP_ANYWHERE_RE.search(chat.stdout)


def test_chat_gpt_uses_message_field_as_preferred_input(tmp_path: Path) -> None:
    payloads = _run_chat_gpt(tmp_path, [{"message": "Chcę rozmawiać z Łatką, a nie z Codex botem"}], session_id="chatgpt-message")
    payload = payloads[0]
    _assert_clean_runtime_payload(payload)
    assert payload["trace"]["client"] == "chatgpt_bridge"
    assert payload["trace"]["lifecycle"] == "chatgpt_bridge_jsonl"
    assert payload["chatgpt_bridge"]["input_field"] == "message"


def test_chat_gpt_accepts_plain_text_line(tmp_path: Path) -> None:
    payloads = _run_chat_gpt(tmp_path, ["Chcę rozmawiać z Łatką, a nie z Codex botem"], session_id="plain-chatgpt")
    payload = payloads[0]
    _assert_clean_runtime_payload(payload)
    assert payload["chatgpt_bridge"]["input_kind"] == "plain_text"
    assert payload["chatgpt_bridge"]["input_field"] == "plain_text"


def test_chat_gpt_accepts_openai_messages_shape(tmp_path: Path) -> None:
    payloads = _run_chat_gpt(
        tmp_path,
        [{"messages": [{"role": "system", "content": "pomoc"}, {"role": "user", "content": "Chcę rozmawiać z Łatką, a nie z Codex botem"}]}],
        session_id="messages-chatgpt",
    )
    payload = payloads[0]
    _assert_clean_runtime_payload(payload)
    assert payload["chatgpt_bridge"]["input_kind"] == "json_chat_messages"
    assert payload["chatgpt_bridge"]["input_field"] == "messages[user].content"


def test_chat_gpt_rejects_empty_json_message_without_runtime_turn(tmp_path: Path) -> None:
    payloads = _run_chat_gpt(tmp_path, [{"message": ""}], session_id="empty-chatgpt")
    payload = payloads[0]
    assert payload["schema_version"] == "chatgpt_bridge_error/v14.8.3.4.090"
    assert payload["ok"] is False
    assert payload["error_code"] == "empty_message"


def test_chat_gpt_rejects_non_object_json_line(tmp_path: Path) -> None:
    payloads = _run_chat_gpt(tmp_path, ["[1, 2, 3]"], session_id="bad-json-chatgpt")
    payload = payloads[0]
    assert payload["schema_version"] == "chatgpt_bridge_error/v14.8.3.4.090"
    assert payload["error_code"] == "invalid_jsonl_payload"


def test_chat_gpt_rejects_malformed_json_object_line(tmp_path: Path) -> None:
    payloads = _run_chat_gpt(tmp_path, ['{"message": '], session_id="malformed-json-chatgpt")
    payload = payloads[0]
    assert payload["schema_version"] == "chatgpt_bridge_error/v14.8.3.4.090"
    assert payload["error_code"] == "malformed_json"


def test_old_chat_jsonl_flag_removed_in_favor_of_chat_gpt(tmp_path: Path) -> None:
    proc = subprocess.run(
        [sys.executable, "-X", "utf8", "main.py", "--root", str(tmp_path), "--chat-jsonl"],
        cwd=ROOT,
        input="",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        env=_env(),
        timeout=30,
        check=False,
    )
    assert proc.returncode == 2
    assert "--chat-gpt" in proc.stderr


def test_no_private_runtime_db_staged() -> None:
    proc = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        check=True,
    )
    forbidden = ("memory/sqlite/", "workspace_runtime/", ".pytest_cache/", ".sqlite3")
    assert not any(part in proc.stdout.replace("\\", "/") for part in forbidden)
