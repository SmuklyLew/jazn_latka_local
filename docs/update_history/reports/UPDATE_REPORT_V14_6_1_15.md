# Raport aktualizacji v14.6.2-runtime-start-fallback-truth-contract

Zaktualizowano system Jaźni z v14.6.2 do v14.6.2-runtime-start-fallback-truth-contract.

## Naprawione

- zbyt szeroki wybór trasy `greeting`;
- powtarzanie długiej formuły obecności w zwykłych turach;
- brak jawnego kontraktu, że ChatGPT nie może zgubić `next_step`, follow-upu albo właściwego pytania runtime;
- zbyt wąskie rozpoznanie prośby o naprawę całego rdzenia/fallbacków.

## Dodane testy

- `tests/test_v146115_contextual_greeting_fallback_repair.py`
- zaktualizowany audyt spójności wersji aktywnych plików.
