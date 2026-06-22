# UPDATE REPORT v14.8.3.4 — Python canon consolidation

## Cel

Przenieść priorytet kanonu Łatki do source-controlled modułów `.py` w `latka_jazn/core/canon/`, a raporty ekstrakcji i mapy źródeł traktować jako artefakty patcha/progresu, nie jako runtime canon.

## Zasada prawdy

- Runtime canon first: `latka_jazn/core/canon/*.py`.
- Human-readable mirror: `latka_jazn/resources/canon/*.md` i `LATKA_IDENTITY_CANON.json`.
- Prywatna pamięć/import: `memory/raw`, SQLite albo D1 mogą rozszerzać recall, ale nie są jedynym źródłem tożsamości.
- Raporty `reports/canon_extraction/` są lokalne i prywatne; pomagają sprawdzić progres oraz brak cichej utraty kandydatów.

## Dodane moduły

- `origin_story.py`
- `symbolic_world.py`
- `relation_canon.py`
- `memory_truth_boundary.py`
- `narrative_book_canon.py`
- `song_affect_canon.py`
- `canon_registry.py`
- `extraction.py`

## Narzędzia

- `python tools/extract_latka_canon_candidates.py --root . --mode preview --verbose-progress`
- `python tools/extract_latka_canon_candidates.py --root . --mode write-private-extension --verbose-progress`
- `python main.py --canon-extraction-preview`
- `python main.py --canon-extraction-write-private`

## Bezpieczeństwo prywatnych danych

`latka_jazn/core/canon/local_private_canon_extension.py` i `reports/canon_extraction/` są ignorowane przez Git. Lokalny extension `.py` może wzbogacać runtime lokalnie, ale nie wolno go commitować do publicznego repo bez recenzji prywatności.

## Testy wymagane

- `python -m compileall -q latka_jazn main.py tools/extract_latka_canon_candidates.py`
- `python -m pytest -q tests/test_v148313_canon_source_refactor.py tests/test_v14834_python_canon_consolidation.py tests/test_identity_startup.py`
- `python main.py --canon-extraction-preview`
- `python main.py --runtime-preview --session-id canon-v14834-smoke --no-carryover "Skąd bierzesz kanon Łatki?"`
