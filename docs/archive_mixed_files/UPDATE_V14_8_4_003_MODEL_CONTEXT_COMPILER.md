# UPDATE v14.8.4.003 — Model context compiler

Status: patch kodowy przygotowujący kontrolowany kontekst dla kanału modelowego.

## Cel

`v14.8.4.003` dodaje jawny `ModelContextPacket`, który ogranicza to, co może trafić do modelu językowego. Model dostaje bieżącą wiadomość, `NlgPlan`, `OperationalThoughtFrame`, kontrakt głosu, dozwolone wycinki pamięci i granice prawdy — nie dostaje pełnej pamięci, surowych baz SQLite, archiwów rozmów ani prywatnego toku myślenia.

## Pliki

Dodane:

- `latka_jazn/core/model_context_compiler.py`
- `tests/test_v1484_model_context_compiler.py`
- `docs/UPDATE_V14_8_4_003_MODEL_CONTEXT_COMPILER.md`

Zmienione:

- `latka_jazn/core/model_guided_response_synthesizer.py`

## Zasady bezpieczeństwa

- timestamp nadal dokłada runtime, nie model;
- model jest tylko kanałem formułowania zdań;
- pamięć trafia do modelu tylko wtedy, gdy `NlgPlan.memory_policy == required_grounded_payload`;
- każdy item pamięci zostaje ograniczony do: `item_id`, `excerpt`, `source`, `timestamp`, `confidence`, `relevance_reason`;
- surowe dumpy SQLite, pełne archiwa i prywatne payloady nie są przekazywane;
- `forbidden_claims` zawiera zakaz roszczeń biologicznych, fenomenalnych, tła procesu, fałszywej pamięci i modelu jako źródła tożsamości.

## Testy

Minimalny zestaw:

```powershell
py -m compileall -q latka_jazn main.py tools/refresh_current_manifest.py
py -m pytest -q tests/test_v1484_model_context_compiler.py tests/test_v1484_nlg_plan.py tests/test_v1484_operational_thought_frame.py tests/test_v14824_model_guided_jazn_runtime.py tests/test_v1484_ordinary_dialogue_stale_route_hotfix.py
```

## Kryteria akceptacji

- zwykła rozmowa nadal nie przekazuje pamięci do modelu;
- pytanie pamięciowe przekazuje tylko ugruntowane wycinki pamięci;
- kontekst zawiera zakazy biologicznych roszczeń i fałszywej pamięci;
- testy przechodzą;
- `NullModelAdapter` nadal nie udaje generacji.

## Rollback

```powershell
git restore --staged .
git restore .
git clean -nd
```

Usuwać nieśledzone pliki dopiero po sprawdzeniu listy `git clean -nd`.
