# Raport aktualizacji v14.5.24

Wersja: `v14.5.24-runtime-bridge-export-hotfix`

## Problem

Runtime potrafił zwracać odpowiedzi ogólne, które były technicznie poprawne, ale zbyt puste: nie wskazywały, gdzie szukać błędu, jeżeli użytkownik oczekiwał działania pamięci, mostu poznawczego albo osobnego modułu.

## Naprawa

- fallback stał się diagnostyczny i wskazuje konkretne pliki/funkcje;
- pakiet `--cognitive-frame` zawiera `fallback_diagnostics`;
- dodano wbudowany eksport: system-only, memory-only, full;
- aktywna baza SQLite została nazwana dla v14.5.24 i zachowuje zaindeksowaną pamięć;
- testy rozszerzono do 41 przypadków.

## Status testów

`pytest -q` → `41 passed in 17.54s`

## Pliki dodane

- `latka_jazn/tools/package_export.py`
- `tests/test_v14524_runtime_bridge_export_hotfix.py`
- `docs/UPDATE_V14_5_24_RUNTIME_BRIDGE_EXPORT_HOTFIX.md`
- `UPDATE_REPORT_V14_5_24.md`

## Pliki zmienione

- `main.py`
- `latka_jazn/core/engine.py`
- `latka_jazn/core/clock.py`
- `latka_jazn/config.py`
- `latka_jazn/memory/store.py`
- `latka_jazn/memory/importer.py`
- `latka_jazn/memory/runtime_persistence.py`
- `latka_jazn/core/runtime_status.py`
- `README.md`
- `START_CHATGPT_FROM_HERE.txt`
