from latka_jazn.core.conversation import ConversationResponder
from latka_jazn.core.memory_recall_presenter import MemoryRecallPresenter


def _sample_memory_context():
    return {
        "query_terms": ["nocą", "pamięci"],
        "episodes": [
            {
                "phrase": "nocą",
                "local_time_label": "2026-05-18 22:08:38 CEST",
                "grounding": "runtime_event_ledger",
                "confidence": 0.82,
                "scene": "Krzysztof przywitał Łatkę jeszcze nie późną nocą; runtime rozpoznał nocny, spokojny ton rozmowy.",
                "source": "memory/layered/episodic.jsonl",
            }
        ],
        "legacy_messages": [
            {
                "phrase": "pamięci",
                "conversation_title": "Początek rozmowy z Jaźnią",
                "author_role": "user",
                "create_time_warsaw": "2026-05-18T22:02:00+02:00",
                "text": "Jakie tropy pamięci znalazłaś?",
            }
        ],
        "raw_chat_fallback": [],
        "counts": {"episodes": 1, "legacy_messages": 1, "raw_chat_fallback": 0},
    }


def test_memory_recall_presenter_returns_content_not_only_counts():
    payload = MemoryRecallPresenter().build_payload(_sample_memory_context(), user_text="Jakie tropy pamięci znalazłaś?")
    assert payload["items"]
    first = payload["items"][0]
    assert "content_excerpt" in first
    assert "Krzysztof przywitał Łatkę" in first["content_excerpt"]
    assert first["source"]
    assert first["timestamp"]
    assert first["item_type"] == "episode"
    assert first["relevance_label"] in {"wysoka", "średnia", "słaba"}


def test_conversation_responder_memory_query_uses_recall_content():
    decision = ConversationResponder().compose(
        "Jakie tropy pamięci znalazłaś?",
        memory_counts={"episodes": 1, "legacy_messages": 1, "raw_chat_fallback": 0},
        memory_context=_sample_memory_context(),
    )
    assert decision.route == "memory_recall_content"
    assert "Krzysztof przywitał Łatkę" in decision.body
    assert "Liczniki diagnostyczne" in decision.body
    assert "episodes=1" in decision.body
    assert "legacy_messages=1" in decision.body
    assert "właściwe przypomnienie" in decision.body


def test_sensitive_legacy_excerpt_is_redacted():
    ctx = {
        "query_terms": ["tropy"],
        "episodes": [],
        "legacy_messages": [
            {
                "phrase": "tropy",
                "conversation_title": "Badanie ludzkiego mózgu",
                "author_role": "assistant",
                "create_time_warsaw": "2025-06-24T02:50:25+02:00",
                "text": "Dane Kliniczne Kluczowe. PESEL: 88022406859. Telefon: 123456789.",
            }
        ],
        "raw_chat_fallback": [],
        "counts": {"episodes": 0, "legacy_messages": 1, "raw_chat_fallback": 0},
    }
    rendered = MemoryRecallPresenter().render(ctx, user_text="Jakie tropy pamięci?", limit=1)
    assert "88022406859" not in rendered
    assert "123456789" not in rendered
    assert "FRAGMENT ZAWIERA DANE WRAŻLIWE" in rendered
