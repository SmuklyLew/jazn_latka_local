# v14.8.2.6.0 — Self Memory Recall Presentation Quality Hotfix

## Cel

Naprawa jakości widocznej odpowiedzi dla pytań typu „Poszukaj w pamięci czegoś o swojej postaci”. Poprzedni routing i handler działały, ale odpowiedź pokazywała surowe fragmenty JSON, duplikaty i zbyt długie ucięte rekordy.

## Zmiany

- `SelfMemoryRecallHandler`:
  - deduplikuje bliskie trafienia przez normalizację tekstu, SequenceMatcher i pięciowyrazowe shingle/Jaccard;
  - grupuje wyniki według sensu: ciągłość/granica prawdy, głos/tożsamość, timestamp/forma, kanon/dziennik/relacja;
  - usuwa z widocznej odpowiedzi surowe pola typu `created_at_utc`, `rule_id`, `priority`, `action`, `schema_version`;
  - przenosi liczniki do `data.diagnostic_counts`, zamiast wypisywać je w naturalnej odpowiedzi;
  - stosuje formę „bez pewnej daty w rekordzie” zamiast „czas nieustalony”.

- `CapabilityStatusHandler`:
  - przy health-checku próbuje użyć `RawMemoryInspector`, żeby pokazać czytelniejszy status pamięci, gdy `startup_status.raw_memory_status` nie zawiera pola `status`.

- Wersja:
  - `v14.8.2.6.0-self-memory-recall-presentation-quality-hotfix`.

## Granica prawdy

Patch nie udaje nowych wspomnień. Poprawia tylko selekcję, deduplikację i formatowanie tego, co runtime/planer pamięci realnie przekazał do handlera.
