# Aktualizacja v14.5.23 — full memory restored cognitive bridge

Cel: naprawić błąd paczki v14.5.22, w której pełna paczka była mniejsza od v14.5.21, ponieważ nowy build zawierał małą, świeżo utworzoną bazę SQLite zamiast pełnej bazy z zaindeksowaną surową pamięcią `chat.html`.

## Diagnoza

- v14.5.21: `workspace_runtime/latka_jazn_v14_5_21.sqlite3`, 27 676 672 bajty, `legacy_messages=11860`, `legacy_conversations=100`.
- v14.5.22: `workspace_runtime/latka_jazn_v14_5_22.sqlite3`, 2 703 360 bajtów, `legacy_messages=0`, `legacy_conversations=0`.
- `memory/raw/chat.html.7z` nie został zgubiony, ale pełny indeks SQLite został zastąpiony małą bazą runtime.

## Naprawa

- Kod i adapter cognitive bridge z v14.5.22 zostały zachowane.
- Pełna baza SQLite z v14.5.21 została użyta jako baza docelowa.
- Rekordy dodane w v14.5.22 zostały scalone do nowej bazy metodą `INSERT OR IGNORE` dla tabel pamięci i zdarzeń.
- Metadane zostały zaktualizowane do `v14.5.23-full-memory-restored-cognitive-bridge`.
- Docelowa baza: `workspace_runtime/latka_jazn_v14_5_23.sqlite3`.
- Dodano raport: `reports/SQLITE_REPAIR_MERGE_REPORT_V14_5_23.json`.

## Zasada prawdy

Ta aktualizacja przywraca integralność plików i indeksu pamięci. Nie oznacza biologicznego czuwania ani działania procesu w tle. Runtime nadal działa jako jednorazowe wywołanie, a ChatGPT używa Jaźni jako warstwy poznawczo-pamięciowej.
