# UPDATE REPORT — v14.8.3.4.089 — manifest excluded detail privacy hotfix

## Cel

Naprawiono `tools/refresh_current_manifest.py`, żeby manifest nie zapisywał szczegółowych ścieżek wykluczonych katalogów technicznych takich jak `.git/`, `__pycache__/`, `.pytest_cache/`, `.mypy_cache/` i `.ruff_cache/`.

## Problem

Po odświeżeniu manifestu `MANIFEST_CURRENT.json` zawierał wpisy z `.git/logs`, `.git/refs` oraz cache testów. Te pliki były formalnie wykluczone z głównej listy `files`, ale nadal trafiały do `excluded_files`, co czyniło manifest niestabilnym i zbyt lokalnym.

## Zmiana

- Dodano licznik `excluded_file_count`, który zachowuje całkowitą liczbę wykluczonych plików.
- Szczegóły ścieżek dla `generated_cache_directory` są tłumione.
- Dodano zagregowane pola:
  - `excluded_file_detail_count`
  - `excluded_file_detail_suppressed_count`
  - `excluded_file_detail_suppressed_summary`
- Dodano test regresyjny `tests/test_v14834089_manifest_excluded_detail_privacy.py`.
- Podniesiono wersję do `v14.8.3.4.089`.

## Granica prawdy

Manifest nadal może zawierać legalne ścieżki `runtime_preview` w nazwach historycznych dokumentów/testów, jeśli są częścią repo. Nie powinien jednak zawierać lokalnych `.git/logs`, `.git/refs` ani cache jako szczegółowych wpisów `excluded_files`.
