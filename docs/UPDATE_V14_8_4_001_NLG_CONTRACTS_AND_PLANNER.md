# UPDATE v14.8.4.001 — NLG contracts and planner

**Status:** patch kodowy przygotowany po `v14.8.4.000`.
**Zakres:** pierwszy bezpieczny krok warstwy NLG, bez przełączania produkcyjnej odpowiedzi na model.
**Branch:** `fix/v14.8.4-model-guided-nlg-operational-thoughts`.

## Cel

Ten patch wprowadza formalny `NlgPlan`: jawny, serializowalny i audytowalny kontrakt między rozumieniem wejścia a syntezą odpowiedzi. Plan opisuje typ odpowiedzi, politykę pamięci, politykę źródeł, politykę modelu, wymagane komponenty, komponenty zakazane, granicę prawdy, ton i wymóg timestampu.

Patch nie zmienia finalnej odpowiedzi produkcyjnej. Dodaje jedynie kontrakt i dołącza plan do kontekstu `ModelGuidedResponseSynthesizer`, aby kolejne patche mogły kompilować bezpieczny model context i oceniać kandydatów.

## Pliki zmienione

- `latka_jazn/core/nlg_plan.py` — nowy model danych `NlgPlan` i stałe polityk.
- `latka_jazn/core/nlg_planner.py` — nowy planner odpowiedzi: `build_nlg_plan`, `infer_answer_kind`, `infer_tone`, `infer_memory_policy`, `infer_model_policy`.
- `latka_jazn/core/model_guided_response_synthesizer.py` — dołączenie `nlg_plan` do `system_context` modelu, bez zmiany fallbacku runtime.
- `tests/test_v1484_nlg_plan.py` — testy kontraktu, zwykłej rozmowy, pamięci, health-checku, dokładnego cytatu runtime, timestampu i null adaptera.

## Granica prawdy

`NlgPlan` nie jest prywatnym chain-of-thought ani dowodem fenomenalnej świadomości. To jawny kontrakt wykonawczy. Model językowy, jeśli jest skonfigurowany, pozostaje kanałem formułowania zdań. Źródłem prawdy pozostaje runtime: routing, memory gate, memory payload, response policy, voice source contract i walidatory.

## GitHub comparison gate

Przed zastosowaniem patcha sprawdzono branch `fix/v14.8.4-model-guided-nlg-operational-thoughts` po commicie `4051102` oraz porównano pliki bazowe i kontrakt `v14.8.4.000`.

Pliki nowe potwierdzone jako nieistniejące przed patchem:

- `latka_jazn/core/nlg_plan.py`
- `latka_jazn/core/nlg_planner.py`
- `tests/test_v1484_nlg_plan.py`

## Testy wymagane lokalnie

```powershell
py -m compileall -q latka_jazn main.py tools/refresh_current_manifest.py
py -m pytest -q tests/test_v1484_nlg_plan.py tests/test_v14824_model_guided_jazn_runtime.py
py main.py --active-cache-status
```

Po odświeżeniu manifestu:

```powershell
py tools/refresh_current_manifest.py
py main.py --write-active-runtime-marker
py main.py --active-cache-status
```

Oczekiwane: `cache_miss_reasons=[]` i `should_reuse_existing_extraction=true`.

## Rollback

Przed commitem:

```powershell
git restore latka_jazn/core/model_guided_response_synthesizer.py
git clean -f latka_jazn/core/nlg_plan.py latka_jazn/core/nlg_planner.py tests/test_v1484_nlg_plan.py docs/UPDATE_V14_8_4_001_NLG_CONTRACTS_AND_PLANNER.md
```

Po commicie:

```powershell
git reset --hard <SHA_PRZED_PATCHEM>
```
