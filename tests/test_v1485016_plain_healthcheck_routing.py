from __future__ import annotations

from types import SimpleNamespace

from latka_jazn.core.handlers.capability_status_handler import CapabilityStatusHandler
from latka_jazn.nlp.dialogue_intent_classifier import DialogueIntentClassifier
from latka_jazn.core.route_registry import RouteRegistry


class _FakeConfig:
    version = "v14.8.5.016.2"
    root = "/tmp/fake-jazn"
    memory_db_path = "memory/sqlite/runtime_write_v1/runtime_memory.sqlite3"


def test_plain_dzialasz_routes_to_runtime_health_check_not_ordinary() -> None:
    report = DialogueIntentClassifier().classify("Działasz?")
    assert report.primary_intent == "runtime_health_check"
    assert report.diagnostic_request is True

    entry = RouteRegistry().resolve(report.primary_intent)
    assert entry.route == "runtime_health_check"
    assert entry.handler_name == "CapabilityStatusHandler"


def test_capability_status_handler_answers_plain_healthcheck_directly(monkeypatch) -> None:
    def fake_startup_status(cfg):
        return SimpleNamespace(to_dict=lambda: {
            "runtime_version": cfg.version,
            "active_root": str(cfg.root),
            "start_file": "main.py",
            "active_database": "memory/sqlite/conversation_archive_v1/conversation_archive_manifest.sqlite3",
            "active_runtime_write_database": "memory/sqlite/runtime_write_v1/runtime_memory.sqlite3",
            "active_cache_status": {
                "version": cfg.version,
                "active_root": str(cfg.root),
                "should_reuse_existing_extraction": True,
                "cache_miss_reasons": [],
            },
            "raw_memory_status": {"status": "indeks_pusty"},
            "conversation_archive_status": {"status": "ready", "ready_for_search": True},
        })

    import latka_jazn.core.handlers.capability_status_handler as module

    monkeypatch.setattr(module, "build_startup_status", fake_startup_status)
    result = CapabilityStatusHandler().handle("Działasz?", {"intent": "runtime_health_check", "config": _FakeConfig()})
    body = result.body.lower()
    assert result.route == "runtime_health_check"
    assert "runtime_version=v14.8.5.016.2" in result.body
    assert "active_database" in body
    assert "cache_miss_reasons" in body
    assert "granica prawdy" in body
