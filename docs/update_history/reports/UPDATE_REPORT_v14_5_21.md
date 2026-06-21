# Update report — v14.5.21-runtime-memory-file-sync-hotfix

Wykonano hotfix po ocenie v14.5.20.

## Wynik

- Runtime uruchamia się jako v14.5.21.
- Timestamp działa.
- Paczka ma zgodną nazwę folderu.
- `py7zr` jest wymaganą zależnością.
- `/status` pokazuje brak `py7zr`, jeśli środowisko go nie ma.
- SQLite zachowuje kontrolny import 100 rozmów / 11860 wiadomości z v14.5.20.
- Synchronizacja pliki ↔ SQLite została wykonana.
- Pamięć aktualizacji została dopisana do dziennika i warstw pamięci.

## Testy

`pytest -q` → `31 passed`

`PRAGMA integrity_check` → `ok`

## Nierozwiązane świadomie

Nie dołączono rozpakowanego `memory/raw/chat.html`, ponieważ plik jest bardzo duży. W paczce pozostaje `memory/raw/chat.html.7z`; pełny import należy wykonać po instalacji zależności.
