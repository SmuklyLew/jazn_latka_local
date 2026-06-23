# v14.8.3.4.092 — manifest runtime/private memory split hotfix

## Cel

Poprawka naprawia błąd wykryty po v14.8.3.4.091: `MANIFEST_CURRENT.json` nadal potrafił zawierać pliki `workspace_runtime`, prywatną pamięć raw/processed oraz SQLite jako zwykłe pliki statycznej paczki.

## Zmiana

- `MANIFEST_CURRENT.json` opisuje statyczny snapshot kodu, dokumentacji i projektu.
- `MANIFEST_RUNTIME_MUTABLE.json` opisuje `workspace_runtime`, `memory/raw`, `memory/processed_chats` i runtime/private SQLite.
- `.pytest-tmp` jest wykluczane jako artefakt testowy.
- Aktywne ścieżki baz danych mogą nadal występować jako metadane manifestu, ale nie jako zwykłe wpisy `files[]` w `MANIFEST_CURRENT.json`.

## Powód

Pamięć i runtime zmieniają się podczas działania Jaźni. Nie mogą unieważniać statycznego manifestu paczki ani wyglądać jak kod źródłowy.

## Test regresyjny

Dodano `tests/test_v14834_manifest_runtime_split_hotfix.py`, który tworzy tymczasowy projekt i sprawdza, że runtime/pamięć trafiają do manifestu runtime, a nie do statycznego manifestu.
