# v14.8.2.6.1 — non-memory-intent memory gating hotfix

## Cel

Naprawić przeciek kontekstu pamięciowego w turach, które nie są pytaniami o pamięć. Po v14.8.2.6.0 finalna odpowiedź health-check była poprawna, ale wewnętrzne `self_state_runtime.active_memories.query_terms` nadal dostawało stare rozszerzenia tematyczne, np. `spacer`, `Olsztyn`, `Ogrodzieniec`, `jelen`, `zamek`.

## Zmiany

- Dodano bramkę pamięci w `JaznEngine._gated_memory_context_for_chatgpt`.
- Dla intencji:
  - `runtime_health_check_after_update`,
  - `capability_status_question`,
  - `internet_access_question`
  runtime nie uruchamia już pełnego `MemorySearchPlanner` ani rozszerzeń tematów pamięciowych.
- Dla intencji pamięciowych, np. `self_memory_recall_request`, realne wyszukiwanie pamięci zostaje zachowane.
- `MemoryUseGate` dostał jawne zbiory `NON_MEMORY_INTENTS` i `MEMORY_REQUIRED_INTENTS`.
- Wersja systemu podniesiona do `v14.8.2.6.1-non-memory-intent-memory-gating-hotfix`.

## Granica prawdy

Brak wyszukiwania pamięci w turze statusowej nie oznacza braku pamięci w systemie. Oznacza tylko, że dana intencja nie powinna mieszać odpowiedzi diagnostycznej z treścią wspomnień.

## Testy

Dodano `tests/test_v148261_non_memory_intent_memory_gating.py`, które sprawdza:

- health-check nie dodaje do `query_terms` spacerów/Olsztyna/Ogrodzieńca,
- pytania o możliwości i internet nie uruchamiają retrievalu pamięci,
- pytanie o postać Łatki nadal używa realnego kontekstu pamięci,
- wersja i user-agent są zaktualizowane do v14.8.2.6.1.
