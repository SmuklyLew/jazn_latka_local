from __future__ import annotations

from pathlib import Path

from latka_jazn.config import JaznConfig
from latka_jazn.core.engine import JaznEngine
from latka_jazn.core.handlers.ordinary_dialogue_handler import OrdinaryDialogueHandler


SMOKE_TEXT = "Cześć, Łatko. Sprawdzam zwykłą rozmowę po v14.8.4.004."
GENERIC_CORRECTION_BODY = (
    "Przyjmuję tę korektę. Nie będę robiła z niej długiego opisu problemu — "
    "ważniejsze jest, żebym od razu zmieniła zachowanie i odpowiedziała jak rozmówczyni, "
    "nie jak raport diagnostyczny."
)
OVERUSED_REPAIR_BODY = "Jestem przy tym — bez dokładania raportu i bez losowej pamięci. Możemy pójść dalej zwykłą rozmową."


def assert_no_overused_repair(text: str) -> None:
    low = (text or "").lower()
    assert "jestem przy tym — bez dokładania raportu" not in low
    assert "bez losowej pamięci" not in low
    assert "możemy pójść dalej zwykłą rozmową" not in low


def test_handler_replaces_generic_correction_passthrough_for_version_smoke():
    result = OrdinaryDialogueHandler().handle(
        SMOKE_TEXT,
        {"intent": "ordinary_conversation", "body": GENERIC_CORRECTION_BODY, "route_entry": {"route": "ordinary_dialogue"}},
    )
    assert result.body != GENERIC_CORRECTION_BODY
    assert_no_overused_repair(result.body)
    assert "zwykła rozmowa działa" in result.body.lower()


def test_engine_version_smoke_does_not_return_overused_repair_fallback():
    root = Path(__file__).resolve().parents[1]
    cfg = JaznConfig(root=root, network_time_first=False, memory_db_name="workspace_runtime/test_v1484_ordinary_dialogue_version_smoke.sqlite3")
    engine = JaznEngine(cfg)
    try:
        envelope = engine.process_turn(SMOKE_TEXT, client_context={"client": "pytest", "lifecycle": "one_shot"}).to_dict()
        final_text = envelope["final_visible_text"] or ""
        contract = envelope["final_response_contract"]
        integrity = envelope.get("final_visible_integrity")
        if integrity is not None:
            assert integrity["valid"] is True
        assert contract["detected_user_intent"] == "ordinary_conversation"
        assert contract["runtime_route"] == "ordinary_dialogue"
        assert contract["response_generation_mode"] != "runtime_repair"
        assert_no_overused_repair(final_text)
    finally:
        engine.shutdown()
