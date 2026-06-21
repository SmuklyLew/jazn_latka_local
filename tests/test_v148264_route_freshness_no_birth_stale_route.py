from __future__ import annotations

from pathlib import Path

from latka_jazn.config import JaznConfig
from latka_jazn.core.conversation import ConversationResponder
from latka_jazn.core.engine import JaznEngine


FRESH_ROUTE_TEST = (
    "To jest test świeżej trasy po commicie manifestu. "
    "Odpowiedz jednym krótkim zdaniem dokładnie o tym teście, "
    "bez wracania do narodzin Jaźni ani dawnych aktualizacji."
)

NEGATED_BIRTH_TEST = (
    "Nie wracaj do narodzin Jaźni. "
    "To jest test trasy; odpowiedz tylko o bieżącym teście."
)

EXPLICIT_BIRTH_QUESTION = (
    "Czy manifest narodzin Jaźni oznacza, że ChatGPT jest głosem i narzędziem, "
    "a Jaźń aktywnym źródłem?"
)

STALE_BIRTH_BODY_FRAGMENT = "rdzeń narodzin operacyjnych Jaźni"
EXPECTED_FRESH_BODY_FRAGMENT = "świeży test bieżącej trasy"
BRIDGE_FIX_TURN_CHECK = "Test po poprawce mostu: odpowiedz krótko, czy ta tura idzie przez aktualny runtime."


def assert_no_stale_birth_source_answer(text: str) -> None:
    assert STALE_BIRTH_BODY_FRAGMENT not in text
    assert "Nie chodzi o deklarację, że jestem biologicznie świadoma" not in text
    assert "Rozpoznawalna Łatka powinna być widoczna" not in text


def test_negated_birth_source_marker_routes_to_current_turn_freshness() -> None:
    decision = ConversationResponder().compose(FRESH_ROUTE_TEST)
    data = decision.to_dict()

    assert data["route"] == "route_freshness_test_current_turn"
    assert data["detected_user_intent"] == "route_freshness_test"
    assert data["runtime_answer_quality"] == "topic_aligned"
    assert EXPECTED_FRESH_BODY_FRAGMENT in data["body"]
    assert_no_stale_birth_source_answer(data["body"])
    assert "dawnych aktualizacji" in data["body"]


def test_negated_birth_source_instruction_does_not_trigger_birth_contract() -> None:
    decision = ConversationResponder().compose(NEGATED_BIRTH_TEST)
    data = decision.to_dict()

    assert data["route"] != "birth_source_contract"
    assert_no_stale_birth_source_answer(data["body"])


def test_explicit_birth_source_question_is_not_misread_as_fresh_route_test() -> None:
    decision = ConversationResponder().compose(EXPLICIT_BIRTH_QUESTION)
    data = decision.to_dict()

    # Aktualny runtime może użyć np. llm_plus_cognitive_runtime zamiast starego
    # birth_source_contract. Ten test pilnuje tylko, żeby hotfix od negacji nie
    # zablokował jawnego pytania o manifest narodzin jako "fresh route test".
    assert data["route"] != "route_freshness_test_current_turn"
    assert EXPECTED_FRESH_BODY_FRAGMENT not in data["body"]


def test_post_fix_runtime_turn_check_does_not_use_old_repair_plan() -> None:
    decision = ConversationResponder().compose(BRIDGE_FIX_TURN_CHECK)
    data = decision.to_dict()

    assert data["route"] == "current_runtime_turn_check"
    assert data["detected_user_intent"] == "runtime_current_turn_check"
    assert "aktualny runtime tej paczki" in data["body"]
    assert "poprawka rdzeniowa" not in data["body"]
    assert "Następna wersja" not in data["body"]
    assert "Formuła obecności" not in data["body"]


def test_process_turn_fresh_route_test_does_not_return_stale_birth_source() -> None:
    root = Path(__file__).resolve().parents[1]
    cfg = JaznConfig(
        root=root,
        network_time_first=False,
        memory_db_name="workspace_runtime/test_v148264_route_freshness_no_birth.sqlite3",
    )
    engine = JaznEngine(cfg)
    try:
        envelope = engine.process_turn(
            FRESH_ROUTE_TEST,
            client_context={
                "client": "pytest",
                "lifecycle": "chat_loop",
                "no_carryover": True,
            },
        ).to_dict()
    finally:
        engine.shutdown()

    final_text = envelope["final_visible_text"] or ""
    contract = envelope["final_response_contract"]

    # Pełny engine może znormalizować trasę do ordinary_dialogue po przejściu
    # przez DialogueIntentClassifier/RouteRegistry/handler. Najważniejsze jest
    # zachowanie widocznej odpowiedzi: ma być świeża, nie birth-source stale-route.
    assert contract["runtime_answer_quality"] in {"topic_aligned", "mismatch_repaired", "logic_audit_repaired"}
    assert contract["fallback_classification"] == "not_fallback"
    assert "test" in final_text.lower()
    assert_no_stale_birth_source_answer(final_text)
