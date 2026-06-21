# v14.8.3 — Polish Reasoning / NLP source-grounded update

Ten patch dodaje warstwę `latka_jazn/nlp_reasoning`, która ma być pomostem między zwykłym tekstem użytkownika, słownikami/NLP i finalną odpowiedzią runtime. Patch nie vendoruje dużych słowników, korpusów ani modeli LLM. Zamiast tego dodaje rejestr źródeł, politykę licencji/cache, lekką normalizację, ramę semantyczną, adapter Morfeusza 2 jako opcjonalny provider lokalny, plany lookupu WSJP/NKJP oraz bootstrap dla maszyny z Internetem.

## Dodane komendy CLI

```powershell
py main.py --polish-reasoning-frame "Witaj w tej mrocznej nocy."
py main.py --polish-reasoning-frame "która jest godzina?"
py main.py --polish-reasoning-sources
py main.py --polish-reasoning-bootstrap-plan
py main.py --wsjp-lookup-plan "mroczny"
py main.py --nkjp-lookup-plan "mroczna noc"
```

## Dodane pliki

```text
latka_jazn/nlp_reasoning/__init__.py
latka_jazn/nlp_reasoning/models.py
latka_jazn/nlp_reasoning/normalizer.py
latka_jazn/nlp_reasoning/source_registry.py
latka_jazn/nlp_reasoning/cache_policy.py
latka_jazn/nlp_reasoning/semantic_rules.py
latka_jazn/nlp_reasoning/response_variant_selector.py
latka_jazn/nlp_reasoning/pipeline.py
latka_jazn/nlp_reasoning/diagnostics.py
latka_jazn/nlp_reasoning/adapters/__init__.py
latka_jazn/nlp_reasoning/adapters/morfeusz_adapter.py
latka_jazn/nlp_reasoning/adapters/typo_normalizer.py
latka_jazn/nlp_reasoning/adapters/online_lookup.py
latka_jazn/nlp_reasoning/adapters/resource_placeholders.py
latka_jazn/resources/polish_reasoning/sources.lock.json
scripts/bootstrap_polish_reasoning.ps1
scripts/bootstrap_polish_reasoning.sh
tests/test_v1483_polish_reasoning_pipeline.py
tests/test_v1483_polish_reasoning_cli.py
```

## Źródła zaprojektowane w rejestrze

```text
Morfeusz2/SGJP — morfologia, lematyzacja właściwa, synteza
PoliMorf — słownik form jako rozszerzenie/fallback
plWordNet/Słowosieć — graf semantyczny i relacje znaczeń
WSJP PAN — definicje, kolokacje, frazeologia, składnia, lookup online
NKJP — korpus użycia, concordance, lookup online
NKJP1M-SGJP — lokalny/licencjonowany podzbiór testowy i anotowany
Walenty — walencja predykatów
spaCy pl_core_news_sm — parser/NER/morfologia jako provider opcjonalny
Stanza PL — alternatywny provider UD
HerBERT — encoder do klasyfikacji/rerankingu
plT5 — model seq2seq do parafrazy i answer planning
PLLuM/Bielik — opcjonalne lokalne generatory/RAG po wyborze checkpointu i licencji
SJP.PL — pomocniczy lookup ortograficzny, nie główny rdzeń semantyczny
```

## Granica prawdy

- `sources.lock.json` opisuje źródła i tryby użycia; nie twierdzi, że dane są pobrane.
- WSJP, NKJP i SJP.PL są używane jako lookup/reference plan, nie jako hurtowo kopiowane zasoby.
- Duże dane i modele mają trafiać do `external_data/`, `cache/`, `hf_models/` albo `models/`, które są ignorowane przez git.
- Morfeusz2 jest providerem opcjonalnym: jeśli nie jest zainstalowany, runtime pokazuje `provider unavailable` i przechodzi na lekki fallback heurystyczny.
- Odpowiedzi rozmowne nadal wymagają generatora/LLM, ale warstwa Polish Reasoning daje uziemiony frame: normalizację, intencję, ton, politykę odpowiedzi i status providerów.

## Testy

```powershell
py -m pytest tests/test_v1482_dialogue_intent_classifier_precision.py tests/test_v1482_runtime_answer_validator_policy.py tests/test_v1482_chat_loop_repeated_template_guard.py tests/test_v1482_dialogue_followup_time_repair.py tests/test_v1482_ordinary_dialogue_night_tone_repair.py tests/test_v1483_polish_reasoning_pipeline.py tests/test_v1483_polish_reasoning_cli.py
```

Spodziewany wynik w środowisku bez ciężkich providerów:

```text
26 passed
```
