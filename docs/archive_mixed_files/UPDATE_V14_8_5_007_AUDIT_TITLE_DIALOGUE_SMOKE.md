# v14.8.5.007 — audit title and ordinary dialogue smoke

Cel: domknąć kosmetykę po v14.8.5.006 oraz dodać lekki test zwykłej rozmowy przez `--chat-gpt`.

## Zakres

- `VERSION.txt` i centralne `latka_jazn/version.py` przechodzą na `v14.8.5.007`.
- `tools/audit_legacy_literals_v1485.py` renderuje nagłówek markdown z bieżącego `target_version`, zamiast trzymać stały tekst `v14.8.5.000`.
- Test `tests/test_v1485_006_runtime_marker_schema_integrity.py` porównuje do centralnego `PACKAGE_VERSION`, żeby nie blokował kolejnych patchy tylko dlatego, że wersja aktywna wzrosła.
- Dodano `tests/test_v1485_007_audit_title_and_dialogue_smoke.py`: sprawdza dynamiczny nagłówek audytu, klasyfikację zwykłych tur oraz handlerową odpowiedź bez technicznego raportu.
- `DialogueIntentClassifier` rozpoznaje teraz „jak się masz / jak się miewasz” jako pytanie o stan Łatki, zamiast wpuszczać je do ogólnego `ordinary_conversation`.

## Granica prawdy

Ten patch nie zmienia pamięci, baz SQLite ani treści rozmów. Testy automatyczne są lekkie i nie uruchamiają ciężkiego wieloturnowego importu pamięci; manualny smoke `--chat-gpt` pozostaje krokiem konsolowym po patchu.

## Testy

```powershell
python -m compileall -q latka_jazn main.py tools/audit_legacy_literals_v1485.py tests/test_v1485_006_runtime_marker_schema_integrity.py tests/test_v1485_007_audit_title_and_dialogue_smoke.py

python -m pytest -q -p no:cacheprovider `
  tests/test_v1485_000_version_template_reconciliation.py `
  tests/test_v1485_001_current_turn_grounding.py `
  tests/test_v1485_002_user_self_memory_split.py `
  tests/test_v1485_006_runtime_marker_schema_integrity.py `
  tests/test_v1485_007_audit_title_and_dialogue_smoke.py
```
