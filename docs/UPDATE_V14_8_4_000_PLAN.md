# UPDATE v14.8.4.000 — Architecture plan and NLG contract documentation

**Status:** patch dokumentacyjny.  
**Nie zmienia runtime logic.**  
**Branch roboczy:** `fix/v14.8.4-model-guided-nlg-operational-thoughts`.  
**Base:** `work/v14-8-3-4-089-manifest-exclusion-detail-hotfix` / tag `stable-v14.8.3.4.093`.

## Cel patcha

Ten patch rozpoczyna serię `v14.8.4 — model-guided NLG + operational thought frame` przez dodanie pełnej dokumentacji planu oraz kontraktu NLG. Patch nie dodaje jeszcze kodu wykonawczego, aby najpierw zamknąć architekturę, granice prawdy i procedurę GitHub comparison gate.

## GitHub comparison gate

Przed przygotowaniem patcha sprawdzono aktualny branch `fix/v14.8.4-model-guided-nlg-operational-thoughts` na GitHub:

- `VERSION.txt` istnieje i wskazuje `v14.8.3.4.093`.
- `docs/PLAN_V14_8_4_MODEL_GUIDED_NLG_OPERATIONAL_THOUGHTS.md` nie istnieje jeszcze na branchu.
- `docs/NLG_CONTRACT_V14_8_4.md` nie istnieje jeszcze na branchu.
- `latka_jazn/core/model_guided_response_synthesizer.py` istnieje i zawiera model-guided path oparty o `ModelAdapterRequest`.
- `latka_jazn/core/free_dialogue_synthesizer.py` istnieje i nadal zawiera regułową syntezę zwykłej rozmowy.
- `latka_jazn/nlp_reasoning/pipeline.py` istnieje i zawiera analizę normalizacja/tokenizacja/Morfeusz/PoliMorf/fallback/semantic frame.
- `latka_jazn/nlp_reasoning/models.py` istnieje i definiuje `SemanticFrame`, `ReplyPolicy` oraz `PolishReasoningFrame`.
- `latka_jazn/resources/polish_reasoning/sources.lock.json` istnieje i zawiera aktualny rejestr źródeł/słowników.

Wniosek: `GitHub comparison gate: PASS` dla patcha dokumentacyjnego. Nowe pliki zostały potwierdzone jako nieobecne.

## Pliki dodane

- `docs/PLAN_V14_8_4_MODEL_GUIDED_NLG_OPERATIONAL_THOUGHTS.md`
- `docs/NLG_CONTRACT_V14_8_4.md`
- `docs/UPDATE_V14_8_4_000_PLAN.md`

## Zakres merytoryczny

Dokument planu opisuje pełną serię patchy:

- `v14.8.4.000 — Architecture plan and NLG contract documentation`
- `v14.8.4.001 — NLG contracts and planner`
- `v14.8.4.002 — Operational thought frame`
- `v14.8.4.003 — Model context compiler`
- `v14.8.4.004 — Response candidate generator/evaluator`
- `v14.8.4.005 — NLP lexical resources registry/cache`
- `v14.8.4.006 — Memory-grounded generation bridge`
- `v14.8.4.007 — Model adapter health and smoke tests`

Dokument kontraktu NLG definiuje minimalne klasy, funkcje i zasady dla kolejnych patchy, w tym `NlgPlan`, `OperationalThoughtFrame`, `ModelContextPacket`, candidate evaluator, lexical registry i model adapter health.

## Źródła zewnętrzne uwzględnione w planie

- Morfeusz 2 — analizator/generator fleksyjny dla polskiego: `https://morfeusz.sgjp.pl/`
- PoliMorf — słownik morfologiczny języka polskiego, licencja BSD-2-Clause według strony ZIL IPI PAN: `https://zil.ipipan.waw.pl/PoliMorf`
- plWordNet/Słowosieć — zasób leksykalno-semantyczny CLARIN: `https://clarin-pl.eu/dspace/handle/11321/554`
- MediaWiki Action API — potencjalny lookup/cache, nie masowy scraping: `https://www.mediawiki.org/wiki/API:Main_page`
- GitHub branch/pull request workflow: `https://docs.github.com/`
- Git apply/diff workflow: `https://git-scm.com/docs/git-apply`, `https://git-scm.com/docs/git-diff`

## Testy po zastosowaniu

Patch dokumentacyjny nie zmienia runtime logic, ale po zastosowaniu należy wykonać:

```powershell
git apply --check .\LATKA_JAZN_v14_8_4_000_ARCHITECTURE_PLAN_NLG_CONTRACT.patch
git apply .\LATKA_JAZN_v14_8_4_000_ARCHITECTURE_PLAN_NLG_CONTRACT.patch
py tools/refresh_current_manifest.py
py -m compileall -q latka_jazn main.py tools/refresh_current_manifest.py
py main.py --active-cache-status
git diff --stat
```

Po odświeżeniu manifestu status powinien pokazać tylko nowe dokumenty oraz manifest/SHA, jeśli generator manifestu je zmienił.

## Kryteria akceptacji

- nowe dokumenty istnieją w `docs/`,
- runtime logic nie została zmieniona,
- compileall przechodzi,
- `--active-cache-status` zwraca wersję aktywnego runtime i brak cache miss po ewentualnym `--write-active-runtime-marker`,
- dokument planu i kontrakt są gotowe jako podstawa do `v14.8.4.001`.

## Rollback

Jeśli patch nie jest jeszcze commitowany:

```powershell
git status
git restore MANIFEST_CURRENT.json MANIFEST_RUNTIME_MUTABLE.json SHA256SUMS SHA256SUMS_STATIC
git clean -f docs/PLAN_V14_8_4_MODEL_GUIDED_NLG_OPERATIONAL_THOUGHTS.md docs/NLG_CONTRACT_V14_8_4.md docs/UPDATE_V14_8_4_000_PLAN.md
```

Jeśli patch został commitowany:

```powershell
git log --oneline -5
git revert <SHA_COMMITU_V14_8_4_000>
```
