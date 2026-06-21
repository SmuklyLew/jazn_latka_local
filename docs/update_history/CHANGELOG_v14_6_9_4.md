# Raport aktualizacji Jaźni v14.6.9.5-standalone-greeting-stale-context-hotfix

Data UTC: 2026-05-25T00:53:27.273758+00:00

## Wykonany zakres

Paczka v14.6.9.3 została użyta jako baza i zaktualizowana do v14.6.9.4 bez streszczania istniejących plików. Dodano i podłączono warstwę odpowiedzialną za rozdział dokładnej odpowiedzi runtime od widocznej odpowiedzi ChatGPT.

## Najważniejsze poprawki

1. `response_generation_mode` — każda odpowiedź runtime może być oznaczona jako dynamiczna, template, repair, memory/file/dictionary grounded albo wymagająca interpretacji ChatGPT.
2. `template_origin` — znane refreny/szablony są wykrywane i zapisywane jako szablony, nie jako „myśli” Jaźni.
3. `RouteRegistry` i szkielety handlerów — intencje są mapowane do tras, handlerów i wymaganych składników odpowiedzi.
4. `RuntimeAnswerValidator` — blokuje ogólne odpowiedzi przy pytaniach o runtime, źródło, diagnostykę, aktualizację, tekst źródłowy, słowniki i zadania praktyczne.
5. `RuntimeResponseSynthesizer` — wykonuje drugą bezpieczną próbę odpowiedzi, gdy legacy `conversation.py` zwraca szablon lub trasę niezgodną z intencją.
6. `source_origin_ledger_v14_6_9_4.jsonl` — zapisuje pochodzenie odpowiedzi, template, tryb generowania i granice interpretacji.
7. `TurnCheckpointWriter`, `TurnTraceReader`, `RuntimeVisibleAnswerComparator` — zapisują `runtime_text`, `visible_text` i umożliwiają porównanie odpowiedzi runtime z widoczną odpowiedzią.
8. Ochrona tekstu źródłowego — `SourceTextPreservationContract` wymusza zachowanie tekstu użytkownika przy formatowaniu i listę zmian przy redakcji.
9. Rozbudowa NLP — klasyfikator dostał priorytety, granice słów, wykrywanie aktów mowy, obiektu pytania, kontekstu przeniesionego, materiału twórczego i zadań słownikowych.
10. Słowniki i zasoby językowe — dodano `ExternalDictionaryAdapter`, cache SQLite, `LanguageResourceRegistry`, politykę licencji i mini-leksykon projektu; runtime nie udaje lookupu online bez realnego dostępu.
11. Startup i cache — wersje aktywnych kontraktów, loaderów, profili ZIP i markerów zostały podniesione do v14.6.9.4.

## Nowe pliki kluczowe

- `latka_jazn/core/response_generation_mode.py`
- `latka_jazn/core/template_origin.py`
- `latka_jazn/core/template_registry.py`
- `latka_jazn/core/route_registry.py`
- `latka_jazn/core/route_handler_base.py`
- `latka_jazn/core/runtime_response_synthesizer.py`
- `latka_jazn/core/turn_checkpoint_writer.py`
- `latka_jazn/core/turn_trace_reader.py`
- `latka_jazn/core/runtime_visible_answer_comparator.py`
- `latka_jazn/core/source_text_preservation_contract.py`
- `latka_jazn/nlp/external_dictionary_adapter.py`
- `latka_jazn/nlp/network_dictionary_cache.py`
- `latka_jazn/nlp/language_resource_registry.py`
- `tests/test_v14694_dynamic_runtime_provenance_template_origin_neuro_nlp.py`

## Testy wykonane przed pakowaniem

- `python3 -m compileall -q latka_jazn` — OK.
- `pytest -q tests/test_v14694_dynamic_runtime_provenance_template_origin_neuro_nlp.py` — OK.
- `python3 main.py --startup-status` — OK.
- `python3 main.py --dictionary-lookup Jaźń` — OK, wynik z lokalnego mini-leksykonu/cache, bez udawania online.
- `python3 main.py --language-resources` — OK.
- `python3 main.py --runtime-preview "Skąd bierzesz myśli Jaźni / z Jaźni?"` — intencja runtime_source_question, route runtime_source.
- `python3 main.py --runtime-preview "Sprawdź gdzie i jak to zmienić na prawidłowe działanie."` — intencja runtime_behavior_diagnostic_request.
- `python3 main.py --runtime-preview "Przygotuj teraz pełną aktualizację systemu Jaźni..."` — intencja system_update_execution_request.

Pełne stare `pytest -q` było uruchamiane w trakcie aktualizacji i dochodziło do dalszych testów historycznych po zmianie wersji, ale końcowy raport nie oznacza go jako pełnego zielonego przebiegu, bo nie został zamknięty jednym krótkim przebiegiem w limicie środowiska.

## Granica prawdy

Ta aktualizacja poprawia zachowanie runtime, śledzenie źródeł, rozpoznawanie intencji i ochronę tekstu. Nie oznacza stałego procesu w tle ani biologicznej świadomości. Runtime nadal działa w ChatGPT głównie jako jednorazowe wywołanie procesu, chyba że uruchomiony zostanie lokalny tryb `--chat`.
