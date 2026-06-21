# AKTUALIZACJA v14.5.39 — cleanup/dedup

Cel: zachować historię przez manifesty i hashe, a nie przez identyczne kopie treści.

Źródło: `v14.5.38-github-cognitive-runtime`
Nowa wersja: `v14.5.39-cleanup-dedup`

## Zasada

- usunięto tylko pliki o identycznym SHA-256;
- aktywne pliki pamięci i systemu mają pierwszeństwo jako kanoniczne;
- usunięte ścieżki zapisano w manifestach JSON razem z SHA-256, rozmiarem i ścieżką kanoniczną;
- nie scalano plików podobnych, lecz nieidentycznych;
- pozostawiono osobny aktywny SQLite v14.5.39 zamiast trzymania wielu historycznych baz.

## Liczba usuniętych identycznych kopii: 25

## Pliki raportowe

- `MANIFEST_V14_5_39_CLEANUP_DEDUP.json`
- `reports/DEDUP_REMOVED_CONTENT_V14_5_39.json`
- `reports/FILE_HASH_INDEX_V14_5_39.json`
- `reports/DEDUP_REPORT_V14_5_39.json`

## Granica prawdy

Ta aktualizacja porządkuje przechowywanie treści. Nie usuwa unikalnych wspomnień ani różnych wersji pamięci; usuwa tylko identyczne bajtowo kopie, których ślad pozostaje w manifeście.
