# Aktualizacja v14.6.1 — NLP adapter + ZIP profiles

## Cel

v14.6.1 jest bezpiecznym krokiem po v14.6.0. Nie wprowadza ciężkiego modelu NLP jako obowiązkowej zależności. Buduje warstwę, która pozwala Jaźni pracować z polskim tekstem bardziej jawnie i lepiej przygotowuje system do późniejszego podłączenia Stanza, Morfeusz2 albo kontekstowego providera LLM.

## Zasada prawdy

Pełna lematyzacja języka polskiego wymaga kontekstu, rozpoznawania części mowy, cech morfologicznych i czasem rozstrzygania znaczenia słowa w zdaniu. v14.6.1 nie udaje pełnego parsera. Gdy działa tylko provider builtin, runtime zwraca ostrożne kandydaty lematów z poziomem pewności i nazwą providera.

## Dodane moduły

- `latka_jazn/nlp/polish_normalizer.py` — normalizacja tekstu PL i ascii-fold.
- `latka_jazn/nlp/polish_tokenizer.py` — tokenizacja z pozycjami znaków.
- `latka_jazn/nlp/polish_lemmatizer.py` — raport NLP: `lemma_candidates`, `selected_lemma`, `confidence`, `provider`, `ambiguity`.
- `latka_jazn/nlp/providers/builtin_provider.py` — zawsze dostępny, ostrożny fallback.
- `latka_jazn/nlp/providers/optional_morfeusz_provider.py` — przygotowany adapter Morfeusz2, domyślnie nieobowiązkowy.
- `latka_jazn/nlp/providers/optional_stanza_provider.py` — przygotowany adapter Stanza, domyślnie nieobowiązkowy.
- `latka_jazn/packaging/package_profiles.py` — jawny opis profili paczek.

## Dodane zasoby

- `latka_jazn/resources/nlp_provider_registry_v14_6_2.json`
- `latka_jazn/resources/polish_lemma_overrides_v14_6_2.json`
- `latka_jazn/resources/semantic_lexicon_v14_6_2.json`
- `latka_jazn/resources/zip_package_profiles_v14_6_2.json`

## Profile eksportu ZIP

- `system` — kod, testy, dokumentacja, manifesty; bez pamięci.
- `memory` — pamięć, warstwy i aktywna baza SQLite.
- `nlp` — adaptery i lekkie zasoby NLP; bez pamięci i bez ciężkich modeli.
- `github_source_safe` — źródła do repo `Latka.Jazn`, bez surowej pamięci i aktywnych baz.
- `full` — pełny snapshot systemu z pamięcią.

## CLI

```bash
python main.py --nlp-frame "Jadę tramwajem przez Częstochowę i myślę o Jaźni"
python main.py --lexical-frame "Rozbuduj lematyzację języka polskiego krok po kroku"
python main.py --export-nlp --output exports/latka_jazn_v14_6_1_NLP_RESOURCES_ONLY.zip
python main.py --export-github-source-safe --output exports/latka_jazn_v14_6_1_GITHUB_SOURCE_SAFE.zip
python main.py --export-full --output exports/latka_jazn_v14_6_1_FULL_SYSTEM_WITH_MEMORY.zip
```

## Integracja z cognitive-frame

`JaznEngine.build_cognitive_frame()` dodaje teraz pole `polish_nlp`, które ChatGPT może traktować jako jawny ślad runtime. Pole nie zastępuje odpowiedzi językowej, tylko pomaga dobrać sens, trasę i granicę prawdy.

## Następne kroki

v14.6.2 może dodać realną instalację i testy jednego z providerów zewnętrznych. v14.6.3 może dodać kontekstowe rozstrzyganie lematów i sensów słów z udziałem LLM albo modelu morfosyntaktycznego.
