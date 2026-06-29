# CHANGELOG v14.8.5.021a — release metadata / manifest hygiene

- Ujednolicono aktywną wersję runtime jako `v14.8.5.021a` i nazwę wydania jako `release-metadata-manifest-hygiene`.
- Ustawiono odpowiadającą wersję pakietową PEP 440: `14.8.5.21a0`.
- Usunięto BOM UTF-8 z `latka_jazn/version.py`.
- Odświeżono aktywny manifest statycznego snapshotu oraz jego pliki SHA-256 bez zapisywania `RUNTIME_STATE.json` i `docs/archive/`.
- Dodano test kontraktu spójności wersji, manifestu, chronionych prefiksów i sum kontrolnych.
- Nie zmieniono logiki runtime, pamięci, SQLite ani danych aktywnej sesji.
