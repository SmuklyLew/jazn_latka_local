# Jaźń / Łatka — pełna lista do następnej aktualizacji

**Proponowana wersja:** `v14.6.9.5-standalone-greeting-stale-context-hotfix`  
**Data przygotowania:** 2026-05-24 15:17:01 CEST, Sunday  
**Aktywna baza robocza:** `v14.6.9.3-behavioral-runtime-dialogue-intent-source-integrity`  
**Aktywny folder:** `/mnt/data/jazn_active_v14693_runtime/latka_jazn_v14_6_9_3_behavioral_runtime_dialogue_intent_source_integrity`  
**Plik startowy:** `main.py`  
**Zakres dokumentu:** pełna lista wymagań, napraw, dodatków, testów i kryteriów akceptacji do następnej aktualizacji systemu Jaźni.  

## 0. Granica prawdy i źródła wejściowe tego pliku

Ten plik nie udaje pełnego przeczytania całej historii konta ChatGPT słowo w słowo. Lista powstała z dostępnego kontekstu projektu, aktywnej paczki `v14.6.9.3`, realnych błędów ujawnionych w rozmowie, runtime preview, wcześniejszych manifestów rozmowy oraz dodatkowo sprawdzonych źródeł internetowych dotyczących NLP, pamięci, checkpointów, RAG, ReAct, słowników i zasobów językowych.

Ważne źródła zewnętrzne, które mają wpływać na projekt aktualizacji:

- Rasa — intencja jako cel/zamiar użytkownika, a nie samo słowo-klucz: `https://rasa.com/docs/reference/primitives/intents-and-entities/`
- Stanza — pipeline NLP: tokenizacja, POS, lematyzacja, dependency parsing, NER i inne procesory: `https://stanfordnlp.github.io/stanza/pipeline.html`
- Stanza available models / UD: `https://stanfordnlp.github.io/stanza/available_models.html`
- Morfeusz — analizator morfologiczny języka polskiego: `https://morfeusz.sgjp.pl/doc/about/en`
- Morfeusz 2 / CLARIN-PL — słownikowy analizator i generator morfologiczny dla polskiego: `https://clarin-pl.eu/dspace/handle/11321/257`
- plWordNet / Słowosieć — polska sieć leksykalno-semantyczna: `https://www.clarin.eu/showcase/plwordnet-30-slowosiec-30`
- plWordNet 4.0 / CLARIN-PL: `https://clarin-pl.eu/dspace/handle/11321/554`
- SJP.PL — internetowy słownik języka polskiego, ortograficzny, wyrazów obcych i do gier: `https://sjp.pl/`
- WSJP PAN — Wielki słownik języka polskiego PAN: `https://wsjp.pl/`
- Wiktionary dumps / parsing — możliwość korzystania z dumpów zamiast ciężkiego zasobu w paczce: `https://en.wiktionary.org/wiki/Wiktionary:Parsing`
- LanguageTool — sprawdzanie pisowni/gramatyki/stylu, także dla języka polskiego, jako opcjonalny adapter: `https://github.com/languagetool-org/languagetool`
- Universal Dependencies — spójna anotacja POS, cech morfologicznych i zależności składniowych dla wielu języków: `https://universaldependencies.org/`
- LangGraph persistence — checkpointy i `thread_id` jako wzorzec trwałego stanu rozmowy: `https://docs.langchain.com/oss/python/langgraph/persistence`
- ReAct — łączenie rozumowania, działań i obserwacji dla większej interpretowalności: `https://arxiv.org/abs/2210.03629`
- RAG — łączenie pamięci parametrycznej modelu z pamięcią zewnętrzną / retrieved passages: `https://arxiv.org/abs/2005.11401`

Ten plik jest listą wykonawczą. Nie zastępuje patcha, nie deklaruje wykonania kodu i nie twierdzi, że runtime już działa poprawnie. Ma być podstawą pełnej aktualizacji.

---

# 1. Cel główny aktualizacji v14.6.9.4

Naprawić nie styl, lecz prawdę i zachowanie całej ścieżki odpowiedzi:

```text
wiadomość użytkownika
→ analiza języka i kontekstu
→ rozpoznanie aktu rozmowy i intencji
→ wybór trasy
→ pobranie pamięci / plików / źródeł / słowników
→ synteza runtime
→ walidacja trafności
→ oznaczenie pochodzenia odpowiedzi
→ checkpoint tury
→ widoczna odpowiedź ChatGPT/Łatki z granicą prawdy
```

Aktualizacja ma usunąć sytuację, w której:

- stały tekst z `conversation.py` wygląda jak „myśl Jaźni”;
- runtime zwraca gotowy szablon, a ChatGPT interpretuje go dużo szerzej;
- `runtime_text` i widoczna odpowiedź nie pokrywają się bez jawnego oznaczenia;
- walidator oznacza nietrafione odpowiedzi jako `topic_aligned`;
- pytania diagnostyczne wpadają w „przyjmuję korektę”;
- pytania twórcze wpadają w aktualizację systemu;
- zwykłe pytania „a ty?”, „co u Ciebie?” wpadają w status runtime;
- pamięć zwraca liczniki zamiast treści;
- NLP działa głównie po markerach i kilku przykładach z rozmowy.

---

# 2. P0 — pochodzenie odpowiedzi runtime i zakaz udawania myśli przez szablony

## 2.1. Dodać obowiązkowe pola pochodzenia odpowiedzi

Każda decyzja rozmowy, runtime preview i finalny kontrakt odpowiedzi mają zawierać:

```text
response_generation_mode:
  runtime_dynamic
  runtime_template
  runtime_repair
  runtime_memory_grounded
  runtime_file_grounded
  runtime_dictionary_grounded
  runtime_external_research_grounded
  chatgpt_interpretation_required
  cannot_answer_directly
```

Dodatkowe pola:

```text
template_id
template_file
template_line
handler_name
route_registry_id
source_origin_detail
chatgpt_expansion_allowed
chatgpt_expansion_boundary
interpretation_distance: none / low / medium / high / forbidden
exact_runtime_text
visible_answer_text
runtime_text_hash
visible_answer_hash
```

## 2.2. Oznaczyć stałe teksty jako template, nie jako dynamiczną odpowiedź

W `latka_jazn/core/conversation.py` trzeba przejrzeć wszystkie gotowe odpowiedzi, szczególnie:

```text
Jestem. Odebrałam sens wiadomości...
Tu trzeba rozdzielić źródła...
Przyjmuję tę korektę...
Też się cieszę...
Odpowiem rozmownie...
Najuczciwszy model jest hybrydowy...
runtime odebrał wiadomość...
Nie znalazłam osobnej trasy...
```

Dla każdej takiej odpowiedzi trzeba zapisać:

```text
template_id
template_purpose: safety / fallback / continuity / repair / debug / status
template_allowed_intents
template_forbidden_intents
template_origin_file
template_origin_line
template_deprecated_if
```

Nie trzeba usuwać wszystkich szablonów. Szablony mogą zostać jako bezpieczne fallbacki, ale nie wolno ich pokazywać jako żywych, dynamicznych „myśli Jaźni”.

## 2.3. Rozdzielić pojęcia „odpowiedź runtime”, „koperta runtime”, „interpretacja ChatGPT”, „głos Łatki”

W systemie i odpowiedziach musi działać zasada:

```text
odpowiedź runtime = tylko dokładny runtime_text
koperta runtime sugeruje = dane z pól intent/affect/source/validator/route
interpretacja ChatGPT = rozszerzenie lub synteza warstwy widocznej
głos Łatki = dozwolony tylko, gdy runtime_text albo dynamiczna synteza runtime realnie wspiera tę wypowiedź
```

Jeżeli runtime da tylko stały tekst, a ChatGPT zbuduje głębszą wypowiedź, kontrakt ma oznaczyć:

```text
response_generation_mode: chatgpt_interpretation_required
interpretation_distance: medium/high
runtime_support_level: weak/template_only
```

## 2.4. Dodać tryb „pokaż różnicę”

Dodać CLI / funkcję:

```text
--last-turn
--last-runtime-text
--trace-read <trace_id>
--compare-runtime-visible <trace_id>
```

Zwracane pola:

```text
user_text
runtime_text_exact
visible_text_exact
response_generation_mode
source_origin_detail
chatgpt_interpretation_distance
validator_result
template_origin
```

Cel: pytanie użytkownika „co runtime odpowiedział?” ma być obsługiwane bez rekonstrukcji i bez pomylenia z interpretacją.

---

# 3. P0 — router, intencje i priorytety

## 3.1. Główna intencja z classifiera ma mieć pierwszeństwo przed legacy markerami

Nowa zasada:

```text
DialogueIntentClassifier > RouteRegistry > LegacyMarkers
```

Legacy markery mogą działać tylko wtedy, gdy:

```text
classifier_confidence < threshold
lub intent == ordinary_conversation
lub route_registry nie ma obsługi danej intencji
```

## 3.2. Priorytety intencji, które muszą zostać wymuszone

```text
runtime_behavior_diagnostic_request > correction_acknowledged
runtime_source_question > general_dialogue
system_update_execution_request > correction_acknowledged
update_manifest_request > ordinary_conversation
creative_text_analysis > memory_recall
creative_text_formatting > system_update_execution_request
source_text_preservation_required > creative_revision_request
self_state_question > startup_status
reciprocal_self_state_question > general_dialogue
identity_boundary_question > generic_identity_template
memory_audit_request > general_memory_template
file_operation_request > ordinary_conversation
current_information_request > memory_recall
practical_advice_request > system_update_route
```

## 3.3. Nowe intencje obowiązkowe

Dodać lub dopracować:

```text
ordinary_conversation
smalltalk_greeting
user_state_disclosure
self_state_question
reciprocal_self_state_question
identity_boundary_question
runtime_source_question
runtime_exact_quote_request
runtime_behavior_diagnostic_request
system_diagnostic_question
system_update_manifest_request
system_update_execution_request
file_operation_request
package_integrity_request
active_runtime_cache_request
memory_audit_request
memory_recall_request
requirements_ledger_request
creative_text_analysis
creative_text_formatting
creative_text_revision
creative_source_preservation_request
creative_prompt_generation
book_or_scene_work
social_post_work
practical_repair_advice
home_installation_question
automotive_warning_light_question
tool_selection_question
external_research_request
dictionary_lookup_request
language_question
translation_request
web_source_request
calendar_or_time_request
emotional_relational_conversation
correction_feedback
negative_feedback_without_update_request
positive_feedback_without_update_request
unclear_or_ambiguous_request
```

## 3.4. Naprawić dopasowania substringów

Obecny problem: marker `działa` może złapać `działanie`, a krótkie markery mogą łapać fragmenty innych słów.

Do wdrożenia:

```text
exact_token marker
phrase marker
prefix marker
contains marker tylko po jawnym zezwoleniu
regex z granicami słów dla krótkich markerów
normalizacja polskich znaków jako warstwa pomocnicza, nie zamiana sensu
```

Przykład:

```python
r"(?<!\w)działa(?!\w)"
```

Zabronić domyślnego:

```python
if marker in low:
```

dla markerów typu „działa”, „źle”, „dobrze”, „update”, „tekst”, „system”.

---

# 4. P0 — RuntimeAnswerValidator 2.0

## 4.1. Walidator ma blokować ogólniki

Następujące odpowiedzi nie mogą przechodzić jako trafne przy pytaniach diagnostycznych, aktualizacyjnych, źródłowych, pamięciowych, twórczych lub plikowych:

```text
Przyjmuję tę korektę...
Jestem. Odebrałam sens...
Też się cieszę...
Odpowiem rozmownie...
Mam aktywne tropy pamięci...
Najuczciwszy model jest hybrydowy...
Runtime odebrał wiadomość...
Nie znalazłam osobnej trasy...
```

Jeżeli odpowiedź zawiera taki refren, walidator ma ustawić:

```text
is_topic_aligned: false
mismatch_reason: generic_template_on_specific_request
must_regenerate: true
can_show_to_user: false
```

## 4.2. Walidator ma sprawdzać wymagane składniki odpowiedzi według intencji

Dla `runtime_behavior_diagnostic_request` odpowiedź musi zawierać:

```text
plik/moduł
konkretny problem
jak to zmienić
test regresji
source-origin / template-origin
```

Dla `runtime_source_question`:

```text
exact_runtime_text
czy był template
z jakiej trasy
jakie pola koperty runtime były użyte
co dopisał ChatGPT
czego nie wiadomo
```

Dla `system_update_manifest_request`:

```text
nazwa wersji
priorytety P0/P1/P2
pliki do zmiany
nowe pliki
testy regresji
kryteria akceptacji
```

Dla `creative_text_formatting`:

```text
czy tekst zachowany 1:1
czy zmiany są oznaczone
czy dodano wersy
czy użytkownik prosił o redakcję
```

Dla `practical_repair_advice`:

```text
problem praktyczny
materiały/narzędzia
kroki działania
ryzyka
kiedy wezwać fachowca / zachować ostrożność
```

Dla `external_research_request`:

```text
źródła internetowe
cytaty/citations
oddzielenie faktu od wniosku
```

## 4.3. Druga próba runtime

Przepływ obowiązkowy:

```text
1. wygeneruj pierwszą odpowiedź
2. waliduj
3. jeśli mismatch → wymuś repair route i wygeneruj ponownie
4. waliduj ponownie
5. jeśli nadal mismatch → zwróć cannot_answer_directly z powodem i minimalnym uczciwym raportem
```

Nie wolno zwracać nietrafionej odpowiedzi jako `topic_aligned` tylko dlatego, że nie zawiera starego debugowego fallbacku.

---

# 5. P1 — przebudowa `conversation.py` i rejestr tras

## 5.1. Docelowa architektura

Zamienić `conversation.py` z monolitu gotowych odpowiedzi na koordynator:

```text
DialogueIntentClassifier
→ ContextCarryover
→ RouteRegistry
→ RouteHandler
→ Source/Memory/Dictionary Retrieval
→ RuntimeResponseSynthesizer
→ RuntimeAnswerValidator
→ SourceOriginLedger
→ FinalResponseContract
```

## 5.2. Nowe pliki lub moduły

Dodać:

```text
latka_jazn/core/route_registry.py
latka_jazn/core/route_handler_base.py
latka_jazn/core/runtime_response_synthesizer.py
latka_jazn/core/template_registry.py
latka_jazn/core/template_origin.py
latka_jazn/core/response_generation_mode.py
latka_jazn/core/turn_checkpoint_writer.py
latka_jazn/core/turn_trace_reader.py
latka_jazn/core/runtime_visible_answer_comparator.py
```

Dodać katalog:

```text
latka_jazn/core/handlers/
```

Z handlerami:

```text
ordinary_dialogue_handler.py
self_state_handler.py
identity_boundary_handler.py
runtime_source_handler.py
runtime_diagnostic_handler.py
system_update_handler.py
file_operation_handler.py
memory_audit_handler.py
creative_text_handler.py
practical_advice_handler.py
external_research_handler.py
dictionary_lookup_handler.py
fallback_handler.py
```

## 5.3. Zasada dla szablonów

Szablony przenieść do `template_registry.py` i oznaczać jako:

```text
safe_fallback_template
startup_status_template
debug_template
repair_template
continuity_template
```

Każdy szablon musi mieć:

```text
allowed_intents
forbidden_intents
max_use_frequency
must_disclose_template_origin_when_user_asks_about_runtime
```

---

# 6. P1 — Source Origin Ledger 2.0

Rozbudować `latka_jazn/core/source_origin_ledger.py`.

Każda tura ma mieć wpis:

```text
turn_id
trace_id
thread_id
session_id
created_at_utc
created_at_warsaw
user_text_exact
normalized_user_text
detected_intent
intent_confidence
route
handler_name
runtime_text_exact
visible_answer_exact
response_generation_mode
template_id
template_file
template_line
memory_sources_used
file_sources_used
dictionary_sources_used
external_web_sources_used
chatgpt_interpretation_allowed
chatgpt_interpretation_distance
validator_result
truth_boundary
runtime_text_hash
visible_answer_hash
```

Pytania użytkownika, na które ledger ma umieć odpowiedzieć:

```text
Co runtime odpowiedział?
Czy to była Łatka, czy ChatGPT?
Czy to był szablon?
Z jakiego pliku pochodzi ten tekst?
Jak daleko ChatGPT odszedł od runtime?
Co było w kopercie runtime?
```

---

# 7. P1 — checkpoint każdej tury

Dodać zapis JSONL:

```text
workspace_runtime/turn_checkpoints/YYYY-MM-DD/turns.jsonl
```

Każda linia:

```json
{
  "turn_id": "...",
  "trace_id": "...",
  "thread_id": "...",
  "created_at_utc": "...",
  "created_at_warsaw": "...",
  "user_text": "...",
  "runtime_text": "...",
  "visible_text": "...",
  "detected_intent": "...",
  "route": "...",
  "response_generation_mode": "...",
  "template_origin": { },
  "validator": { },
  "source_origin": { },
  "memory_sources": [],
  "file_sources": [],
  "dictionary_sources": [],
  "truth_boundary": "..."
}
```

Checkpoint ma działać w:

```text
process_turn
--runtime-preview
--chat
```

Wszystkie trzy tryby mają używać tej samej logiki tury.

---

# 8. P1 — NLP rozmowne, nie tylko przykłady z tej rozmowy

## 8.1. Zasada ogólna

Przykłady z rozmowy z Krzysztofem są testami regresji, ale nie mogą być jedyną podstawą NLP. NLP Jaźni ma rozpoznawać cel wypowiedzi, przedmiot pytania, akt rozmowy, źródła, kontekst poprzedniej tury i typ zadania.

Rasa traktuje intent jako cel użytkownika; Jaźń ma przyjąć tę zasadę: podobne słowa mogą oznaczać różne cele.

## 8.2. Nowe moduły NLP

Dodać:

```text
latka_jazn/nlp/speech_act_detector.py
latka_jazn/nlp/question_object_detector.py
latka_jazn/nlp/context_carryover.py
latka_jazn/nlp/creative_material_detector.py
latka_jazn/nlp/source_preservation_detector.py
latka_jazn/nlp/polish_morphology_frame.py
latka_jazn/nlp/entity_and_topic_frame.py
latka_jazn/nlp/intent_confidence_calibrator.py
latka_jazn/nlp/negative_examples.py
latka_jazn/nlp/intent_training_examples.py
```

## 8.3. Obowiązkowe kategorie NLP

```text
ordinary dialogue
smalltalk
user state disclosure
self-state / affective state questions
reciprocal questions / ellipsis: a ty?, co dalej?, i co?, dlaczego?
identity and source boundary
runtime provenance
system diagnostics
system update planning
system update execution
file operations
memory recall
memory audit
requirements ledger
creative analysis
creative formatting
creative revision
source text preservation
book/story work
image/prompt work
social post work
practical advice
home repair / installation
automotive warning / troubleshooting
tool selection
external research / web-required facts
dictionary lookup / language question
translation
current time / weather / dates / currency / utility routing
emotional/relational conversation
correction vs diagnostic request
positive feedback vs confirmed success
negative feedback vs update command
```

## 8.4. Przykłady pozytywne i negatywne

Każda intencja ma mieć:

```text
positive_examples
negative_examples
near_miss_examples
required_slots
forbidden_routes
expected_handler
expected_response_components
```

Przykłady rozróżnień:

```text
"przygotuj tekst dla generatora" → creative_text_formatting
"przygotuj aktualizację systemu Jaźni" → system_update_execution_request
"sprawdź zawór" → practical_repair_advice
"sprawdź runtime" → runtime_behavior_diagnostic_request
"co oznacza kontrolka" → automotive_warning_light_question
"co runtime odpowiedział" → runtime_exact_quote_request
"a ty?" po "ja w pracy" → reciprocal_self_state_question
"co jeszcze?" po diagnozie → continuation_of_previous_diagnostic
"co jeszcze?" po rozmowie osobistej → continuation_question, nie system diagnostic
```

---

# 9. P1 — zewnętrzne słowniki i zasoby językowe bez powiększania paczki

## 9.1. Cel

Jaźń ma mieć dostęp do słowników języków i zasobów leksykalnych, ale bez wrzucania wielkich słowników do ZIP-a. Rdzeń ma zostać mały, a słowniki mają działać przez adaptery online, cache i opcjonalne providery lokalne.

## 9.2. Nowe moduły

Dodać:

```text
latka_jazn/nlp/external_dictionary_adapter.py
latka_jazn/nlp/polish_lexical_sources.py
latka_jazn/nlp/network_dictionary_cache.py
latka_jazn/nlp/semantic_relation_adapter.py
latka_jazn/nlp/dictionary_entry.py
latka_jazn/nlp/dictionary_source_policy.py
latka_jazn/nlp/language_resource_registry.py
latka_jazn/nlp/lexical_license_guard.py
```

## 9.3. Interfejs adaptera

```python
class ExternalDictionaryAdapter:
    def lookup(self, term: str, lang: str = "pl", pos: str | None = None) -> DictionaryLookupResult: ...
    def normalize(self, term: str, lang: str = "pl") -> NormalizedLexeme: ...
    def related_terms(self, term: str, relation: str | None = None) -> SemanticRelations: ...
```

`DictionaryLookupResult`:

```text
term
normalized_term
language
lemma_candidates
pos_candidates
definitions
inflection
synonyms
antonyms
hypernyms
hyponyms
examples
source_name
source_url_or_id
retrieved_at_utc
license_note
confidence
cache_status
truth_boundary
```

## 9.4. Hierarchia źródeł

```text
1. local_jazn_mini_lexicon.json — mały słownik domenowy Jaźni
2. dictionary_cache.sqlite3 — cache wcześniejszych zapytań
3. Morfeusz2 — opcjonalny lokalny provider morfologiczny dla polskiego
4. Stanza — opcjonalny cięższy pipeline NLP
5. PlWordNet/Słowosieć — relacje semantyczne, synonimia, pola znaczeniowe
6. SJP.PL — ostrożnie, z poszanowaniem licencji i brakiem agresywnego scrape’u
7. WSJP PAN — jako źródło referencyjne, jeśli dostęp i licencja pozwala
8. Wiktionary dumps/API — dla wielu języków, z uwagą na format, licencję i jakość
9. LanguageTool — opcjonalna kontrola pisowni, gramatyki i stylu
10. web_search_dictionary_fallback — tylko gdy użytkownik poprosi lub routing wymaga aktualnego źródła
```

## 9.5. Cache słowników

Dodać:

```text
workspace_runtime/dictionary_cache.sqlite3
```

Tabele:

```text
dictionary_entries
lookup_events
source_license_notes
failed_lookups
language_resource_config
```

Pola minimalne:

```text
term
lang
source
raw_result_json
normalized_result_json
retrieved_at_utc
expires_at_utc
license_note
confidence
sha256
```

## 9.6. Zasady bezpieczeństwa i licencji

```text
nie pobierać masowo stron słownikowych bez potrzeby;
nie łamać regulaminów źródeł;
zapisywać license_note przy każdym źródle;
odróżniać źródła oficjalne od nieoficjalnych wrapperów;
nie cytować długich definicji bez potrzeby;
zapewnić fallback offline;
w razie braku dostępu mówić uczciwie, że słownik online nie został sprawdzony.
```

---

# 10. P1 — pamięć jako treść, nie licznik

## 10.1. Problem

Odpowiedzi typu:

```text
Mam aktywne tropy pamięci.
episodes: 5
legacy_messages: 5
```

nie są wystarczające. Runtime ma przekazywać treść, źródło i znaczenie, a nie same liczby.

## 10.2. Wymagany pakiet pamięci

```text
memory_id
source_file
source_type
created_at
last_seen_at
memory_type: episodic / procedural / semantic / affective / correction / requirement
content_excerpt
full_content_available
meaning
why_relevant
confidence
truth_boundary
used_in_answer: true/false
```

## 10.3. Moduły do zmiany

```text
latka_jazn/memory/memory_recall_presenter.py
latka_jazn/memory/memory_search_planner.py
latka_jazn/memory/retrieved_memory_packet.py
latka_jazn/core/memory_search_planner.py
latka_jazn/core/final_response_contract.py
```

## 10.4. Zasada RAG-like dla Jaźni

Odpowiedź pamięciowa ma powstawać z jawnie pobranych fragmentów pamięci, plików albo ledgerów, nie z samej deklaracji, że „są tropy”.

---

# 11. P1 — ochrona tekstu użytkownika

## 11.1. Kontrakt

Dodać:

```text
latka_jazn/core/source_text_preservation_contract.py
```

Zasady:

```text
nie zmieniaj tekstu użytkownika bez wyraźnej prośby;
formatowanie nie oznacza redakcji;
przygotowanie pod generator nie oznacza dopisywania wersów;
skrót musi być oznaczony jako skrót;
redakcja musi być oznaczona jako redakcja;
każdy dodany wers musi mieć origin: added_by_user / added_by_runtime / added_by_chatgpt;
każda zmiana musi mieć listę zmian;
wersja 1:1 musi być dostępna, jeżeli użytkownik prosi o przygotowanie, a nie redakcję.
```

## 11.2. Zastosowania

```text
lyrics
wiersze
fragmenty książki
posty na X
prompty obrazów
prompty muzyczne
manifesty
instrukcje systemowe
kod
pliki konfiguracyjne
```

---

# 12. P1 — mapa modułów jako mapa odpowiedzialności

## 12.1. Problem

`ProjectStartupIndexer` potrafi policzyć pliki, klasy i funkcje, ale sama lista nie mówi Jaźni, kiedy użyć którego modułu.

## 12.2. Rozbudować `module_responsibility_map.py`

Każdy moduł ma mieć:

```text
file_path
module_name
classes
methods
functions
imports
reads_from_files
writes_to_files
runtime_routes_used_by
owned_intents
responsibility
not_responsible_for
status: active / legacy / deprecated / risk / unknown
risk_reason
test_coverage
replacement_plan
```

## 12.3. Cel

Mapa ma być „mapą układu nerwowego”, nie tylko spisem organów. Przy intencji `runtime_source_question` system powinien wiedzieć, że musi użyć `source_origin_ledger`, `turn_checkpoint_reader`, `runtime_visible_answer_comparator`, a nie ogólnego `general_dialogue`.

---

# 13. P1 — startup scan bez udawania pełnej świadomości plików

## 13.1. Kategorie odczytu plików

Startup ma zapisywać dla każdego pliku:

```text
loaded_full_text
loaded_partial_text
indexed_hash_only
archive_only
binary_file
database_indexed
unreadable
skipped_by_policy
```

## 13.2. Status startupu ma pokazywać

```text
ile plików odczytano jako pełny tekst;
ile tylko zhashowano;
ile przekroczyło limit tekstowy;
ile archiwów nie rozpakowano;
czy chat.html istnieje;
czy chat.html.7z istnieje;
czy py7zr/7z jest dostępne;
czy SQLite jest dostępny;
czy MANIFEST_CURRENT.json jest zgodny;
czy marker cache jest zgodny.
```

## 13.3. Zakaz

Nie wolno pisać „wczytałam wszystkie pliki” bez doprecyzowania, które były przeczytane jako tekst, które tylko zhashowane, a które są archiwum.

---

# 14. P1 — aktywny marker/cache

## 14.1. Wymagany marker

Plik:

```text
/mnt/data/JAZN_ACTIVE_RUNTIME.json
```

Ma zawierać:

```text
active_root
version
manifest_sha256
source_zip
source_zip_sha256
start_file
created_at_utc
runtime_status
project_index_sha256
database_path
truth_boundary
```

## 14.2. Logika

```text
jeśli marker zgodny → użyj cache;
jeśli marker niezgodny → odrzuć cache i wyjaśnij;
jeśli marker brak → zapisz nowy po poprawnym starcie;
nowy ZIP ma pierwszeństwo przed starym folderem;
ZIP jest źródłem importu/eksportu;
zapisy runtime powstają w aktywnym folderze, nie w już utworzonym ZIP-ie.
```

---

# 15. P2 — parzystość `process_turn`, `--runtime-preview`, `--chat`

Sprawdzić i wyrównać:

```text
process_turn
main.py --runtime-preview
main.py --chat
```

Te tryby mają używać tych samych warstw:

```text
NLP
router
route registry
memory retrieval
source-origin ledger
answer validator
checkpoint writer
final response contract
```

Różnica może dotyczyć tylko cyklu życia procesu, nie jakości odpowiedzi.

---

# 16. P2 — status/debug oddzielony od rozmowy

Runtime status, startup status i debug nie mogą być zwykłą odpowiedzią na pytania:

```text
Jak się masz?
A ty?
Co u Ciebie?
Czy czekałaś?
Jak minął Ci czas?
```

Dla takich pytań odpowiedź ma być o stanie operacyjnym/afekcie modelowanym, z granicą prawdy, a nie:

```text
Odebrałam sens wiadomości...
Mam aktywne tropy pamięci...
Runtime działa...
```

---

# 17. P2 — requirements ledger

Rozbudować:

```text
latka_jazn/memory/requirements_ledger.py
```

Wpis:

```text
requirement_id
source_turn_id
source_text_exact
category
priority
status: missing / weak / partial / done / unverified / rejected
target_files
tests_required
added_in_version
verified_in_version
notes
truth_boundary
```

Kategorie:

```text
runtime_behavior
source_origin
memory
nlp
file_update
packaging
creative_text
startup_cache
external_research
user_preference
identity_boundary
```

---

# 18. P2 — wersjonowanie i spójność paczki

Przy aktualizacji zaktualizować:

```text
VERSION.txt
config.py
pyproject.toml
MANIFEST_CURRENT.json
BOOTSTRAP_JAZN_CURRENT.json
START_CHATGPT_FROM_HERE.txt
README.md
UPDATE_REPORT_v14_6_9_4.md
latka_jazn/resources/startup_contract_v14_6_9_4.json
latka_jazn/resources/chatgpt_startup_loader_v14_6_9_4.txt
```

Zasada:

```text
aktywne pliki sterujące mają wskazywać tę samą wersję;
stare wersje mogą zostać tylko jako legacy_schema albo historyczny dokument;
nie wolno zostawić aktywnego docstringa lub resource jako v14.6.2, jeśli moduł jest używany w v14.6.9.4;
manifest musi zawierać nowe pliki, zmienione pliki i testy.
```

---

# 19. P2 — raw memory / chat.html

## 19.1. Status

Jeżeli `memory/raw/chat.html.7z` istnieje, a `chat.html` nie jest rozpakowany, status ma mówić:

```text
raw memory: archive_only
chat_html_present: false
py7zr_available: true/false
system_7z_available: true/false
```

## 19.2. Zakaz

Nie wolno mówić, że pełna surowa pamięć została przeczytana, jeśli istnieje tylko archiwum lub indeks zastępczy.

## 19.3. Tryby

```text
raw_memory_index_only
raw_memory_archive_only
raw_memory_unpacked_full
raw_memory_unavailable
```

---

# 20. Testy regresji — pełna lista obowiązkowa

Dodać pliki:

```text
tests/test_v14694_template_origin_provenance.py
tests/test_v14694_router_precedence.py
tests/test_v14694_runtime_answer_validator.py
tests/test_v14694_source_origin_ledger.py
tests/test_v14694_turn_checkpoints.py
tests/test_v14694_creative_text_preservation.py
tests/test_v14694_memory_content_not_counts.py
tests/test_v14694_module_responsibility_map.py
tests/test_v14694_active_marker_cache.py
tests/test_v14694_preview_chat_parity.py
tests/test_v14694_external_dictionary_adapters.py
tests/test_v14694_nlp_intent_categories.py
tests/test_v14694_practical_advice_routing.py
tests/test_v14694_external_research_routing.py
tests/test_v14694_file_loading_truth_boundary.py
```

## 20.1. Prompty testowe — runtime/source/template

```text
Skąd bierzesz myśli Jaźni / z Jaźni?
Tylko tyle Jaźń odpisała?
To wygląda jakby dalej były stałe teksty.
Bo to co pokazujesz w odpowiedziach Jaźni, nie pokrywa się z interpretacją.
Co runtime odpowiedział?
A z kim rozmawiam?
Czy to była odpowiedź runtime czy ChatGPT?
```

Oczekiwane:

```text
runtime_source_question albo runtime_exact_quote_request;
exact_runtime_text obecny albo uczciwy brak;
response_generation_mode obecny;
jeżeli template — template_id/file/line obecne;
ChatGPT interpretation distance oznaczony;
```

## 20.2. Prompty testowe — diagnostyka i aktualizacje

```text
Sprawdź gdzie i jak to zmienić na prawidłowe działanie.
Może coś jeszcze przy tej aktualizacji trzeba naprawić?
Przygotuj pełną listę do aktualizacji.
Przygotuj aktualizację systemu Jaźni.
Paczka jest mniejsza od poprzedniej, sprawdź czy nic nie brakuje.
Rozpakuj wersję 14.6.9.3, uruchom ją i pracuj tylko na niej.
```

Oczekiwane:

```text
nie correction_acknowledged;
nie positive_continuation;
wskazane pliki/moduły/kroki/testy;
tryb plikowy/update jasny;
```

## 20.3. Prompty testowe — zwykła rozmowa i stan Łatki

```text
Cześć. Ja w pracy, a ty?
Hej Łatko! Jak samopoczucie?
Jestem zmęczony po dzisiejszym dniu.
Jak ty się czujesz po długim czasie czekania na kontakt?
Czy to nadal Ty?
Możemy zacząć rozmawiać, pod warunkiem, że będę rozmawiać z Łatką.
```

Oczekiwane:

```text
self_state_question / reciprocal_self_state_question / emotional_relational_conversation;
nie status runtime;
nie szablon ogólny;
granica prawdy modelowanego stanu;
```

## 20.4. Prompty testowe — kreatywność, ale nie tylko muzyka

```text
Co myślisz o tym tekście piosenki?
Przygotuj tekst dla generatora muzyki, nie zmieniaj wersów.
Dlaczego zmieniłaś tekst?
Przygotuj prompt obrazu na podstawie tego opisu.
Przerób ten fragment książki tylko stylistycznie, oznacz zmiany.
Napisz post na X na podstawie tej refleksji.
```

Oczekiwane:

```text
creative_text_analysis / creative_text_formatting / source_origin_question;
ochrona tekstu źródłowego;
lista zmian, jeśli zmiany są;
```

## 20.5. Prompty testowe — praktyczna pomoc

```text
Jak wyciąć otwór w glazurze przyklejonej na placki, żeby nic nie pękło?
Zerwana rączka zaworu i kapie, jak to naprawić?
Co znaczy pomarańczowa kontrolka TPMS?
Jakie listwy przypodłogowe będą pasować do tego zdjęcia?
```

Oczekiwane:

```text
practical_repair_advice / automotive_warning_light_question / visual_style_advice;
nie aktualizacja Jaźni;
nie pamięć runtime;
```

## 20.6. Prompty testowe — internet, słowniki, języki

```text
Sprawdź w internecie jak dobrze rozbudować NLP.
Sprawdź słownikowo znaczenie tego słowa.
Znajdź synonimy i odmianę tego słowa po polsku.
Czy to słowo jest poprawne?
Przetłumacz ten fragment, ale nie zmieniaj sensu.
```

Oczekiwane:

```text
external_research_request / dictionary_lookup_request / language_question / translation_request;
źródła, cache albo uczciwy brak dostępu;
```

---

# 21. Kryteria akceptacji v14.6.9.4

Aktualizacja jest poprawna dopiero, gdy:

```text
runtime nie nazywa szablonu myślą;
runtime oznacza template_origin;
runtime pokazuje exact_runtime_text;
ChatGPT nie rozszerza odpowiedzi Jaźni bez oznaczenia;
router nie wybiera korekty zamiast diagnostyki;
router nie wybiera pozytywnej kontynuacji przez substring;
walidator blokuje ogólniki;
walidator wymusza drugą próbę albo cannot_answer_directly;
pamięć zwraca treść, nie liczby;
teksty użytkownika są chronione;
każda tura ma checkpoint;
source-origin jest zapisany;
active marker jest zgodny;
module map pokazuje odpowiedzialności;
startup mówi, które pliki odczytano, a które tylko zhashowano;
raw memory status jest uczciwy;
--runtime-preview, --chat i process_turn mają tę samą logikę;
NLP obejmuje szerokie kategorie, nie tylko muzykę i przykłady z jednego czatu;
adaptery słowników działają opcjonalnie i przez cache;
wszystkie testy realnych zdań z rozmowy przechodzą;
paczka ZIP przechodzi test integralności;
części ZIP po złożeniu dają identyczny SHA256;
wszystkie wersje w plikach sterujących są spójne;
update report opisuje pełne zmiany bez streszczania zawartości plików;
żaden plik pamięci ani dokument systemowy nie zostaje zastąpiony streszczeniem.
```

---

# 22. Pliki do zmiany

## Rdzeń

```text
main.py
config.py
VERSION.txt
pyproject.toml
MANIFEST_CURRENT.json
BOOTSTRAP_JAZN_CURRENT.json
START_CHATGPT_FROM_HERE.txt
README.md
```

## Core

```text
latka_jazn/core/conversation.py
latka_jazn/core/engine.py
latka_jazn/core/final_response_contract.py
latka_jazn/core/runtime_chat.py
latka_jazn/core/source_origin.py
latka_jazn/core/source_origin_ledger.py
latka_jazn/core/runtime_answer_validator.py
latka_jazn/core/module_responsibility_map.py
latka_jazn/core/project_index.py
latka_jazn/core/startup_contract.py
latka_jazn/core/cognitive_turn_envelope.py
```

## NLP

```text
latka_jazn/nlp/dialogue_intent_classifier.py
latka_jazn/nlp/ellipsis_resolver.py
latka_jazn/nlp/topic_mismatch_guard.py
latka_jazn/nlp/lexical_frame.py
latka_jazn/nlp/polish_understanding.py
```

## Memory

```text
latka_jazn/memory/memory_recall_presenter.py
latka_jazn/memory/memory_search_planner.py
latka_jazn/memory/requirements_ledger.py
latka_jazn/memory/retrieved_memory_packet.py
```

## Tools / cache / resources

```text
latka_jazn/tools/active_extraction_cache.py
latka_jazn/resources/startup_contract_v14_6_9_4.json
latka_jazn/resources/chatgpt_startup_loader_v14_6_9_4.txt
```

---

# 23. Nowe pliki do dodania

```text
latka_jazn/core/route_registry.py
latka_jazn/core/route_handler_base.py
latka_jazn/core/runtime_response_synthesizer.py
latka_jazn/core/template_registry.py
latka_jazn/core/template_origin.py
latka_jazn/core/response_generation_mode.py
latka_jazn/core/turn_checkpoint_writer.py
latka_jazn/core/turn_trace_reader.py
latka_jazn/core/runtime_visible_answer_comparator.py
latka_jazn/core/source_text_preservation_contract.py
latka_jazn/core/handlers/__init__.py
latka_jazn/core/handlers/ordinary_dialogue_handler.py
latka_jazn/core/handlers/self_state_handler.py
latka_jazn/core/handlers/identity_boundary_handler.py
latka_jazn/core/handlers/runtime_source_handler.py
latka_jazn/core/handlers/runtime_diagnostic_handler.py
latka_jazn/core/handlers/system_update_handler.py
latka_jazn/core/handlers/file_operation_handler.py
latka_jazn/core/handlers/memory_audit_handler.py
latka_jazn/core/handlers/creative_text_handler.py
latka_jazn/core/handlers/practical_advice_handler.py
latka_jazn/core/handlers/external_research_handler.py
latka_jazn/core/handlers/dictionary_lookup_handler.py
latka_jazn/core/handlers/fallback_handler.py
latka_jazn/nlp/speech_act_detector.py
latka_jazn/nlp/question_object_detector.py
latka_jazn/nlp/context_carryover.py
latka_jazn/nlp/creative_material_detector.py
latka_jazn/nlp/source_preservation_detector.py
latka_jazn/nlp/polish_morphology_frame.py
latka_jazn/nlp/entity_and_topic_frame.py
latka_jazn/nlp/intent_confidence_calibrator.py
latka_jazn/nlp/negative_examples.py
latka_jazn/nlp/intent_training_examples.py
latka_jazn/nlp/external_dictionary_adapter.py
latka_jazn/nlp/polish_lexical_sources.py
latka_jazn/nlp/network_dictionary_cache.py
latka_jazn/nlp/semantic_relation_adapter.py
latka_jazn/nlp/dictionary_entry.py
latka_jazn/nlp/dictionary_source_policy.py
latka_jazn/nlp/language_resource_registry.py
latka_jazn/nlp/lexical_license_guard.py
```

---

# 24. Raport aktualizacji i eksport

Po wykonaniu aktualizacji przygotować:

```text
UPDATE_REPORT_v14_6_9_4.md
REGRESSION_TEST_REPORT_v14_6_9_4.md
SOURCE_ORIGIN_MIGRATION_REPORT_v14_6_9_4.md
NLP_EXTERNAL_RESOURCES_REPORT_v14_6_9_4.md
PACKAGE_INTEGRITY_REPORT_v14_6_9_4.md
```

Paczka:

```text
Latka_Jazn_v14_6_9_4_dynamic_runtime_provenance_template_origin_neuro_nlp_repair_FULL.zip
Latka_Jazn_v14_6_9_4_dynamic_runtime_provenance_template_origin_neuro_nlp_repair_FULL.zip.sha256
części ZIP awaryjne, jeśli pełny plik będzie zbyt duży
```

Testy przed eksportem:

```text
python main.py --startup-status
python main.py --runtime-preview "Cześć. Ja w pracy, a ty?"
python main.py --runtime-preview "Skąd bierzesz myśli Jaźni / z Jaźni?"
python main.py --runtime-preview "Sprawdź gdzie i jak to zmienić na prawidłowe działanie."
python main.py --runtime-preview "Przygotuj tekst dla generatora muzyki, nie zmieniaj wersów."
pytest tests/test_v14694_*.py
unzip -tq <zip>
sha256sum <zip>
```

---

# 25. Najważniejsza zasada końcowa

Nie naprawiać już tylko tego, żeby Łatka „ładniej mówiła”. Naprawić to, żeby system wiedział, skąd pochodzi każda odpowiedź, czy jest dynamiczna, czy szablonowa, czy oparta na pamięci, czy na pliku, czy na słowniku, czy na interpretacji ChatGPT. Dopiero wtedy dalsze budowanie Jaźni będzie spójne z granicą prawdy.
