from __future__ import annotations

import shutil
from pathlib import Path

from latka_jazn.adapters.chatgpt_adapter import ChatGPTAdapter
from latka_jazn.config import JaznConfig
from latka_jazn.core.engine import JaznEngine
from latka_jazn.memory.runtime_persistence import RuntimeMemoryWriter


def _copy_canon(root: Path) -> None:
    source_canon = Path(__file__).resolve().parents[1] / "memory" / "raw" / "LATKA_IDENTITY_CANON.json"
    target_canon = root / "memory" / "raw" / "LATKA_IDENTITY_CANON.json"
    target_canon.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_canon, target_canon)


def test_chatgpt_contract_contains_anti_paraphrase_rule() -> None:
    contract = ChatGPTAdapter(JaznConfig(network_time_first=False)).contract()
    assert "dialog" in contract.dialogue_rule.lower()
    assert "parafraz" in contract.anti_paraphrase_rule.lower()
    assert "ciągłą parafrazę" in ChatGPTAdapter(JaznConfig(network_time_first=False)).system_contract()


def test_cognitive_frame_contains_dialogue_context_and_guidance(tmp_path: Path) -> None:
    _copy_canon(tmp_path)
    cfg = JaznConfig(root=tmp_path, memory_db_name="workspace_runtime/test.sqlite3", network_time_first=False)
    engine = JaznEngine(cfg)
    try:
        packet = engine.build_cognitive_frame(
            "Ważniejsze jest, żebyś prowadziła dialog/rozmowę, a nie cały czas opisywała to, o czym mówię. To naprawa systemu Jaźni.",
            client_context={"client": "unit_test"},
        )
    finally:
        engine.shutdown()

    assert "dialogue_repair" in packet["intent_tags"]
    assert packet["dialogue_context"]["mode"] == "balanced_dialogue"
    assert packet["dialogue_context"]["repair_requested"] is True
    assert any("Nie odpowiadaj serią parafraz" in item for item in packet["reply_guidance"])
    assert packet["persistence"]["candidate_kind"] == "reguła_proceduralna"


def test_runtime_memory_promotes_dialogue_repair_to_procedural_rule(tmp_path: Path) -> None:
    writer = RuntimeMemoryWriter(tmp_path, version="v14.8.2.4-logic-routing-memory-grounding-repair")
    candidate = writer.build_candidate_from_runtime_turn(
        user_text="To jest kwestia naprawy systemu Jaźni: prowadź dialog, nie opisuj i nie parafrazuj cały czas moich wypowiedzi.",
        importance=0.5,
        importance_reason="test",
        emotional_tags=["correction"],
    )
    assert candidate.kind == "reguła_proceduralna"
    assert "nowy wkład" in (candidate.procedural_action or "")
    assert "ciągłe opisywanie" in (candidate.procedural_reason or "")
