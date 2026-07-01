# UPDATE v14.8.5.016.1 — runtime-preview compact / dev-preview split

## Cel

`python main.py --runtime-preview <tekst>` nie może zalewać terminala pełną kopertą `cognitive_turn_envelope`, bo wynik bywa wielomegabajtowy i nieczytelny w VS Code/PowerShell. Ten tryb ma pozostać krótkim podglądem diagnostycznym jednej tury runtime, a pełny payload techniczny ma być dostępny jawnie przez tryb deweloperski.

## Zmiana kontraktu CLI

- `--runtime-preview` wypisuje teraz na stdout tylko kompaktowy JSON:
  - `final_visible_text`,
  - `runtime_route`,
  - `primary_intent`,
  - `diagnostic_request`,
  - `fallback_classification`,
  - `runtime_answer_quality`,
  - `timestamp_trusted`,
  - `final_visible_integrity_valid`,
  - `runtime_response_status`,
  - ścieżkę do pełnego payloadu, jeśli użyto `--runtime-preview-output`.
- `--runtime-preview` nie jest zwykłą rozmową z Łatką i nie powinien być uznawany za pełną widoczną odpowiedź użytkownikowi.
- `--dev-preview` zachowuje dawny pełny payload techniczny na stdout, gdy nie podano output file.
- `--runtime-preview-output <plik.json>` działa zarówno z `--runtime-preview`, jak i `--dev-preview`: zapisuje pełny payload do pliku, a stdout zostaje krótki.

## Granica prawdy

`--runtime-preview` i `--dev-preview` są jednorazowymi wywołaniami `process_turn`. Nie dowodzą procesu w tle. Do stałej rozmowy służy `python main.py --chat`, a do daemonu `--daemon-start` / `--daemon-status`.

## Testy

Dodano:

- `tests/test_v14850161_runtime_preview_compact_cli.py`

Sprawdzone lokalnie:

```text
python -m compileall main.py latka_jazn tests
python -m pytest tests/test_v14850161_runtime_preview_compact_cli.py tests/test_v1485015_runtime_access_contract.py tests/test_v1485012_daemon_runtime.py -q
14 passed
```
