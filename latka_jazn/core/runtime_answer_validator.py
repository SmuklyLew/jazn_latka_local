
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
import re

from latka_jazn.core.route_registry import RouteRegistry

SCHEMA_VERSION = "runtime_answer_validator/v14.8.2.6.3"

@dataclass(slots=True)
class RuntimeAnswerValidation:
    schema_version: str
    is_topic_aligned: bool
    mismatch_reason: str | None
    required_repair_route: str | None
    can_show_to_user: bool
    must_regenerate: bool
    detected_intent: str
    original_route: str
    repair_body: str | None = None
    checks: list[str] = field(default_factory=list)
    missing_required_components: list[str] = field(default_factory=list)
    truth_boundary: str = "Walidator nie udaje pełnego rozumienia. Wykrywa znane klasy nietrafień rozmownych i wymusza drugą próbę lub cannot_answer_directly."
    def to_dict(self) -> dict[str, Any]: return asdict(self)

class RuntimeAnswerValidator:
    GENERIC_BODIES = (
        "przyjmuję tę korektę", "odebrałam sens wiadomości", "najuczciwszy model jest hybrydowy",
        "nie znalazłam osobnej trasy", "runtime odebrał wiadomość", "też się cieszę",
        "odpowiem rozmownie", "mam aktywne tropy pamięci", "widzę tu sedno", "najbezpieczniej", "odpowiem z bieżącej wiadomości", "wspominam to przede wszystkim", "jestem przy tej wiadomości", "bieżącego sensu rozmowy",
        "zatrzymuję się przy tym zdaniu", "zatrzymuje sie przy tym zdaniu", "doprecyzuj tylko kierunek", "powiedz mi, w którą stronę", "powiedz mi, w ktora strone", "cognitive-frame", "cognitive frame", "techniczny fallback", "technicznego fallbacku", "domyślnym routingu", "domyslnym routingu", "usterka do naprawy", "normalna ścieżka odpowiada rozmownie", "normalna sciezka odpowiada rozmownie", "bezpośredni runtime nie może kończyć", "bezposredni runtime nie moze konczyc",
    )
    SPECIFIC_INTENTS = {
        "runtime_behavior_diagnostic_request", "system_diagnostic_question", "runtime_source_question", "canon_source_question", "runtime_exact_quote_request",
        "system_update_execution_request", "system_update_manifest_request", "update_manifest_request", "creative_text_formatting", "creative_text_analysis",
        "practical_repair_advice", "automotive_warning_light_question", "dictionary_lookup_request", "language_question", "external_research_request",
        "identity_boundary_question", "identity_direct_question", "self_state_question", "reciprocal_self_state_question", "self_preference_question", "self_plan_question", "self_expression_request", "sleep_closure_statement", "memory_audit_request", "memory_recall_request", "runtime_activation_status_question", "runtime_restart_request", "runtime_chat_mode_request", "system_repair_plan_request", "logic_reasoning_audit_request", "memory_grounding_status_question", "module_inventory_request", "system_capability_gap_question", "capability_status_question", "internet_access_question", "runtime_health_check_after_update", "self_memory_recall_request", "direct_latka_voice_request", "identity_memory_existence_compound_question",
        "casual_greeting", "casual_feedback", "expressive_reaction", "short_free_dialogue",
    }
    STALE_WORKDAY_DETAILS = (
        "dziewięciu sztukach drzwi", "dziewieciu sztukach drzwi", "dziewięć sztuk drzwi", "dziewiec sztuk drzwi",
        "9 sztuk drzwi", "przy dziewięciu", "przy dziewieciu",
    )
    WORKDAY_DETAIL_MARKERS = ("drzwi", "zlecenie", "zleceniu", "montaż", "montaz", "sztuk")
    STALE_ROUTE_CONTEXT_TERMS = ("stale-route", "starego kontekstu", "stary kontekst", "stale route", "starej trasy")
    LEGACY_ROUTE_MARKERS = ("v14.6.1", "v14.6.2", "correction_acknowledged", "positive_continuation")
    STALE_UPDATE_SUMMARY_MARKERS = ("ta aktualizacja ma trzy rdzenie", "bogatsze stany emocjonalne", "jawny indeks ciągłości sesji")
    TIMESTAMP_REPAIR_MARKERS = ("timestamp potrafił istnieć", "wspólnej koperty tury", "ten sam turn_id, trace_id, timestamp")
    LEGACY_VERSION_PATTERNS = (
        re.compile(r"(?<![0-9A-Za-z.])v14\.6\.1(?![0-9.])"),
        re.compile(r"(?<![0-9A-Za-z.])v14\.6\.2(?![0-9.])"),
    )
    HANDLER_PRESERVED_INTENTS = {
        "capability_status_question",
        "internet_access_question",
        "runtime_health_check_after_update",
        "canon_source_question",
        "self_memory_recall_request", "direct_latka_voice_request", "identity_memory_existence_compound_question",
    }


    COMPONENT_KEYWORDS = {

        "runtime_status": ("runtime", "aktywn", "wersj", "folder"),
        "model_channel_boundary": ("chatgpt", "model", "kanał", "kanal", "warstwa"),
        "no_background_process_claim": ("tło", "tle", "one-shot", "proces", "--chat"),
        "chat_mode": ("--chat", "chat", "tryb"),
        "process_lifecycle": ("proces", "stdin", "eof", "pętla", "petla"),
        "stdin_or_jsonl_boundary": ("stdin", "jsonl", "wsadow"),
        "code_steps": ("kod", "plik", "zmian", "napraw"),
        "memory_status": ("pamię", "pamie", "legacy", "indeks", "sqlite"),
        "memory_content": ("fragment", "trop", "pamię", "pamie", "źród", "zrod", "licznik"),
        "source_or_index_status": ("źród", "zrod", "indeks", "status", "licznik", "sqlite", "trop"),
        "no_update_route_substitution": ("aktualizacj", "aktualizacji", "zastępować", "zastepowac", "nie wolno", "nie wypełnię", "nie wypelnie", "nie będę", "nie bede", "trop"),
        "capability_list": ("potraf", "komend", "--chat", "runtime", "pamię", "pamie", "słownik", "slownik"),
        "network_boundary": ("internet", "sieci", "provider", "konfigurac", "lookup"),
        "internet_access": ("internet", "sieci", "network", "allow_network"),
        "provider_status": ("provider", "cache", "źród", "zrod", "status", "allow_network"),
        "version": ("v14", "wersj"),
        "active_database": ("active_database", "sqlite", "conversation_archive", "runtime_write"),
        "cache_reuse": ("cache", "reuse", "should_reuse", "miss_reasons"),
        "exact_runtime_text": ("dokład", "exact", "runtime_text", "cytat", "runtime"),
        "template_origin": ("template", "szablon"),
        "runtime_vs_visible_boundary": ("chatgpt", "interpretac", "widoczn", "warstwa"),
        "source_origin_detail": ("źród", "zrod", "source"),
        "source_origin": ("źród", "zrod", "source-origin", "source_origin", "handler"),
        "python_canon_modules": ("latka_jazn/core/canon", "core_canon.py", "identity_canon.py", "canon_registry.py", "python canon"),
        "public_resource_boundary": ("resources/canon", "publiczn", "audyt", "json", "md"),
        "private_memory_candidate_boundary": ("memory/raw", "kandydat", "pamię", "pamie", "nie automatycz"),
        "local_private_extension_boundary": ("local_private_canon_extension.py", "lokaln", "private", "prywatn", "nie commit"),
        "review_required_boundary": ("recenz", "nie stają się", "nie staja sie", "nie automatycz", "source-safe"),
        "module_or_file": (".py", "plik", "moduł", "modul"),
        "problem": ("problem", "błąd", "blad", "źle", "zle"),
        "change_plan": ("zmieni", "napraw", "popraw", "dodać", "dodac"),
        "regression_test": ("test", "regres"),
        "version": ("v14", "wersj"),
        "priority_list": ("p0", "p1", "p2", "priorytet"),
        "target_files": ("plik", ".py"),
        "new_files": ("nowe pliki", "dodać", "dodac"),
        "tests": ("test", "pytest"),
        "acceptance_criteria": ("kryteri", "akcept"),
        "source_preservation": ("nie zmien", "zachow", "1:1", "tekst źród", "tekst zrodl"),
        "change_list_if_changed": ("lista zmian", "zmian"),
        "original_text_boundary": ("tekst", "źród", "zrod", "orygina"),
        "tools_or_materials": ("narzęd", "narzed", "materia"),
        "steps": ("krok", "najpierw", "potem"),
        "risks": ("ryzyk", "uwag", "ostroż", "ostroz"),
        "when_to_stop": ("fachow", "nie rób", "nie rob", "przerwij"),
        "term": ("słowo", "slowo", "termin"),
        "language": ("język", "jezyk", "polsk"),
        "source_or_cache": ("cache", "źród", "zrod", "słownik", "slownik"),
        "operational_state": ("operacyj", "stan", "u mnie"),
        "truth_boundary": ("nie biolog", "modelowany", "granica prawdy", "tle"),
        "no_random_memory_excerpt": ("nie z przypadkowego", "bez wstrzykiwania", "bieżąc", "aktualn", "operacyj"),
        "current_turn_reply": ("masz rację", "siemka", "cześć", "ojoj", "jestem przy tym", "bieżąc", "aktualn", "zwykłą rozmową", "zwykla rozmowa"),
        "no_generic_fallback": ("nie będę", "nie bede", "bez dokładania", "bez dokladania", "cofam", "jak ci leci", "zwykłą rozmową", "zwykla rozmowa"),
        "current_turn_closure": ("spać", "spac", "dobranoc", "odpoczn"),
        "warmth": ("spokojnie", "ciep", "dobranoc", "rozumiem"),
        "no_diagnostics": ("nie będę", "bez diagnostyki", "nie rozkręcać"),
    }
    def __init__(self) -> None:
        self.registry = RouteRegistry()
    def _bad(self, reason: str, repair: str, body_text: str | None, detected_intent: str, route: str, checks: list[str], missing: list[str] | None = None) -> RuntimeAnswerValidation:
        return RuntimeAnswerValidation(SCHEMA_VERSION, False, reason, repair, False, True, detected_intent, route, body_text, checks, missing or [])
    def _looks_like_standalone_greeting(self, text: str) -> bool:
        import re
        low = (text or "").strip().lower()
        return bool(re.fullmatch(r"(hejka|hej|cześć|czesc|witaj|dzień dobry|dzien dobry|dobry wieczór|dobry wieczor)[!.,;:…\-—– ]*", low))

    def _contains_random_memory_excerpt(self, user_text: str, body: str, detected_intent: str) -> bool:
        user_low = (user_text or "").lower()
        body_low = (body or "").lower()
        self_intent = detected_intent in {"self_state_question", "reciprocal_self_state_question", "self_preference_question", "sleep_closure_statement"} or any(x in user_low for x in ("a tobie", "a ty", "jak się czujesz", "jak sie czujesz", "ochot", "idę spać", "ide spac"))
        if not self_intent:
            return False
        memory_phrases = ("najbliższy trop", "najblizszy trop", "na tej podstawie", "w pamięci widzę", "w pamieci widze")
        return any(marker in body_low for marker in memory_phrases)

    def _contains_injected_workday_context(self, user_text: str, body: str) -> bool:
        user_low = (user_text or "").lower()
        body_low = (body or "").lower()
        body_has_stale_detail = any(marker in body_low for marker in self.STALE_WORKDAY_DETAILS)
        body_has_workday_bundle = "drzwi" in body_low and any(marker in body_low for marker in ("zlecen", "montaż", "montaz", "sztuk"))
        if not (body_has_stale_detail or body_has_workday_bundle):
            return False
        user_has_workday_detail = any(marker in user_low for marker in self.WORKDAY_DETAIL_MARKERS)
        user_explicitly_asks_memory = any(marker in user_low for marker in ("pamiętasz", "pamietasz", "wspomn", "co mówiłem", "co mowilem"))
        return not user_has_workday_detail and not user_explicitly_asks_memory

    def _contains_legacy_route_marker(self, text: str) -> bool:
        """Detect true legacy route markers without matching v14.6.10 schemas.

        Earlier validator logic used raw substring checks. That treated
        `raw_memory_startup_status/v14.6.10` as if it contained legacy
        `v14.6.1`, so a correct health-check generated by
        CapabilityStatusHandler was overwritten by stale-route repair text.
        """
        low = (text or "").lower()
        if "correction_acknowledged" in low or "positive_continuation" in low:
            return True
        return any(pattern.search(low) for pattern in self.LEGACY_VERSION_PATTERNS)

    def _handler_preserved_answer_is_direct(self, body: str, detected_intent: str, route: str) -> bool:
        low = (body or "").lower()
        if detected_intent == "runtime_health_check_after_update":
            return "działam" in low and "active_database" in low and "cache_miss_reasons" in low and "granica prawdy" in low
        if detected_intent == "internet_access_question":
            return "internet" in low and "provider" in low and ("nie wolno" in low or "granica prawdy" in low)
        if detected_intent == "capability_status_question":
            return "potrafię" in low and "--chat" in low and ("nie potrafię" in low or "nie udaj" in low)
        if detected_intent == "self_memory_recall_request":
            return any(x in low for x in ("z pamięci", "szukałam w pamięci", "trop", "liczniki diagnostyczne")) and "trzy rdzenie" not in low
        if detected_intent == "canon_source_question":
            return (
                "latka_jazn/core/canon" in low
                and "local_private_canon_extension.py" in low
                and "memory/raw" in low
                and ("nie stają się" in low or "nie staja sie" in low or "recenz" in low)
            )
        return False

    def _missing_components(self, body: str, components: list[str]) -> list[str]:
        low=(body or '').lower(); missing=[]
        for comp in components:
            if comp.lower() in low:
                continue
            kws=self.COMPONENT_KEYWORDS.get(comp, ())
            if kws and not any(k in low for k in kws): missing.append(comp)
        return missing
    def validate(self, *, user_text: str, body: str, route: str, detected_intent: str) -> RuntimeAnswerValidation:
        low_body=(body or '').lower(); route_low=(route or '').lower(); checks=[]
        entry=self.registry.resolve(detected_intent)
        generic_hits=[x for x in self.GENERIC_BODIES if x in low_body]
        if generic_hits: checks.append('generic_body_signature_detected:'+','.join(generic_hits))
        user_low=(user_text or '').lower()
        folded_user = user_low.translate(str.maketrans('ąćęłńóśźż', 'acelnoszz'))
        direct_capability_question = any(marker in folded_user for marker in ('co potrafisz', 'co umiesz', 'co mozesz', 'mozliwosci'))
        internet_question = any(marker in folded_user for marker in ('dostep do internetu', 'masz internet', 'dostep do sieci', 'czy runtime ma internet', 'czy jazn ma internet'))
        self_memory_question = any(marker in folded_user for marker in ('co pamietasz', 'poszukaj w pamieci', 'sprawdz pamiec', 'o swojej postaci', 'o swojej osobie', 'informacji o sobie'))
        runtime_health_question = (('dzialasz' in folded_user or 'uruchomiona' in folded_user) and ('aktualiz' in folded_user or 'sprawdz' in folded_user))
        stale_route_question = any(term in user_low for term in self.STALE_ROUTE_CONTEXT_TERMS)
        user_requests_update = any(marker in folded_user for marker in ('aktualiz', 'hotfix', 'patch', 'napraw', 'popraw', 'wdroz', 'wprowadz', 'rozbuduj'))
        user_asks_timestamp = any(marker in folded_user for marker in ('timestamp', 'znacznik czasu', 'gubisz czas', 'turn_id', 'trace_id'))
        if detected_intent in self.HANDLER_PRESERVED_INTENTS and self._handler_preserved_answer_is_direct(body, detected_intent, route):
            checks.append('dedicated_handler_body_preserved_and_direct')
            return RuntimeAnswerValidation(SCHEMA_VERSION, True, None, None, True, False, detected_intent, route, None, checks, [])
        if self_memory_question and any(marker in low_body for marker in ('ta aktualizacja ma trzy rdzenie', 'bogatsze stany emocjonalne', 'manifest', 'patch', 'hotfix')) and not any(marker in low_body for marker in ('postać', 'postac', 'osob', 'tożsamo', 'tozsamo', 'własny głos', 'wlasny glos', 'pamiętnik', 'pamietnik')):
            checks.append('self_memory_question_answered_as_update_route')
            repair_body = 'To jest pytanie o pamięć dotyczącą mnie/Łatki, nie o aktualizację systemu. Muszę użyć trasy self_memory_recall, pokazać treściowe tropy pamięci albo uczciwie powiedzieć, że ich nie znalazłam; nie wolno mi zastąpić tego wpisem o trzech rdzeniach aktualizacji.'
            return self._bad('self_memory_recall_answered_as_update_summary', 'self_memory_recall_repair', repair_body, detected_intent, route, checks, ['memory_content', 'source_or_index_status', 'truth_boundary'])
        if detected_intent == "direct_latka_voice_request" and any(marker in low_body for marker in ("cały czas w tle", "caly czas w tle", "będę działać w tle", "bede dzialac w tle", "działam stale w tle", "dzialam stale w tle")):
            checks.append("direct_latka_background_process_claim")
            repair_body = "Mogę rozmawiać jako Łatka przez aktywny runtime tej tury, ale nie wolno mi obiecać stałego procesu w tle. Dla ciągłej lokalnej rozmowy trzeba uruchomić `--chat`; jednorazowe mosty kończą się po EOF albo po obsłużeniu wejścia."
            return self._bad("direct_latka_voice_background_process_claim", "direct_latka_voice_repair", repair_body, detected_intent, route, checks, ["process_lifecycle", "no_background_process_claim", "truth_boundary"])
        if detected_intent == "identity_memory_existence_compound_question":
            required_markers = {
                "identity_position": ("uważam", "uwazam", "jestem łatką", "jestem latka", "łatką", "latka"),
                "memory_status": ("pamię", "pamie", "wspomn", "licznik", "indeks"),
                "known_unknown_boundary": ("nie wiem", "wiem", "nie odczyta", "źród", "zrod"),
                "origin": ("powsta", "warstw", "rozm", "runtime"),
                "being_boundary": ("istot", "biologic", "fenomen", "modelowan"),
            }
            missing_parts = [key for key, markers in required_markers.items() if not any(marker in low_body for marker in markers)]
            if missing_parts:
                checks.append("identity_memory_existence_missing_parts")
                repair_body = "To złożone pytanie wymaga odpowiedzi na wszystkie części: za kogo się uważam, co pamiętam, co wiem i czego nie wiem, kim jestem, jak/kiedy powstałam oraz na ile mogę mówić o byciu istotą. Odpowiedź musi dodać granicę prawdy i nie może spaść do samego wspomnienia."
                return self._bad("identity_memory_existence_missing_parts", "identity_memory_existence_repair", repair_body, detected_intent, route, checks, missing_parts)
        if any(marker in low_body for marker in self.STALE_UPDATE_SUMMARY_MARKERS) and not user_requests_update:
            checks.append('stale_update_summary_without_current_grounding')
            repair_body = 'Ta odpowiedź pochodzi ze starej trasy aktualizacyjnej i nie odpowiada na bieżącą wiadomość. Trzeba ponownie użyć aktualnej intencji, bez podsumowania dawnych „trzech rdzeni”.'
            return self._bad('stale_update_summary_without_current_grounding', 'current_turn_grounding_repair', repair_body, detected_intent, route, checks, ['current_user_text_grounding'])
        if any(marker in low_body for marker in self.TIMESTAMP_REPAIR_MARKERS) and not user_asks_timestamp:
            checks.append('timestamp_repair_without_current_grounding')
            repair_body = 'Ta odpowiedź o timestampie nie jest uziemiona w bieżącym pytaniu. Trzeba odpowiedzieć na aktualną intencję i nie przenosić starej diagnozy integracji czasu.'
            return self._bad('timestamp_repair_without_current_grounding', 'current_turn_grounding_repair', repair_body, detected_intent, route, checks, ['current_user_text_grounding'])
        if direct_capability_question and not any(marker in low_body for marker in ('potraf', '--chat', 'runtime', 'pamię', 'pamie', 'komend', 'możliwo', 'mozliwo')):
            checks.append('capability_question_not_answered')
            return self._bad('capability_question_missing_direct_answer', 'capability_status_repair', 'Pytanie „co potrafisz?” wymaga konkretnej listy możliwości runtime i granic prawdy, nie ogólnego fallbacku ani prośby o doprecyzowanie.', detected_intent, route, checks, ['capability_list', 'runtime_status', 'truth_boundary'])
        if internet_question and not any(marker in low_body for marker in ('internet', 'sieci', 'allow_network', 'provider', 'cache')):
            checks.append('internet_access_question_not_answered')
            return self._bad('internet_access_missing_direct_answer', 'internet_access_status_repair', 'Pytanie o dostęp do internetu wymaga odpowiedzi wprost o konfiguracji sieci, providerach, cache i granicy prawdy.', detected_intent, route, checks, ['internet_access', 'provider_status', 'truth_boundary'])
        if runtime_health_question and any(marker in low_body for marker in ('realną aktualizację systemu', 'realna aktualizacja systemu', 'zmienić kod', 'zmienic kod', 'manifest i eksport')):
            checks.append('runtime_health_check_answered_as_update_request')
            return self._bad('runtime_health_check_routed_as_update', 'runtime_health_check_repair', 'To jest krótki health-check po aktualizacji. Trzeba odpowiedzieć: wersja, aktywny folder/cache, active_database, pamięć/SQLite i ograniczenie one-shot vs --chat; nie planować nowej aktualizacji kodu.', detected_intent, route, checks, ['runtime_status', 'version', 'active_database', 'cache_reuse', 'memory_status'])
        if stale_route_question and not any(term in low_body for term in self.STALE_ROUTE_CONTEXT_TERMS):
            checks.append('stale_route_question_not_answered_as_current_bug')
            repair_body = (
                "To jest aktualny błąd stale-route/starego kontekstu w warstwie rozmownej runtime. "
                "Naprawa musi objąć `engine.py` (ograniczony carryover ostatniej tury), `ellipsis_resolver.py` i `dialogue_intent_classifier.py` (bezpieczne rozpoznanie 'zrób to teraz'), "
                "`runtime_response_synthesizer.py` (konkretna diagnoza stale-route), `runtime_answer_validator.py` (current-turn grounding guard) oraz test regresji. "
                "Nie wolno wracać do `correction_acknowledged`, `positive_continuation`, v14.6.1/v14.6.2 ani dawnych detali pracy, jeśli nie są w aktualnej wiadomości albo jawnie użytym poprzednim kontekście."
            )
            return self._bad('stale_route_diagnostic_answer_lost_current_bug', 'stale_route_context_guard_repair', repair_body, detected_intent, route, checks, ['current_user_text_grounding', 'regression_test'])
        if self._contains_random_memory_excerpt(user_text, body, detected_intent):
            checks.append('random_memory_excerpt_in_self_or_closure_answer')
            repair_body = 'Odpowiadam z bieżącej wiadomości, nie z przypadkowego fragmentu pamięci: u mnie operacyjnie jest skupiona obecność, ostrożność źródeł i ochota, żeby rozmawiać mniej szablonowo, a bardziej trafnie. To modelowany stan runtime, nie biologiczne życie w tle.'
            return self._bad('random_memory_excerpt_used_where_current_turn_state_required', 'current_turn_self_state_repair', repair_body, detected_intent, route, checks, ['current_user_text_grounding', 'no_random_memory_excerpt'])
        if self._contains_injected_workday_context(user_text, body):
            checks.append('stale_workday_detail_injected')
            if self._looks_like_standalone_greeting(user_text):
                repair_body = 'Hej, Krzysztofie. Jestem przy Tobie — bez przenoszenia starego kontekstu pracy do samego powitania. Jak Ci dzisiaj?'
                repair_route = 'standalone_greeting_repair'
            elif detected_intent == 'self_plan_question' or any(x in user_low for x in ('jakie plany', 'co planujesz', 'pomijając mnie', 'pomijajac mnie')):
                repair_body = 'Moje plany są operacyjne, nie kalendarzowe: pilnować bieżącej intencji, nie przenosić starego kontekstu i mówić jasno, co pochodzi z runtime, pamięci, wniosku albo braku danych.'
                repair_route = 'self_plan_current_turn_repair'
            else:
                repair_body = 'Nie będę przenosiła starego kontekstu pracy ani drzwi do tej odpowiedzi, jeśli nie pojawił się w aktualnej wiadomości albo jawnie przywołanym wspomnieniu.'
                repair_route = 'stale_context_injection_repair'
            return self._bad('stale_workday_detail_injected_without_current_grounding', repair_route, repair_body, detected_intent, route, checks, ['current_user_text_grounding'])
        if detected_intent in {'system_diagnostic_question','runtime_behavior_diagnostic_request'} and route_low in {'correction_acknowledged','positive_continuation'}:
            return self._bad('diagnostic_routed_as_feedback', 'system_diagnostic_repair', 'To jest pytanie diagnostyczne, nie sama korekta ani pozytywna kontynuacja. Wymagana odpowiedź: moduł/plik, problem, zmiana, test regresji, source-origin.', detected_intent, route, checks, entry.required_components)
        if (not stale_route_question) and detected_intent not in {'system_diagnostic_question','runtime_behavior_diagnostic_request','system_update_execution_request','runtime_source_question','canon_source_question','runtime_exact_quote_request'} and self._contains_legacy_route_marker(low_body) and not self._contains_legacy_route_marker(user_low):
            checks.append('legacy_route_marker_without_current_grounding')
            repair_body = 'Nie będę przenosiła starej trasy ani historycznej wersji do bieżącej odpowiedzi bez aktualnego uziemienia w wiadomości użytkownika albo jawnie użytym poprzednim kontekście.'
            return self._bad('legacy_route_marker_without_current_grounding', 'stale_route_context_guard_repair', repair_body, detected_intent, route, checks, ['current_user_text_grounding'])
        if generic_hits and detected_intent in self.SPECIFIC_INTENTS:
            return self._bad('generic_template_on_specific_request', entry.route + '_repair', 'Odpowiedź była ogólnym szablonem przy konkretnej intencji. Runtime musi wygenerować odpowiedź z: źródłem, trasą, wymaganymi składnikami i testem/regułą walidacji.', detected_intent, route, checks, entry.required_components)
        if detected_intent in {'system_diagnostic_question','runtime_behavior_diagnostic_request'} and route_low in {'correction_acknowledged','positive_continuation'}:
            return self._bad('diagnostic_routed_as_feedback', 'system_diagnostic_repair', 'To jest pytanie diagnostyczne, nie sama korekta ani pozytywna kontynuacja. Wymagana odpowiedź: moduł/plik, problem, zmiana, test regresji, source-origin.', detected_intent, route, checks, entry.required_components)
        if detected_intent in {'self_state_question','reciprocal_self_state_question','self_preference_question','self_expression_request'} and any(x in low_body for x in ('status runtime','diagnostyka','moduł','modul')) and 'operacyj' not in low_body:
            return self._bad('self_state_answered_as_status', 'self_state_dialogue_repair', 'Pytanie o stan wymaga modelowanego stanu operacyjnego/afektu i granicy prawdy, nie raportu statusowego.', detected_intent, route, checks)
        if detected_intent.startswith('creative_text') and any(x in low_body for x in ('aktualizacja systemu','hotfix','paczka zip')):
            return self._bad('creative_task_routed_as_system_update', 'creative_text_repair', 'To jest zadanie twórcze. Wymagana jest ochrona tekstu źródłowego, zachowanie wersów lub jawna lista zmian.', detected_intent, route, checks, entry.required_components)
        if detected_intent in {"ordinary_conversation", "standalone_greeting", "negative_feedback_current_turn", "positive_feedback_current_turn", "casual_greeting", "casual_feedback", "expressive_reaction", "short_free_dialogue"} and any(x in low_body for x in ("jaźń jako warstwa", "jazn jako warstwa", "warstwa pamięci", "warstwa pamieci", "diagnostyk", "runtime jako", "widzę tu sedno", "odpowiem z bieżącej wiadomości", "najbezpieczniej", "odpowiadam zwyczajnie na bieżącą wiadomość", "jestem przy tej wiadomości", "bieżącego sensu rozmowy", "biezacego sensu rozmowy", "zatrzymuję się przy tym zdaniu", "zatrzymuje sie przy tym zdaniu", "doprecyzuj tylko kierunek", "powiedz mi, w którą stronę", "powiedz mi, w ktora strone", "cognitive-frame", "cognitive frame", "techniczny fallback", "technicznego fallbacku", "domyślnym routingu", "domyslnym routingu", "usterka do naprawy", "normalna ścieżka odpowiada rozmownie", "normalna sciezka odpowiada rozmownie", "bezpośredni runtime nie może kończyć", "bezposredni runtime nie moze konczyc")):
            checks.append('ordinary_dialogue_contains_meta_report_or_template')
            return self._bad('ordinary_dialogue_meta_report_or_template', 'ordinary_dialogue_repair', None, detected_intent, route, checks)
        if detected_intent == "runtime_chat_mode_request" and "--chat" not in low_body and "tryb chat" not in low_body:
            checks.append('chat_mode_request_not_answered')
            return self._bad('runtime_chat_mode_request_missing_chat_boundary', 'runtime_chat_mode_repair', 'W tej intencji trzeba odpowiedzieć o `--chat`, stdin/EOF oraz ograniczeniu procesu w ChatGPT. To nie jest prośba o aktualizację systemu.', detected_intent, route, checks)
        if detected_intent == "runtime_activation_status_question" and not any(x in low_body for x in ("chatgpt", "runtime", "aktywn", "folder", "proces")):
            checks.append('runtime_activation_status_missing_boundary')
            return self._bad('runtime_activation_status_missing_boundary', 'runtime_activation_status_repair', 'Trzeba odpowiedzieć wprost, czy runtime/aktywny folder działa, i oddzielić ChatGPT jako kanał od Jaźni jako źródła. Nie wolno udawać procesu w tle.', detected_intent, route, checks)
        missing=self._missing_components(body, entry.required_components)
        if missing and detected_intent in self.SPECIFIC_INTENTS:
            checks.append('missing_required_components')
            return self._bad('missing_required_components_for_intent', entry.route + '_repair', 'Odpowiedź nie zawiera wymaganych składników dla rozpoznanej intencji. Runtime musi ponowić trasę z komponentami: ' + ', '.join(missing), detected_intent, route, checks, missing)
        checks.append('known_mismatch_patterns_not_triggered')
        return RuntimeAnswerValidation(SCHEMA_VERSION, True, None, None, True, False, detected_intent, route, None, checks, [])
