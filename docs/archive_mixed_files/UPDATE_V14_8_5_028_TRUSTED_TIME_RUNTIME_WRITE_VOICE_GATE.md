# UPDATE v14.8.5.028 — TrustedTimeBridge + RuntimeWriteAccessContract + First-Person Feminine Voice Gate

## Cel

Ten mikro-patch wzmacnia trzy słabe punkty wykryte po odchudzeniu paczki v14.8.5.027:

1. daemon mógł pozostać `active_degraded`, gdy istniejący proces nie dostał świeżego injected trusted timestampu;
2. `memory/sqlite/runtime_write_v1/` został słusznie wyjęty z paczki, ale runtime nadal musi umieć utworzyć czystą bieżącą warstwę zapisu;
3. widoczny głos Łatki może osuwać się w trzecią osobę albo język loadera, zamiast pierwszoosobowej formy żeńskiej.

## Zmiany

- `TrustedTimeBridge`: dodano endpoint daemonu `POST /trusted-time` i CLI bridge, który wstrzykuje timestamp do już działającego daemonu bez restartu.
- `RuntimeWriteAccessContract`: dodano kontrakt statusu i inicjalizacji `runtime_write_v1`; nowy czysty katalog jest tworzony bez przywracania starych shardów/testów.
- `First-Person Feminine Voice Gate`: rozszerzono `VoiceSourceContract` i walidator odpowiedzi o wykrywanie `voice_perspective_mismatch` w zwykłych odpowiedziach.
- Plan 14.8.6.0 pozostaje docelowy dla `MemoryRecallQualityEvaluator` i `Reflection Promotion Policy`; ten patch przygotowuje bezpieczne fundamenty przed tym etapem.

## Granica prawdy

Patch nie importuje prywatnych eksportów, nie robi push/pull do GitHub i nie publikuje SQLite. `runtime_write_v1` jest lokalną warstwą zapisu runtime i wymaga osobnego workflow zgody użytkownika dla trwałego wyniesienia danych poza środowisko.
