# Current package version: v14.8.5.006-runtime-marker-schema-integrity-hotfix
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from latka_jazn.version import PACKAGE_VERSION, PACKAGE_VERSION_FULL, schema_version

ACTIVE_PACKAGE_VERSION = PACKAGE_VERSION


def _configure_stdio_utf8() -> None:
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8")


from latka_jazn.config import JaznConfig
from latka_jazn.core.canon.extraction import run_canon_extraction
from latka_jazn.core.clock import WarsawClock
from latka_jazn.core.emotions import AffectiveState
from latka_jazn.core.identity_guard import IdentityPerspectiveGuard
from latka_jazn.core.renderer import ResponseRenderer
from latka_jazn.core.runtime_status import build_runtime_status
from latka_jazn.core.startup_contract import build_startup_status, build_startup_summary, build_self_check, build_truth_boundary_check, classify_fallback_text
from latka_jazn.core.engine import JaznEngine
from latka_jazn.core.memory_search_planner import MemorySearchPlanner
from latka_jazn.core.runtime_chat import run_persistent_chat
from latka_jazn.core.runtime_session import JaznRuntimeSession
from latka_jazn.memory.raw_memory_status import RawMemoryInspector
from latka_jazn.memory.normalization_sidecar import MemoryNormalizationSidecar
from latka_jazn.memory.conversation_archive import ConversationArchiveStore
from latka_jazn.tools.package_export import export_package
from latka_jazn.tools.dedup_manifest import write_dedup_report
from latka_jazn.tools.active_extraction_cache import build_active_runtime_status, write_active_runtime_marker, visible_preview_contract_version
from latka_jazn.core.polish_understanding import PolishUnderstandingEngine
from latka_jazn.core.lexical_semantics import LexicalSemanticUnderstanding
from latka_jazn.nlp.polish_lemmatizer import PolishLemmatizationEngine
from latka_jazn.integrations.github_repository_plan import build_github_repository_plan, write_github_repository_plan
from latka_jazn.core.project_index import build_project_startup_index
from latka_jazn.nlp.topic_mismatch_guard import TopicMismatchGuard
from latka_jazn.nlp.dialogue_intent_classifier import DialogueIntentClassifier
from latka_jazn.core.route_registry import RouteRegistry
from latka_jazn.core.module_responsibility_map import ModuleResponsibilityMap
from latka_jazn.memory.requirements_ledger import RequirementsLedger
from latka_jazn.core.turn_trace_reader import TurnTraceReader
from latka_jazn.core.runtime_visible_answer_comparator import RuntimeVisibleAnswerComparator
from latka_jazn.nlp.external_dictionary_adapter import ExternalDictionaryAdapter
from latka_jazn.nlp.language_resource_registry import LanguageResourceRegistry
from latka_jazn.core.voice_source_contract import VoiceSourceContract
from latka_jazn.core.runtime_rendering_modes import RuntimeRenderingModeSelector
from latka_jazn.memory.raw_chat_importer import RawChatImporter
from latka_jazn.model_adapters.null_model_adapter import NullModelAdapter
from latka_jazn.nlp_reasoning.diagnostics import build_polish_morphology_diagnostics, build_polish_reasoning_diagnostics
from latka_jazn.nlp_reasoning.source_registry import PolishReasoningSourceRegistry
from latka_jazn.nlp_reasoning.adapters.online_lookup import PolishOnlineLookupPlanner
from latka_jazn.core.turn_route_trace import TurnRouteTrace
from latka_jazn.nlp_reasoning.lexical_resource_registry import LexicalResourceRegistry


def _render_readonly_status(root: Path | None = None) -> str:
    cfg = JaznConfig(root=root or Path(__file__).resolve().parent, network_time_first=False)
    clock = WarsawClock(cfg.timezone)
    renderer = ResponseRenderer(clock, IdentityPerspectiveGuard())
    body = build_runtime_status(cfg, store=None, readonly=True)
    return renderer.render(body, AffectiveState(), clock.now(network_first=False))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="Runtime Jaźni Łatki: rozmowa bezpośrednia, cognitive-frame, diagnostyka i eksport paczek.",
        allow_abbrev=False,
    )
    parser.add_argument("--root", type=Path, default=None, help="Folder główny aktywnej paczki Jaźni.")
    parser.add_argument("--status", "--status-readonly", "--diagnostics-readonly", action="store_true", dest="status_readonly", help="Pokaż diagnostykę bez zapisu do pamięci. --status jest jawnym aliasem, nie skrótem argparse.")
    parser.add_argument("--cognitive-frame", "--chatgpt-frame", "--brain-frame", action="store_true", dest="cognitive_frame", help="Zwróć wewnętrzny pakiet poznawczy JSON dla ChatGPT, nie gotową odpowiedź użytkownikowi.")
    parser.add_argument("--debug-direct", action="store_true", dest="debug_direct", help="Pokaż techniczną ścieżkę bezpośrednią i fallback diagnostyczny zamiast rozmownej odpowiedzi.")
    parser.add_argument("--chat", "--loop", action="store_true", dest="chat_loop", help="Uruchom stałą pętlę rozmowy: jeden JaznEngine działa przez wiele tur aż do /exit lub EOF.")
    parser.add_argument("--chat-gpt", action="store_true", dest="chat_gpt", help="Uruchom główny most ChatGPT w protokole JSONL: przyjmuje message/text/user_text/content/prompt, format messages[].content albo zwykły tekst; zwraca jedną linię JSON na turę.")
    parser.add_argument("--session-id", default=None, help="Jawny identyfikator sesji dla kontrolowanego carryover w --chat/--chat-gpt.")
    parser.add_argument("--no-carryover", action="store_true", dest="no_carryover", help="Zablokuj użycie poprzedniej tury nawet jeśli istnieje runtime_state.json.")
    parser.add_argument("--github-plan", action="store_true", dest="github_plan", help="Zapisz i pokaż plan repozytoriów Latka.Jazn oraz Latka.Jazn.Memory bez wykonywania pushu.")
    parser.add_argument("--dedup-report", action="store_true", dest="dedup_report", help="Zbuduj raport duplikatów treści i SHA-256 bez usuwania plików.")
    parser.add_argument("--lexical-frame", action="store_true", dest="lexical_frame", help="Pokaż raport leksykalny aktualnej Jaźni: polskie rozumienie + rozszerzona semantyka słów i fraz.")
    parser.add_argument("--nlp-frame", action="store_true", dest="nlp_frame", help="Pokaż raport NLP aktualnej Jaźni: tokeny, lemma_candidates, selected_lemma, confidence i provider.")
    parser.add_argument("--runtime-preview", action="store_true", dest="runtime_preview", help="Pokaż dokładną odpowiedź runtime oraz pakiet cognitive-frame/source_origin/self_state dla mostu ChatGPT.")
    parser.add_argument("--runtime-preview-output", type=Path, default=None, help="Opcjonalna ścieżka pliku JSON dla --runtime-preview; pełny payload trafia do pliku, a stdout zwraca krótkie potwierdzenie.")
    parser.add_argument("--active-cache-status", action="store_true", dest="active_cache_status", help="Pokaż status aktywnego rozpakowanego folderu i decyzję, czy trzeba ponownie rozpakować ZIP.")
    parser.add_argument("--project-startup-index", action="store_true", dest="project_startup_index", help="Zbuduj i pokaż mapę plików oraz modułów/funkcji Jaźni przy rozruchu.")
    parser.add_argument("--topic-guard", action="store_true", dest="topic_guard", help="Pokaż raport TopicMismatchGuard dla wiadomości bez generowania pełnej odpowiedzi.")
    parser.add_argument("--dialogue-intent", action="store_true", dest="dialogue_intent", help="Pokaż klasyfikację aktu rozmowy aktywnego runtime bez generowania odpowiedzi.")
    parser.add_argument("--module-responsibility-map", action="store_true", dest="module_responsibility_map", help="Zbuduj semantyczną mapę odpowiedzialności modułów i funkcji.")
    parser.add_argument("--seed-requirements-ledger", action="store_true", dest="seed_requirements_ledger", help="Dopisz wymagania aktywnego manifestu do requirements ledger.")
    parser.add_argument("--last-turn", action="store_true", dest="last_turn", help="Pokaż ostatni turn checkpoint: exact_runtime_text, visible_text, route, template_origin i source-origin.")
    parser.add_argument("--compare-runtime-visible", action="store_true", dest="compare_runtime_visible", help="Porównaj exact runtime text z widoczną odpowiedzią ChatGPT dla ostatniej tury albo --trace-id.")
    parser.add_argument("--dictionary-lookup", action="store_true", dest="dictionary_lookup", help="Sprawdź termin przez cache/mini-leksykon/adaptory słowników; nie udawaj lookupu online bez providera.")
    parser.add_argument("--language-resources", action="store_true", dest="language_resources", help="Pokaż rejestr dostępnych i opcjonalnych zasobów językowych/słownikowych.")
    parser.add_argument("--polish-reasoning-frame", action="store_true", dest="polish_reasoning_frame", help="Pokaż warstwowy frame Polish Reasoning: normalizacja, morfologia, semantyka, reply policy i status providerów.")
    parser.add_argument("--polish-reasoning-sources", action="store_true", dest="polish_reasoning_sources", help="Pokaż rejestr źródeł/licencji/cache dla warstwy Polish Reasoning.")
    parser.add_argument("--polish-reasoning-bootstrap-plan", action="store_true", dest="polish_reasoning_bootstrap_plan", help="Pokaż komendy lokalnej instalacji providerów NLP bez ich automatycznego pobierania.")
    parser.add_argument("--nlp-resource-status", action="store_true", dest="nlp_resource_status", help="Pokaż status lexical resource registry/cache: źródła, licencje, dostępność i projektowy leksykon bez pobierania dużych danych.")
    parser.add_argument("--polish-morphology", action="store_true", dest="polish_morphology", help="Pokaż szczegółową analizę morfologiczną v14.8.4: Morfeusz/PoliMorf, kandydaci i selected_lemma.")
    parser.add_argument("--morfeusz-status", action="store_true", dest="morfeusz_status", help="Pokaż status realnego providera Morfeusz2/SGJP w Polish Reasoning.")
    parser.add_argument("--polimorf-status", action="store_true", dest="polimorf_status", help="Pokaż status opcjonalnego lokalnego providera PoliMorf.")
    parser.add_argument("--wsjp-lookup-plan", action="store_true", dest="wsjp_lookup_plan", help="Zbuduj bezpieczny plan lookupu WSJP dla terminu; nie scrapuje masowo strony.")
    parser.add_argument("--nkjp-lookup-plan", action="store_true", dest="nkjp_lookup_plan", help="Zbuduj bezpieczny plan lookupu NKJP/concordance dla terminu; nie pobiera pełnego korpusu.")
    parser.add_argument("--voice-source-contract", action="store_true", dest="voice_source_contract", help="Pokaż kontrakt: Jaźń jako źródło, ChatGPT/model jako kanał głosu.")
    parser.add_argument("--rendering-mode", action="store_true", dest="rendering_mode", help="Pokaż decyzję naturalna odpowiedź vs exact runtime/diagnostyka.")
    parser.add_argument("--raw-chat-status", action="store_true", dest="raw_chat_status", help="Pokaż status memory/raw/chat.html i chat.html.7z bez rozpakowywania.")
    parser.add_argument("--raw-chat-status-json", action="store_true", dest="raw_chat_status_json", help="Pokaż uczciwy status raw memory/indexu jako JSON aktywnego runtime.")
    parser.add_argument("--conversation-archive-status", action="store_true", dest="conversation_archive_status", help="Pokaż status conversation_archive/FTS/staging zbudowanych z raw_chats/*.html.")
    parser.add_argument("--conversation-archive-search", action="store_true", dest="conversation_archive_search", help="Szukaj w osobnym conversation_fts i zwróć UID/provenance do archive/staging.")
    parser.add_argument("--conversation-archive-limit", type=int, default=8, help="Limit trafień dla --conversation-archive-search.")
    parser.add_argument("--conversation-archive-show-snippets", action="store_true", dest="conversation_archive_show_snippets", help="Dołącz krótkie excerpt z prywatnego archive do wyników wyszukiwania.")
    parser.add_argument("--status-json", action="store_true", dest="status_json", help="Pokaż startup/runtime status jako JSON bez parsowania prozy.")
    parser.add_argument("--model-adapter-status", action="store_true", dest="model_adapter_status", help="Pokaż status adapterów modeli: skonfigurowane/nieudawane.")
    parser.add_argument("--startup-status", action="store_true", dest="startup_status", help="Pokaż własny kontrakt startowy runtime: lekki loader ChatGPT + obowiązki przejęte przez Jaźń.")
    parser.add_argument("--startup-status-fast", action="store_true", dest="startup_status_fast", help="Pokaż szybki startup status bez deep SQLite i bez sieci.")
    parser.add_argument("--startup-status-deep", action="store_true", dest="startup_status_deep", help="Pokaż pełny deep startup audit; może trwać długo.")
    parser.add_argument("--turn-trace", action="store_true", dest="turn_trace", help="Pokaż lekki ślad trasy tury: classifier -> guard -> route -> handler -> validator.")
    parser.add_argument("--network-time-check", action="store_true", dest="network_time_check", help="Jawna diagnostyka czasu sieciowego; zwykła rozmowa jej nie używa.")
    parser.add_argument("--sqlite-integrity-audit", action="store_true", dest="sqlite_integrity_audit", help="Jawny deep audit SQLite z integrity_check/foreign_key_check.")
    parser.add_argument("--self-check", action="store_true", dest="self_check", help="Pokaż skrócony self-check runtime i potwierdzenie, że procedura startowa jest własnością systemu Jaźni.")
    parser.add_argument("--truth-boundary-check", action="store_true", dest="truth_boundary_check", help="Pokaż granicę prawdy runtime/ChatGPT/pliki/pamięć/ZIP.")
    parser.add_argument("--fallback-audit", action="store_true", dest="fallback_audit", help="Zbadaj tekst jako możliwy fallback, stale route albo kontrakt zamiast odpowiedzi.")
    parser.add_argument("--memory-plan", action="store_true", dest="memory_plan", help="Pokaż plan wyszukiwania pamięci i trafienia plików kanonicznych bez generowania zwykłej odpowiedzi.")
    parser.add_argument("--canon-extraction-preview", action="store_true", dest="canon_extraction_preview", help="Przeskanuj prywatne źródła kanonu i zapisz raport/progress bez modyfikowania kanonu runtime.")
    parser.add_argument("--canon-extraction-write-private", action="store_true", dest="canon_extraction_write_private", help="Przeskanuj źródła i zapisz lokalny prywatny moduł .py canon extension; nie commitować bez recenzji.")
    parser.add_argument("--canon-extraction-progress", type=Path, default=None, help="Opcjonalna ścieżka JSONL postępu dla ekstrakcji kanonu.")
    parser.add_argument("--canon-extraction-verbose-progress", action="store_true", dest="canon_extraction_verbose_progress", help="Wypisuj zdarzenia progress JSONL na stdout oprócz zapisu do pliku.")
    parser.add_argument("--canon-extra-source", action="append", default=[], help="Dodatkowe źródło kanonu względne wobec root; można powtórzyć.")
    parser.add_argument("--memory-normalization-status", action="store_true", dest="memory_normalization_status", help="Pokaż status niedestrukcyjnego sidecara normalizacji pamięci.")
    parser.add_argument("--normalize-memory-sidecar", action="store_true", dest="normalize_memory_sidecar", help="Zbuduj lub zaktualizuj sidecar normalizacji pamięci bez modyfikowania aktywnej bazy rozmów.")
    parser.add_argument("--wake-state-status", action="store_true", dest="wake_state_status", help="Pokaż status aktywnego wake_state z sidecara pamięci.")
    parser.add_argument("--build-wake-state", action="store_true", dest="build_wake_state", help="Zbuduj wake_state z istniejących rekordów sidecara normalizacji.")
    parser.add_argument("--dedupe-memory-sidecar", action="store_true", dest="dedupe_memory_sidecar", help="Zbuduj warstwowe grupy duplikatów w sidecarze bez kasowania rekordów źródłowych.")
    parser.add_argument("--dry-run", action="store_true", dest="dry_run", help="Tryb kontrolny dla operacji normalizacji/wake_state bez zapisu.")
    parser.add_argument("--normalization-limit", type=int, default=None, help="Opcjonalny limit rekordów dla sidecara normalizacji, używany głównie w testach i audytach.")
    parser.add_argument("--dedupe-min-group-size", type=int, default=2, help="Minimalny rozmiar grupy dla warstwowej deduplikacji sidecara.")
    parser.add_argument("--write-active-runtime-marker", action="store_true", dest="write_active_runtime_marker", help="Zapisz JAZN_ACTIVE_RUNTIME.json dla aktywnego folderu i cache rozpakowania.")
    parser.add_argument("--source-zip", type=Path, default=None, help="Opcjonalna ścieżka ZIP-a źródłowego do porównania checksum w aktywnym cache.")
    parser.add_argument("--marker-output", type=Path, default=None, help="Opcjonalna ścieżka pliku JAZN_ACTIVE_RUNTIME.json.")
    parser.add_argument("--record-final-reply", action="store_true", dest="record_final_reply", help="Dopisz do ledgera finalną widoczną odpowiedź ChatGPT dla podanego turn_id/trace_id/timestamp_header.")
    parser.add_argument("--turn-id", default=None, help="turn_id z cognitive_turn_envelope dla --record-final-reply.")
    parser.add_argument("--trace-id", default=None, help="trace_id z cognitive_turn_envelope dla --record-final-reply.")
    parser.add_argument("--timestamp-header", default=None, help="timestamp_header z cognitive_turn_envelope dla --record-final-reply.")
    parser.add_argument("--state-emoticon", default="🌿", help="Emotikon stanu używany, jeśli finalny tekst wymaga dopięcia timestampu.")
    parser.add_argument("--final-text-file", type=Path, default=None, help="Opcjonalny plik z finalną widoczną odpowiedzią do zapisania w ledgerze.")
    export_group = parser.add_mutually_exclusive_group()
    export_group.add_argument("--export-system", action="store_true", help="Utwórz paczkę system-only bez memory/ i workspace_runtime/.")
    export_group.add_argument("--export-memory", action="store_true", help="Utwórz paczkę memory-only z memory/ i workspace_runtime/.")
    export_group.add_argument("--export-full", action="store_true", help="Utwórz pełną paczkę systemu wraz z pamięcią.")
    export_group.add_argument("--export-nlp", action="store_true", help="Utwórz paczkę NLP-resources-only bez pamięci i bez ciężkich modeli.")
    export_group.add_argument("--export-github-source-safe", action="store_true", help="Utwórz paczkę źródłową bez surowej pamięci i aktywnych baz SQLite.")
    parser.add_argument("--output", type=Path, default=None, help="Opcjonalna ścieżka ZIP dla eksportu.")
    parser.add_argument("message", nargs=argparse.REMAINDER, help="Treść wiadomości dla runtime.")
    return parser


def _message_from_remainder(parts: list[str]) -> str:
    if parts and parts[0] == "--":
        parts = parts[1:]
    return " ".join(parts).strip()


def _build_light_turn_trace(cfg: JaznConfig, text: str) -> dict:
    intent = DialogueIntentClassifier().classify(text)
    guard = TopicMismatchGuard().analyse(text, runtime_version=cfg.version).to_dict()
    entry = RouteRegistry().resolve(intent.primary_intent, confidence=intent.confidence)
    return TurnRouteTrace(
        user_text_preview=(text or "")[:240],
        speech_act=intent.speech_act,
        question_object=intent.question_object,
        primary_intent_initial=intent.primary_intent,
        primary_intent_final=intent.primary_intent,
        secondary_intents=list(intent.secondary_intents),
        topic_guard=guard,
        selected_route=entry.route,
        selected_handler=entry.handler_name,
        startup_status_mode="fast",
        sqlite_health_mode="metadata",
        network_time_used=False,
        deep_audit_used=False,
        runtime_answer_validation={
            "status": "not_run_without_response",
            "truth_boundary": "--turn-trace alone does not generate a final answer; combine with --runtime-preview to inspect validator output.",
        },
        final_text_source="not_generated",
    ).to_dict()


def main(argv: list[str] | None = None) -> int:
    _configure_stdio_utf8()
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--chat-jsonl" in argv:
        sys.stderr.write("Flaga --chat-jsonl została usunięta z aktywnego CLI. Użyj: python main.py --chat-gpt --session-id <id>\n")
        return 2
    parser = _build_parser()
    ns = parser.parse_args(argv)
    if ns.runtime_preview_output is None and "--runtime-preview-output" in ns.message:
        idx = ns.message.index("--runtime-preview-output")
        if idx + 1 >= len(ns.message):
            parser.error("--runtime-preview-output requires a path")
        ns.runtime_preview_output = Path(ns.message[idx + 1])
        ns.message = ns.message[:idx] + ns.message[idx + 2:]
    root = ns.root.resolve() if ns.root else None

    if ns.status_readonly:
        print(_render_readonly_status(root))
        return 0

    config = JaznConfig(root=root) if root else None

    if ns.startup_status or ns.startup_status_fast or ns.startup_status_deep:
        cfg = config or JaznConfig()
        mode = "deep" if ns.startup_status_deep else "fast"
        print(json.dumps(build_startup_status(cfg, source_zip=ns.source_zip, mode=mode).to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if ns.status_json:
        cfg = config or JaznConfig()
        archive_store = ConversationArchiveStore(cfg.root)
        print(json.dumps({
            "runtime_version": cfg.version,
            "startup_summary": build_startup_summary(cfg, source_zip=ns.source_zip),
            "startup_status_mode": "fast",
            "sqlite_health_mode": "metadata",
            "raw_memory_status": RawMemoryInspector(cfg.root, cfg.memory_db_path).inspect().to_dict(),
            "conversation_archive_status": archive_store.status(health_mode="metadata").to_dict(),
        }, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if ns.network_time_check:
        cfg = config or JaznConfig()
        print(json.dumps({"runtime_version": cfg.version, "network_time_check": WarsawClock(cfg.timezone).network_time_check()}, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if ns.sqlite_integrity_audit:
        cfg = config or JaznConfig()
        print(json.dumps({"runtime_version": cfg.version, "sqlite_integrity_audit": ConversationArchiveStore(cfg.root).status(health_mode="deep").to_dict()}, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if ns.turn_trace and not ns.runtime_preview:
        cfg = config or JaznConfig()
        text = _message_from_remainder(ns.message)
        print(json.dumps({"runtime_version": cfg.version, "turn_route_trace": _build_light_turn_trace(cfg, text)}, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if ns.self_check:
        cfg = config or JaznConfig()
        print(json.dumps(build_self_check(cfg), ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if ns.truth_boundary_check:
        cfg = config or JaznConfig()
        print(json.dumps(build_truth_boundary_check(cfg), ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if ns.fallback_audit:
        text = _message_from_remainder(ns.message)
        print(json.dumps(classify_fallback_text(text), ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if ns.memory_plan:
        cfg = config or JaznConfig()
        text = _message_from_remainder(ns.message)
        planner = MemorySearchPlanner(cfg.root)
        plan = planner.plan(text)
        archive_store = ConversationArchiveStore(cfg.root)
        archive_query = " ".join((plan.search_terms or plan.focus_terms or [])[:8]) or text
        payload = {
            "schema_version": schema_version("memory_plan_cli"),
            "runtime_version": cfg.version,
            "memory_search_plan": plan.to_dict(),
            "source_file_hits": [hit.to_dict() for hit in planner.search_source_files(plan, limit=8)],
            "conversation_archive_status": archive_store.status(check_integrity=False).to_dict(),
            "conversation_archive_hits": archive_store.search(archive_query, limit=8, include_snippets=False).to_dict(),
            "truth_boundary": "To jest plan, kanoniczne trafienia plików i metadane trafień conversation_archive/FTS, nie pełna rozmowna odpowiedź ani dowód pełnego odczytu całej pamięci.",
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if ns.canon_extraction_preview or ns.canon_extraction_write_private:
        cfg = config or JaznConfig()
        mode = "write-private-extension" if ns.canon_extraction_write_private else "preview"
        payload = {
            "runtime_version": cfg.version,
            "canon_extraction": run_canon_extraction(
                cfg.root,
                mode=mode,
                progress_path=ns.canon_extraction_progress,
                verbose_progress=ns.canon_extraction_verbose_progress,
                extra_sources=ns.canon_extra_source or [],
            ),
            "truth_boundary": "Raport i progress są artefaktem patcha. Właściwy runtime canon jest w plikach .py; lokalny prywatny extension .py wymaga recenzji przed commitem.",
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if ns.conversation_archive_status:
        cfg = config or JaznConfig()
        payload = {
            "runtime_version": cfg.version,
            "conversation_archive_status": ConversationArchiveStore(cfg.root).status().to_dict(),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if ns.conversation_archive_search:
        cfg = config or JaznConfig()
        text = _message_from_remainder(ns.message)
        payload = {
            "runtime_version": cfg.version,
            "conversation_archive_search": ConversationArchiveStore(cfg.root).search(
                text,
                limit=ns.conversation_archive_limit,
                include_snippets=ns.conversation_archive_show_snippets,
            ).to_dict(),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if ns.memory_normalization_status:
        cfg = config or JaznConfig()
        sidecar = MemoryNormalizationSidecar(
            cfg.root,
            source_db_path=cfg.root / cfg.memory_db_name,
            sidecar_db_path=cfg.root / cfg.audit_db_name,
            runtime_version=cfg.version,
        )
        payload = {"runtime_version": cfg.version, "memory_normalization_status": sidecar.status().to_dict()}
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if ns.normalize_memory_sidecar:
        cfg = config or JaznConfig()
        sidecar = MemoryNormalizationSidecar(
            cfg.root,
            source_db_path=cfg.root / cfg.memory_db_name,
            sidecar_db_path=cfg.root / cfg.audit_db_name,
            runtime_version=cfg.version,
        )
        payload = {
            "runtime_version": cfg.version,
            "memory_normalization_report": sidecar.normalize(dry_run=ns.dry_run, limit=ns.normalization_limit).to_dict(),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if ns.wake_state_status:
        cfg = config or JaznConfig()
        sidecar = MemoryNormalizationSidecar(
            cfg.root,
            source_db_path=cfg.root / cfg.memory_db_name,
            sidecar_db_path=cfg.root / cfg.audit_db_name,
            runtime_version=cfg.version,
        )
        payload = {"runtime_version": cfg.version, "wake_state_status": sidecar.wake_state_status().to_dict()}
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if ns.build_wake_state:
        cfg = config or JaznConfig()
        sidecar = MemoryNormalizationSidecar(
            cfg.root,
            source_db_path=cfg.root / cfg.memory_db_name,
            sidecar_db_path=cfg.root / cfg.audit_db_name,
            runtime_version=cfg.version,
        )
        payload = {"runtime_version": cfg.version, "wake_state_build_report": sidecar.build_wake_state(dry_run=ns.dry_run).to_dict()}
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if ns.dedupe_memory_sidecar:
        cfg = config or JaznConfig()
        sidecar = MemoryNormalizationSidecar(
            cfg.root,
            source_db_path=cfg.root / cfg.memory_db_name,
            sidecar_db_path=cfg.root / cfg.audit_db_name,
            runtime_version=cfg.version,
        )
        payload = {
            "runtime_version": cfg.version,
            "layered_dedupe_report": sidecar.build_layered_dedupe(
                dry_run=ns.dry_run,
                min_group_size=ns.dedupe_min_group_size,
            ).to_dict(),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if ns.project_startup_index:
        cfg = config or JaznConfig()
        payload = build_project_startup_index(cfg.root, write=True)
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if ns.topic_guard:
        cfg = config or JaznConfig()
        text = _message_from_remainder(ns.message)
        payload = TopicMismatchGuard().analyse(text, runtime_version=cfg.version).to_dict()
        print(json.dumps({"runtime_version": cfg.version, "topic_mismatch_guard": payload}, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if ns.dialogue_intent:
        cfg = config or JaznConfig()
        text = _message_from_remainder(ns.message)
        payload = DialogueIntentClassifier().classify(text).to_dict()
        print(json.dumps({"runtime_version": cfg.version, "dialogue_intent_classifier": payload}, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if ns.module_responsibility_map:
        cfg = config or JaznConfig()
        payload = ModuleResponsibilityMap(cfg.root).build(write=True)
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if ns.seed_requirements_ledger:
        cfg = config or JaznConfig()
        path = RequirementsLedger(cfg.root).seed_manifest_requirements()
        print(json.dumps({"runtime_version": cfg.version, "requirements_ledger": str(path), "seeded": True}, ensure_ascii=False, indent=2, sort_keys=True))
        return 0


    if ns.last_turn:
        cfg = config or JaznConfig()
        payload = TurnTraceReader(cfg.root).latest() or {"schema_version": schema_version("turn_checkpoint"), "found": False, "reason": "no_checkpoint_found"}
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if ns.compare_runtime_visible:
        cfg = config or JaznConfig()
        payload = RuntimeVisibleAnswerComparator(cfg.root).compare(ns.trace_id)
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if ns.language_resources:
        cfg = config or JaznConfig()
        payload = {"runtime_version": cfg.version, "language_resource_registry": LanguageResourceRegistry().to_dict()}
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if ns.polish_reasoning_sources:
        cfg = config or JaznConfig()
        payload = {"runtime_version": cfg.version, "polish_reasoning_sources": PolishReasoningSourceRegistry(cfg.root).to_dict()}
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if ns.nlp_resource_status:
        cfg = config or JaznConfig()
        registry = LexicalResourceRegistry(
            cfg.root,
            verified_sources_path=cfg.root / cfg.lexical_resources_registry_path,
            project_lexicon_path=cfg.root / cfg.latka_project_lexicon_path,
            cache_path=cfg.lexical_resource_cache_path,
        )
        payload = {"runtime_version": cfg.version, "nlp_resource_status": registry.to_dict()}
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if ns.polish_morphology or ns.morfeusz_status or ns.polimorf_status:
        cfg = config or JaznConfig()
        text = _message_from_remainder(ns.message)
        payload = build_polish_morphology_diagnostics(cfg.root, text)
        if ns.morfeusz_status or ns.polimorf_status:
            wanted = "morfeusz2-sgjp" if ns.morfeusz_status else "polimorf"
            statuses = payload["polish_morphology"].get("provider_statuses", [])
            payload = {
                "runtime_version": cfg.version,
                "schema_version": "polish_provider_status/v14.8.4",
                "provider_status": next((item for item in statuses if item.get("provider") == wanted), None),
                "truth_boundary": "Status providera mówi tylko, czy lokalny adapter jest dostępny. Nie oznacza pobrania pełnego słownika ani pełnej dezambiguacji języka.",
            }
        else:
            payload = {"runtime_version": cfg.version, **payload}
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if ns.polish_reasoning_frame or ns.polish_reasoning_bootstrap_plan:
        cfg = config or JaznConfig()
        text = _message_from_remainder(ns.message)
        payload = build_polish_reasoning_diagnostics(cfg.root, text)
        if ns.polish_reasoning_bootstrap_plan:
            payload = {
                "runtime_version": cfg.version,
                "schema_version": "polish_reasoning_bootstrap_plan/v14.8.4",
                "bootstrap_commands": payload["bootstrap_commands"],
                "source_registry": payload["source_registry"],
                "truth_boundary": "Bootstrap instaluje providery i modele z Internetu lokalnie; patch nie vendoruje dużych słowników ani modeli.",
            }
        else:
            payload = {"runtime_version": cfg.version, **payload}
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if ns.wsjp_lookup_plan or ns.nkjp_lookup_plan:
        cfg = config or JaznConfig()
        term = _message_from_remainder(ns.message)
        planner = PolishOnlineLookupPlanner()
        lookup = planner.nkjp(term).to_dict() if ns.nkjp_lookup_plan else planner.wsjp(term).to_dict()
        payload = {
            "runtime_version": cfg.version,
            "schema_version": "polish_reasoning_lookup_plan/v14.8.3",
            "lookup_plan": lookup,
            "truth_boundary": "To jest plan/link lookupu. Runtime nie twierdzi, że pobrał definicję lub przykłady bez realnego żądania HTTP i zapisu źródła.",
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if ns.voice_source_contract:
        cfg = config or JaznConfig()
        payload = {"runtime_version": cfg.version, "voice_source_contract": VoiceSourceContract.build(runtime_active=True, runtime_mode="one_shot").to_dict()}
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if ns.rendering_mode:
        cfg = config or JaznConfig()
        text = _message_from_remainder(ns.message)
        payload = {"runtime_version": cfg.version, "runtime_rendering_mode": RuntimeRenderingModeSelector().select(text).to_dict()}
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if ns.raw_chat_status or getattr(ns, "raw_chat_status_json", False):
        cfg = config or JaznConfig()
        payload = {"runtime_version": cfg.version, "raw_chat_status": RawMemoryInspector(cfg.root, cfg.memory_db_path).inspect().to_dict()}
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if ns.model_adapter_status:
        cfg = config or JaznConfig()
        payload = {"runtime_version": cfg.version, "model_adapter_status": NullModelAdapter().describe()}
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if ns.dictionary_lookup:
        cfg = config or JaznConfig()
        term = _message_from_remainder(ns.message)
        payload = {"runtime_version": cfg.version, "dictionary_lookup": ExternalDictionaryAdapter(cfg.root, allow_network=cfg.dictionary_allow_network, user_agent=cfg.network_user_agent, timeout_seconds=cfg.dictionary_online_lookup_timeout_seconds, max_retries=cfg.network_max_retries, cache_ttl_seconds=cfg.network_cache_ttl_seconds).lookup(term).to_dict()}
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if ns.active_cache_status or ns.write_active_runtime_marker:
        cfg = config or JaznConfig()
        if ns.write_active_runtime_marker:
            payload = write_active_runtime_marker(cfg.root, source_zip=ns.source_zip, marker_output=ns.marker_output)
        else:
            payload = build_active_runtime_status(cfg.root, source_zip=ns.source_zip, marker_output=ns.marker_output)
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if ns.github_plan:
        cfg = config or JaznConfig()
        path = write_github_repository_plan(cfg.root)
        plan = build_github_repository_plan(cfg.root).to_dict()
        plan["written_to"] = str(path)
        print(json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if ns.dedup_report:
        cfg = config or JaznConfig()
        path = write_dedup_report(cfg.root, cfg.root / "reports" / "DEDUP_REPORT_V14_6_1.json")
        print(path.read_text(encoding="utf-8"))
        return 0

    if ns.lexical_frame:
        cfg = config or JaznConfig()
        text = _message_from_remainder(ns.message)
        polish = PolishUnderstandingEngine(cfg.root).analyse(text)
        nlp = PolishLemmatizationEngine(cfg.root).analyse(text)
        lexical = LexicalSemanticUnderstanding(cfg.root).analyse(text, polish_report=polish.to_dict(), nlp_report=nlp.to_dict())
        print(json.dumps({"runtime_version": cfg.version, "polish_understanding": polish.to_dict(), "polish_nlp": nlp.to_dict(), "lexical_semantic_understanding": lexical.to_dict()}, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if ns.nlp_frame:
        cfg = config or JaznConfig()
        text = _message_from_remainder(ns.message)
        nlp = PolishLemmatizationEngine(cfg.root).analyse(text)
        print(json.dumps({"runtime_version": cfg.version, "polish_nlp": nlp.to_dict()}, ensure_ascii=False, indent=2, sort_keys=True))
        return 0


    if ns.record_final_reply:
        engine = JaznEngine(config)
        try:
            if not ns.turn_id or not ns.trace_id or not ns.timestamp_header:
                parser.error("--record-final-reply wymaga --turn-id, --trace-id i --timestamp-header")
            if ns.final_text_file:
                final_text = ns.final_text_file.read_text(encoding="utf-8")
            else:
                final_text = _message_from_remainder(ns.message)
            result = engine.persist_final_visible_reply(
                turn_id=ns.turn_id,
                trace_id=ns.trace_id,
                timestamp_header=ns.timestamp_header,
                final_text=final_text,
                state_emoticon=ns.state_emoticon,
                source="chatgpt_visible_layer_cli",
                client_context={"client": "chatgpt_visible_layer_cli", "lifecycle": "one_shot_visible_capture"},
            )
            print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        finally:
            engine.shutdown()
        return 0

    if ns.runtime_preview:
        engine = JaznEngine(config)
        try:
            text = _message_from_remainder(ns.message)
            envelope = engine.process_turn(
                text,
                client_context={
                    "client": "chatgpt_runtime_preview",
                    "lifecycle": "one_shot_preview",
                    "preview_phase": "single_integrated_process_turn",
                    "session_id": ns.session_id,
                    "no_carryover": ns.no_carryover,
                },
            )
            envelope_dict = envelope.to_dict()
            cognitive_frame = envelope_dict.get("cognitive_frame") or {}
            runtime_text = envelope_dict.get("final_visible_text") or ""
            final_contract = envelope_dict.get("final_response_contract") or {}
            payload = {
                "schema_version": schema_version("runtime_preview"),
                "runtime_version": engine.config.version,
                "mode": "diagnostic_runtime_preview_single_process_turn_not_background_daemon",
                "turn_trace": envelope_dict.get("trace"),
                "runtime_text": runtime_text,
                "fallback_detected": any(
                    signature in runtime_text
                    for signature in (
                        "Nie znalazłam osobnej trasy odpowiedzi",
                        "runtime odebrał wiadomość",
                        "debugowy fallback",
                        "pusty fallback",
                    )
                ) or final_contract.get("fallback_classification") not in {None, "not_fallback"},
                "runtime_answer_quality": final_contract.get("runtime_answer_quality"),
                "fallback_classification": final_contract.get("fallback_classification"),
                "startup_procedure_required": bool(final_contract.get("startup_procedure_required")),
                "source_origin": cognitive_frame.get("source_origin"),
                "self_state_runtime": cognitive_frame.get("self_state_runtime"),
                "affect_mix": envelope_dict.get("affect_mix"),
                "dialogue_state": envelope_dict.get("dialogue_state"),
                "turn_route_trace": (cognitive_frame.get("turn_route_trace") or (envelope_dict.get("conversation_decision") or {}).get("turn_route_trace")),
                "final_response_contract": envelope_dict.get("final_response_contract"),
                "cognitive_turn_envelope": envelope_dict,
                "cognitive_frame": cognitive_frame,
                "visible_runtime_preview_contract": {
                    "schema_version": visible_preview_contract_version(engine.config.root),
                    "timestamp_header": (envelope_dict.get("trace") or {}).get("timestamp_header"),
                    "active_root": str(engine.config.root),
                    "start_file": "main.py",
                    "response_source": "runtime.process_turn + final_response_contract",
                    "required_visible_fields": ["timestamp_header", "active_root", "start_file", "runtime_answer_quality", "fallback_classification", "response_source", "one_shot_or_chat_loop_limit"],
                    "must_show_when_user_asks_about_runtime_files_timestamp_preview_or_fallback": True,
                    "one_shot_or_chat_loop_limit": "--runtime-preview jest jednorazowym wywołaniem; stałą pętlę daje dopiero python main.py --chat.",
                },
                "active_extraction_cache_status": build_active_runtime_status(engine.config.root),
                "startup_summary": build_startup_summary(engine.config),
                "free_dialogue_memory_nlp_bridge": build_startup_summary(engine.config),
                "truth_boundary": "Ten tryb wykonuje jedno zintegrowane wywołanie process_turn: runtime buduje cognitive-frame i z tej samej koperty tworzy finalną odpowiedź. Nie udaje stałego procesu w tle.",
            }
            payload_json = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
            if ns.runtime_preview_output:
                ns.runtime_preview_output.parent.mkdir(parents=True, exist_ok=True)
                ns.runtime_preview_output.write_text(payload_json + "\n", encoding="utf-8")
                print(json.dumps({
                    "runtime_version": engine.config.version,
                    "runtime_preview_output": str(ns.runtime_preview_output),
                    "written": True,
                    "truth_boundary": "Pełny runtime-preview zapisano do pliku; stdout zawiera tylko krótkie potwierdzenie.",
                }, ensure_ascii=False, indent=2, sort_keys=True))
            else:
                print(payload_json)
        finally:
            engine.shutdown()
        return 0


    if ns.chat_gpt:
        sessions: dict[str, JaznRuntimeSession] = {}
        generated_session: JaznRuntimeSession | None = None
        default_client = "chatgpt_bridge"
        default_lifecycle = "chatgpt_bridge_jsonl"
        bridge_protocol_version = schema_version("chatgpt_bridge_jsonl")
        accepted_input_fields = ["message", "text", "user_text", "content", "prompt"]

        def bridge_meta(
            *,
            client: str = default_client,
            input_kind: str | None = None,
            input_field: str | None = None,
            line_index: int | None = None,
        ) -> dict:
            meta = {
                "protocol_version": bridge_protocol_version,
                "accepted_input_fields": accepted_input_fields,
                "accepted_input_shapes": [
                    "plain_text_line",
                    "json_object.message",
                    "json_object.text",
                    "json_object.user_text",
                    "json_object.content",
                    "json_object.prompt",
                    "json_object.messages[].content",
                ],
                "preferred_input_field": "message",
                "client": client,
                "lifecycle": default_lifecycle,
                "mode": "primary_chatgpt_bridge",
                "deprecated_flag_removed": "--chat-jsonl",
            }
            if input_kind is not None:
                meta["input_kind"] = input_kind
            if input_field is not None:
                meta["input_field"] = input_field
            if line_index is not None:
                meta["line_index"] = line_index
            return meta

        def error_payload(
            *,
            error_code: str,
            error: str,
            client: str = default_client,
            input_kind: str | None = None,
            input_field: str | None = None,
            line_index: int | None = None,
        ) -> dict:
            return {
                "schema_version": schema_version("chatgpt_bridge_error"),
                "chatgpt_bridge": bridge_meta(
                    client=client,
                    input_kind=input_kind,
                    input_field=input_field,
                    line_index=line_index,
                ),
                "ok": False,
                "error_code": error_code,
                "error": error,
            }

        def extract_user_text(payload: dict) -> tuple[str, str, str]:
            for candidate in accepted_input_fields:
                value = payload.get(candidate)
                if value is not None and str(value).strip():
                    return str(value).strip(), "json", candidate

            messages = payload.get("messages")
            if isinstance(messages, list):
                fallback_content = ""
                fallback_field = "messages[].content"
                for item in messages:
                    if not isinstance(item, dict):
                        continue
                    content = item.get("content")
                    if content is None:
                        continue
                    if isinstance(content, list):
                        parts = []
                        for part in content:
                            if isinstance(part, dict):
                                text_part = part.get("text")
                                if text_part is not None:
                                    parts.append(str(text_part))
                            elif part is not None:
                                parts.append(str(part))
                        content_text = "".join(parts).strip()
                    else:
                        content_text = str(content).strip()
                    if not content_text:
                        continue
                    fallback_content = content_text
                    if str(item.get("role") or "").lower() == "user":
                        return content_text, "json_chat_messages", "messages[user].content"
                if fallback_content:
                    return fallback_content, "json_chat_messages", fallback_field

            return "", "json", "<missing>"

        def get_session(session_id: str | None, *, client: str) -> tuple[JaznRuntimeSession, str]:
            nonlocal generated_session
            if session_id:
                if session_id not in sessions:
                    sessions[session_id] = JaznRuntimeSession(
                        config,
                        session_id=session_id,
                        no_carryover=ns.no_carryover,
                        source_client=client,
                    )
                return sessions[session_id], "payload"
            if ns.session_id:
                if ns.session_id not in sessions:
                    sessions[ns.session_id] = JaznRuntimeSession(
                        config,
                        session_id=ns.session_id,
                        no_carryover=ns.no_carryover,
                        source_client=client,
                    )
                return sessions[ns.session_id], "cli_arg"
            if generated_session is None:
                generated_session = JaznRuntimeSession(
                    config,
                    session_id=None,
                    no_carryover=ns.no_carryover,
                    source_client=client,
                )
                sessions[generated_session.state.session_id] = generated_session
            return generated_session, "generated"


        try:
            for line_index, line in enumerate(sys.stdin, 1):
                line = line.strip()
                if not line:
                    continue
                if line in {"/exit", "exit"}:
                    break

                input_kind = "plain_text"
                input_field = "plain_text"
                payload_session_id = None
                client = default_client

                try:
                    payload = json.loads(line)
                except json.JSONDecodeError as exc:
                    if line[:1] in {"{", "["}:
                        print(json.dumps(error_payload(
                            error_code="malformed_json",
                            error=f"Niepoprawna linia JSONL: {exc.msg}",
                            input_kind="malformed_json",
                            input_field="<parse_error>",
                            line_index=line_index,
                        ), ensure_ascii=False, sort_keys=True), flush=True)
                        continue
                    user_text = line
                else:
                    input_kind = "json"
                    if not isinstance(payload, dict):
                        print(json.dumps(error_payload(
                            error_code="invalid_jsonl_payload",
                            error="Każda linia --chat-gpt musi być obiektem JSON albo zwykłym tekstem.",
                            input_kind="json_non_object",
                            input_field="<non_object>",
                            line_index=line_index,
                        ), ensure_ascii=False, sort_keys=True), flush=True)
                        continue
                    client = str(payload.get("client") or default_client)
                    payload_session_id = str(payload.get("session_id") or "").strip() or None
                    user_text, input_kind, input_field = extract_user_text(payload)

                if not user_text.strip():
                    print(json.dumps(error_payload(
                        error_code="empty_message",
                        error="Pusta wiadomość nie została przekazana do runtime Jaźni.",
                        client=client,
                        input_kind=input_kind,
                        input_field=input_field,
                        line_index=line_index,
                    ), ensure_ascii=False, sort_keys=True), flush=True)
                    continue

                session, session_id_source = get_session(payload_session_id, client=client)
                try:
                    result = session.process_user_text(
                        user_text,
                        client=client,
                        lifecycle=default_lifecycle,
                        session_id_source=session_id_source,
                        process_reused=True,
                    )
                except Exception as exc:
                    print(json.dumps(error_payload(
                        error_code="runtime_turn_failed",
                        error=f"Runtime Jaźni przerwał turę: {type(exc).__name__}: {exc}",
                        client=client,
                        input_kind=input_kind,
                        input_field=input_field,
                        line_index=line_index,
                    ), ensure_ascii=False, sort_keys=True), flush=True)
                    continue
                result["chatgpt_bridge"] = bridge_meta(
                    client=client,
                    input_kind=input_kind,
                    input_field=input_field,
                    line_index=line_index,
                )
                result["ok"] = True
                print(json.dumps(result, ensure_ascii=False, sort_keys=True), flush=True)
        finally:
            for session in sessions.values():
                session.close()
        return 0

    if ns.export_system or ns.export_memory or ns.export_full or ns.export_nlp or ns.export_github_source_safe:
        cfg = config or JaznConfig()
        mode = "system" if ns.export_system else "memory" if ns.export_memory else "nlp" if ns.export_nlp else "github_source_safe" if ns.export_github_source_safe else "full"
        report = export_package(cfg.root, mode, ns.output)
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if ns.chat_loop:
        session = JaznRuntimeSession(config, session_id=ns.session_id, no_carryover=ns.no_carryover, source_client="chat")
        try:
            run_persistent_chat(session, session_id=ns.session_id, no_carryover=ns.no_carryover)
        finally:
            session.close()
        return 0

    engine = JaznEngine(config)
    try:
        text = _message_from_remainder(ns.message)
        if ns.cognitive_frame:
            packet = engine.build_cognitive_frame(text, client_context={"client": "chatgpt_cli_bridge", "lifecycle": "one_shot"})
            print(json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True))
        elif text:
            if ns.debug_direct:
                print(engine.handle_user_message(text, client_context={"client": "cli_direct_debug", "debug_direct": True, "lifecycle": "one_shot"}))
            else:
                envelope = engine.process_turn(text, client_context={"client": "cli_direct_conversation", "debug_direct": False, "lifecycle": "one_shot", "session_id": ns.session_id, "no_carryover": ns.no_carryover})
                print(envelope.final_visible_text or envelope.final_response_contract.get("final_visible_text", ""))
        else:
            print(engine.bootstrap())
    finally:
        engine.shutdown()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        # Pozwala bezpiecznie ucinać długie podglądy JSON przez `head`/pipe
        # bez fałszywego wrażenia awarii runtime.
        try:
            sys.stdout.close()
        except Exception:
            pass
        raise SystemExit(0)
