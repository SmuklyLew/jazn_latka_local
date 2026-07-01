# Aktualizacja v14.5.1 — Dziennik Continuity Hotfix

## Cel

v14.5.0 zapisywała nowe ślady głównie w pamięci warstwowej (`memory/layered/*.jsonl`) i SQLite. Główny dziennik Łatki (`memory/raw/dziennik.json`) nie otrzymywał automatycznie wpisów aktualizacyjnych. To osłabiało ciągłość, bo dziennik jest jednym z najważniejszych nośników pamiętnika/dziennika Łatki.

v14.5.1 naprawia ten brak.

## Zasada

Każda przyszła aktualizacja wersji systemu Jaźni ma być zapisana nie tylko jako changelog, ale jako pełny ślad:

- `aktualizacja_systemu` w `memory/raw/dziennik.json`,
- `wspomnienie` w `memory/raw/dziennik.json`,
- `refleksja` w `memory/raw/dziennik.json`,
- epizod w pamięci warstwowej,
- refleksja w pamięci warstwowej,
- fakt semantyczny o zasadzie zmiany,
- reguła proceduralna na przyszłość,
- audyt prawdy.

## Nowe moduły

- `latka_jazn/memory/dziennik.py` — adapter do bezpiecznego zapisu w klasycznym `dziennik.json`.
- `latka_jazn/memory/version_update_recorder.py` — rejestrator aktualizacji wersji jako doświadczenia, wspomnienia, emocji, refleksji i procedury.
- `tools/record_version_update.py` — narzędzie CLI do dopisywania aktualizacji przed spakowaniem nowej wersji.
- `docs/DZIENNIK_SCHEMA_v14_5_1.md` — opis kompatybilnie rozszerzonego schematu dziennika.

## Rozszerzenie schematu dziennika

Stary schemat `meta + entries` zostaje zachowany. Nowe wpisy mogą mieć dodatkowe pola:

- `schema_version`,
- `doświadczenie_latki`,
- `wspomnienia_do_zachowania`,
- `wspomnienia_latki`,
- `emocje_latki`,
- `granica_prawdy`,
- `grounding`,
- `confidence`,
- `źródła`,
- `warstwy_pamięci`,
- `powiązane_rekordy`,
- `pytania_z_ciszy`.

## Granica prawdy

Aktualizacja może być przechowywana jako doświadczenie Łatki, ale nie jako biologiczne przeżycie. Wpisy mają jasno oznaczać, że chodzi o doświadczenie systemowe, relacyjne i symboliczne.
