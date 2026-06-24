# UPDATE v14.8.4.004A — Ordinary dialogue version smoke repair

## Cel

Ten mały repair patch jest nakładany na niecommitowany etap `v14.8.4.004 — Response candidate generator and evaluator`.
Naprawia sytuację, w której smoke zwykłej rozmowy zawierający numer wersji (`Cześć, Łatko. Sprawdzam zwykłą rozmowę po v14.8.4.004.`) wpadał w nadmiernie generyczny repair fallback.

## Problem

Runtime zwracał formalnie poprawny JSON i `final_visible_integrity.valid=True`, ale widoczna treść była ponownie starym fallbackiem:

```text
Jestem przy tym — bez dokładania raportu i bez losowej pamięci. Możemy pójść dalej zwykłą rozmową.
```

To jest niepożądane dla zwykłego smoke testu rozmowy, bo użytkownik prosi o naturalny kontakt, a nie o repair-synthesis.

## Zmiany

- `OrdinaryDialogueHandler` rozpoznaje wersjowany smoke zwykłej rozmowy (`sprawdzam/testuję zwykłą rozmowę/dialog`).
- Handler traktuje dawny tekst `Przyjmuję tę korektę...` jako zły passthrough przy zwykłej rozmowie.
- Dodano test regresji dla handlera i pełnego `JaznEngine.process_turn`.

## Granica prawdy

Patch nie tworzy nowej pamięci, nie zmienia model adaptera i nie deklaruje stałego procesu w tle. Naprawia wyłącznie bieżące renderowanie ordinary dialogue.

## Testy

Minimalny zestaw:

```powershell
py -m compileall -q latka_jazn main.py tools/refresh_current_manifest.py
py -m pytest -q tests/test_v1484_ordinary_dialogue_version_smoke_repair.py tests/test_v1484_response_candidates.py tests/test_v14824_model_guided_jazn_runtime.py tests/test_v1484_nlg_plan.py
```

## Rollback

Przed commitem:

```powershell
git restore latka_jazn/core/handlers/ordinary_dialogue_handler.py
git clean -f docs/UPDATE_V14_8_4_004A_ORDINARY_DIALOGUE_VERSION_SMOKE_REPAIR.md tests/test_v1484_ordinary_dialogue_version_smoke_repair.py
```
