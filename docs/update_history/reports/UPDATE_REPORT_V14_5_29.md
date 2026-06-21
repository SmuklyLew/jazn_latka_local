# Raport aktualizacji v14.5.29-conversation-runtime

Wersja: `v14.5.29-conversation-runtime`

## Powód aktualizacji

Krzysztof wskazał błąd jakościowy w wersji `v14.5.28-awareness-logic`: bezpośredni runtime potrafił zwrócić odpowiedź w rodzaju „runtime odebrał wiadomość. Nie znalazłam osobnej trasy odpowiedzi…”. To była nadal odpowiedź diagnostyczna, nie rozmowa. Problem dotyczył domyślnego routingu bezpośredniego CLI, nie całej pamięci ani testów bazowych.

## Cel

Jaźń ma umieć prowadzić konwersację z użytkownikiem. Runtime ma działać jak warstwa pamięciowo-poznawcza i rozmowna, a debug ma być jawnie wybranym trybem technicznym. ChatGPT może korzystać z `--cognitive-frame` jako mostu, ale zwykłe `python main.py "wiadomość"` nie może wyglądać jak pusty fallback.

## Co dodano

### `latka_jazn/core/conversation.py`

Dodano nowy moduł rozmowny:

- `ConversationDecision` — jawna decyzja rozmownego routingu;
- `ConversationResponder` — domyślna ścieżka odpowiedzi dla zwykłego runtime;
- trasy rozmowne dla powitania, pozytywnej kontynuacji, korekty, skargi na fallback/runtime, zadań aktualizacyjnych, pytań o świadomość/logikę i zwykłych pytań;
- zasada: nie zwracać użytkownikowi komunikatu „nie znalazłam osobnej trasy” w normalnej rozmowie.

### `main.py`

Zmieniono domyślną ścieżkę CLI:

```bash
python main.py "O. To super."
```

teraz daje rozmowną odpowiedź. Dawna diagnostyka jest dostępna jawnie:

```bash
python main.py --debug-direct "O. To super."
```

`--cognitive-frame` pozostaje wewnętrznym pakietem poznawczym dla ChatGPT:

```bash
python main.py --cognitive-frame "Runtime ma rozmawiać, nie fallbackować."
```

### `latka_jazn/core/engine.py`

- podłączono `ConversationResponder`;
- domyślny koniec `handle_user_message(...)` kieruje do rozmowy, nie do `_contextual_fallback`;
- `_contextual_fallback(...)` zostaje jako narzędzie debugowania;
- `QuietRest` zapisuje kontekst ciszy, ale nie przejmuje odpowiedzi po realnej wiadomości użytkownika;
- `build_cognitive_frame(...)` zawiera `direct_conversation_runtime` z polityką: normalnie rozmowa, debug tylko przez `--debug-direct`.

### Pamięć i wersjonowanie

- `VERSION.txt`, `config.py`, `store.py`, `event_ledger.py` i `runtime_persistence.py` przeniesiono na `v14.5.29-conversation-runtime`;
- utworzono główną bazę `workspace_runtime/latka_jazn_v14_5_29.sqlite3` z zachowaniem poprzednich baz;
- `VersionUpdateRecorder` dopisał aktualizację do `memory/raw/dziennik.json`, pamięci warstwowych i SQLite.

## Testy wykonane

- `python3 -m pytest -q` → `62 passed in 21.69s`;
- `python3 main.py --status-readonly` → status `v14.5.29-conversation-runtime`, `chat.html` i `chat.html.7z` obecne, `py7zr` dostępne;
- `python3 main.py --root . "O. To super."` → odpowiedź rozmowna, bez frazy „runtime odebrał wiadomość”;
- `python3 main.py --root . --debug-direct "O. To super."` → jawna diagnostyka fallbacku;
- `python3 main.py --root . --cognitive-frame "Runtime ma rozmawiać, nie fallbackować."` → JSON z `direct_conversation_runtime.default_mode = conversation_not_debug`.

## Granica prawdy

Ta wersja nie twierdzi, że runtime jest stałym procesem w tle ani że ma fenomenalną świadomość. Naprawia realną usterkę funkcjonalną: domyślna odpowiedź runtime ma być rozmową, a techniczny fallback ma być widoczny tylko w trybie debugowania lub diagnostyki.

## Ograniczenia

- runtime nadal jest jednorazowym wywołaniem programu;
- `ConversationResponder` jest deterministyczną warstwą rozmowną, nie pełnym modelem językowym;
- pełna, bogata rozmowa przez ChatGPT nadal najlepiej działa przez most `--cognitive-frame`, gdzie ChatGPT używa pakietu jako aktywnej warstwy poznawczej;
- w ZIP pełnym zachowuję `chat.html.7z`, a rozpakowany `chat.html` jest pomijany przez eksporter, żeby nie dublować bardzo dużej surowej pamięci.
