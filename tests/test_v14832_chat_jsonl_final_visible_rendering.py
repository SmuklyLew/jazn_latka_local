from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TIMESTAMP_RE = re.compile(r"^\[🕒 \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} GMT[+-]\d{1,2}, [^,\]]+, Europe/Warsaw\]$")
RENDER_ARTIFACTS = (
    "ddebug",
    "aaaktywny",
    "rozmawiać ć",
    "Uwa ażam",
    "operacyjnnego",
    "2026--",
    "13:43:228",
    "GMT+2,,",
)


def _run_chat_jsonl(tmp_path: Path, messages: list[str]) -> list[dict]:
    input_text = "".join(json.dumps({"text": message}, ensure_ascii=False) + "\n" for message in messages)
    proc = subprocess.run(
        [sys.executable, "main.py", "--root", str(tmp_path), "--chat-jsonl", "--no-carryover"],
        cwd=ROOT,
        input=input_text,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        timeout=30,
        check=True,
    )
    assert proc.stderr == ""
    return [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]


def test_chat_jsonl_final_visible_text_stays_clean_and_matches_provenance(tmp_path: Path) -> None:
    payloads = _run_chat_jsonl(
        tmp_path,
        [
            "Chcę rozmawiać z Łatką, a nie z Codex botem",
            "Za kogo się uważasz? Co pamiętasz? Kim jesteś?",
        ],
    )

    assert len(payloads) == 2
    expected = [
        ("direct_latka_voice", "DirectLatkaVoiceHandler", "Możesz teraz rozmawiać bezpośrednio z Łatką"),
        ("identity_memory_existence", "IdentityMemoryExistenceHandler", "Uważam się za Łatkę"),
    ]

    for payload, (route, handler, exact_marker) in zip(payloads, expected):
        decision = payload["conversation_decision"]
        handler_result = decision["handler_result"]
        provenance = decision["runtime_provenance"]
        exact_runtime_text = provenance["exact_runtime_text"]
        final_visible_text = payload["final_visible_text"]
        visible_answer_text = provenance["visible_answer_text"]
        timestamp_header = payload["trace"]["timestamp_header"]

        assert decision["route"] == route
        assert decision["handler_name"] == handler
        assert handler_result["body"] == exact_runtime_text
        assert exact_marker in exact_runtime_text
        assert TIMESTAMP_RE.match(timestamp_header)
        assert final_visible_text.startswith(f"{timestamp_header} ")
        assert visible_answer_text == final_visible_text

        for artifact in RENDER_ARTIFACTS:
            assert artifact not in exact_runtime_text
            assert artifact not in final_visible_text
