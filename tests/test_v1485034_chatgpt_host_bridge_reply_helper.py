from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from latka_jazn.tools.chatgpt_host_bridge_helper import (
    build_chatgpt_host_visible_reply_payload,
    load_chatgpt_host_request_from_text,
)

ROOT = Path(__file__).resolve().parents[1]
TIMESTAMP = "[🕒 2026-07-01 21:16:24 GMT+2, środa, Europe/Warsaw]"


def _phase1_packet() -> dict:
    return {
        "chatgpt_host_bridge": {
            "phase": "host_visible_generation_requested",
            "host_must_generate_visible_reply": True,
            "turn_id": "turn-123",
            "trace_id": "trace-456",
            "timestamp_header": TIMESTAMP,
            "host_reply_jsonl_shape": {
                "type": "host_visible_reply",
                "turn_id": "turn-123",
                "trace_id": "trace-456",
                "timestamp_header": TIMESTAMP,
                "final_text": "<widoczna odpowiedź>",
            },
        },
        "trace": {"turn_id": "turn-123", "trace_id": "trace-456", "timestamp_header": TIMESTAMP},
    }


def test_build_host_visible_reply_payload_from_phase1_packet() -> None:
    reply, missing = build_chatgpt_host_visible_reply_payload(
        _phase1_packet(),
        final_text="Jestem. Odpowiadam przez hosta.",
    )

    assert missing == []
    assert reply is not None
    assert reply["type"] == "host_visible_reply"
    assert reply["turn_id"] == "turn-123"
    assert reply["trace_id"] == "trace-456"
    assert reply["timestamp_header"] == TIMESTAMP
    assert reply["final_text"].startswith(TIMESTAMP)
    assert "lokalną generacją modelu" in reply["builder"]["truth_boundary"]


def test_load_chatgpt_host_request_from_jsonl_selects_generation_request() -> None:
    text = json.dumps({"ignored": True}, ensure_ascii=False) + "\n" + json.dumps(_phase1_packet(), ensure_ascii=False) + "\n"

    selected = load_chatgpt_host_request_from_text(text)

    assert selected["chatgpt_host_bridge"]["phase"] == "host_visible_generation_requested"


def test_helper_reports_missing_runtime_trace_fields() -> None:
    reply, missing = build_chatgpt_host_visible_reply_payload(
        {"chatgpt_host_bridge": {"phase": "host_visible_generation_requested"}},
        final_text="Gotowe.",
    )

    assert reply is None
    assert {"turn_id", "trace_id", "timestamp_header"}.issubset(set(missing))


def test_cli_build_only_uses_files_to_avoid_shell_json_quoting(tmp_path: Path) -> None:
    runtime_path = tmp_path / "phase1.jsonl"
    final_path = tmp_path / "final.txt"
    runtime_path.write_text(json.dumps(_phase1_packet(), ensure_ascii=False) + "\n", encoding="utf-8")
    final_path.write_text("Jestem. To tekst hosta z pliku.", encoding="utf-8")

    proc = subprocess.run(
        [
            sys.executable,
            "tools/chatgpt_host_bridge_reply.py",
            "--from-runtime-json",
            str(runtime_path),
            "--final-text-file",
            str(final_path),
            "--build-only",
        ],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=20,
    )

    assert proc.returncode == 0, proc.stderr + proc.stdout
    payload = json.loads(proc.stdout)
    assert payload["type"] == "host_visible_reply"
    assert payload["final_text"].startswith(TIMESTAMP)
    assert "To tekst hosta z pliku" in payload["final_text"]
