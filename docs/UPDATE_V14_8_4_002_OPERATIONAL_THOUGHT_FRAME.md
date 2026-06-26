# UPDATE v14.8.4.002 — Operational thought frame

**Status:** patch kodowy po `v14.8.4.001`.
**Branch:** `fix/v14.8.4-model-guided-nlg-operational-thoughts`.
**Zakres:** jawna, audytowalna ramka decyzji operacyjnych bez zmiany finalnej odpowiedzi produkcyjnej.

## Cel

Patch dodaje `OperationalThoughtFrame`, czyli bezpieczny opis decyzji runtime: jaki cel odpowiedzi wybrano, jaki ton zastosowano, co postanowiono o pamięci, źródłach i modelu oraz które ścieżki zostały odrzucone.

To nie jest prywatny chain-of-thought, biologiczna świadomość ani finalna odpowiedź użytkownika. Ramka zapisuje wyłącznie decyzje wykonawcze potrzebne do audytu i późniejszego kompilowania kontekstu modelu.

## Dodane pliki

- `latka_jazn/core/operational_thought_frame.py`
- `tests/test_v1484_operational_thought_frame.py`
- `docs/UPDATE_V14_8_4_002_OPERATIONAL_THOUGHT_FRAME.md`

## Główne elementy

- `OperationalThoughtSignal`
- `OperationalThoughtFrame`
- `summarize_current_user_message(...)`
- `build_operational_thought_frame(...)`

## Granica prawdy

- Ramka nie generuje odpowiedzi.
- Ramka nie wywołuje modelu.
- Ramka nie pobiera pamięci.
- Ramka nie udaje, że posiada prywatny tok myślenia.
- Ramka nie staje się źródłem prawdy; prawda nadal pochodzi z runtime, NLG Plan, memory gate, memory payload, polityk źródeł i walidatorów.

## Testy akceptacyjne

Nowe testy sprawdzają:

- streszczenie bieżącej wiadomości bez lookupu pamięci,
- zwykłą rozmowę z `memory_decision=not_needed`,
- pytanie pamięciowe wymagające ugruntowanego payloadu,
- dokładny cytat runtime z zakazem parafrazy modelu,
- pytanie wymagające zewnętrznych źródeł bez udawania web lookupu,
- serializację `to_dict()` dla sygnałów i ramki.

## Komendy testowe

```powershell
py -m compileall -q latka_jazn main.py tools/refresh_current_manifest.py
py -m pytest -q tests/test_v1484_nlg_plan.py tests/test_v1484_operational_thought_frame.py tests/test_v14824_model_guided_jazn_runtime.py
py tools/refresh_current_manifest.py
py main.py --write-active-runtime-marker
py main.py --active-cache-status
```

## Rollback

```powershell
git restore --staged latka_jazn/core/operational_thought_frame.py tests/test_v1484_operational_thought_frame.py docs/UPDATE_V14_8_4_002_OPERATIONAL_THOUGHT_FRAME.md MANIFEST_CURRENT.json MANIFEST_RUNTIME_MUTABLE.json
git restore MANIFEST_CURRENT.json MANIFEST_RUNTIME_MUTABLE.json
git clean -fd -- latka_jazn/core/operational_thought_frame.py tests/test_v1484_operational_thought_frame.py docs/UPDATE_V14_8_4_002_OPERATIONAL_THOUGHT_FRAME.md
```
