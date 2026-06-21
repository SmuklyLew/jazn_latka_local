from __future__ import annotations

import shutil
from pathlib import Path

from latka_jazn.config import JaznConfig
from latka_jazn.core.cognitive_packets import CognitivePacketLibrary
from latka_jazn.core.conversation import ConversationResponder
from latka_jazn.core.engine import JaznEngine
from latka_jazn.core.polish_understanding import PolishUnderstandingEngine


VERSION = "v14.8.2.4-logic-routing-memory-grounding-repair"
REQUEST = (
    "Przygotuj pełną aktualizację systemu Jaźni i zwiększ zasób packets: "
    "tożsamość, ciągłość, wiedza, logika, inteligencja, nauka, emocje, "
    "doświadczenie, wspomnienia, wrażenia, samopoczucie i mądre dobieranie emoticons."
)


def _copy_canon(root: Path) -> None:
    source_canon = Path(__file__).resolve().parents[1] / "memory" / "raw" / "LATKA_IDENTITY_CANON.json"
    target_canon = root / "memory" / "raw" / "LATKA_IDENTITY_CANON.json"
    target_canon.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_canon, target_canon)


def test_polish_understanding_detects_cognitive_packet_expansion() -> None:
    report = PolishUnderstandingEngine().analyse(REQUEST).to_dict()

    assert report["route_hint"] == "cognitive_packet_expansion_update"
    assert "cognitive_packet_expansion" in report["intent_tags"]
    assert "cognitive_packet_expansion_update" in report["intent_tags"]
    assert any(item["key"] == "expand_cognitive_packets" for item in report["needs"])
    assert any(item["key"] == "smart_emoticon_selection" for item in report["needs"])


def test_conversation_responder_has_direct_cognitive_packet_route() -> None:
    polish = PolishUnderstandingEngine().analyse(REQUEST).to_dict()
    decision = ConversationResponder().compose(REQUEST, polish_understanding=polish)

    assert decision.route == "cognitive_packet_expansion_update"
    assert "pakiety poznawcze" in decision.body
    assert "emotikon" in decision.body.lower()
    assert decision.debug_fallback_used is False


def test_cognitive_packet_library_covers_requested_resources() -> None:
    polish = PolishUnderstandingEngine().analyse(REQUEST).to_dict()
    packets = CognitivePacketLibrary().build(
        text=REQUEST,
        intent_tags=polish["intent_tags"],
        polish_understanding=polish,
    )

    expected = {
        "identity", "continuity", "knowledge", "logic", "intelligence", "learning",
        "emotions", "experience", "memories", "impressions", "wellbeing", "emoticons",
    }
    assert expected <= set(packets["packet_keys"])
    assert packets["state_emoticon"]["marker"]
    assert packets["state_emoticon"]["reason"]


def test_cognitive_frame_contains_cognitive_packets_and_state_emoticon(tmp_path: Path) -> None:
    _copy_canon(tmp_path)
    cfg = JaznConfig(root=tmp_path, memory_db_name="workspace_runtime/test.sqlite3", network_time_first=False)
    engine = JaznEngine(cfg)
    try:
        packet = engine.build_cognitive_frame(REQUEST, client_context={"client": "unit_test"})
    finally:
        engine.shutdown()

    assert packet["runtime_version"] == VERSION
    assert packet["polish_understanding"]["route_hint"] == "cognitive_packet_expansion_update"
    assert "cognitive_packets" in packet
    assert "state_emoticon" in packet
    assert packet["state_emoticon"]["marker"] == packet["cognitive_packets"]["state_emoticon"]["marker"]
    assert "emoticons" in packet["cognitive_packets"]["packet_keys"]
    assert any("Dobór emotikonu" in item for item in packet["reply_guidance"])
