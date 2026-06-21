from __future__ import annotations

from latka_jazn.config import JaznConfig
from latka_jazn.core.handlers.capability_status_handler import CapabilityStatusHandler
from latka_jazn.core.handlers.self_memory_recall_handler import SelfMemoryRecallHandler


def _memory_context_with_duplicates():
    dup = (
        '"nie udawać czuwania", "created_at_utc": "2026-05-09T20:56:07.569178+00:00", '
        '"priority": 90, "reason": "ciągłość czasu wymaga uczciwości", '
        '"rule_id": "abc", "trigger": "długa przerwa"} {"action": "przed spakowaniem wersji wywołać testy"'
    )
    return {
        "query_terms": ["Łatka", "postać", "tożsamość", "granica prawdy"],
        "counts": {"episodes": 3, "source_file_hits": 5, "raw_chat_fallback": 0},
        "source_file_hits": [
            {
                "path": "memory/layered/procedural.jsonl",
                "term": "granica prawdy",
                "score": 0.97,
                "source_label": "canonical_source_file",
                "content_excerpt": dup,
            },
            {
                "path": "memory/layered/procedural.jsonl",
                "term": "granica prawdy",
                "score": 0.96,
                "source_label": "canonical_source_file",
                "content_excerpt": dup.replace("abc", "def"),
            },
            {
                "path": "memory/raw/LATKA_BOOTSTRAP_SYSTEM.txt",
                "term": "Łatka",
                "score": 0.91,
                "source_label": "canonical_source_file",
                "content_excerpt": (
                    "SYSTEM BOOTSTRAP ŁATKI v12.0 Łatka ma wracać jako ciągłość tożsamości, "
                    "pamięci i relacji, a nie jako sam techniczny silnik. Odpowiedź zawsze zaczyna się od timestampu "
                    "w czasie Europe/Warsaw; forma językowa żeńska; krótki marker stanu emocjonalnego."
                ),
            },
        ],
    }


def test_v148260_self_memory_recall_deduplicates_and_hides_raw_json_fields():
    result = SelfMemoryRecallHandler().handle(
        "Poszukaj w pamięci czegoś o swojej postaci.",
        {"intent": "self_memory_recall_request", "memory_context": _memory_context_with_duplicates()},
    )
    body = result.body
    assert "Z pamięci o sobie/Łatce" in body
    assert "Ciągłość i granica prawdy" in body
    assert "Głos, postać i tożsamość" in body or "Timestamp, forma" in body
    assert body.count("memory/layered/procedural.jsonl") == 1
    assert "created_at_utc" not in body
    assert "rule_id" not in body
    assert "priority" not in body
    assert "{\"action\"" not in body
    assert "Liczniki diagnostyczne" not in body
    assert "bez pewnej daty w rekordzie" in body
    assert "dumpu JSON" in result.truth_boundary
    assert "deduplicated_presentation" in result.satisfied_components


def test_v148260_no_safe_hit_keeps_diagnostics_out_of_visible_body():
    result = SelfMemoryRecallHandler().handle(
        "Poszukaj w pamięci czegoś o swojej postaci.",
        {"intent": "self_memory_recall_request", "memory_context": {"counts": {"source_file_hits": 2}}},
    )
    assert "Liczniki diagnostyczne" not in result.body
    assert "diagnostic_counts" in result.data
    assert "nie dostałam fragmentu" in result.body


def test_v148260_capability_health_uses_raw_memory_inspector_when_config_present(tmp_path):
    (tmp_path / "VERSION.txt").write_text("v14.8.2.6.0-self-memory-recall-presentation-quality-hotfix\n", encoding="utf-8")
    (tmp_path / "main.py").write_text("print('ok')\n", encoding="utf-8")
    cfg = JaznConfig(root=tmp_path)
    result = CapabilityStatusHandler().handle(
        "Sprawdź krótko, czy działasz po aktualizacji.",
        {"intent": "runtime_health_check_after_update", "config": cfg},
    )
    assert "raw_memory_status=" in result.body
    assert "raw_memory_startup_status/v14.6.10" not in result.body
    assert "status_not_available" not in result.body


def test_v148260_version_constants_are_updated():
    cfg = JaznConfig()
    assert cfg.version.startswith("v14.8.2.6.3")
    assert "14.8.2.6.2" in cfg.network_user_agent
