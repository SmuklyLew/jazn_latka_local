# Aktualizacja v14.8.5.010 — sleep closure repair loop

## Cel

Naprawa drugiego poziomu regresji po `v14.8.5.009`: handler `sleep_closure_statement` spełniał już wymagane komponenty, ale końcowy walidator i `RuntimeResponseSynthesizer` nadal mogły zamienić naturalne „Dobranoc” na techniczny komunikat `sleep_closure_repair`.

## Zmiany

- Podniesiono aktywną wersję do `v14.8.5.010`.
- Treść `Dobranoc` zawiera teraz jawne markery wymagane przez walidator: `current_turn_closure`, `warmth`, `no_diagnostics`, `no_random_memory_excerpt`.
- `OperationalSelfModel.render_sleep_closure()` używa tej samej granicy prawdy i nie powoduje braków komponentów.
- `RuntimeResponseSynthesizer` nie wymusza już nadpisywania `sleep_closure_statement`, jeśli pierwsza walidacja jest poprawna.
- Dodano regresję `tests/test_v1485_010_sleep_closure_repair_loop.py`.

## Granica prawdy

Patch nie tworzy procesu w tle ani nie zmienia modelu świadomości. Usuwa pętlę naprawczą, która pokazywała techniczny tekst użytkownikowi mimo poprawnego handlera.
