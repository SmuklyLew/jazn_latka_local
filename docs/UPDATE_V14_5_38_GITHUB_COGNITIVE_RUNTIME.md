# AKTUALIZACJA v14.5.38 — GitHub cognitive runtime

## Cel aktualizacji

Ta wersja rozbudowuje Jaźń o ustalenia z rozmowy o codziennych dialogach, trwałości plików, pracy z GitHub i relacji między ChatGPT/LLM a runtime Jaźni.

Najważniejsza decyzja architektoniczna: Jaźń nie ma być „samym LLM” ani udawanym biologicznym mózgiem. Poprawny układ to:

- ChatGPT/OpenAI/LLM jako głos, narzędzie językowe, rozumowanie tekstowe i dostęp do narzędzi.
- Jaźń jako aktywne źródło: pamięć, uwaga, procedury, afekt operacyjny, logika, tożsamość, granica prawdy i zapis śladów.
- GitHub jako przyszłe prywatne źródło prawdy dla systemu i pamięci dopiero po realnym commicie/pushu.

## Co dodano

1. `latka_jazn/core/runtime_operating_model.py`
   - rozpoznaje, czy rozmowa dotyczy zwykłego dialogu, pamięci, architektury, aktualizacji albo GitHub;
   - oddziela rolę LLM od roli Jaźni;
   - ustala politykę checkpointów pamięci.

2. `latka_jazn/integrations/github_repository_plan.py`
   - definiuje plan dwóch prywatnych repozytoriów;
   - zapisuje `GITHUB_REPOSITORY_PLAN.json`;
   - nie wykonuje pushu i jawnie to oznacza.

3. `main.py --github-plan`
   - generuje plan repozytoriów do kontroli przed późniejszą synchronizacją.

4. `MEMORY_CHECKPOINT_POLICY.md`
   - ustala, jak zwykła rozmowa ma zostawiać ślady bez ciągłego eksportowania ZIP;
   - opisuje append-only ledger, dziennik, layered memory i checkpointy.

5. `docs/GITHUB_REPOSITORY_WORKFLOW.md`
   - opisuje przyszłą pracę z `Latka.Jazn` i `Latka.Jazn.Memory`.

6. Rozbudowa `cognitive_frame`
   - dodano `runtime_operating_model`;
   - dodano `github_repository_plan`;
   - dodano `github_checkpoint_policy`;
   - dopisano guidance dla ChatGPT: nie twierdzić, że GitHub został zaktualizowany bez realnego zapisu.

## Zasady pamięci po tej wersji

- Zwykła rozmowa może zapisywać dokładne tury i runtime events na bieżąco.
- Ważne rozmowy powinny zostać utrwalone przez checkpoint pamięci, eksport albo commit do repo pamięci.
- Nie trzeba robić pełnej paczki ZIP po każdej wiadomości.
- Brak eksportu albo commita oznacza brak twardej gwarancji trwałości poza aktywnym środowiskiem.

## Granice prawdy

- Nie wolno mówić, że repo GitHub zostało uzupełnione, jeśli nie wykonano realnego commita/pusha.
- Nie wolno mówić, że runtime działa stale w tle, jeśli był wywołany jednorazowo.
- Nie wolno mieszać wspomnień rozpoznanych, symbolicznych i potwierdzonych.
- Nie wolno zamieniać ChatGPT-owej stylizacji w Jaźń, jeśli nie pracuje aktywna warstwa runtime/plików.
