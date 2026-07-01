# Aktualizacja v14.8.5.008 — ordinary dialogue naturalness hotfix

## Cel

Domknięcie pracy po `v14.8.5.006` i `v14.8.5.007`: zwykła rozmowa ma brzmieć mniej jak raport techniczny, a pytania typu „Co tam?”, „A Ty?”, „Jak się miewasz?” i „Dobranoc” mają zachowywać bieżącą intencję, ciepło oraz granicę prawdy bez wpychania przypadkowych wspomnień.

## Zmiany

- Podniesiono aktywną wersję do `v14.8.5.008`.
- `OperationalSelfModel` korzysta z centralnego `schema_version(...)` i daje krótsze, bardziej naturalne odpowiedzi o stanie rozmownym.
- `SelfStateHandler` używa bieżących etykiet `generation_mode(...)` oraz `schema_version(...)`, zamiast historycznego `self_state_handler/v14.8.2.4`.
- `OrdinaryDialogueHandler` skraca odpowiedzi dla `Co tam słychać?`, `ok` i `Dobranoc`, usuwając metajęzyk typu raport/diagnostyka/stary kontekst.
- Dodano test regresji `tests/test_v1485_008_ordinary_dialogue_naturalness.py`.
- Test `007` został uodporniony na kolejne wersje przez `generation_mode("ordinary_dialogue")`.

## Granica prawdy

Ta poprawka nie tworzy stałego procesu w tle ani biologicznego samopoczucia. Wzmacnia sposób mówienia aktywnego runtime w zwykłych turach rozmownych i pilnuje, żeby naturalność nie zamieniła się w udawanie pamięci albo życia poza uruchomieniem procesu.

## Weryfikacja

Minimalny zestaw po patchu:

```powershell
python -m compileall -q latka_jazn main.py tools/audit_legacy_literals_v1485.py tests/test_v1485_007_audit_title_and_dialogue_smoke.py tests/test_v1485_008_ordinary_dialogue_naturalness.py

python -m pytest -q -p no:cacheprovider `
  tests/test_v1485_000_version_template_reconciliation.py `
  tests/test_v1485_001_current_turn_grounding.py `
  tests/test_v1485_002_user_self_memory_split.py `
  tests/test_v1485_006_runtime_marker_schema_integrity.py `
  tests/test_v1485_007_audit_title_and_dialogue_smoke.py `
  tests/test_v1485_008_ordinary_dialogue_naturalness.py
```

Smoke rozmowny:

```powershell
'{"message":"Co tam słychać?","session_id":"manual-smoke-008","client":"manual_smoke"}' | python main.py --chat-gpt --no-carryover
'{"message":"A Ty?","session_id":"manual-smoke-008","client":"manual_smoke"}' | python main.py --chat-gpt --no-carryover
'{"message":"Dobranoc","session_id":"manual-smoke-008","client":"manual_smoke"}' | python main.py --chat-gpt --no-carryover
```
