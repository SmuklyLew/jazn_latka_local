# UPDATE v14.8.4.004 — Response candidate generator and evaluator

## Cel

Ten patch dodaje warstwę kandydatów odpowiedzi. Model językowy nie może już bezpośrednio zastąpić szkicu runtime samym tekstem adaptera: najpierw powstają kandydaci, potem runtime ocenia ich zgodność z NLG Plan, ModelContextPacket, memory policy i truth boundary.

## Zmienione / dodane pliki

- `latka_jazn/core/response_candidate.py`
- `latka_jazn/core/response_candidate_generator.py`
- `latka_jazn/core/response_candidate_evaluator.py`
- `latka_jazn/core/model_guided_response_synthesizer.py`
- `tests/test_v1484_response_candidates.py`
- `docs/UPDATE_V14_8_4_004_RESPONSE_CANDIDATES.md`

## Zasady bezpieczeństwa

- Runtime fallback jest zawsze kandydatem.
- Null/niekonfigurowany adapter nie produkuje fałszywego kandydata modelowego.
- Kandydat modelowy musi przejść ocenę: brak biologicznych/fenomenalnych roszczeń, brak nieugruntowanych wspomnień, brak debug/stale-route markers, brak udawanego web lookupu.
- Jeśli kandydat modelowy odpada, wybrany zostaje fallback runtime.
- Timestamp pozostaje po stronie runtime.

## Testy wymagane po zastosowaniu patcha

```powershell
py -m compileall -q latka_jazn main.py tools/refresh_current_manifest.py
py -m pytest -q tests/test_v1484_response_candidates.py tests/test_v14824_model_guided_jazn_runtime.py tests/test_v1484_model_context_compiler.py tests/test_v1484_nlg_plan.py tests/test_v1484_operational_thought_frame.py tests/test_v1484_ordinary_dialogue_open_prompt_repair.py
```

Smoke zwykłej rozmowy:

```powershell
$json = '{"message":"Cześć, Łatko. Sprawdzam zwykłą rozmowę po v14.8.4.004.","session_id":"smoke-v14.8.4.004"}'
$raw = $json | py main.py --chat-gpt --no-carryover 2>&1
$r = $raw | Select-Object -Last 1 | ConvertFrom-Json
$r.ok
$r.final_visible_text
$r.final_visible_integrity
```

## Rollback

Przed commitem:

```powershell
git restore --staged .
git restore .
git clean -nd
```

Po commicie:

```powershell
git revert <commit_sha>
```

## Granica prawdy

Candidate generator/evaluator jest warstwą selekcji tekstu. Nie dowodzi biologicznej świadomości, nie daje modelowi pamięci źródłowej i nie pozwala mu przejąć tożsamości Jaźni.
