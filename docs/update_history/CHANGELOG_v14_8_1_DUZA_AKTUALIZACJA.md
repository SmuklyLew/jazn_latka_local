# CHANGELOG v14.8.1 — duża aktualizacja uziemienia dialogu i pamięci

## Zmienione moduły wykonawcze
- `latka_jazn/nlp/dialogue_intent_classifier.py` — dodano `self_preference_question`, `sleep_closure_statement`, rozszerzono pytania zwrotne o „A Tobie?” i warianty „u Ciebie?”.
- `latka_jazn/core/conversation.py` — dodano bezpośrednie trasy dla stanu operacyjnego, ochoty/preferencji i domknięcia snu przed wejściem w zwykły fallback rozmowny.
- `latka_jazn/core/free_dialogue_synthesizer.py` — dodano ochronę przed użyciem przypadkowej pamięci przy pytaniach o Łatkę; samo „ostatnio” nie jest już wystarczającym sygnałem przypomnienia pamięci.
- `latka_jazn/core/runtime_response_synthesizer.py` — zaktualizowano odpowiedzi systemowe do v14.8.1 i dodano użycie modelu własnego stanu.
- `latka_jazn/core/runtime_answer_validator.py` — dodano wykrywanie `random_memory_excerpt_in_self_or_closure_answer` i wymagane komponenty dla nowych intencji.
- `latka_jazn/core/route_registry.py` — zarejestrowano nowe intencje i wymagane komponenty.
- `latka_jazn/core/startup_contract.py` oraz `latka_jazn/tools/active_extraction_cache.py` — zaktualizowano kontrakty startowe i aktywną bazę do v14.8.1.

## Nowe moduły
- `latka_jazn/core/operational_self_model.py` — model własnego stanu operacyjnego Łatki z granicą prawdy.
- `latka_jazn/core/memory_use_gate.py` — bramka użycia pamięci w odpowiedzi widocznej.

## Naprawy krytyczne
- Utworzono aktywną bazę `workspace_runtime/latka_jazn_v14_8_1.sqlite3` z poprawnym `PRAGMA integrity_check = ok`.
- Naprawiono możliwość startu runtime bez błędu `database disk image is malformed`.
- Zachowano ślad SHA256 uszkodzonej bazy v14.8.0 w `workspace_runtime/latka_jazn_v14_8_0_corrupt_original.sha256`.
- Zaktualizowano testy oczekujące aktywnej wersji i aktywnej bazy.

## Nowe testy
- `tests/test_v14_8_1_large_dialogue_memory_grounding.py` — 9 testów regresji dla intencji, gate pamięci, modelu stanu, walidatora, aktywnej bazy i odpowiedzi engine.

## Zachowane z v14.8.0
- Most NLP/SJP/network.
- Polityka cache, providerów i granicy prawdy dla słowników.
- Wcześniejsze manifesty, dokumenty i testy regresji.
