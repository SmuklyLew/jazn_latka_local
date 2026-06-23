# Raport patcha v14.8.3.4.091 — memory/timestamp bridge repair

Data: 2026-06-23 20:55 CEST / Europe/Warsaw

## Zakres

Patch naprawia trzy praktyczne problemy:

1. widoczna odpowiedź `--chat-gpt` nie może zgubić `timestamp_header` z runtime;
2. finalny payload mostu ChatGPT jest naprawiany i walidowany przed zwrotem JSON;
3. recall pamięci w zwykłej turze może korzystać z `conversation_archive_v1/FTS` i przekazywać treściowe fragmenty, nie tylko liczniki.

## Zmienione pliki

```text
M	MANIFEST_CURRENT.json
M	MANIFEST_RUNTIME_MUTABLE.json
M	SHA256SUMS
M	SHA256SUMS_STATIC
M	VERSION.txt
A	docs/UPDATE_V14_8_3_4_091_MEMORY_TIMESTAMP_BRIDGE_REPAIR.md
M	latka_jazn/__init__.py
M	latka_jazn/config.py
M	latka_jazn/core/engine.py
M	latka_jazn/core/memory_recall_presenter.py
M	latka_jazn/core/runtime_session.py
M	latka_jazn/core/session_provenance.py
M	latka_jazn/memory/memory_recall_contract.py
M	main.py
A	tests/test_v14834_memory_timestamp_bridge_repair.py
M	tools/refresh_current_manifest.py
```

## Najważniejsze zmiany techniczne

- `repair_final_visible_integrity()` w `latka_jazn/core/session_provenance.py` przywraca/prefiksuje timestamp i synchronizuje `runtime_provenance.visible_answer_text`.
- `JaznRuntimeSession.process_user_text()` używa naprawy przed walidacją finalnej odpowiedzi.
- `main.py --chat-gpt` zwraca jawny błąd JSON `runtime_turn_failed`, jeśli runtime przerwie pojedynczą turę, zamiast ubijać cały most.
- `JaznEngine._conversation_archive_context_hits()` dopina `ConversationArchiveStore.search(..., include_snippets=True)` do zwykłego memory recall.
- `MemoryRecallPresenter` i `MemoryRecallContractBuilder` obsługują `conversation_archive_hits`.
- `tools/refresh_current_manifest.py` poprawia aktywne ścieżki manifestu z dawnego `chat_context.sqlite3` na układ `conversation_archive_v1+fts_v1+staging_v1+runtime_write_v1`.

## Testy wykonane

- `python -m compileall -q latka_jazn main.py tools/refresh_current_manifest.py` — OK.
- `python -m pytest -q tests/test_v14834_memory_timestamp_bridge_repair.py` — 5 passed.
- Smoke `main.py --chat-gpt --no-carryover` — OK: `final_visible_text` zaczyna się od `trace.timestamp_header`, `final_visible_integrity.valid=true`.
- `python main.py --chat-jsonl` — OK: kod 2 i komunikat migracyjny do `--chat-gpt`.
- `git apply --check LATKA_JAZN_v14_8_3_4_091_MEMORY_TIMESTAMP_BRIDGE_REPAIR.patch` na baseline wybranych plików — OK.

## Status aktywnego folderu po patchu

```json
{
  "version": "v14.8.3.4.091",
  "active_root": "/mnt/data/jazn_work",
  "start_file": "main.py",
  "manifest_current_sha256": "cbde96213a71f762ea010310b73e4bf236be700d67f8269a76e0b2e9aebacd83",
  "should_reuse_existing_extraction": true,
  "cache_hit_reasons": [
    "active_root_exists",
    "VERSION.txt_exists",
    "start_file_exists",
    "MANIFEST_CURRENT.json_exists",
    "marker_active_root_matches",
    "marker_version_matches",
    "active_marker_written_now"
  ],
  "cache_miss_reasons": [],
  "storage_layout": "conversation_archive_v1+fts_v1+staging_v1+runtime_write_v1",
  "active_database": "memory/sqlite/conversation_archive_v1/conversation_archive_manifest.sqlite3",
  "active_runtime_write_database": "memory/sqlite/runtime_write_v1/runtime_memory.sqlite3",
  "active_conversation_fts": "memory/sqlite/conversation_fts_v1/conversation_fts_0001.sqlite3",
  "active_staging_database": "memory/sqlite/staging_v1/staging_memory_0001.sqlite3"
}
```

## Ograniczenia uczciwe

- Kontener nie miał DNS do `github.com`, więc nie mogłem zrobić zwykłego `git clone`. Repo sprawdziłem przez connector GitHub, a roboczy patch zrobiłem na paczce ZIP v14.8.3.4.090 z `/mnt/data`.
- GitHub `master` widoczny przez connector wskazywał commit `e58f227...` i wersję `v14.8.3.1`, natomiast dostarczony ZIP ma wersję `v14.8.3.4.090`. Patch jest przygotowany względem ZIP-a `v14.8.3.4.090`, nie względem starszego `master`.
- Pełne, naiwne ładowanie 3,5 GB pamięci do RAM zresetowało środowisko. Po tym duże pliki pamięci były traktowane bezpiecznie: przez ZIP/metadane, rozmiary, SQLite integrity, a nie jednorazowe wczytanie do pamięci procesu.

## Artefakty

- Patch SHA256: `8f04959ad7cc76280ad17c816a9a3da45a65eb35419b24d74f7f1d342c59aa4d`
- Audit SHA256: `d641b98be9ee5729e90a4739426af0cb4aeb0258b65f2425b25a82ef1a15b8ce`
