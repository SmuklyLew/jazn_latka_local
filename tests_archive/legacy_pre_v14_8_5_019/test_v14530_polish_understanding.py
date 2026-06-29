from __future__ import annotations

import shutil
from pathlib import Path

from latka_jazn.config import JaznConfig
from latka_jazn.core.engine import JaznEngine
from latka_jazn.core.polish_understanding import PolishUnderstandingEngine


def _copy_canon(root: Path) -> None:
    source_canon = Path(__file__).resolve().parents[1] / "memory" / "raw" / "LATKA_IDENTITY_CANON.json"
    target_canon = root / "memory" / "raw" / "LATKA_IDENTITY_CANON.json"
    target_canon.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_canon, target_canon)


def test_polish_understanding_detects_dictionary_solution_request() -> None:
    text = (
        "Poszukaj rozwiązania które pomoże systemowi Jaźni rozumieć wypowiedzi. "
        "Może z dostępem do polskiego słownika, żeby było mniej ogólnikowo. "
        "Dasz radę zrobić to dobrze i poprawnie?"
    )
    report = PolishUnderstandingEngine().analyse(text).to_dict()

    assert report["route_hint"] == "v14_6_1_nlp_adapter_update"
    assert "language_understanding" in report["intent_tags"]
    assert "polish_dictionary" in report["intent_tags"]
    assert "anti_generic" in report["intent_tags"]
    assert "polish_understanding_update" in report["intent_tags"]
    assert "rozumieć" in report["lemmas"]
    assert "słownik" in report["lemmas"]
    assert any(item["key"] == "less_generic_answers" for item in report["needs"])
    assert report["tools"]["builtin_lexicon"] is True


def test_cognitive_frame_contains_polish_understanding_packet(tmp_path: Path) -> None:
    _copy_canon(tmp_path)
    cfg = JaznConfig(root=tmp_path, memory_db_name="workspace_runtime/test.sqlite3", network_time_first=False)
    engine = JaznEngine(cfg)
    try:
        packet = engine.build_cognitive_frame(
            "Jaźń potrzebuje polskiego słownika i rozumienia wypowiedzi, żeby nie odpowiadać ogólnikowo.",
            client_context={"client": "unit_test"},
        )
    finally:
        engine.shutdown()

    assert packet["runtime_version"] == "v14.8.2.4-logic-routing-memory-grounding-repair"
    assert "polish_understanding" in packet
    assert packet["polish_understanding"]["route_hint"] == "v14_6_1_nlp_adapter_update"
    assert "polish_understanding_update" in packet["intent_tags"]
    assert any("polish_understanding" in item for item in packet["reply_guidance"])


def test_direct_runtime_uses_specific_polish_understanding_route(tmp_path: Path) -> None:
    _copy_canon(tmp_path)
    cfg = JaznConfig(root=tmp_path, memory_db_name="workspace_runtime/test.sqlite3", network_time_first=False)
    engine = JaznEngine(cfg)
    try:
        reply = engine.handle_user_message(
            "Poszukaj rozwiązania dla Jaźni: rozumienie wypowiedzi, polski słownik, mniej ogólnikowo. Dasz radę?",
            client_context={"client": "unit_test"},
        )
    finally:
        engine.shutdown()

    assert "Rozumiem pytanie. Odpowiem" not in reply
    assert "warstwę rozumienia polskiej wypowiedzi" in reply
    assert "słownik domenowy Jaźni" in reply
