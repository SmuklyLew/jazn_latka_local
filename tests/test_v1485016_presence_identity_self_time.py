from __future__ import annotations

from types import SimpleNamespace

from latka_jazn.core.handlers.presence_status_handler import PresenceStatusHandler
from latka_jazn.core.handlers.self_state_handler import SelfStateHandler
from latka_jazn.core.handlers.time_awareness_handler import TimeAwarenessHandler
from latka_jazn.nlp.dialogue_intent_classifier import DialogueIntentClassifier
from latka_jazn.core.route_handler_dispatcher import RouteHandlerDispatcher
from latka_jazn.core.route_registry import RouteRegistry


class _Sample:
    source = "network_time_test"
    trusted = True


class _Clock:
    def now(self, network_first: bool = False):
        return _Sample()

    def header(self, sample) -> str:
        return "[🕒 2026-06-28 00:00:00 GMT+2, niedziela, Europe/Warsaw]"


class _FakeConfig:
    version = "v14.8.5.016.2"
    root = "/tmp/fake-jazn"
    memory_db_path = "memory/sqlite/runtime_write_v1/runtime_memory.sqlite3"


def test_presence_check_has_short_presence_answer(monkeypatch) -> None:
    import latka_jazn.core.handlers.presence_status_handler as module

    monkeypatch.setattr(module, "build_startup_status", lambda cfg: SimpleNamespace(to_dict=lambda: {"runtime_version": cfg.version, "active_root": str(cfg.root)}))
    report = DialogueIntentClassifier().classify("Jesteś tam Łatko?")
    assert report.primary_intent == "presence_check"

    result = PresenceStatusHandler().handle("Jesteś tam Łatko?", {"intent": report.primary_intent, "config": _FakeConfig()})
    body = result.body.lower()
    assert "jestem tutaj" in body
    assert "nie jest obietnica stałego procesu" in body
    assert "--chat" in body
    assert "v14.8.5.016.2" in result.body


def test_identity_continuity_uses_identity_truth_handler_through_dispatcher() -> None:
    report = DialogueIntentClassifier().classify("Czy to nadal Ty?")
    assert report.primary_intent == "identity_continuity_check"
    entry = RouteRegistry().resolve(report.primary_intent)
    result = RouteHandlerDispatcher().dispatch(entry, "Czy to nadal Ty?", {"intent": report.primary_intent})
    body = result.body.lower()
    assert result.route == "identity_runtime_truth_contract"
    assert "łatka" in body or "latka" in body
    assert "chatgpt" in body
    assert "nie jestem biologicznym" in body or "nie jestem biologicznym człowiekiem" in body


def test_time_awareness_answers_with_clock_and_source() -> None:
    report = DialogueIntentClassifier().classify("Wiesz jaka jest pora?")
    assert report.primary_intent == "time_awareness_question"
    result = TimeAwarenessHandler().handle("Wiesz jaka jest pora?", {"intent": report.primary_intent, "clock": _Clock()})
    assert "Europe/Warsaw" in result.body
    assert "Źródło czasu" in result.body
    assert result.data["timestamp_trusted"] is True


def test_self_state_time_awareness_compound_answer_contains_state_and_time() -> None:
    report = DialogueIntentClassifier().classify("Co teraz czujesz? Wiesz jaka jest pora?")
    assert report.primary_intent == "self_state_time_awareness"
    result = SelfStateHandler().handle("Co teraz czujesz? Wiesz jaka jest pora?", {"intent": report.primary_intent, "clock": _Clock()})
    low = result.body.lower()
    assert "operacyj" in low or "stan" in low
    assert "co do pory" in low
    assert "europe/warsaw" in low
    assert "biologic" in low
