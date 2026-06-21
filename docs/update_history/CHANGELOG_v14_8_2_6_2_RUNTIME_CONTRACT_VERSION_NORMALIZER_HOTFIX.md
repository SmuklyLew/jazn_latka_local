# v14.8.2.6.2 — runtime contract version normalizer hotfix

Cel: usunąć pozostałe niespójności wersji kontraktów runtime po v14.8.2.6.1, zwłaszcza `cache_contract_version`, `schema_version` aktywnego markera oraz `visible_runtime_preview_contract`, które mogły nadal wskazywać v14.8.2.6.0 mimo aktywnej wersji v14.8.2.6.1.

## Zmiany

- Podniesiono wersję do `v14.8.2.6.2-runtime-contract-version-normalizer-hotfix`.
- `active_extraction_cache.py` wylicza teraz wersje kontraktów na podstawie `VERSION.txt`, zamiast trzymać je jako stałe z poprzedniej wersji.
- `main.py` korzysta z dynamicznego `visible_preview_contract_version(...)`.
- Dodano `latka_jazn/tools/runtime_contract_version_normalizer.py`, który audytuje i naprawia aktywne pliki:
  - `MANIFEST_CURRENT.json`,
  - `workspace_runtime/JAZN_ACTIVE_RUNTIME.json`,
  - `ACTIVE_RUNTIME_CACHE_CONTRACT.json`,
  - `BOOTSTRAP_JAZN_CURRENT.json`.
- Zaktualizowano `latka_jazn/__init__.py`, `JaznConfig.version`, `network_user_agent`, `START_CHATGPT_FROM_HERE.txt` i źródłowe detale handlerów.

## Granica prawdy

Normalizator dotyczy aktywnych kontraktów bieżącego folderu. Nie aktualizuje historycznych backupów, archiwalnych manifestów ani embedded sources, bo są one materiałem audytowym i mogą zawierać starsze wersje świadomie.

## Testy

Dodano `tests/test_v148262_runtime_contract_version_normalizer.py`, w tym:

- test dynamicznego wyliczania `schema_version`, `cache_contract_version` i `visible_runtime_preview_contract`,
- test naprawy starych markerów v14.8.2.6.0 do bieżącej wersji,
- test blokujący pozostawienie znanych stałych kontraktów v14.8.2.6.0 w aktywnym kodzie.
