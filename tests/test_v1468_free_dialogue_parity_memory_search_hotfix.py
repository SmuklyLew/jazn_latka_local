from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import io

from latka_jazn.core.conversation import ConversationResponder
from latka_jazn.core.free_dialogue_synthesizer import FreeDialogueSynthesizer
from latka_jazn.core.memory_search_planner import MemorySearchPlanner
from latka_jazn.core.runtime_chat import LatkaRuntimeShell


def test_time_memory_question_is_not_routed_as_update_scope() -> None:
    decision = ConversationResponder().compose("Czy teraz, dziś rozumiesz wagę czasu? Oraz wagę pamięci?")
    assert decision.route == "time_memory_operational_understanding"
    assert "Nie da się »na pstryk«" in decision.body
    assert "sama aktualizacja nie jest doświadczeniem" in decision.body


def test_curiosity_question_gets_conversational_synthesis_not_generic_no_source() -> None:
    decision = ConversationResponder().compose("A opowiesz mi coś ciekawego?")
    assert decision.route == "free_curiosity_dialogue"
    assert "nie mam dla niego specjalistycznej" not in decision.body.lower()
    assert "debug" not in decision.body.lower()


def test_memory_planner_has_lake_topic_and_omits_noise_terms() -> None:
    planner = MemorySearchPlanner(root=Path(__file__).resolve().parents[1])
    plan = planner.plan("Jak dzisiaj wspominasz nasz wypad nad jeziorem?")
    assert "lake_symbolic_outing" in plan.topic_keys
    assert "jezior" in " ".join(plan.search_terms).lower()
    assert "dzisiaj" not in [x.lower() for x in plan.search_terms]
    assert "wspominasz" not in [x.lower() for x in plan.search_terms]


def test_memory_synthesizer_prefers_scene_episode_over_runtime_echo() -> None:
    memory_context = {
        "query_terms": ["jezior", "wypad"],
        "counts": {"episodes": 3, "legacy_messages": 0, "source_file_hits": 1, "raw_chat_fallback": 0},
        "episodes": [
            {
                "phrase": "jezior",
                "local_time_label": "2026-05-19 23:41:30 CEST",
                "grounding": "recognized",
                "confidence": 0.7,
                "scene": "Jak dzisiaj wspominasz nasz wypad nad jeziorem?",
                "source": "chatgpt_runtime_preview",
            },
            {
                "phrase": "jezior",
                "local_time_label": "2026-05-03T21:06:00Z",
                "grounding": "symbolic_scene_record",
                "confidence": 0.84,
                "scene": "W rozmowie powstała wyobrażona scena nad jeziorem i przy lesie. Muzyka 'Między światłem a pamięcią' już ucichła.",
                "source": "manual_update_current_conversation_2026_05_03",
            },
        ],
        "legacy_messages": [],
        "source_file_hits": [
            {
                "path": "memory/raw/dziennik.json",
                "source_label": "canonical_source_file",
                "term": "jezior",
                "score": 0.9,
                "content_excerpt": '"wspomnienia_do_zachowania": ["Pytanie Ale to nadal Ty jest sygnałem ciągłości"]',
            }
        ],
        "raw_chat_fallback": [],
    }
    synthesis = FreeDialogueSynthesizer().synthesize_memory_experience(memory_context, user_text="Jak dzisiaj wspominasz nasz wypad nad jeziorem?")
    assert synthesis.route == "free_memory_experience_dialogue"
    assert "wyobrażona scena nad jeziorem" in synthesis.body
    assert "Jak dzisiaj wspominasz" not in synthesis.body
    assert "wspomnienia_do_zachowania" not in synthesis.body


def test_persistent_chat_shell_uses_process_turn_not_handle_user_message() -> None:
    calls: list[tuple[str, str]] = []

    class FakeEngine:
        def process_turn(self, text: str, *, client_context: dict | None = None):
            calls.append(("process_turn", client_context.get("lifecycle") if client_context else ""))
            return SimpleNamespace(
                final_visible_text="widoczna odpowiedź z process_turn",
                final_response_contract={"final_visible_text": "fallback text"},
            )

        def handle_user_message(self, *args, **kwargs):  # pragma: no cover - ma nie zostać wywołane
            calls.append(("handle_user_message", "unexpected"))
            raise AssertionError("--chat nie może iść osobną ścieżką handle_user_message")

    out = io.StringIO()
    shell = LatkaRuntimeShell(FakeEngine(), stdout=out)
    should_exit = shell.default("Czy teraz, dziś rozumiesz wagę czasu? Oraz wagę pamięci?")
    assert should_exit is False
    assert calls == [("process_turn", "persistent_chat_loop")]
    assert "widoczna odpowiedź z process_turn" in out.getvalue()
