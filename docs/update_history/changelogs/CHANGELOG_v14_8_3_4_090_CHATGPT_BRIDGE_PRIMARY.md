# CHANGELOG v14.8.3.4.090 — ChatGPT bridge primary

- Zmieniono główny wsadowy most ChatGPT z `--chat-jsonl` na `--chat-gpt`.
- Usunięto aktywną flagę `--chat-jsonl` z parsera CLI; stara flaga daje komunikat migracyjny.
- Rozszerzono wejście mostu o `message`, `text`, `user_text`, `content`, `prompt`, `messages[].content` i zwykły tekst.
- Dodano kontrolowane błędy dla pustej wiadomości, nie-obiektu JSON i uszkodzonego JSON.
- Dodano metadane `chatgpt_bridge` w odpowiedziach poprawnych i błędach mostu.
- Zaktualizowano dokumentację aktywnego startu, AGENTS, inventory komend, runtime chat note, startup contract i testy regresyjne.
- Zachowano `--chat` jako właściwy tryb żywej lokalnej rozmowy.
