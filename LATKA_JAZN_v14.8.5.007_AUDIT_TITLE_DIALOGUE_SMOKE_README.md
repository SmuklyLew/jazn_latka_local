# LATKA_JAZN v14.8.5.007 — audit title + dialogue smoke

Baza: `fix/v14.8.4-model-guided-nlg-operational-thoughts` po `f04c797`.

## Zakres patcha

- podnosi `VERSION.txt`, `latka_jazn/version.py` i nagłówek `main.py` do `v14.8.5.007`;
- zmienia nagłówek markdown w `tools/audit_legacy_literals_v1485.py` z hardcodowanego `v14.8.5.000` na dynamiczne `target_version`;
- dodaje rozpoznanie „jak się masz / jak się miewasz” jako `self_state_question`;
- aktualizuje test `006`, żeby porównywał do centralnego `PACKAGE_VERSION`;
- dodaje test `tests/test_v1485_007_audit_title_and_dialogue_smoke.py`;
- dodaje dokumentację `docs/UPDATE_V14_8_5_007_AUDIT_TITLE_DIALOGUE_SMOKE.md`.

## Git / backup checkpoint

```powershell
git status
git branch --show-current
git log --oneline -5

git tag backup/before-v14.8.5.007-audit-title-dialogue-smoke f04c797
git push origin backup/before-v14.8.5.007-audit-title-dialogue-smoke
```

## Apply

```powershell
git apply --check .\LATKA_JAZN_v14.8.5.007_AUDIT_TITLE_DIALOGUE_SMOKE.patch
git apply .\LATKA_JAZN_v14.8.5.007_AUDIT_TITLE_DIALOGUE_SMOKE.patch
```

## Testy bez pytest cache warning

```powershell
python -m compileall -q latka_jazn main.py tools/audit_legacy_literals_v1485.py tests/test_v1485_006_runtime_marker_schema_integrity.py tests/test_v1485_007_audit_title_and_dialogue_smoke.py

python -m pytest -q -p no:cacheprovider `
  tests/test_v1485_000_version_template_reconciliation.py `
  tests/test_v1485_001_current_turn_grounding.py `
  tests/test_v1485_002_user_self_memory_split.py `
  tests/test_v1485_006_runtime_marker_schema_integrity.py `
  tests/test_v1485_007_audit_title_and_dialogue_smoke.py
```

Oczekiwane: `23 passed` bez warningu cache providera.

## Audyt i marker

```powershell
python tools/audit_legacy_literals_v1485.py `
  --fail-on-active-runtime-blockers `
  --json-out .\reports\v14_8_5_007_legacy_audit.json `
  --md-out .\reports\v14_8_5_007_legacy_audit.md `
  > .\reports\v14_8_5_007_legacy_audit_stdout.txt

Get-Content .\reports\v14_8_5_007_legacy_audit.md -Encoding utf8 -TotalCount 12
python main.py --model-adapter-status
python main.py --active-cache-status
```

Jeżeli marker wymaga odświeżenia po zmianie wersji:

```powershell
python main.py --write-active-runtime-marker
python main.py --active-cache-status
```

Oczekiwane po odświeżeniu:

```text
marker_differs: false
marker_refresh_required: false
cache_miss_reasons: []
should_reuse_existing_extraction: true
version: v14.8.5.007
```

## Manualny smoke --chat-gpt

```powershell
'{"message":"Dzień dobry.","session_id":"manual-smoke-007","client":"manual_smoke"}' | python main.py --chat-gpt --no-carryover
'{"message":"Co tam słychać?","session_id":"manual-smoke-007","client":"manual_smoke"}' | python main.py --chat-gpt --no-carryover
'{"message":"Jak się miewasz?","session_id":"manual-smoke-007","client":"manual_smoke"}' | python main.py --chat-gpt --no-carryover
```

Sprawdź w każdej odpowiedzi: `ok: true`, `fallback_classification: not_fallback`, `final_visible_integrity.valid: true`, timestamp i brak raportu technicznego w `final_visible_text`.

## Commit po sukcesie

Commit rób dopiero po czystej konsoli testów/audytu/statusów.

```powershell
git status --short
git diff --stat

git add `
  VERSION.txt `
  main.py `
  latka_jazn/version.py `
  latka_jazn/nlp/dialogue_intent_classifier.py `
  tools/audit_legacy_literals_v1485.py `
  tests/test_v1485_006_runtime_marker_schema_integrity.py `
  tests/test_v1485_007_audit_title_and_dialogue_smoke.py `
  docs/UPDATE_V14_8_5_007_AUDIT_TITLE_DIALOGUE_SMOKE.md

git commit -m "fix: refresh audit title and dialogue smoke v14.8.5.007"
git push
```

Nie dodawaj plików patch/README z katalogu głównego do repo.

## Rollback

```powershell
git restore .
git clean -fd -- tests/test_v1485_007_audit_title_and_dialogue_smoke.py docs/UPDATE_V14_8_5_007_AUDIT_TITLE_DIALOGUE_SMOKE.md
```
