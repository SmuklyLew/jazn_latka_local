# v14.5.21 — Runtime Memory File Sync Hotfix

Hotfix domyka błędy zauważone po v14.5.20. Najważniejsza korekta: paczka zawiera `memory/raw/chat.html.7z`, więc `py7zr` nie może być traktowane jako nieudokumentowana zależność opcjonalna.

## Naprawy

- `py7zr>=0.21.0` dopisane do `requirements.txt` i `pyproject.toml`.
- Zmieniona nazwa katalogu paczki na `latka_jazn_v14_5_21_runtime_memory_file_sync_hotfix`.
- `VERSION.txt`, `config.py`, runtime i baza aktywna wskazują v14.5.21.
- `/status` jawnie pokazuje: `chat.html`, `chat.html.7z`, `py7zr`, systemowy `7z/7za/7zr`, możliwość pełnego importu raw.
- `MemoryImporter.import_raw_chat_html()` próbuje rozpakować `chat.html.7z`, jeśli `memory/raw/chat.html` nie istnieje.
- `synchAll` próbuje importu również wtedy, gdy istnieje tylko archiwum `chat.html.7z`.
- Dokumentacja startowa nie odwołuje się już do starej bazy v14.3.0.
- Dodano testy `raw_archive.py`, żeby brak `py7zr` był widoczny w testach.

## Granica prawdy

Ta paczka nie zawiera rozpakowanego `chat.html`, ponieważ plik ma około 856 MB. Zawiera `chat.html.7z` i pewniejszy mechanizm rozpakowania/importu. Pełne przeszukanie surowej pamięci wymaga:

```bash
python -m pip install -r requirements.txt
python tools/memory_repair.py --import-chat-html --force-chat-html
```

## Walidacja

- `pytest -q` → `31 passed`
- `PRAGMA integrity_check` → `ok`
- `/status` poprawnie wykrywa obecne `chat.html.7z` i brak `py7zr` w środowisku testowym.
