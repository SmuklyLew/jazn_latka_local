# CHANGELOG v14.8.2 — logic-routing-memory-grounding-repair

Data: 2026-06-04

## Zmiany główne
- Dodano `TurnResponsePolicy`, `TurnLogicAuditor`, `ReasoningController`, `RuntimeSessionState`, `JaznRuntimeSession`.
- Dodano handlery: `RuntimeActivationStatusHandler`, `RuntimeChatModeHandler`, `SystemRepairPlanHandler`.
- Naprawiono klasyfikację `póki co`, `runtime-preview/--chat`, `kod źródłowy`.
- Dodano `RawMemoryInspector` i statusy raw memory: archiwum / indeks_pusty / indeks_dostępny.
- Przeniesiono aktywną bazę na `latka_jazn_v14_8_2.sqlite3` z zachowaniem dużej pamięci (`legacy_messages > 0`).
- Dodano testy regresji v14.8.2.

## Granice prawdy
- `chat.html.7z` pozostaje archiwum, jeśli `chat.html` nie został rozpakowany.
- `--chat` nie jest procesem w tle po zakończeniu procesu Pythona.
- Pełny pytest w tym środowisku przekroczył limit czasu; zielone są testy P0/smoke wskazane w raporcie.
