from pathlib import Path

from latka_jazn.config import JaznConfig
from latka_jazn.core.engine import JaznEngine
from latka_jazn.core.signal_matching import NeurologicalSignalRouter, marker_present
from latka_jazn.core.polish_understanding import PolishUnderstandingEngine
from latka_jazn.core.affective_granularity import AffectiveGranularityModel

VERSION = "v14.8.2.4-logic-routing-memory-grounding-repair"


def test_marker_present_does_not_match_zle_inside_zlecenie() -> None:
    text = "Za chwilę jadę na kolejne zlecenie, dziś 9 sztuk drzwi."
    assert not marker_present(text, "zle")
    assert not marker_present(text, "źle")
    assert marker_present(text, "zlecenie")


def test_neurological_signal_router_separates_workday_from_correction() -> None:
    route = NeurologicalSignalRouter().analyse("Za chwilę jadę na kolejne zlecenie, dziś 9 sztuk drzwi.")
    assert route.primary == "ordinary_workday_dialogue"
    assert route.daily_life_score > route.correction_score
    assert "daily_life" in route.signals
    assert "correction" not in route.signals


def test_polish_understanding_keeps_zlecenie_out_of_update_request() -> None:
    report = PolishUnderstandingEngine(Path(__file__).resolve().parents[1]).analyse("Za chwilę jadę na kolejne zlecenie, dziś 9 sztuk drzwi.")
    assert "update_request" not in report.intent_tags


def test_affective_granularity_keeps_zlecenie_out_of_error_tension() -> None:
    report = AffectiveGranularityModel().analyse("Za chwilę jadę na kolejne zlecenie, dziś 9 sztuk drzwi.")
    assert "napięcie naprawcze" not in [item["name"] for item in report.to_dict()["blend"]]


def test_runtime_workday_message_is_not_debug_correction() -> None:
    cfg = JaznConfig(version=VERSION, root=Path(__file__).resolve().parents[1], memory_db_name="workspace_runtime/test_v14691_workday.sqlite3", allow_network=False, network_time_first=False)
    engine = JaznEngine(cfg)
    try:
        envelope = engine.process_turn("Za chwilę jadę na kolejne zlecenie, dziś 9 sztuk drzwi.", client_context={"client": "pytest", "lifecycle": "one_shot"})
        data = envelope.to_dict()
        contract = data["final_response_contract"]
        frame = data["cognitive_frame"]
        assert contract["runtime_route"] == "ordinary_workday_dialogue"
        assert contract["fallback_classification"] == "not_fallback"
        assert "korekt" not in contract["body"].lower()
        assert frame["neurological_signal_route"]["primary"] == "ordinary_workday_dialogue"
    finally:
        engine.shutdown()
