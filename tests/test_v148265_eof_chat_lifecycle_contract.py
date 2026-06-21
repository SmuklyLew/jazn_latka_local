from __future__ import annotations

import io
import json

from latka_jazn.core.runtime_chat import LatkaRuntimeShell, run_persistent_chat


class DummyEngine:
    def process_turn(self, *args, **kwargs):  # pragma: no cover - EOF test must not process turns
        raise AssertionError("EOF-only chat loop must not process a user turn")

    def build_cognitive_frame(self, *args, **kwargs):  # pragma: no cover
        raise AssertionError("EOF-only chat loop must not build a frame")


def _last_lifecycle_payload(output: str) -> dict:
    marker = "[runtime_lifecycle_end] "
    lines = [line for line in output.splitlines() if line.startswith(marker)]
    assert lines, output
    return json.loads(lines[-1][len(marker):])


def test_chat_loop_reports_stdin_eof_without_claiming_background_process():
    out = io.StringIO()
    shell = LatkaRuntimeShell(
        DummyEngine(),
        stdin=io.StringIO(""),
        stdout=out,
        session_id="pytest-eof",
    )

    shell.cmdloop()

    payload = _last_lifecycle_payload(out.getvalue())
    assert payload["exit_reason"] == "stdin_eof"
    assert payload["stdin_is_tty"] is False
    assert payload["process_persistence"] == "ephemeral_stdin_pipe"
    assert payload["background_process_claim_allowed"] is False
    assert payload["session_id"] == "pytest-eof"
    assert "--chat-jsonl" in payload["recommended_chatgpt_mode"]


def test_chat_loop_reports_user_exit_command():
    out = io.StringIO()
    shell = LatkaRuntimeShell(
        DummyEngine(),
        stdin=io.StringIO("/exit\n"),
        stdout=out,
        session_id="pytest-exit",
    )

    shell.cmdloop()

    payload = _last_lifecycle_payload(out.getvalue())
    assert payload["exit_reason"] == "user_exit_command"
    assert payload["background_process_claim_allowed"] is False
    assert payload["session_id"] == "pytest-exit"


def test_run_persistent_chat_returns_lifecycle_after_eof():
    out = io.StringIO()
    lifecycle = run_persistent_chat(
        DummyEngine(),
        stdin=io.StringIO(""),
        stdout=out,
        session_id="pytest-runner",
        no_carryover=True,
    )

    assert lifecycle.exit_reason == "stdin_eof"
    assert lifecycle.session_id == "pytest-runner"
    assert lifecycle.no_carryover is True
    assert lifecycle.background_process_claim_allowed is False
    assert _last_lifecycle_payload(out.getvalue())["exit_reason"] == "stdin_eof"
