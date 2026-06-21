# CHANGELOG v14.8.1-large-dialogue-memory-grounding-update

## Dodano

- `SJPReferenceProvider` jako bezpieczne źródło referencyjne linkowe dla SJP.PL.
- Jawny status `sjp_reference_provider` i `wsjp_reference_provider` w `--startup-status`.
- Plan aktualizacji `docs/PLAN_AKTUALIZACJI_v14_8_0_NLP_SJP_NETWORK.md`.
- Testy regresji v14.8.0 dla SJP/WSJP, routera NLP/SJP i mini-leksykonu.

## Zmieniono

- Wersja systemu: `v14.8.1-large-dialogue-memory-grounding-update`.
- `ExternalDictionaryAdapter` działa jako kompozyt: cache, mini-leksykon, Morfeusz opcjonalny, Wiktionary API, SJP reference, WSJP reference, plWordNet opcjonalny, LanguageTool opcjonalny.
- `DialogueIntentClassifier` daje pierwszeństwo aktualizacji systemu NLP/SJP nad pojedynczym lookupiem słownikowym.
- Mini-leksykon domenowy zawiera teraz pojęcia `nlp`, `sjp`, `wsjp`.
- Polityka źródeł słownikowych wymaga, żeby źródła referencyjne nie udawały definicji.

## Granica prawdy

SJP.PL i WSJP PAN są w v14.8.0 domyślnie używane jako linki referencyjne, a nie jako scrapowane źródła definicji. Runtime ma pokazywać status providerów i nie twierdzić, że pobrał więcej, niż faktycznie pobrał.
