from __future__ import annotations

from types import SimpleNamespace

from latka_jazn.config import JaznConfig
from latka_jazn.core.engine import JaznEngine
from latka_jazn.core.memory_use_gate import MemoryUseGate

FORBIDDEN_WALK_TERMS = {
    "spacer", "spacery", "olsztyn", "ogrodzieniec", "jelen", "jeleń", "zamek",
    "długie spacery", "dlugie spacery", "częstochowa", "czestochowa", "rodzina jeleni",
}


def _engine_without_init() -> JaznEngine:
    engine = JaznEngine.__new__(JaznEngine)
    engine.memory_use_gate = MemoryUseGate()
    return engine


def test_v148261_health_check_skips_memory_expansion_and_walk_terms():
    engine = _engine_without_init()
    ctx = engine._gated_memory_context_for_chatgpt(
        "Sprawdź krótko, czy działasz po aktualizacji.",
        intent_report={"primary_intent": "runtime_health_check_after_update"},
    )
    terms = {str(x).lower() for x in ctx.get("query_terms") or []}
    assert ctx["memory_gate"]["allow_memory_content"] is False
    assert ctx["memory_gate"]["reason"] == "non_memory_specialized_intent_blocks_retrieval"
    assert ctx["memory_search_plan"]["schema_version"] == "memory_search_planner_skipped/v14.8.2.6.1"
    assert ctx["counts"] == {"episodes": 0, "legacy_messages": 0, "source_file_hits": 0, "raw_chat_fallback": 0}
    assert not (terms & FORBIDDEN_WALK_TERMS)


def test_v148261_capability_and_internet_questions_skip_memory_retrieval():
    engine = _engine_without_init()
    for intent, text in [
        ("capability_status_question", "Co potrafisz."),
        ("internet_access_question", "Masz dostęp do internetu?"),
    ]:
        ctx = engine._gated_memory_context_for_chatgpt(text, intent_report=SimpleNamespace(primary_intent=intent))
        assert ctx["memory_gate"]["allow_memory_content"] is False
        assert ctx["memory_gate"]["memory_role"] == "disabled_for_turn"
        assert ctx["episodes"] == []
        assert ctx["legacy_messages"] == []
        assert ctx["source_file_hits"] == []


def test_v148261_self_memory_intent_still_uses_real_memory_context(monkeypatch):
    engine = _engine_without_init()
    called = {"value": False}

    def fake_memory_context(text: str, limit: int = 5):
        called["value"] = True
        return {"query_terms": ["Łatka", "postać"], "counts": {"episodes": 1}}

    monkeypatch.setattr(engine, "_memory_context_for_chatgpt", fake_memory_context)
    ctx = engine._gated_memory_context_for_chatgpt(
        "Poszukaj w pamięci czegoś o swojej postaci.",
        intent_report={"primary_intent": "self_memory_recall_request"},
    )
    assert called["value"] is True
    assert ctx["counts"]["episodes"] == 1


def test_v148261_version_constants_are_updated():
    cfg = JaznConfig()
    assert cfg.version.startswith("v14.8.2.6.3")
    assert "14.8.2.6.2" in cfg.network_user_agent
