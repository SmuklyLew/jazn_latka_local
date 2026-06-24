# v14.8.5.000 — version/template reconciliation

Cel: rozpocząć pełną aktualizację po v14.8.4.006 od usunięcia rozjazdów wersji i aktywnych starych szablonów. Ta wersja tworzy centralne źródło prawdy `latka_jazn/version.py`, aktualizuje podstawowe kontrakty runtime oraz dodaje audyt legacy literals.

## Zakres P0

- `VERSION.txt` przechodzi na `v14.8.5.000`.
- `main.py`, `JaznConfig`, `latka_jazn/__init__.py`, active extraction cache i audyty wersji korzystają z jednej linii wersji.
- Aktywne schema_version mają raportować `v14.8.5.000`, nie stare kontrakty `v14.8.2.x` / `v14.8.3.4.093`.
- `tools/audit_legacy_literals_v1485.py` klasyfikuje stare literały jako: aktywny blocker, historia docs, historia zasobów, test do migracji albo review.

## Granica prawdy

Stare wersje wolno zachować w `docs/update_history/`, zasobach historycznych i archiwalnych testach. Nie wolno używać ich jako aktywnej trasy, aktywnego schema_version ani gotowego tekstu odpowiedzi zwykłej rozmowy.

## Testy

```powershell
py -m compileall -q latka_jazn main.py tools/audit_legacy_literals_v1485.py
py -m pytest -q tests/test_v1485_000_version_template_reconciliation.py
```
