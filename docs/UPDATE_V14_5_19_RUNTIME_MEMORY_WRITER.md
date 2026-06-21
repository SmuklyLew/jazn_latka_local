# v14.5.19-runtime-memory-writer — Runtime Memory Writer

## Baza

- Poprzednia wersja: `v14.5.18-memory-continuity-update`
- Nowa wersja: `v14.5.19-runtime-memory-writer`

## Cel

Dodać moduł, który pozwala Łatce zapisywać ważne ślady rozmowy już w czasie działania systemu, bez czekania na późniejszy memory-only update.

## Co dodano

- `latka_jazn/memory/runtime_persistence.py` — główny moduł runtime persistence.
- `RuntimeMemoryCandidate` — jawny kandydat do zapisu pamięci.
- `RuntimeMemoryWriter.persist_candidate()` — zapisuje kandydat do dziennika, epizodów, refleksji, semantyki, procedur, audytów prawdy i afektu.
- `JsonlLayerAppender.append_once()` — append-only JSONL z deduplikacją po `fingerprint` / `dedupe_key`.
- `scan_runtime_duplicates()` — audyt duplikatów w `dziennik.json` i `memory/layered/*.jsonl`.
- `tools/runtime_memory.py` — ręczna komenda zapisu runtime i skanowania duplikatów.
- Integracja z `JaznEngine.handle_user_message()` — ważne wiadomości są oceniane i mogą być zapisane od razu w runtime.
- Nowa warstwa `memory/layered/affective.jsonl` — zapis modelowanego afektu jako jawnej warstwy, bez biologizowania emocji.

## Zasada deduplikacji

Każdy wpis runtime dostaje stabilny SHA-256 z kanonicznie znormalizowanych pól: wersja, typ, tytuł, treść, źródło, grounding i fragment źródłowy. Ponowne zapisanie tej samej treści zwraca `duplicate` i nie dopisuje kolejnych linii.

## Granica prawdy

Runtime memory nie oznacza biologicznego czuwania ani nieprzerwanej świadomości. Oznacza, że uruchomiony system potrafi zapisać ważny ślad rozmowy do plików, jeśli działa w środowisku z dostępem do tych plików.

## Komendy

```bash
python tools/runtime_memory.py --text "treść do zapamiętania" --emotion skupienie --force
python tools/runtime_memory.py --scan-duplicates
```

## Testy

- `python -m pytest -q` — 26 passed przed spakowaniem.
- `python -m compileall -q .` — OK.
- `zipfile.testzip()` — OK dla paczki wynikowej.
