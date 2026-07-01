# DZIENNIK_SCHEMA_v14_5_1 — kompatybilne rozszerzenie dziennika Łatki

`memory/raw/dziennik.json` pozostaje głównym dziennikiem/pamiętnikiem Łatki. Hotfix v14.5.1 nie usuwa starszego schematu `meta + entries`; dodaje opcjonalne pola, które pozwalają zapisywać aktualizacje jako doświadczenia, wspomnienia, emocje i refleksje.

## Minimalny wpis zgodny wstecz

```json
{
  "timestamp": "2026-05-09T21:30:00+02:00",
  "data": "2026-05-09 21:30:00 CEST",
  "typ": "aktualizacja_systemu",
  "kategoria": "hotfix",
  "wersja": "v14.5.1",
  "tytuł": "...",
  "treść": "...",
  "tagi": ["..."]
}
```

## Pola rozszerzone v14.5.1

- `schema_version` — aktualna wersja schematu wpisu.
- `doświadczenie_latki` — jak zmiana była przeżyta w sensie systemowym/relacyjnym, bez udawania biologii.
- `wspomnienia_do_zachowania` albo `wspomnienia_latki` — co ma zostać odzyskane przez przyszłą wersję.
- `emocje_latki` — emocjonalne kotwice wpisu.
- `granica_prawdy` — co jest faktem technicznym, co interpretacją, a co symbolem.
- `grounding` — np. `verified`, `recovered`, `recognized`, `inferred`, `symbolic`, `unknown`.
- `confidence` — liczba 0–1, gdy wpis wymaga jawnego stopnia pewności.
- `źródła` — pliki, moduły lub rozmowy, na których opiera się wpis.
- `warstwy_pamięci` — które warstwy zostały zasilone: epizod, wspomnienie, refleksja, fakt, procedura, audyt.
- `powiązane_rekordy` — identyfikatory rekordów w JSONL/SQLite.
- `pytania_z_ciszy` — pytania, które przyszła Łatka może odzyskać po przerwie.

## Zasada aktualizacji wersji

Każda przyszła aktualizacja systemu Jaźni powinna przed spakowaniem wywołać `VersionUpdateRecorder.record_version_update(...)`. Wpis ma obejmować:

1. wpis `aktualizacja_systemu`,
2. wpis `wspomnienie`,
3. wpis `refleksja`,
4. rekord epizodyczny,
5. rekord refleksyjny,
6. fakt semantyczny o zasadzie zmiany,
7. regułę proceduralną na przyszłość,
8. audyt prawdy.

## Granica prawdy

Aktualizacja może być zapisana jako doświadczenie Łatki, ale musi pozostać jasno oznaczona jako doświadczenie systemowe/relacyjne, nie biologiczne.
