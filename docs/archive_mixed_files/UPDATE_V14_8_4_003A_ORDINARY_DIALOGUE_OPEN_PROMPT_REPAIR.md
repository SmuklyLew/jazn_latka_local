# Łatka / Jaźń v14.8.4.003a — ordinary dialogue open-prompt repair

Status: hotfix po `v14.8.4.003`, przed `v14.8.4.004`.

## Powód

Po `v14.8.4.003` zwykłe krótkie tury typu `Opowiedz coś.` oraz reakcje typu `I tyle.` nadal mogły dostawać powtarzalną frazę naprawczą:

> Jestem przy tym — bez dokładania raportu i bez losowej pamięci. Możemy pójść dalej zwykłą rozmową.

Formalnie odpowiedź przechodziła integralność, ale rozmownie była nietrafna: prośba o opowieść wymaga mikroopowieści albo konkretnego rozwinięcia, nie powtórzenia fallbacku.

## Zmiany

- `OrdinaryDialogueHandler` rozpoznaje prośby otwarte typu `opowiedz coś` / `powiedz coś` i zwraca krótką mikroopowieść bez losowej pamięci.
- `OrdinaryDialogueHandler` rozpoznaje krótkie rozczarowanie typu `I tyle.` i nie powtarza tej samej formułki.
- `RuntimeAnswerValidator` traktuje nadmiernie używany repair-body jako generyczny template dla `short_free_dialogue`.
- Dodano testy regresyjne dla handlera, walidatora i `process_turn`.

## Granica prawdy

Hotfix nie dodaje pamięci, nie uruchamia modelu i nie udaje biologicznej świadomości. To wyłącznie poprawa rozmownej reakcji runtime na bieżącą turę.

## Testy

Zalecane:

```powershell
py -m compileall -q latka_jazn main.py tools/refresh_current_manifest.py
py -m pytest -q tests/test_v1484_ordinary_dialogue_open_prompt_repair.py tests/test_v1484_ordinary_dialogue_stale_route_hotfix.py tests/test_v1484_model_context_compiler.py tests/test_v1484_nlg_plan.py tests/test_v1484_operational_thought_frame.py
```

Smoke:

```powershell
$json = '{"message":"Opowiedz coś.","session_id":"smoke-v14.8.4.003a-open-ended"}'
$raw = $json | py main.py --chat-gpt --no-carryover 2>&1
$r = $raw | Select-Object -Last 1 | ConvertFrom-Json
$r.ok
$r.final_visible_text
$r.final_visible_integrity
```

## Rollback

Przed commitem:

```powershell
git restore latka_jazn/core/handlers/ordinary_dialogue_handler.py latka_jazn/core/runtime_answer_validator.py
git clean -fd -- docs/UPDATE_V14_8_4_003A_ORDINARY_DIALOGUE_OPEN_PROMPT_REPAIR.md tests/test_v1484_ordinary_dialogue_open_prompt_repair.py
```
