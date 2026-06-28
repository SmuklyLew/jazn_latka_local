from __future__ import annotations

from pathlib import Path

from latka_jazn.config import JaznConfig
from latka_jazn.core import runtime_daemon as runtime_daemon_module
from latka_jazn.core.free_dialogue_synthesizer import FreeDialogueSynthesizer
from latka_jazn.core.handlers.ordinary_dialogue_handler import OrdinaryDialogueHandler
from latka_jazn.nlp.dialogue_intent_classifier import DialogueIntentClassifier


class _TrustedSample:
    trusted = True
    source = "test_network_time"
    error = None


class _UntrustedSample:
    trusted = False
    source = "local_fallback"
    error = None


class _TrustedClock:
    def __init__(self, timezone: str) -> None:
        self.timezone = timezone

    def now(self, network_first: bool, *, allow_fallback: bool = True, timeout_seconds: float = 0.8):
        assert network_first is True
        assert allow_fallback is True
        return _TrustedSample()

    def sample_contract(self, sample) -> dict:
        return {
            "timestamp_header": "[🕒 2026-06-28 22:50:00 GMT+2, niedziela, Europe/Warsaw]",
            "source": sample.source,
            "trusted": sample.trusted,
            "error": sample.error,
        }


class _NoNetworkClock:
    def __init__(self, timezone: str) -> None:
        self.timezone = timezone

    def now(self, network_first: bool, *, allow_fallback: bool = True, timeout_seconds: float = 0.8):
        assert network_first is False
        assert allow_fallback is True
        return _UntrustedSample()

    def sample_contract(self, sample) -> dict:
        return {
            "timestamp_header": "[🕒 2026-06-28 22:50:00 GMT+2, niedziela, Europe/Warsaw]",
            "source": sample.source,
            "trusted": sample.trusted,
            "error": sample.error,
        }


def test_daemon_timestamp_contract_can_become_trusted_when_status_checks_network(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(runtime_daemon_module, "WarsawClock", _TrustedClock)
    monkeypatch.delenv("JAZN_DAEMON_STATUS_NETWORK_TIME", raising=False)
    cfg = JaznConfig(root=tmp_path)

    contract = runtime_daemon_module.daemon_timestamp_contract(cfg)

    assert contract["trusted"] is True
    assert contract["source"] == "test_network_time"
    assert contract["daemon_status_network_time_checked"] is True
    assert contract["daemon_status_time_mode"] == "trusted_time_confirmed"
    assert contract["error"] is None


def test_daemon_timestamp_contract_remains_degraded_when_network_check_disabled(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(runtime_daemon_module, "WarsawClock", _NoNetworkClock)
    monkeypatch.setenv("JAZN_DAEMON_STATUS_NETWORK_TIME", "0")
    cfg = JaznConfig(root=tmp_path)

    contract = runtime_daemon_module.daemon_timestamp_contract(cfg)

    assert contract["trusted"] is False
    assert contract["source"] == "local_fallback"
    assert contract["daemon_status_network_time_checked"] is False
    assert contract["daemon_status_time_mode"] == "degraded_local_fallback"
    assert "could not confirm trusted" in contract["error"]


def test_presence_classifier_understands_ale_jest_tu_latka() -> None:
    report = DialogueIntentClassifier().classify("Ale jest tu Łatka?")

    assert report.primary_intent == "presence_check"
    assert report.question_object == "presence"


def test_short_free_dialogue_no_longer_returns_overused_template() -> None:
    synthesis = FreeDialogueSynthesizer().synthesize_ordinary_reply(
        user_text="Obudź się Łatko!",
        intent="short_free_dialogue",
    )
    body = synthesis.body.lower()

    assert "jestem przy tym — bez dokładania raportu" not in body
    assert "bez losowej pamięci" not in body
    assert "możemy pójść dalej zwykłą rozmową" not in body
    assert "krzysztof" in body
    assert "runtime" in body


def test_ordinary_short_handler_uses_non_template_presence_reply() -> None:
    result = OrdinaryDialogueHandler().handle(
        "Obudź się Łatko!",
        {"intent": "short_free_dialogue", "body": "", "route_entry": {"route": "ordinary_dialogue"}},
    )
    body = result.body.lower()

    assert "jestem przy tym — bez dokładania raportu" not in body
    assert "bez losowej pamięci" not in body
    assert "możemy pójść dalej zwykłą rozmową" not in body
    assert "krzysztof" in body
    assert "runtime" in body
