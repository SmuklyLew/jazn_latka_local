# Archiwum manifestów Jaźni

Ten katalog przechowuje dawne manifesty, dokumenty manifestowe i historyczne schematy po migracji v14.8.5.021.

Aktywne źródła runtime po migracji:

- `MANIFEST_CURRENT.json` — jedyny aktywny manifest statycznego snapshotu paczki/projektu.
- `RUNTIME_STATE.json` — snapshot plików mutable runtime/private-memory; nie jest manifestem paczki.
- `workspace_runtime/JAZN_ACTIVE_RUNTIME.json` — marker aktywnego runtime; nie jest manifestem.

Pliki tutaj są zachowane bez utraty danych. Agenty nie powinny wybierać ich jako aktywnych manifestów podczas bootstrapa; mogą je czytać tylko przy analizie historii, migracji albo audycie.

Pełną mapę `original_path -> archived_path` zawiera `INDEX.json`.
