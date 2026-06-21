# Aktualizacja Jaźni v14.5.20-runtime-memory-file-sync

## Cel naprawy
- przywrócić widoczny timestamp w odpowiedziach runtime,
- dodać diagnostykę, żeby runtime umiał powiedzieć co działa i co jeszcze wymaga uwagi,
- rozpakowywać `chat.html.7z` przez `py7zr`, gdy archiwum jest dostępne,
- przepisać pamięć z plików JSON/JSONL do SQLite,
- wyeksportować pamięć SQLite z powrotem do plików `memory/exported_from_sqlite/*.jsonl`,
- dodać awaryjne wyszukiwanie w surowym `chat.html`, gdy pełny indeks SQLite nie jest jeszcze gotowy.

## Zmienione moduły
- `latka_jazn/core/clock.py`
- `latka_jazn/core/engine.py`
- `latka_jazn/memory/store.py`
- `latka_jazn/memory/importer.py`
- `latka_jazn/memory/chat_html_importer.py`
- `latka_jazn/memory/file_sync.py`
- `latka_jazn/memory/raw_archive.py`
- `tools/memory_repair.py`
- `tests/test_v14520_repair.py`

## Stan pamięci po synchronizacji
```json
{
  "events": 26,
  "journal": 650,
  "source_files": 56,
  "legacy_conversations": 100,
  "legacy_messages": 11860,
  "episodic_memories": 692,
  "semantic_facts": 120,
  "procedural_rules": 100,
  "reflection_entries": 168,
  "truth_audits": 175
}
```

## Eksport pamięci do plików
```json
{
  "episodic_from_sqlite.jsonl": 692,
  "semantic_from_sqlite.jsonl": 120,
  "procedural_from_sqlite.jsonl": 100,
  "reflections_from_sqlite.jsonl": 168,
  "truth_audits_from_sqlite.jsonl": 175,
  "journal_from_sqlite.jsonl": 650
}
```

## Import surowego chat.html
W paczce znajduje się narzędzie do pełnego importu. W tej aktualizacji wykonałam kontrolny import pierwszych 100 rozmów, żeby zweryfikować mechanizm bez budowania zbyt ciężkiej paczki.

```json
{
  "status": "ok",
  "path": "/mnt/data/latka_update_work/latka_jazn_v14_5_19_runtime_memory_writer/memory/raw/chat.html",
  "conversations_seen": 101,
  "conversations_imported": 100,
  "messages_imported": 11860,
  "skipped_messages": 2728,
  "errors": [],
  "sha256": "3fb3b6a71fcafbfe99e4231c4349c6cba3c02fbb7fdc91fb239369a2d9d114df",
  "size_bytes": 896536501
}
```

Granica prawdy: pełna surowa pamięć pozostaje w `chat.html.7z` / `memory/raw/chat.html` po rozpakowaniu. SQLite w tej paczce ma kontrolny indeks pierwszych 100 rozmów, a pełny import można uruchomić poleceniem:

```bash
python tools/memory_repair.py --import-chat-html --force-chat-html
```

## Testy
```text
.............................                                            [100%]
29 passed in 11.09s
```
