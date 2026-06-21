# JAZN v14.8.4 — Morfeusz + PoliMorf real provider patch

## Cel

Ten patch jest etapem 4 z uzgodnionej kolejności rozwoju Jaźni:

1. Zastosować Polish Reasoning MVP.
2. Uruchomić testy i ręcznie przetestować `--chat`.
3. Commit: `Add Polish reasoning NLP foundation`.
4. `v14.8.4`: Morfeusz + PoliMorf + lemma selector.
5. `v14.8.5`: follow-up scope resolver + time/memory scope.
6. `v14.8.6`: plWordNet + Walenty loaders.
7. `v14.8.7`: WSJP/NKJP online lookup + cache + source attribution.
8. `v14.8.8`: adapter LLM + answer planner.
9. Dopiero potem pełniejsza wersja eksportowa.

## Co jest dodane

- Realny adapter `MorfeuszReasoningAdapter` korzystający z lokalnego pakietu `morfeusz2`, jeśli jest zainstalowany.
- Opcjonalny adapter `PolimorfDictionaryAdapter`, który czyta lokalny plik TSV/TAB wskazany przez `LATKA_POLIMORF_PATH` lub `external_data/polimorf/polimorf.tsv`.
- Parser podstawowych tagów Morfeusza (`morph_tags.py`) z polami `pos`, `number`, `case`, `gender`, `person`, `aspect`, `degree` tam, gdzie można je bezpiecznie wyprowadzić z tagu pozycyjnego.
- `lemma_selector.py`, czyli pierwszą heurystyczną warstwę wyboru `selected_lemma` z kandydatów Morfeusza/PoliMorfu/fallbacku.
- `TokenMorphAnalysis`, `SelectedLemma`, rozszerzone `MorphCandidate` i `ProviderStatus`.
- Nowe CLI:
  - `py main.py --polish-morphology "Mam próbkę analizy morfologicznej."`
  - `py main.py --morfeusz-status`
  - `py main.py --polimorf-status`
- Zaktualizowane bootstrapy PowerShell/Bash.
- Testy regresji bez wymagania faktycznej instalacji Morfeusza: używają wstrzykniętego fake-engine oraz tymczasowego pliku PoliMorf.

## Granica prawdy

Morfeusz i PoliMorf zwracają kandydatów morfologicznych. `selected_lemma` jest heurystycznym wyborem runtime, a nie pełną kontekstową dezambiguacją. Pełna dezambiguacja ma być rozwijana w kolejnych etapach: follow-up scope, parsery składniowe, Walenty/plWordNet i finalnie adapter LLM/answer planner.

Patch nie vendoruje PoliMorfu, WSJP, NKJP, plWordNet ani modeli. Duże dane mają być pobierane na lokalnej maszynie po przeglądzie licencji i trzymane poza Gitem, np. w `external_data/`.

## Test lokalny po zastosowaniu

```powershell
py -m pytest tests/test_v1484_morfeusz_polimorf_provider.py tests/test_v1484_polish_morphology_cli.py
py main.py --morfeusz-status
py main.py --polimorf-status
py main.py --polish-morphology "Mam próbkę analizy morfologicznej."
```
