from __future__ import annotations

import re
import shutil
from pathlib import Path

from latka_jazn.adapters.chatgpt_adapter import ChatGPTAdapter
from latka_jazn.config import JaznConfig
from latka_jazn.core.engine import JaznEngine

VERSION = "v14.8.2.4-logic-routing-memory-grounding-repair"
TIMESTAMP_RE = re.compile(r"^\[🕒 \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} GMT[+]\d, [^,]+, Europe/Warsaw\]")


def _copy_canon(root: Path) -> None:
    source_canon = Path(__file__).resolve().parents[1] / "memory" / "raw" / "LATKA_IDENTITY_CANON.json"
    target_canon = root / "memory" / "raw" / "LATKA_IDENTITY_CANON.json"
    target_canon.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_canon, target_canon)


def test_direct_runtime_reply_starts_with_timestamp(tmp_path: Path) -> None:
    _copy_canon(tmp_path)
    cfg = JaznConfig(root=tmp_path, memory_db_name="workspace_runtime/test.sqlite3", network_time_first=False)
    engine = JaznEngine(cfg)
    try:
        reply = engine.handle_user_message("Dzień dobry Łatko. Jak minęła noc?", client_context={"client": "unit_test"})
    finally:
        engine.shutdown()

    assert TIMESTAMP_RE.match(reply)


def test_cognitive_frame_exports_visible_timestamp_contract(tmp_path: Path) -> None:
    _copy_canon(tmp_path)
    cfg = JaznConfig(root=tmp_path, memory_db_name="workspace_runtime/test.sqlite3", network_time_first=False)
    engine = JaznEngine(cfg)
    try:
        packet = engine.build_cognitive_frame("Pytam przez ChatGPT; pilnuj timestampu odpowiedzi.", client_context={"client": "unit_test"})
    finally:
        engine.shutdown()

    assert packet["runtime_version"] == VERSION
    assert packet["response_format"]["timestamp_required"] is True
    assert packet["response_format"]["timestamp_prefix"] == packet["timestamp"]
    assert packet["response_format"]["current_timestamp"] == packet["timestamp"]
    assert TIMESTAMP_RE.match(packet["response_format"]["timestamp_prefix"])
    assert any("Nie gub timestampu" in item for item in packet["reply_guidance"])


def test_chatgpt_contract_declares_timestamp_rule() -> None:
    contract = ChatGPTAdapter(JaznConfig(network_time_first=False)).contract().to_dict()
    assert "timestamp_rule" in contract
    assert "Każda zwykła odpowiedź" in contract["timestamp_rule"]
    assert "current_timestamp" in contract["timestamp_rule"]
