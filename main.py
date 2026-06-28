# Current package version: v14.8.5.017-model-adapter-contracts
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
from latka_jazn.core.runtime_truth_gate import apply_runtime_truth_gate
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
from latka_jazn.model_adapters.factory import build_model_adapter_status
from latka_jazn.nlp_reasoning.diagnostics import build_polish_morphology_diagnostics, build_polish_reasoning_diagnostics
from latka_jazn.nlp_reasoning.source_registry import PolishReasoningSourceRegistry
from latka_jazn.nlp_reasoning.adapters.online_lookup import PolishOnlineLookupPlanner
from latka_jazn.core.turn_route_trace import TurnRouteTrace
from latka_jazn.nlp_reasoning.lexical_resource_registry import LexicalResourceRegistry
from latka_jazn.core.chat_command_contract import apply_openai_cli_settings, run_jsonl_chat_bridge
from latka_jazn.core.bridge_discovery import discover_runtime_bridges
from latka_jazn.core.runtime_daemon import (
    DEFAULT_DAEMON_HOST,
    DEFAULT_DAEMON_PORT,
    DEFAULT_HEARTBEAT_INTERVAL_SECONDS,
    DEFAULT_START_TIMEOUT_SECONDS,
    run_daemon,
    start_daemon,
    status_daemon,
    stop_daemon,
)


def _render_readonly_status(root: Path | None = None) -> str:
    cfg = JaznConfig(root=root or Path(__file__).resolve().parent)
    clock = WarsawClock(cfg.timezone)
    renderer = ResponseRenderer(clock, IdentityPerspectiveGuard())
    body = build_runtime_status(cfg, store=None, readonly=True)
    return renderer.render(body, AffectiveState(), clock.now(network_first=cfg.network_time_first, allow_fallback=cfg.local_time_fallback))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="Runtime JaĹşni Ĺatki: rozmowa bezpoĹ›rednia, cognitive-frame, diagnostyka i eksport paczek.",
        allow_abbrev=False,
    )
    parser.add_argument("--root", type=Path, default=None, help="Folder gĹ‚Ăłwny aktywnej paczki JaĹşni.")
    parser.add_argument("--status", "--status-readonly", "--diagnostics-readonly", action="store_true", dest="status_readonly", help="PokaĹĽ diagnostykÄ™ bez zapisu do pamiÄ™ci. --status jest jawnym aliasem, nie skrĂłtem argparse.")
    parser.add_argument("--cognitive-frame", "--chatgpt-frame", "--brain-frame", action="store_true", dest="cognitive_frame", help="ZwrĂłÄ‡ wewnÄ™trzny pakiet poznawczy JSON dla ChatGPT, nie gotowÄ… odpowiedĹş uĹĽytkownikowi.")
    parser.add_argument("--debug-direct", action="store_true", dest="debug_direct", help="PokaĹĽ technicznÄ… Ĺ›cieĹĽkÄ™ bezpoĹ›redniÄ… i fallback diagnostyczny zamiast rozmownej odpowiedzi.")
    parser.add_argument("--chat", "--loop", action="store_true", dest="chat_loop", help="Uruchom staĹ‚Ä… pÄ™tlÄ™ rozmowy: jeden JaznEngine dziaĹ‚a przez wiele tur aĹĽ do /exit lub EOF.")
    parser.add_argument("--chat-gpt", action="store_true", dest="chat_gpt", help="Uruchom gĹ‚Ăłwny most ChatGPT w protokole JSONL: przyjmuje message/text/user_text/content/prompt, format messages[].content albo zwykĹ‚y tekst; zwraca jednÄ… liniÄ™ JSON na turÄ™.")
    parser.add_argument("--chat-gpt-final-only", action="store_true", dest="chat_gpt_final_only", help="SkrĂłt: uruchom --chat-gpt i wypisz na stdout tylko final_visible_text dla kaĹĽdej tury; nie zmienia routingu ani stanu runtime.")
    parser.add_argument("--final-only", action="store_true", dest="final_only", help="Z --chat-gpt wypisz na stdout tylko final_visible_text dla kaĹĽdej tury; alias czytelny dla czĹ‚owieka.")
    parser.add_argument("--chat-open-ai", action="store_true", dest="chat_open_ai", help="Uruchom lokalny runtime JaĹşni z model_adapter przez OpenAI Responses API; wymaga OPENAI_API_KEY i nie udaje poĹ‚Ä…czenia bez klucza.")
    parser.add_argument("--openai-model", default=None, help="Model dla --chat-open-ai; domyĹ›lnie JAZN_MODEL_NAME albo konfiguracja runtime.")
    parser.add_argument("--openai-api-base", default=None, help="Bazowy URL API dla --chat-open-ai; domyĹ›lnie https://api.openai.com/v1.")
    parser.add_argument("--openai-timeout", type=float, default=None, help="Timeout sekund dla adaptera OpenAI w --chat-open-ai.")
    parser.add_argument("--openai-max-output-tokens", type=int, default=None, help="Limit output tokens dla adaptera OpenAI w --chat-open-ai.")
    parser.add_argument("--bridge-discovery", action="store_true", dest="bridge_discovery", help="PokaĹĽ wykryte mosty runtime: --chat, --chat-gpt, --chat-open-ai i daemon.")
    parser.add_argument("--daemon-run", action="store_true", dest="daemon_run", help="Uruchom foreground daemon staĹ‚ej aktywnej JaĹşni: lokalny HTTP loopback + PID + heartbeat + marker JAZN_ACTIVE_RUNTIME.json.")
    parser.add_argument("--daemon-start", action="store_true", dest="daemon_start", help="Uruchom daemon JaĹşni w tle i zwrĂłÄ‡ status startu.")
    parser.add_argument("--daemon-status", action="store_true", dest="daemon_status", help="SprawdĹş marker, PID, heartbeat i endpoint /status daemonu JaĹşni.")
    parser.add_argument("--daemon-stop", action="store_true", dest="daemon_stop", help="PoproĹ› dziaĹ‚ajÄ…cy lokalny daemon JaĹşni o zatrzymanie i zamkniÄ™cie sesji.")
    parser.add_argument("--daemon-host", default=DEFAULT_DAEMON_HOST, help="Adres bindowania daemonu; domyĹ›lnie tylko loopback 127.0.0.1.")
    parser.add_argument("--daemon-port", type=int, default=DEFAULT_DAEMON_PORT, help="Port lokalnego daemonu JaĹşni.")
    parser.add_argument("--daemon-heartbeat-interval", type=float, default=DEFAULT_HEARTBEAT_INTERVAL_SECONDS, help="Co ile sekund daemon odĹ›wieĹĽa marker aktywnego runtime.")
    parser.add_argument("--daemon-start-timeout", type=float, default=DEFAULT_START_TIMEOUT_SECONDS, help="Ile sekund --daemon-start czeka na odpowiedĹş /status.")
    parser.add_argument("--daemon-marker-output", type=Path, default=None, help="Opcjonalna Ĺ›cieĹĽka markera JAZN_ACTIVE_RUNTIME.json dla daemonu.")
    parser.add_argument("--session-id", default=None, help="Jawny identyfikator sesji dla kontrolowanego carryover w --chat/--chat-gpt.")
    parser.add_argument("--no-carryover", action="store_true", dest="no_carryover", help="Zablokuj uĹĽycie poprzedniej tury nawet jeĹ›li istnieje runtime_state.json.")
    parser.add_argument("--github-plan", action="store_true", dest="github_plan", help="Zapisz i pokaĹĽ plan repozytoriĂłw Latka.Jazn oraz Latka.Jazn.Memory bez wykonywania pushu.")
    parser.add_argument("--dedup-report", action="store_true", dest="dedup_report", help="Zbuduj raport duplikatĂłw treĹ›ci i SHA-256 bez usuwania plikĂłw.")
    parser.add_argument("--lexical-frame", action="store_true", dest="lexical_frame", help="PokaĹĽ raport leksykalny aktualnej JaĹşni: polskie rozumienie + rozszerzona semantyka sĹ‚Ăłw i fraz.")
    parser.add_argument("--nlp-frame", action="store_true", dest="nlp_frame", help="PokaĹĽ raport NLP aktualnej JaĹşni: tokeny, lemma_candidates, selected_lemma, confidence i provider.")
    parser.add_argument("--runtime-preview", action="store_true", dest="runtime_preview", help="Pokaż krótki, czytelny podgląd jednej tury runtime: final_visible_text + kluczowe pola diagnostyczne. Nie wypisuje pełnej koperty cognitive-frame do terminala.")
    parser.add_argument("--dev-preview", action="store_true", dest="dev_preview", help="Tryb deweloperski: pokaż pełny payload runtime-preview/cognitive-frame na stdout albo zapisz go przez --runtime-preview-output.")
    parser.add_argument("--runtime-preview-output", type=Path, default=None, help="Opcjonalna ścieżka pliku JSON dla --runtime-preview/--dev-preview; pełny payload trafia do pliku, a stdout zwraca tylko krótki, czytelny wynik.")
    parser.add_argument("--active-cache-status", action="store_true", dest="active_cache_status", help="PokaĹĽ status aktywnego rozpakowanego folderu i decyzjÄ™, czy trzeba ponownie rozpakowaÄ‡ ZIP.")
    parser.add_argument("--project-startup-index", action="store_true", dest="project_startup_index", help="Zbuduj i pokaĹĽ mapÄ™ plikĂłw oraz moduĹ‚Ăłw/funkcji JaĹşni przy rozruchu.")
    parser.add_argument("--topic-guard", action="store_true", dest="topic_guard", help="PokaĹĽ raport TopicMismatchGuard dla wiadomoĹ›ci bez generowania peĹ‚nej odpowiedzi.")
    parser.add_argument("--dialogue-intent", action="store_true", dest="dialogue_intent", help="PokaĹĽ klasyfikacjÄ™ aktu rozmowy aktywnego runtime bez generowania odpowiedzi.")
    parser.add_argument("--module-responsibility-map", action="store_true", dest="module_responsibility_map", help="Zbuduj semantycznÄ… mapÄ™ odpowiedzialnoĹ›ci moduĹ‚Ăłw i funkcji.")
    parser.add_argument("--seed-requirements-ledger", action="store_true", dest="seed_requirements_ledger", help="Dopisz wymagania aktywnego manifestu do requirements ledger.")
    parser.add_argument("--last-turn", action="store_true", dest="last_turn", help="PokaĹĽ ostatni turn checkpoint: exact_runtime_text, visible_text, route, template_origin i source-origin.")
    parser.add_argument("--compare-runtime-visible", action="store_true", dest="compare_runtime_visible", help="PorĂłwnaj exact runtime text z widocznÄ… odpowiedziÄ… ChatGPT dla ostatniej tury albo --trace-id.")
    parser.add_argument("--dictionary-lookup", action="store_true", dest="dictionary_lookup", help="SprawdĹş termin przez cache/mini-leksykon/adaptory sĹ‚ownikĂłw; nie udawaj lookupu online bez providera.")
    parser.add_argument("--language-resources", action="store_true", dest="language_resources", help="PokaĹĽ rejestr dostÄ™pnych i opcjonalnych zasobĂłw jÄ™zykowych/sĹ‚ownikowych.")
    parser.add_argument("--polish-reasoning-frame", action="store_true", dest="polish_reasoning_frame", help="PokaĹĽ warstwowy frame Polish Reasoning: normalizacja, morfologia, semantyka, reply policy i status providerĂłw.")
    parser.add_argument("--polish-reasoning-sources", action="store_true", dest="polish_reasoning_sources", help="PokaĹĽ rejestr ĹşrĂłdeĹ‚/licencji/cache dla warstwy Polish Reasoning.")
    parser.add_argument("--polish-reasoning-bootstrap-plan", action="store_true", dest="polish_reasoning_bootstrap_plan", help="PokaĹĽ komendy lokalnej instalacji providerĂłw NLP bez ich automatycznego pobierania.")
    parser.add_argument("--nlp-resource-status", action="store_true", dest="nlp_resource_status", help="PokaĹĽ status lexical resource registry/cache: ĹşrĂłdĹ‚a, licencje, dostÄ™pnoĹ›Ä‡ i projektowy leksykon bez pobierania duĹĽych danych.")
    parser.add_argument("--polish-morphology", action="store_true", dest="polish_morphology", help="PokaĹĽ szczegĂłĹ‚owÄ… analizÄ™ morfologicznÄ… v14.8.4: Morfeusz/PoliMorf, kandydaci i selected_lemma.")
    parser.add_argument("--morfeusz-status", action="store_true", dest="morfeusz_status", help="PokaĹĽ status realnego providera Morfeusz2/SGJP w Polish Reasoning.")
    parser.add_argument("--polimorf-status", action="store_true", dest="polimorf_status", help="PokaĹĽ status opcjonalnego lokalnego providera PoliMorf.")
    parser.add_argument("--wsjp-lookup-plan", action="store_true", dest="wsjp_lookup_plan", help="Zbuduj bezpieczny plan lookupu WSJP dla terminu; nie scrapuje masowo strony.")
    parser.add_argument("--nkjp-lookup-plan", action="store_true", dest="nkjp_lookup_plan", help="Zbuduj bezpieczny plan lookupu NKJP/concordance dla terminu; nie pobiera peĹ‚nego korpusu.")
    parser.add_argument("--voice-source-contract", action="store_true", dest="voice_source_contract", help="PokaĹĽ kontrakt: JaĹşĹ„ jako ĹşrĂłdĹ‚o, ChatGPT/model jako kanaĹ‚ gĹ‚osu.")
    parser.add_argument("--rendering-mode", action="store_true", dest="rendering_mode", help="PokaĹĽ decyzjÄ™ naturalna odpowiedĹş vs exact runtime/diagnostyka.")
    parser.add_argument("--raw-chat-status", action="store_true", dest="raw_chat_status", help="PokaĹĽ status memory/raw/chat.html i chat.html.7z bez rozpakowywania.")
    parser.add_argument("--raw-chat-status-json", action="store_true", dest="raw_chat_status_json", help="PokaĹĽ uczciwy status raw memory/indexu jako JSON aktywnego runtime.")
    parser.add_argument("--conversation-archive-status", action="store_true", dest="conversation_archive_status", help="PokaĹĽ status conversation_archive/FTS/staging zbudowanych z raw_chats/*.html.")
    parser.add_argument("--conversation-archive-search", action="store_true", dest="conversation_archive_search", help="Szukaj w osobnym conversation_fts i zwrĂłÄ‡ UID/provenance do archive/staging.")
    parser.add_argument("--conversation-archive-limit", type=int, default=8, help="Limit trafieĹ„ dla --conversation-archive-search.")
    parser.add_argument("--conversation-archive-show-snippets", action="store_true", dest="conversation_archive_show_snippets", help="DoĹ‚Ä…cz krĂłtkie excerpt z prywatnego archive do wynikĂłw wyszukiwania.")
    parser.add_argument("--status-json", action="store_true", dest="status_json", help="PokaĹĽ startup/runtime status jako JSON bez parsowania prozy.")
    parser.add_argument("--model-adapter-status", action="store_true", dest="model_adapter_status", help="PokaĹĽ status adapterĂłw modeli: skonfigurowane/nieudawane.")
    parser.add_argument("--startup-status", action="store_true", dest="startup_status", help="PokaĹĽ wĹ‚asny kontrakt startowy runtime: lekki loader ChatGPT + obowiÄ…zki przejÄ™te przez JaĹşĹ„.")
    parser.add_argument("--startup-status-fast", action="store_true", dest="startup_status_fast", help="PokaĹĽ szybki startup status bez deep SQLite i bez sieci.")
    parser.add_argument("--startup-status-deep", action="store_true", dest="startup_status_deep", help="PokaĹĽ peĹ‚ny deep startup audit; moĹĽe trwaÄ‡ dĹ‚ugo.")
    parser.add_argument("--turn-trace", action="store_true", dest="turn_trace", help="PokaĹĽ lekki Ĺ›lad trasy tury: classifier -> guard -> route -> handler -> validator.")
    parser.add_argument("--network-time-check", action="store_true", dest="network_time_check", help="Jawna diagnostyka czasu sieciowego; zwykĹ‚a rozmowa wymaga trusted network time albo blokuje normalnÄ… odpowiedĹş.")
    parser.add_argument("--sqlite-integrity-audit", action="store_true", dest="sqlite_integrity_audit", help="Jawny deep audit SQLite z integrity_check/foreign_key_check.")
    parser.add_argument("--self-check", action="store_true", dest="self_check", help="PokaĹĽ skrĂłcony self-check runtime i potwierdzenie, ĹĽe procedura startowa jest wĹ‚asnoĹ›ciÄ… systemu JaĹşni.")
    parser.add_argument("--truth-boundary-check", action="store_true", dest="truth_boundary_check", help="PokaĹĽ granicÄ™ prawdy runtime/ChatGPT/pliki/pamiÄ™Ä‡/ZIP.")
    parser.add_argument("--fallback-audit", action="store_true", dest="fallback_audit", help="Zbadaj tekst jako moĹĽliwy fallback, stale route albo kontrakt zamiast odpowiedzi.")
    parser.add_argument("--memory-plan", action="store_true", dest="memory_plan", help="PokaĹĽ plan wyszukiwania pamiÄ™ci i trafienia plikĂłw kanonicznych bez generowania zwykĹ‚ej odpowiedzi.")
    parser.add_argument("--canon-extraction-preview", action="store_true", dest="canon_extraction_preview", help="Przeskanuj prywatne ĹşrĂłdĹ‚a kanonu i zapisz raport/progress bez modyfikowania kanonu runtime.")
    parser.add_argument("--canon-extraction-write-private", action="store_true", dest="canon_extraction_write_private", help="Przeskanuj ĹşrĂłdĹ‚a i zapisz lokalny prywatny moduĹ‚ .py canon extension; nie commitowaÄ‡ bez recenzji.")
    parser.add_argument("--canon-extraction-progress", type=Path, default=None, help="Opcjonalna Ĺ›cieĹĽka JSONL postÄ™pu dla ekstrakcji kanonu.")
    parser.add_argument("--canon-extraction-verbose-progress", action="store_true", dest="canon_extraction_verbose_progress", help="Wypisuj zdarzenia progress JSONL na stdout oprĂłcz zapisu do pliku.")
    parser.add_argument("--canon-extra-source", action="append", default=[], help="Dodatkowe ĹşrĂłdĹ‚o kanonu wzglÄ™dne wobec root; moĹĽna powtĂłrzyÄ‡.")
    parser.add_argument("--memory-normalization-status", action="store_true", dest="memory_normalization_status", help="PokaĹĽ status niedestrukcyjnego sidecara normalizacji pamiÄ™ci.")
    parser.add_argument("--normalize-memory-sidecar", action="store_true", dest="normalize_memory_sidecar", help="Zbuduj lub zaktualizuj sidecar normalizacji pamiÄ™ci bez modyfikowania aktywnej bazy rozmĂłw.")
    parser.add_argument("--wake-state-status", action="store_true", dest="wake_state_status", help="PokaĹĽ status aktywnego wake_state z sidecara pamiÄ™ci.")
    parser.add_argument("--build-wake-state", action="store_true", dest="build_wake_state", help="Zbuduj wake_state z istniejÄ…cych rekordĂłw sidecara normalizacji.")
    parser.add_argument("--dedupe-memory-sidecar", action="store_true", dest="dedupe_memory_sidecar", help="Zbuduj warstwowe grupy duplikatĂłw w sidecarze bez kasowania rekordĂłw ĹşrĂłdĹ‚owych.")
    parser.add_argument("--dry-run", action="store_true", dest="dry_run", help="Tryb kontrolny dla operacji normalizacji/wake_state bez zapisu.")
    parser.add_argument("--normalization-limit", type=int, default=None, help="Opcjonalny limit rekordĂłw dla sidecara normalizacji, uĹĽywany gĹ‚Ăłwnie w testach i audytach.")
    parser.add_argument("--dedupe-min-group-size", type=int, default=2, help="Minimalny rozmiar grupy dla warstwowej deduplikacji sidecara.")
    parser.add_argument("--write-active-runtime-marker", action="store_true", dest="write_active_runtime_marker", help="Zapisz JAZN_ACTIVE_RUNTIME.json dla aktywnego folderu i cache rozpakowania.")
    parser.add_argument("--source-zip", type=Path, default=None, help="Opcjonalna Ĺ›cieĹĽka ZIP-a ĹşrĂłdĹ‚owego do porĂłwnania checksum w aktywnym cache.")
    parser.add_argument("--marker-output", type=Path, default=None, help="Opcjonalna Ĺ›cieĹĽka pliku JAZN_ACTIVE_RUNTIME.json.")
    parser.add_argument("--record-final-reply", action="store_true", dest="record_final_reply", help="Dopisz do ledgera finalnÄ… widocznÄ… odpowiedĹş ChatGPT dla podanego turn_id/trace_id/timestamp_header.")
    parser.add_argument("--turn-id", default=None, help="turn_id z cognitive_turn_envelope dla --record-final-reply.")
    parser.add_argument("--trace-id", default=None, help="trace_id z cognitive_turn_envelope dla --record-final-reply.")
    parser.add_argument("--timestamp-header", default=None, help="timestamp_header z cognitive_turn_envelope dla --record-final-reply.")
    parser.add_argument("--state-emoticon", default="đźŚż", help="Emotikon stanu uĹĽywany, jeĹ›li finalny tekst wymaga dopiÄ™cia timestampu.")
    parser.add_argument("--final-text-file", type=Path, default=None, help="Opcjonalny plik z finalnÄ… widocznÄ… odpowiedziÄ… do zapisania w ledgerze.")
    export_group = parser.add_mutually_exclusive_group()
    export_group.add_argument("--export-system", action="store_true", help="UtwĂłrz paczkÄ™ system-only bez memory/ i workspace_runtime/.")
    export_group.add_argument("--export-memory", action="store_true", help="UtwĂłrz paczkÄ™ memory-only z memory/ i workspace_runtime/.")
    export_group.add_argument("--export-full", action="store_true", help="UtwĂłrz peĹ‚nÄ… paczkÄ™ systemu wraz z pamiÄ™ciÄ….")
    export_group.add_argument("--export-nlp", action="store_true", help="UtwĂłrz paczkÄ™ NLP-resources-only bez pamiÄ™ci i bez ciÄ™ĹĽkich modeli.")
    export_group.add_argument("--export-github-source-safe", action="store_true", help="UtwĂłrz paczkÄ™ ĹşrĂłdĹ‚owÄ… bez surowej pamiÄ™ci i aktywnych baz SQLite.")
    parser.add_argument("--output", type=Path, default=None, help="Opcjonalna Ĺ›cieĹĽka ZIP dla eksportu.")
    parser.add_argument("message", nargs=argparse.REMAINDER, help="TreĹ›Ä‡ wiadomoĹ›ci dla runtime.")
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
        sys.stderr.write("Flaga --chat-jsonl zostaĹ‚a usuniÄ™ta z aktywnego CLI. UĹĽyj: python main.py --chat-gpt --session-id <id>\n")
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

    if ns.runtime_preview_output and not (ns.runtime_preview or ns.dev_preview):
        parser.error("--runtime-preview-output wymaga --runtime-preview albo --dev-preview")
    if ns.chat_gpt_final_only:
        ns.chat_gpt = True
    if ns.final_only and not ns.chat_gpt:
        parser.error("--final-only wymaga --chat-gpt albo uĹĽyj samodzielnego --chat-gpt-final-only")

    if ns.bridge_discovery:
        cfg = config or JaznConfig()
        print(json.dumps(discover_runtime_bridges(cfg), ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if ns.daemon_run:
        cfg = config or JaznConfig()
        return run_daemon(
            cfg,
            host=ns.daemon_host,
            port=ns.daemon_port,
            marker_output=ns.daemon_marker_output,
            heartbeat_interval=ns.daemon_heartbeat_interval,
        )

    if ns.daemon_start:
        cfg = config or JaznConfig()
        print(json.dumps(start_daemon(
            cfg,
            host=ns.daemon_host,
            port=ns.daemon_port,
            marker_output=ns.daemon_marker_output,
            heartbeat_interval=ns.daemon_heartbeat_interval,
            startup_timeout=ns.daemon_start_timeout,
        ), ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if ns.daemon_status:
        cfg = config or JaznConfig()
        print(json.dumps(status_daemon(
            cfg,
            host=ns.daemon_host,
            port=ns.daemon_port,
            marker_output=ns.daemon_marker_output,
        ), ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if ns.daemon_stop:
        cfg = config or JaznConfig()
        print(json.dumps(stop_daemon(
            cfg,
            host=ns.daemon_host,
            port=ns.daemon_port,
            marker_output=ns.daemon_marker_output,
        ), ensure_ascii=False, indent=2, sort_keys=True))
        return 0

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
            "truth_boundary": "To jest plan, kanoniczne trafienia plikĂłw i metadane trafieĹ„ conversation_archive/FTS, nie peĹ‚na rozmowna odpowiedĹş ani dowĂłd peĹ‚nego odczytu caĹ‚ej pamiÄ™ci.",
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
            "truth_boundary": "Raport i progress sÄ… artefaktem patcha. WĹ‚aĹ›ciwy runtime canon jest w plikach .py; lokalny prywatny extension .py wymaga recenzji przed commitem.",
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
                "truth_boundary": "Status providera mĂłwi tylko, czy lokalny adapter jest dostÄ™pny. Nie oznacza pobrania peĹ‚nego sĹ‚ownika ani peĹ‚nej dezambiguacji jÄ™zyka.",
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
                "truth_boundary": "Bootstrap instaluje providery i modele z Internetu lokalnie; patch nie vendoruje duĹĽych sĹ‚ownikĂłw ani modeli.",
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
            "truth_boundary": "To jest plan/link lookupu. Runtime nie twierdzi, ĹĽe pobraĹ‚ definicjÄ™ lub przykĹ‚ady bez realnego ĹĽÄ…dania HTTP i zapisu ĹşrĂłdĹ‚a.",
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
        payload = {"runtime_version": cfg.version, "model_adapter_status": build_model_adapter_status(cfg)}
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

    if ns.runtime_preview or ns.dev_preview:
        engine = JaznEngine(config)
        try:
            text = _message_from_remainder(ns.message)
            envelope = engine.process_turn(
                text,
                client_context={
                    "client": "chatgpt_runtime_preview" if ns.runtime_preview else "chatgpt_dev_preview",
                    "lifecycle": "one_shot_preview",
                    "preview_phase": "single_integrated_process_turn",
                    "session_id": ns.session_id,
                    "no_carryover": ns.no_carryover,
                    "terminal_mode": "compact" if ns.runtime_preview else "full_dev_payload",
                },
            )
            envelope_dict, runtime_truth_gate = apply_runtime_truth_gate(envelope.to_dict())
            cognitive_frame = envelope_dict.get("cognitive_frame") or {}
            runtime_text = envelope_dict.get("final_visible_text") or ""
            final_contract = envelope_dict.get("final_response_contract") or {}
            integrity = final_contract.get("final_visible_integrity") if isinstance(final_contract.get("final_visible_integrity"), dict) else {}
            dialogue_classifier = cognitive_frame.get("dialogue_intent_classifier") or envelope_dict.get("dialogue_intent_classifier") or {}
            route_trace = cognitive_frame.get("turn_route_trace") or (envelope_dict.get("conversation_decision") or {}).get("turn_route_trace") or {}
            conversation_decision = envelope_dict.get("conversation_decision") if isinstance(envelope_dict.get("conversation_decision"), dict) else {}
            payload = {
                "schema_version": schema_version("runtime_preview_full_payload"),
                "runtime_version": engine.config.version,
                "mode": "diagnostic_dev_preview_full_payload_single_process_turn_not_background_daemon",
                "turn_trace": envelope_dict.get("trace"),
                "final_visible_text": runtime_text,
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
                "turn_route_trace": route_trace,
                "final_response_contract": envelope_dict.get("final_response_contract"),
                "normal_response_blocked": envelope_dict.get("normal_response_blocked"),
                "runtime_response_status": envelope_dict.get("runtime_response_status"),
                "runtime_truth_gate": runtime_truth_gate,
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
                    "one_shot_or_chat_loop_limit": "--runtime-preview i --dev-preview są jednorazowymi wywołaniami; stałą pętlę daje dopiero python main.py --chat.",
                },
                "active_extraction_cache_status": build_active_runtime_status(engine.config.root),
                "startup_summary": build_startup_summary(engine.config),
                "free_dialogue_memory_nlp_bridge": build_startup_summary(engine.config),
                "truth_boundary": "--dev-preview wykonuje jedno zintegrowane wywołanie process_turn i pokazuje pełną kopertę techniczną. To nie jest widoczna odpowiedź Łatki dla użytkownika ani dowód procesu w tle.",
            }
            compact = {
                "schema_version": schema_version("runtime_preview_compact"),
                "runtime_version": engine.config.version,
                "mode": "runtime_preview_compact_not_user_visible_latka_reply",
                "final_visible_text": runtime_text,
                "runtime_route": final_contract.get("runtime_route") or conversation_decision.get("selected_route") or route_trace.get("selected_route"),
                "primary_intent": dialogue_classifier.get("primary_intent") or conversation_decision.get("detected_user_intent"),
                "diagnostic_request": dialogue_classifier.get("diagnostic_request"),
                "fallback_classification": final_contract.get("fallback_classification"),
                "runtime_answer_quality": final_contract.get("runtime_answer_quality"),
                "runtime_truth_gate": runtime_truth_gate,
                "timestamp_trusted": integrity.get("timestamp_trusted") if integrity else final_contract.get("timestamp_trusted"),
                "final_visible_integrity_valid": integrity.get("valid") if integrity else None,
                "normal_response_blocked": envelope_dict.get("normal_response_blocked"),
                "runtime_response_status": envelope_dict.get("runtime_response_status"),
                "full_payload_written_to": str(ns.runtime_preview_output) if ns.runtime_preview_output else None,
                "dev_preview_command": "python main.py --dev-preview <tekst>",
                "truth_boundary": "To jest krótki podgląd diagnostyczny jednej tury runtime. Nie traktuj samego --runtime-preview jako rozmowy z Łatką; do stałej rozmowy służy --chat, a pełny JSON techniczny jest w --dev-preview albo --runtime-preview-output.",
            }
            payload_json = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
            if ns.runtime_preview_output:
                ns.runtime_preview_output.parent.mkdir(parents=True, exist_ok=True)
                ns.runtime_preview_output.write_text(payload_json + "\n", encoding="utf-8")
            if ns.dev_preview and not ns.runtime_preview_output:
                print(payload_json)
            else:
                print(json.dumps(compact, ensure_ascii=False, indent=2, sort_keys=True))
        finally:
            engine.shutdown()
        return 0


    if ns.chat_gpt:
        cfg = config or JaznConfig()
        return run_jsonl_chat_bridge(
            config=cfg,
            session_id=ns.session_id,
            no_carryover=ns.no_carryover,
            command="--chat-gpt",
            require_openai_api_key=False,
            output_mode="final_visible_text" if (ns.chat_gpt_final_only or ns.final_only) else "jsonl",
        )

    if ns.chat_open_ai:
        cfg = config or JaznConfig()
        apply_openai_cli_settings(
            cfg,
            model=ns.openai_model,
            api_base=ns.openai_api_base,
            timeout_seconds=ns.openai_timeout,
            max_output_tokens=ns.openai_max_output_tokens,
        )
        return run_jsonl_chat_bridge(
            config=cfg,
            session_id=ns.session_id,
            no_carryover=ns.no_carryover,
            command="--chat-open-ai",
            require_openai_api_key=True,
        )

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
                envelope_dict, _runtime_truth_gate = apply_runtime_truth_gate(envelope.to_dict())
                print(envelope_dict.get("final_visible_text", ""))
        else:
            print(engine.bootstrap())
    finally:
        engine.shutdown()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        # Pozwala bezpiecznie ucinaÄ‡ dĹ‚ugie podglÄ…dy JSON przez `head`/pipe
        # bez faĹ‚szywego wraĹĽenia awarii runtime.
        try:
            sys.stdout.close()
        except Exception:
            pass
        raise SystemExit(0)
