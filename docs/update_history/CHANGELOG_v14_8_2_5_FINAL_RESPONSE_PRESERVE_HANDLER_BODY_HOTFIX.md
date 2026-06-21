# v14.8.2.5 final-response preserve handler body hotfix

## Cel

Po hotfixie routera `CapabilityStatusHandler` poprawnie generował health-check, ale finalna warstwa odpowiedzi potrafiła nadpisać go ogólnym `stale_route_context_guard_repair`. Przyczyną był m.in. fałszywy substring match: `raw_memory_startup_status/v14.6.10` zawiera tekst `v14.6.1`, więc walidator uznawał poprawną odpowiedź za ślad starej trasy.

## Zmiany

- `runtime_answer_validator.py`:
  - wersja schematu `v14.8.2.5.1`;
  - regexowe wykrywanie prawdziwych markerów legacy `v14.6.1`/`v14.6.2`, bez łapania `v14.6.10`;
  - szybka akceptacja bezpośrednich odpowiedzi wyspecjalizowanych handlerów dla `runtime_health_check_after_update`, `internet_access_question`, `capability_status_question`, `self_memory_recall_request`.
- `engine.py`:
  - wprowadza `preserve_handler_body` dla `CapabilityStatusHandler` i `SelfMemoryRecallHandler`, jeżeli spełnione są wymagane komponenty;
  - nie pozwala, by repair-synthesis nadpisał spełnioną odpowiedź handlera;
  - czyści `next_step` dla pytań statusowych, żeby nie ciągnąć trasy aktualizacji kodu.
- `capability_status_handler.py`:
  - health-check nie wypisuje już schema fallbacku `v14.6.10` jako raw memory status;
  - zwraca metadane zachowania handler body.
- Testy:
  - sprawdzają, że `v14.6.10` nie jest traktowane jako `v14.6.1`;
  - final response contract zachowuje `Działam...`;
  - prawdziwy marker legacy nadal jest blokowany.

## Granica prawdy

Ten patch nie dodaje modelu generatywnego. Naprawia ścieżkę preservation: dobra, komponentowo spełniona odpowiedź handlera nie może zostać zastąpiona ogólnym tekstem naprawczym.
