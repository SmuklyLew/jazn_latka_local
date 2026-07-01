# v14.5.26 — Full Completeness Repair

Ta aktualizacja naprawia problem kontroli kompletności paczki po zmianie wersji.

## Zasady

1. Pełna paczka ma zawierać system, pamięć, workspace runtime oraz surową pamięć `memory/raw/chat.html.7z`.
2. Zmiana nazwy głównej bazy SQLite nie może wyglądać jak utrata danych. Poprzednie bazy są zachowywane w `workspace_runtime/previous_versions/`.
3. Rozmiar ZIP nie jest jedynym dowodem kompletności. Liczą się: lista plików, suma rozmiarów bez kompresji, hash plików krytycznych i liczby rekordów SQLite.
4. Surowe zdarzenia append-only pozostają dokładne i nie są zastępowane streszczeniem.
5. Jeżeli źródło jest ucięte, system ma oznaczyć ucięcie, a nie dopisywać brakujący tekst własną narracją.

## Pliki kontrolne

- `reports/PACKAGE_COMPLETENESS_AUDIT_V14_5_26.json`
- `MANIFEST_V14_5_26_FULL_COMPLETENESS_REPAIR.json`
- `tests/test_v14526_package_completeness.py`
