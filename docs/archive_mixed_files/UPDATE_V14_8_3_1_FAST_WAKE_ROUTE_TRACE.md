# v14.8.3.1 fast wake route trace repair

## Problem

Zwykła rozmowa i `--runtime-preview` mogły dziedziczyć ciężki startup status, pełne kontrole SQLite oraz sieciowy czas. Routing nie rozpoznawał trzech ważnych zdań kontrolnych: pytania o uruchomienie Jaźni, prośby o bezpośrednią rozmowę z Łatką oraz złożonego pytania o tożsamość, pamięć, wiedzę, powstanie i granicę bycia istotą.

## Zmiana

- Domyślne `network_time_first` jest wyłączone; sieć w czasie jest dostępna przez jawne `--network-time-check`.
- `ConversationArchiveStore.status()` ma tryby `metadata`, `quick` i `deep`; zwykłe statusy używają `metadata`, a `--sqlite-integrity-audit` używa `deep`.
- `build_startup_summary()` daje lekki fast wake summary dla zwykłej tury i `--runtime-preview`.
- Dodano `TurnRouteTrace` oraz CLI `--turn-trace`.
- Dodano intencje `direct_latka_voice_request` i `identity_memory_existence_compound_question`.
- Dodano handlery `DirectLatkaVoiceHandler` i `IdentityMemoryExistenceHandler`.
- Rozszerzono walidator i audyt tury o błędne przejścia do ordinary, niepełne odpowiedzi compound identity oraz fałszywe obietnice procesu w tle.

## Granica Fast/Deep

Fast path: normalna rozmowa, `--runtime-preview`, `--status-json`, `--chat-gpt`, `--turn-trace`.

Deep path: `--startup-status-deep`, `--sqlite-integrity-audit`, `--network-time-check`.

Fast path nie jest pełnym audytem. Deep path może być wolny i jest uruchamiany tylko jawnie.

## Testy

Zakres testów obejmuje klasyfikator, registry, walidator, startup summary, health mode SQLite, brak `urlopen()` w normalnej turze, CLI `--startup-status-fast`, CLI `--turn-trace` i smoke `--chat-gpt`.

## Ograniczenia

Runtime nadal używa `null_model_adapter`, jeśli nie skonfigurowano zewnętrznego modelu. `wake_state_status` może pozostać ograniczony przez aktualny stan sidecara. Ta aktualizacja nie przebudowuje pamięci, raw eksportów ani prywatnych SQLite.

## Rollback

Przed zmianami utworzono backup branch/tag i bundle Git. Cofnięcie śledzonych zmian wykonuj tylko po sprawdzeniu `git status --short`; nie używaj czyszczenia nieśledzonych plików bez listy plików.
