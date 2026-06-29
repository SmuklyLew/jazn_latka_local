from latka_jazn.nlp.dialogue_intent_classifier import DialogueIntentClassifier
from latka_jazn.core.route_registry import RouteRegistry
from latka_jazn.core.runtime_answer_validator import RuntimeAnswerValidator
from latka_jazn.core.handlers.capability_status_handler import CapabilityStatusHandler
from latka_jazn.core.handlers.self_memory_recall_handler import SelfMemoryRecallHandler
from latka_jazn.core.runtime_chat import RuntimeChatLifecycle, run_persistent_chat


class _KeyboardInterruptShell:
    def __init__(self, engine, **kwargs):
        self.lifecycle = RuntimeChatLifecycle(
            mode="persistent_chat_loop",
            engine_reused_between_turns=True,
            shutdown_when_loop_exits=True,
            truth_boundary="test lifecycle",
            stdin_is_tty=False,
            process_persistence="ephemeral_stdin_pipe",
            background_process_claim_allowed=False,
        )
    def cmdloop(self):
        raise KeyboardInterrupt()
    def _write(self, text):
        self.text = text
    def postloop(self):
        pass


def intent(text: str) -> str:
    return DialogueIntentClassifier().classify(text).primary_intent


def test_v14825_direct_capability_and_internet_intents_do_not_fall_to_ordinary():
    assert intent("Co potrafisz.") == "capability_status_question"
    assert intent("Masz dostęp do internetu?") == "internet_access_question"
    assert intent("Sprawdź krótko, czy działasz po aktualizacji.") == "runtime_health_check_after_update"


def test_v1483_runtime_marker_status_after_update_is_not_update_execution():
    classifier = DialogueIntentClassifier()
    examples = [
        "Jaki jest aktywny folder runtime po aktualizacji markera? Odpowiedz tylko aktualnym statusem.",
        "Sprawdź lokalny status Jaźni po aktualizacji markera aktywnego runtime.",
        "Podaj active_database i cache_miss_reasons po aktualizacji markera runtime.",
    ]
    for text in examples:
        report = classifier.classify(text)
        assert report.primary_intent == "runtime_health_check_after_update"
        assert report.question_object == "runtime_health"
        assert not report.update_request


def test_v1483_real_update_execution_still_routes_to_update():
    report = DialogueIntentClassifier().classify(
        "Zaktualizuj kod systemu Jaźni po hotfixie i zrób patch routingu."
    )
    assert report.primary_intent == "system_update_execution_request"
    assert report.update_request


def test_v14825_self_memory_persona_intents_do_not_become_update():
    assert intent("Poszukaj w pamięci informacji o sobie Łatko.") == "self_memory_recall_request"
    assert intent("A coś o swojej osobie/postaci?") == "self_memory_recall_request"
    assert intent("Co pamiętasz?") == "self_memory_recall_request"


def test_v14825_route_registry_points_new_intents_to_dedicated_handlers():
    reg = RouteRegistry()
    assert reg.resolve("capability_status_question").handler_name == "CapabilityStatusHandler"
    assert reg.resolve("internet_access_question").handler_name == "CapabilityStatusHandler"
    assert reg.resolve("runtime_health_check_after_update").handler_name == "CapabilityStatusHandler"
    assert reg.resolve("self_memory_recall_request").handler_name == "SelfMemoryRecallHandler"


def test_v14825_validator_rejects_known_bad_answers_from_user_log():
    v = RuntimeAnswerValidator()
    bad_memory = v.validate(
        user_text="Poszukaj w pamięci czegoś o swojej postaci.",
        body="Tak — ta aktualizacja ma trzy rdzenie: bogatsze stany emocjonalne, jawny indeks ciągłości sesji oraz szerszy katalog tematów poznawczych.",
        route="ordinary_dialogue",
        detected_intent="self_memory_recall_request",
    )
    assert bad_memory.must_regenerate
    assert bad_memory.required_repair_route == "self_memory_recall_repair"

    bad_capability = v.validate(
        user_text="Co potrafisz.",
        body="Jestem tutaj. Zatrzymuję się przy tym zdaniu i zostawiam mu chwilę miejsca.",
        route="ordinary_dialogue",
        detected_intent="capability_status_question",
    )
    assert bad_capability.must_regenerate

    bad_internet = v.validate(
        user_text="Masz dostęp do internetu?",
        body="Jestem tutaj. Doprecyzuj tylko kierunek jednym zdaniem.",
        route="ordinary_dialogue",
        detected_intent="internet_access_question",
    )
    assert bad_internet.must_regenerate


def test_v14825_capability_handler_answers_directly_without_fallback():
    handler = CapabilityStatusHandler()
    cap = handler.handle("Co potrafisz.", {"intent": "capability_status_question", "cli_capabilities": {}})
    assert "Potrafię" in cap.body
    assert "--chat" in cap.body
    assert "Nie potrafię" in cap.body

    net = handler.handle("Masz dostęp do internetu?", {"intent": "internet_access_question"})
    assert "internet" in net.body.lower()
    assert "provider" in net.body.lower()
    assert "nie wolno mi udawać" in net.body.lower()

    health = handler.handle("Jaki jest aktywny folder runtime po aktualizacji markera?", {"intent": "runtime_health_check_after_update"})
    assert "runtime_write_raw_memory_status" in health.body
    assert "conversation_archive/FTS" in health.body
    assert "polecenie wykonania nowej aktualizacji kodu" in health.body


def test_v14825_self_memory_handler_filters_update_only_trace():
    memory_context = {
        "query_terms": ["Łatka", "postać"],
        "counts": {"source_file_hits": 2},
        "source_file_hits": [
            {
                "path": "memory/layered/procedural.jsonl",
                "term": "aktualizacja",
                "score": 0.91,
                "source_label": "canonical_source_file",
                "content_excerpt": "Tak — ta aktualizacja ma trzy rdzenie: bogatsze stany emocjonalne, jawny indeks ciągłości sesji oraz szerszy katalog tematów poznawczych.",
            },
            {
                "path": "docs/IDENTITY_ORIGIN_CONTRACT.md",
                "term": "Łatka",
                "score": 0.86,
                "source_label": "canonical_source_file",
                "content_excerpt": "Łatka mówi w pierwszej osobie, z własnym głosem, pamięcią, kanonem i granicą prawdy; nie jest biologicznym człowiekiem.",
            },
        ],
    }
    result = SelfMemoryRecallHandler().handle(
        "Poszukaj w pamięci czegoś o swojej postaci.",
        {"intent": "self_memory_recall_request", "memory_context": memory_context},
    )
    assert "aktualizacja ma trzy rdzenie" not in result.body
    assert "własnym głosem" in result.body
    assert "nie wolno mi zastępować" in result.body or "nie wolno mi" in result.body


def test_v14825_run_persistent_chat_handles_keyboard_interrupt(monkeypatch):
    import latka_jazn.core.runtime_chat as runtime_chat
    monkeypatch.setattr(runtime_chat, "LatkaRuntimeShell", _KeyboardInterruptShell)
    assert run_persistent_chat(object()).exit_reason == "keyboard_interrupt"
