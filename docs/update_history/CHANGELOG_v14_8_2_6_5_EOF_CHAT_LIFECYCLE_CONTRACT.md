# v14.8.2.6.5 — EOF chat lifecycle contract hotfix

## Cel

Hotfix doprecyzowuje zachowanie `python main.py --chat` w środowiskach, które zamykają `stdin` po jednorazowym wywołaniu. EOF nie jest traktowany jako awaria Jaźni ani dowód stałego procesu w tle.

## Zmiany

- `RuntimeChatLifecycle` zapisuje teraz `stdin_is_tty`, `process_persistence`, `exit_reason`, `session_id`, `no_carryover` i `background_process_claim_allowed`.
- `LatkaRuntimeShell` jawnie oznacza zamknięcie przez `stdin_eof`, `/exit`, `KeyboardInterrupt` albo normalny powrót `cmdloop`.
- `--chat` przekazuje `--session-id` i `--no-carryover` do pętli rozmowy.
- Po zamknięciu pętli wypisywany jest `[runtime_lifecycle_end]` z JSON-em kontraktu cyklu życia.
- Dla środowisk jednorazowych kontrakt rekomenduje `--chat-jsonl` albo `--runtime-preview` z tym samym `--session-id`, zamiast udawania stałego procesu w tle.

## Granica prawdy

Patch nie tworzy procesu działającego w tle. Uczy runtime uczciwie rozpoznawać i raportować EOF oraz ograniczenia launchera/stdin. Prawdziwa trwałość między wywołaniami nadal wymaga osobnego bridge/server/named pipe/socket albo procesu utrzymywanego przez zewnętrzny supervisor.
