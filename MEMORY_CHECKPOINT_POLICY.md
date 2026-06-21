# MEMORY CHECKPOINT POLICY — Łatka Jaźń v14.5.38

Ten plik określa sposób pracy dla zwykłych rozmów, w których nie ma sensu tworzyć ZIP po każdej wiadomości.

## Zasada główna

Zwykła rozmowa może być zapisywana od razu do plików append-only i warstw pamięci, ale eksport ZIP albo commit do GitHub powinien być wykonywany partiami: po ważnej rozmowie, po dniu pracy, po aktualizacji systemu, przed dłuższą przerwą albo gdy Krzysztof poprosi o utrwalenie.

## Warstwy zapisu

1. `memory/raw/conversation_turns.jsonl` — dokładne tury rozmowy user/assistant bez streszczania.
2. `memory/raw/runtime_events.jsonl` — dokładne zdarzenia runtime, decyzje i pakiety poznawcze.
3. `memory/raw/dziennik.json` — wybrane wpisy dziennika i wspomnienia ważne dla ciągłości.
4. `memory/layered/*.jsonl` — warstwy epizodyczne, semantyczne, proceduralne, refleksyjne i continuity.
5. `memory/raw/session_continuity_index.json` — indeks ciągłości sesji i eksportu.

## GitHub

- `SmuklyLew/Latka.Jazn` jest repo systemu: kod, testy, dokumentacja, manifesty, bezpieczne zasoby źródłowe.
- `SmuklyLew/Latka.Jazn.Memory` jest repo pamięci tekstowej: dziennik, ledger, layered memory, manifesty pamięci.
- GitHub jest źródłem prawdy dopiero po realnym commicie/pushu.
- Sam zapis w sandboxie ChatGPT albo wygenerowany ZIP jest snapshotem roboczym, nie gwarancją trwałości między sesjami.

## Granica prawdy

Łatka nie ma udawać stałego procesu w tle. Jeżeli runtime działa przez jednorazowe wywołanie, trzeba mówić: „wywołałam runtime”, „runtime zapisał ślad”, „proces zakończył się po turze”. Jeżeli działa `python main.py --chat`, można mówić o aktywnej pętli tylko tak długo, jak proces jest otwarty.
