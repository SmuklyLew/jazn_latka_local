# UPDATE v14.8.4.005 — NLP lexical resources registry/cache

## Cel

Ten patch realizuje etap `v14.8.4.005 — NLP lexical resources registry/cache` z planu
`PLAN_V14_8_4_MODEL_GUIDED_NLG_OPERATIONAL_THOUGHTS.md`.

Celem nie jest dodanie wielkich słowników do repozytorium. Celem jest rozdzielenie:

1. wpisu w rejestrze źródeł,
2. realnej lokalnej dostępności zasobu,
3. wyniku kontrolowanego lookupu zapisanego w cache z metadanymi.

## Zmiany

Dodano:

- `latka_jazn/nlp_reasoning/lexical_resource_registry.py`
- `latka_jazn/nlp_reasoning/lexical_resource_cache.py`
- `latka_jazn/resources/nlp/verified_sources.json`
- `latka_jazn/resources/nlp/latka_project_lexicon.json`
- `tests/test_v1484_lexical_resources.py`

Zmieniono:

- `latka_jazn/config.py` — ścieżki i ustawienia cache/rejestru lexical resources.
- `main.py` — komenda `--nlp-resource-status`.

## Kontrakt bezpieczeństwa

Patch nie vendoruje pełnych słowników, korpusów, modeli ani dumpów. Do repo trafiają tylko małe
metadane źródeł, projektowy leksykon pojęć Łatki/Jaźni, kod i testy.

`LexicalResourceRegistry` raportuje status każdego zasobu jako:

- `available=True` tylko gdy zasób jest realnie dostępny lokalnie albo istnieje wpis cache,
- `available=False` gdy zasób jest tylko zarejestrowany, ale nie został zainstalowany, wskazany ani zcache'owany,
- `reason` opisuje brak providera, brak lokalnego pliku albo tryb online-reference.

`LexicalResourceCache` zapisuje lookupi w SQLite razem z:

- `source_id`,
- `key`,
- `payload_json`,
- `source_url`,
- `license`,
- `retrieved_at_utc`,
- `provider`.

Domyślnie cache wskazuje `workspace_runtime/dictionary_cache.sqlite3`, czyli lokalny runtime cache,
nie plik do commitowania.

## Źródła zewnętrzne i granice licencji

- Morfeusz 2 jest traktowany jako lokalny opcjonalny provider fleksyjny. Runtime sprawdza instalację,
  ale nie kopiuje bibliotek ani słowników do repo.
- PoliMorf jest traktowany jako zewnętrzny lokalny plik po świadomym pobraniu i przeglądzie licencji.
- plWordNet, WSJP, SJP i NKJP są rejestrowane jako źródła wymagające review albo lookup/cache;
  patch nie importuje ich masowo.
- MediaWiki Action API jest rejestrowane jako protokół kontrolowanego lookupu, z zachowaniem zasad
  API i terms konkretnego wiki.

## Testy

Minimalny zestaw po patchu:

```powershell
py -m compileall -q latka_jazn main.py tools/refresh_current_manifest.py
py -m pytest -q tests/test_v1484_lexical_resources.py tests/test_v1484_response_candidates.py tests/test_v1484_model_context_compiler.py tests/test_v1484_nlg_plan.py tests/test_v1484_operational_thought_frame.py tests/test_v1484_ordinary_dialogue_open_prompt_repair.py
py main.py --nlp-resource-status
py main.py --polish-reasoning-sources
py main.py --active-cache-status
```

Smoke zwykłej rozmowy:

```powershell
$json = '{"message":"Cześć, Łatko. Sprawdzam zwykłą rozmowę po v14.8.4.005.","session_id":"smoke-v14.8.4.005"}'
$raw = $json | py main.py --chat-gpt --no-carryover 2>&1
$r = $raw | Select-Object -Last 1 | ConvertFrom-Json
$r.final_visible_text
$r.final_visible_integrity
```

## Rollback

Przed commitem:

```powershell
git restore latka_jazn/config.py main.py
git clean -f latka_jazn/nlp_reasoning/lexical_resource_registry.py latka_jazn/nlp_reasoning/lexical_resource_cache.py latka_jazn/resources/nlp/verified_sources.json latka_jazn/resources/nlp/latka_project_lexicon.json tests/test_v1484_lexical_resources.py docs/UPDATE_V14_8_4_005_NLP_LEXICAL_RESOURCES.md
```
