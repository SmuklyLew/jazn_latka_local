from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _run_chat_gpt_healthcheck(tmp_path: Path) -> dict:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["JAZN_TRUSTED_TIME_ISO"] = datetime.now(timezone.utc).isoformat()
    env["JAZN_TRUSTED_TIME_SOURCE"] = "chatgpt_web_time_tool"
    env["JAZN_TRUSTED_TIME_MAX_AGE_SECONDS"] = "999999999"
    proc = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            "main.py",
            "--root",
            str(tmp_path),
            "--chat-gpt",
            "--no-carryover",
            "--session-id",
            "body-consistency-healthcheck",
        ],
        cwd=ROOT,
        input="Działasz?\n",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        env=env,
        timeout=40,
        check=True,
    )
    assert proc.stderr == ""
    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    assert len(lines) == 1
    return json.loads(lines[0])


def test_chat_gpt_healthcheck_conversation_decision_body_matches_final_handler_body(tmp_path: Path) -> None:
    payload = _run_chat_gpt_healthcheck(tmp_path)

    decision = payload["conversation_decision"]
    handler_result = decision["handler_result"]
    final_contract = payload["final_response_contract"]

    assert decision["detected_user_intent"] == "runtime_health_check"
    assert decision["handler_name"] == "CapabilityStatusHandler"
    assert decision["preserve_handler_body"] is True

    assert decision["body"] == handler_result["body"]
    assert decision["body"] == payload["exact_runtime_text"]
    assert decision["body"] == final_contract["body"]
    assert decision["body_sync"]["status"] == "synchronized_to_preserved_handler_body"
    assert decision["body_sync"]["conversation_body_matches_final_body"] is True
    assert decision["body_sync"]["handler_body_matches_final_body"] is True


def test_chat_gpt_healthcheck_conversation_decision_body_does_not_keep_stale_casual_draft(tmp_path: Path) -> None:
    payload = _run_chat_gpt_healthcheck(tmp_path)

    decision_body = payload["conversation_decision"]["body"]
    exact_runtime_text = payload["exact_runtime_text"]
    final_visible_text = payload["final_visible_text"]

    assert "Krótki raport health-check" in decision_body
    assert "Krótki raport health-check" in exact_runtime_text
    assert "Też się cieszę" not in decision_body
    assert "Najważniejsze, żeby ta poprawa była odczuwalna" not in decision_body
    assert "Też się cieszę" not in exact_runtime_text
    assert "Najważniejsze, żeby ta poprawa była odczuwalna" not in exact_runtime_text
    assert "Też się cieszę" not in final_visible_text
    assert "Najważniejsze, żeby ta poprawa była odczuwalna" not in final_visible_text
