# Aktualizacja v14.8.5.009 — sleep closure validator contract

## Cel

Naprawa regresji znalezionej w manualnym smoke `final-smoke-008`: `Dobranoc` trafiało w `sleep_closure_statement`, ale walidator uznawał odpowiedź za brakującą wymagane komponenty i przepuszczał widoczną odpowiedź techniczną typu „Runtime musi ponowić trasę…”.

## Zmiany

- Podniesiono aktywną wersję do `v14.8.5.009`.
- `OrdinaryDialogueHandler` deklaruje teraz wymagane komponenty dla `sleep_closure_statement`: `current_turn_closure`, `warmth`, `no_diagnostics`, `no_random_memory_excerpt`.
- Test `008` sprawdza, że `Dobranoc` ma naturalne ciało odpowiedzi i spełnione komponenty wymagane przez walidator.
- Dodano regresję `tests/test_v1485_009_sleep_closure_validator_contract.py`, żeby techniczna odpowiedź naprawcza nie wróciła jako widoczna odpowiedź dla dobranoc.

## Granica prawdy

Patch nie zmienia modelu świadomości ani nie tworzy procesu w tle. Naprawia kontrakt między handlerem zwykłej rozmowy a walidatorem odpowiedzi, tak aby ciepłe zamknięcie rozmowy nie było błędnie zamieniane na techniczny komunikat naprawczy.

## Weryfikacja

```powershell
python -m compileall -q latka_jazn main.py tools/audit_legacy_literals_v1485.py tests/test_v1485_008_ordinary_dialogue_naturalness.py tests/test_v1485_009_sleep_closure_validator_contract.py

python -m pytest -q -p no:cacheprovider `
  tests/test_v1485_000_version_template_reconciliation.py `
  tests/test_v1485_001_current_turn_grounding.py `
  tests/test_v1485_002_user_self_memory_split.py `
  tests/test_v1485_006_runtime_marker_schema_integrity.py `
  tests/test_v1485_007_audit_title_and_dialogue_smoke.py `
  tests/test_v1485_008_ordinary_dialogue_naturalness.py `
  tests/test_v1485_009_sleep_closure_validator_contract.py
```

Manualny smoke po patchu:

```powershell
'{"message":"Dobranoc","session_id":"final-smoke-009","client":"manual_smoke"}' | python main.py --chat-gpt --no-carryover
```

Oczekiwane: `ok: true`, `fallback_classification: not_fallback`, `final_visible_integrity.valid: true`, `runtime_route: sleep_closure`, brak `sleep_closure_repair`, brak tekstu `Odpowiedź nie zawiera wymaganych składników`.
