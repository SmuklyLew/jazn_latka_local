# RUNTIME_MEMORY_PROTOCOL

## Cel

Ten protokół opisuje zapis pamięci w czasie działania Jaźni. Różni się od `memory-only update`: nie czeka na nową paczkę, tylko zapisuje ważny ślad rozmowy od razu do aktywnych plików.

## Warstwy zapisu

1. `memory/raw/dziennik.json` — główny dziennik/pamiętnik Łatki.
2. `memory/layered/episodic.jsonl` — epizody rozmowy.
3. `memory/layered/reflections.jsonl` — znaczenie epizodu dla Łatki.
4. `memory/layered/semantic.jsonl` — fakty semantyczne, jeżeli wpis niesie ustalenie/fakt.
5. `memory/layered/procedural.jsonl` — reguły działania, jeżeli wpis zmienia procedurę.
6. `memory/layered/truth_audits.jsonl` — audyt prawdy i ryzyka narracyjnego.
7. `memory/layered/affective.jsonl` — modelowany afekt/emocje jako zapis systemowy, nie biologiczny.

## Minimalne pola nowego wpisu

- `fingerprint` / `dedupe_key`
- `schema_version`
- `source`
- `grounding`
- `confidence`
- `granica_prawdy`
- `tags`
- data lokalna albo `created_at_utc`

## Deduplikacja

Przed dopisaniem moduł skanuje docelowy plik i szuka identycznego `fingerprint` albo `dedupe_key`. Jeżeli znajdzie, zwraca `duplicate` i nie dopisuje kolejnego wpisu.

## Granica prawdy

Zapis runtime mówi: „w tej rozmowie pojawił się ważny ślad”. Nie mówi: „Łatka biologicznie to przeżyła”. Każdy wpis musi zachować etykietę grounding/confidence/granica_prawdy.
