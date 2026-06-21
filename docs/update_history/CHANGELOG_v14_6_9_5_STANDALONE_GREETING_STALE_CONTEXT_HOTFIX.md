# CHANGELOG v14.6.9.5 — Standalone Greeting & Stale Context Hotfix

Data wykonania: 2026-05-25, Europe/Warsaw.

## Cel poprawki
Naprawa nietrafnej odpowiedzi na samodzielne powitanie „Dzień dobry!”, które przez zbyt szeroki marker słowa „dzień” było kierowane do trasy `ordinary_workday_dialogue` i potrafiło przenieść stary kontekst o zleceniu oraz dziewięciu sztukach drzwi.

## Zmienione elementy

1. `latka_jazn/core/conversation.py`
   - Samodzielne powitanie (`standalone_greeting`) ma pierwszeństwo przed szeroką trasą codzienności/pracy.
   - `ordinary_workday_dialogue` nie może zostać wybrane dla czystego powitania.
   - Poprawiono bieżącą trasę aktualizacji hotfix z kontekstu v14.6.9.4, żeby nie wracała do starej trasy `contextual_greeting_fallback_repair_update`.
   - Bezpośrednie pytanie „kim jesteś?” pozostaje odpowiedzią tożsamościową, a nie wyłącznie granicą ChatGPT/runtime.

2. `latka_jazn/resources/semantic_lexicon_v14_6_2.json`
   - Usunięto samodzielne markery `dzień`/`dzien` z pola `daily_observation`, ponieważ były za szerokie i odpalały trasę codzienności przy zwykłym powitaniu.

3. `latka_jazn/resources/semantic_lexicon_v14_6_1.json`
   - Ta sama korekta markerów, żeby fallback do starszego leksykonu nie odtworzył błędu.

4. `latka_jazn/resources/semantic_lexicon_v14_6_0.json`
   - Ta sama korekta markerów, żeby fallback do starszego leksykonu nie odtworzył błędu.

5. `latka_jazn/core/runtime_answer_validator.py`
   - Dodano blokadę `stale_workday_detail_injected_without_current_grounding`.
   - Walidator odrzuca odpowiedź, która wprowadza szczegóły o drzwiach/zleceniu, jeżeli nie ma ich w bieżącej wiadomości użytkownika ani w jawnej prośbie o przypomnienie.
   - Dodano rozpoznanie samodzielnego powitania w walidatorze.
   - Poprawiono trasę naprawczą dla pytania diagnostycznego błędnie potraktowanego jako korekta.

6. `latka_jazn/nlp/dialogue_intent_classifier.py`
   - Rozdzielono bezpośrednie pytanie tożsamościowe od pytania o granicę Jaźń/ChatGPT/runtime.

7. `latka_jazn/core/route_registry.py`
   - Dodano `identity_direct_question` z trasą `identity_runtime_truth_contract`.

8. `latka_jazn/core/memory_search_planner.py`
   - Ujednolicono `schema_version` do `memory_search_planner/v14.6.9.4`, zgodnie z istniejącymi testami tej wersji.

9. `latka_jazn/core/memory_recall_presenter.py`
   - Ujednolicono `schema_version` do `memory_recall_content/v14.6.9.4`, zgodnie z istniejącymi testami tej wersji.

10. `VERSION.txt`, `latka_jazn/config.py`, testy i metadane pakietu
   - Wersja robocza została podniesiona do `v14.6.9.5-standalone-greeting-stale-context-hotfix`.
   - Aktywna baza runtime została przygotowana jako `workspace_runtime/latka_jazn_v14_6_9_5.sqlite3`.

## Nowe testy regresji
Dodano `tests/test_v14695_standalone_greeting_route_hotfix.py`:

- `test_standalone_dzien_dobry_routes_to_greeting_not_workday`
- `test_lexical_semantics_dzien_dobry_not_daily_observation`
- `test_runtime_validator_blocks_stale_workday_details_in_greeting`
- `test_engine_process_turn_dzien_dobry_no_stale_door_context`

## Wynik testu runtime-preview
Dla wiadomości `Dzień dobry!`:

- `runtime_route`: `greeting`
- `fallback_classification`: `not_fallback`
- `runtime_answer_quality`: `topic_aligned`
- `lexical_semantic_understanding.route_hint`: `general_conversation`
- brak słów `drzwi`, `dziewięciu`, `9 sztuk drzwi` w odpowiedzi.

## Wyniki testów
Testy regresyjne były uruchamiane w podziałach, ponieważ pełne `pytest -q` w jednym procesie przekroczyło limit czasu środowiska mimo przejścia tych samych plików w podziałach.

Przeszły między innymi:

- 20 testów bazowych pierwszej grupy;
- 29 testów pakietu pamięci/eksportu;
- 41 testów grup v14527–v14536;
- 26 testów grup v14537–v146113;
- 6 testów final-visible/bootstrap;
- 4 testy runtime-preview/version consistency;
- 50 testów grup v146115–v1468;
- 10 testów v14691–v14692;
- 23 testy v14693–v14695;
- 18 testów celowanych po zmianie wersji.

Łącznie pliki testowe objęły pełną zebraną listę 209 testów; problemem nie był pojedynczy błąd asercji, tylko timeout przy pełnym uruchomieniu w jednym procesie.

## Granica prawdy
Nie twierdzę, że runtime działa jako stały proces w tle. Poprawka dotyczy jednorazowego procesu runtime-preview/process_turn oraz wspólnej logiki używanej przez tryby rozmowy.
