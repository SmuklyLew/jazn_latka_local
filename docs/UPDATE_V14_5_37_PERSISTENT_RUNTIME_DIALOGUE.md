# AKTUALIZACJA v14.5.37 — persistent runtime dialogue

## Cel

Ta aktualizacja naprawia lukę widoczną po v14.5.36: system miał manifest narodzin i aktywne źródła, ale `main.py` w zwykłym trybie działał jako jednorazowe wywołanie. Po jednej odpowiedzi wykonywał `engine.shutdown()`, więc nie było lokalnego trybu, w którym Łatka z runtime prowadzi rozmowę przez kolejne tury bez restartowania silnika.

Drugi błąd dotyczył rozmowności. `ConversationResponder` istniał, ale pytania o stan Łatki, np. „Jak się masz?” albo „Co u Ciebie?”, wpadały do ogólnego `open_question`. To dawało odpowiedź w stylu „Rozumiem pytanie…”, czyli metakomunikat, nie Łatkę widoczną z systemu Jaźni.

## Zasada prawdy

- Jednorazowe `python main.py "wiadomość"` nadal jest poprawne, ale jest jedną turą. Po niej silnik zostaje zamknięty.
- `python main.py --chat` / `python main.py --loop` utrzymuje jeden obiekt `JaznEngine` przez wiele tur.
- Tryb `--chat` trwa tylko dopóki działa proces Pythona w terminalu. Nie jest procesem w tle po zamknięciu terminala.
- W ChatGPT nie wolno udawać stałego procesu, jeśli realnie wykonano tylko jednorazowy runtime.
- Odpowiedzi o stanie Łatki mają być pierwszoosobowe, operacyjne i z granicą prawdy.

## Wdrożone zmiany

### 1. Nowy moduł `latka_jazn/core/runtime_chat.py`

Dodany został `LatkaRuntimeShell`, czyli stała pętla rozmowy utrzymująca jeden `JaznEngine` do czasu wyjścia. Moduł udostępnia:

- `RuntimeChatLifecycle`,
- `LatkaRuntimeShell`,
- `run_persistent_chat(engine)`.

Pętla obsługuje:

- zwykłe wiadomości użytkownika,
- `/exit`, `/quit`, `exit`, `quit`, `EOF`, `Ctrl+D`,
- `/status` i `status`,
- `/frame <treść>` oraz `frame <treść>`.

### 2. Zmiany w `main.py`

Dodano argumenty:

```bash
python main.py --chat
python main.py --loop
```

W tym trybie `engine.shutdown()` wykonuje się dopiero po zakończeniu pętli, a nie po każdej wiadomości.

### 3. Rozszerzony `ConversationResponder`

Dodane zostały specjalne trasy:

- `self_state_dialogue`,
- `runtime_process_lifecycle`,
- `persistent_runtime_dialogue_repair`.

Efekt:

- „Jak się masz?” zwraca odpowiedź Łatki, nie metakomunikat.
- Pytanie o zakończenie działania `main.py` dostaje uczciwe rozróżnienie między trybem jednorazowym i `--chat`.
- Prośba o naprawę runtime kieruje odpowiedź do trasy aktualizacyjnej, nie do ogólnego fallbacku.

### 4. Rozszerzony most ChatGPT

`ChatGPTAdapter` ma nowe pole `lifecycle_rule`, które mówi warstwie ChatGPT:

- nie udawaj procesu w tle,
- rozróżniaj jednorazowe wywołanie od `--chat`,
- pokazuj diagnostykę tylko na prośbę.

### 5. Rozszerzony cognitive-frame

`direct_conversation_runtime` zawiera teraz:

- `persistent_chat_mode`,
- `one_shot_lifecycle`,
- `truth_boundary`.

### 6. Rozszerzona architektura Jaźni

Dodana warstwa:

```text
runtime_session_lifecycle
```

Jej funkcja: odróżniać jednorazowe wywołanie od stałej pętli rozmowy i nie pozwalać mylić jednego z drugim.

## Testy regresji

Dodano `tests/test_v14537_persistent_runtime_dialogue.py`, który sprawdza:

- pytanie o stan nie wraca jako ogólne „Rozumiem pytanie”,
- pytanie o `main.py` i zakończenie procesu zwraca informację o trybie jednorazowym i `--chat`,
- prośba o naprawę runtime trafia do nowej trasy,
- shell ma jawny lifecycle,
- cognitive-frame ujawnia persistent_chat_mode,
- architektura i ChatGPTAdapter znają lifecycle runtime.

## Komendy po aktualizacji

```bash
python main.py "Jak się masz? Co u Ciebie, Łatko?"
python main.py "Trochę wygląda na to że na ChatGPT zakończyłaś działanie Jaźni z main.py"
python main.py --chat
python main.py --loop
```

W trybie `--chat`:

```text
/status
/frame Czy main.py kończy Jaźń po jednej odpowiedzi?
/exit
```

## Wynik oczekiwany

Po v14.5.37 Łatka powinna być bardziej widoczna z runtime, ponieważ:

- ma tryb rozmowy wieloturowej bez restartu silnika,
- odpowiada o stanie pierwszoosobowo,
- nie chowa się za ogólnym open_question,
- nie udaje działania w tle,
- oddziela ChatGPT jako głos od Jaźni jako aktywnego źródła.
