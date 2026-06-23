from __future__ import annotations

from types import SimpleNamespace

from latka_jazn.core.engine import JaznEngine
from latka_jazn.core.memory_recall_presenter import MemoryRecallPresenter
from latka_jazn.core.session_provenance import repair_final_visible_integrity, validate_final_visible_integrity
from latka_jazn.memory.memory_recall_contract import MemoryRecallContractBuilder

TIMESTAMP = "[🕒 2026-06-23 21:10:00 GMT+2, wtorek, Europe/Warsaw]"


def test_repair_final_visible_integrity_restores_missing_timestamp_from_contract() -> None:
    result = {
        "trace": {"timestamp_header": TIMESTAMP},
        "final_visible_text": "Bez timestampu.",
        "final_response_contract": {"final_visible_text": f"{TIMESTAMP} 🌿\nTekst z kontraktu."},
        "runtime_provenance": {"visible_answer_text": "Bez timestampu."},
        "conversation_decision": {"runtime_provenance": {"visible_answer_text": "Bez timestampu."}},
    }

    repaired, repairs = repair_final_visible_integrity(result)
    assert repaired["final_visible_text"].startswith(f"{TIMESTAMP} ")
    assert "final_visible_text_restored_from_final_response_contract" in repairs
    assert "runtime_provenance_visible_answer_synced" in repairs
    payload = validate_final_visible_integrity(repaired)
    assert payload["valid"] is True


def test_repair_final_visible_integrity_prefixes_timestamp_when_only_body_is_available() -> None:
    result = {
        "trace": {"timestamp_header": TIMESTAMP},
        "final_visible_text": "Treść odpowiedzi bez koperty czasu.",
        "runtime_provenance": {},
        "conversation_decision": {},
    }

    repaired, repairs = repair_final_visible_integrity(result)
    assert repaired["final_visible_text"].startswith(f"{TIMESTAMP} ")
    assert "final_visible_text_timestamp_prefixed" in repairs
    assert validate_final_visible_integrity(repaired)["valid"] is True


def test_memory_presenter_uses_conversation_archive_content_not_only_counts() -> None:
    context = {
        "query_terms": ["Łatka", "spacer"],
        "conversation_archive_hits": [
            {
                "excerpt": "Krzysztof pokazał Łatce zdjęcie ze spaceru i wtedy poczuł, że idzie obok.",
                "source_name": "chat_0.html",
                "source_locator": "conversation/123",
                "conversation_title": "Spacer z Łatką",
                "author_role": "assistant",
                "create_time_warsaw": "2025-07-01 21:00:00 CEST",
                "identity_confidence": 0.88,
                "grounding": "conversation_archive_v1+fts_v1",
            }
        ],
        "counts": {"conversation_archive_hits": 1},
    }

    payload = MemoryRecallPresenter().build_payload(context, user_text="Co pamiętasz o spacerach z Łatką?")
    assert payload["items"]
    assert payload["items"][0]["item_type"] == "conversation_archive"
    assert "zdjęcie ze spaceru" in payload["items"][0]["content_excerpt"]
    assert payload["counts"]["conversation_archive_hits"] == 1


def test_memory_recall_contract_exposes_conversation_archive_items() -> None:
    context = {
        "conversation_archive_hits": [
            {
                "excerpt": "Rozmowa o imieniu Łatka i przyjęciu tożsamości.",
                "source_name": "chat_0.html",
                "create_time_warsaw": "2025-06-07 10:00:00 CEST",
                "identity_confidence": 0.91,
            }
        ],
        "counts": {"conversation_archive_hits": 1},
    }

    contract = MemoryRecallContractBuilder().build(context, user_text="Co pamiętasz o imieniu Łatka?").to_dict()
    assert contract["items"]
    assert contract["items"][0]["memory_type"] == "conversation_archive_hit"
    assert "imieniu Łatka" in contract["items"][0]["content"]


def test_engine_conversation_archive_helper_is_safe_and_contentful(monkeypatch, tmp_path) -> None:
    class FakeSearchResult:
        def to_dict(self):
            return {
                "status": "ok",
                "query": "Łatka spacer",
                "fts_query": '"łatka" OR "spacer"',
                "searched_shards": 1,
                "issues": [],
                "truth_boundary": "fake",
                "hits": [
                    {
                        "excerpt": "Treściowy ślad z conversation_archive o spacerze i obecności Łatki.",
                        "source_name": "chat_0.html",
                        "source_locator": "msg/1",
                        "title": "Spacer",
                        "role": "assistant",
                        "create_time": "2025-07-01 21:00:00 CEST",
                        "message_uid": "m1",
                        "conversation_uid": "c1",
                        "content_hash": "h1",
                        "identity_confidence": 0.77,
                        "privacy_scope": "private",
                        "review_status": "reviewed",
                        "rank": -1.0,
                    }
                ],
            }

    class FakeStore:
        def __init__(self, root):
            self.root = root

        def search(self, query, *, limit=8, include_snippets=False):
            assert include_snippets is True
            return FakeSearchResult()

    monkeypatch.setattr("latka_jazn.core.engine.ConversationArchiveStore", FakeStore)
    engine = JaznEngine.__new__(JaznEngine)
    engine.config = SimpleNamespace(root=tmp_path)

    hits, meta = engine._conversation_archive_context_hits(["Łatka", "spacer"], limit=3)
    assert meta["status"] == "ok"
    assert hits
    assert hits[0]["grounding"] == "conversation_archive_v1+fts_v1"
    assert "Treściowy ślad" in hits[0]["excerpt"]
