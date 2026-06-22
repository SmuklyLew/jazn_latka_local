# UPDATE REPORT v14.8.3.4.088 — Canon Source Question Hotfix

## Cel

Naprawiono trasowanie pytań o źródła kanonu Łatki. Pytania typu „Skąd bierzesz kanon Łatki?” nie powinny trafiać do `RuntimeSourceHandler`, bo ten handler odpowiada o źródle bieżącej odpowiedzi runtime, a nie o źródłach kanonu.

## Problem przed zmianą

- input: `Skąd bierzesz kanon Łatki?`
- selected_route: `runtime_source`
- selected_handler: `RuntimeSourceHandler`
- runtime_answer_quality: `mismatch_repaired`
- odpowiedź: metaopis runtime/source-origin zamiast odpowiedzi o kanonie

## Zmiany

- Dodano intent `canon_source_question`.
- Dodano route `canon_source`.
- Dodano `CanonSourceHandler`.
- Dodano `canon_source_summary()` bez wykonywania `local_private_canon_extension.py`.
- Dopisano handler do `RouteHandlerDispatcher`.
- Dopisano wymagane komponenty w `RouteRegistry`.
- Dopisano obsługę nowego intentu w `RuntimeAnswerValidator`.
- Dodano zachowanie ciała dedykowanego handlera w `JaznEngine` dla `CanonSourceHandler`.
- Dodano test regresyjny `tests/test_v14834088_canon_source_question_handler.py`.
- Dodano opcjonalny zapis pełnego `--runtime-preview` do pliku przez `--runtime-preview-output PATH`.

## Granica prawdy

Source-controlled Python canon jest źródłem pierwszym. `memory/raw` i `reports/canon_extraction` są kandydatami do recenzji. `local_private_canon_extension.py` jest lokalnym prywatnym rozszerzeniem i nie powinien być commitowany bez świadomej recenzji.

## Pliki zmienione

- `VERSION.txt`
- `latka_jazn/nlp/dialogue_intent_classifier.py`
- `latka_jazn/core/route_registry.py`
- `latka_jazn/core/route_handler_dispatcher.py`
- `latka_jazn/core/runtime_answer_validator.py`
- `latka_jazn/core/engine.py`
- `latka_jazn/core/canon/__init__.py`
- `latka_jazn/core/canon/canon_registry.py`
- `latka_jazn/core/handlers/canon_source_handler.py`
- `main.py`
- `tests/test_v14834088_canon_source_question_handler.py`
- `docs/update_history/reports/UPDATE_REPORT_v14_8_3_4_088_CANON_SOURCE_QUESTION_HOTFIX.md`

## Testy

Wymagane minimum:

```powershell
python -m compileall -q latka_jazn main.py tools/extract_latka_canon_candidates.py

python -m pytest -q `
  tests/test_v148313_canon_source_refactor.py `
  tests/test_v14834_python_canon_consolidation.py `
  tests/test_v14834088_canon_source_question_handler.py `
  tests/test_identity_startup.py
```

## Kryteria akceptacji

- `runtime_version`: `v14.8.3.4.088`
- `selected_route`: `canon_source`
- `selected_handler`: `CanonSourceHandler`
- `runtime_answer_quality` nie jest `mismatch_repaired`
- `final_visible_text` zawiera:
  - `latka_jazn/core/canon`
  - `source_controlled_python_canon_first`
  - `resources/canon`
  - `memory/raw`
  - `reports/canon_extraction`
  - `local_private_canon_extension.py`
- `canon_source_summary()` nie wykonuje `local_private_canon_extension.py`.
- `local_private_canon_extension.py` nie jest staged ani commitowany.
- `reports/canon_extraction/` nie jest staged ani commitowane.

## Git safety

Nie używać `git add .` ani `git add -A`.

Przed commitem sprawdzić:

```powershell
git diff --cached --name-only | Select-String "reports/memory|memory_unification|migration_candidates|patches/|SHA256SUMS|backup|workspace_runtime|memory/|local_private_canon_extension"
```
