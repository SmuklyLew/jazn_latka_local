# Aktualizacja v14.5.25 — realtime exact event ledger

## Powód aktualizacji

W rozmowie wykryto, że v14.5.24 ma mechanizm runtime memory, ale nie ma jednoznacznej gwarancji: „każde wydarzenie obsłużone przez runtime zostaje dopisane do surowych plików bez streszczania”. SQLite rejestrował eventy szeroko, natomiast pliki pamięci długoterminowej były selektywne. Dodatkowo wiadomość o zasadzie zapisu „na bierzaco w tle” mogła zostać odrzucona przez `RuntimeMemoryWriter` jako `below_threshold`.

## Zakres naprawy

Aktualizacja dodaje surowy append-only event ledger i wzmacnia rozpoznawanie proceduralnych pytań o pamięć.

## Zmienione i dodane pliki

- `latka_jazn/memory/event_ledger.py` — nowy moduł dokładnego zapisu eventów i tur;
- `latka_jazn/core/engine.py` — integracja event ledger z bootstrapem, zwykłymi wiadomościami, cognitive-frame, odpowiedziami, diagnostyką, startem i shutdownem;
- `latka_jazn/memory/runtime_persistence.py` — lepsze rozpoznawanie polskich odmian i literówek, procedura dla dokładnego zapisu zdarzeń;
- `latka_jazn/config.py` — wersja i ścieżka bazy v14.5.25;
- `latka_jazn/memory/store.py` — meta wersji v14.5.25;
- `docs/RUNTIME_EVENT_LEDGER_PROTOCOL.md` — jawny protokół braku streszczeń i rozdzielenia surowego logu od pamięci długoterminowej;
- `tests/test_v14525_realtime_exact_event_ledger.py` — testy regresji dla dokładnego zapisu.

## Co teraz jest zapisywane zawsze przy wywołaniu runtime

- wiadomość użytkownika w `handle_user_message()`;
- wiadomość użytkownika w `build_cognitive_frame()`;
- odpowiedź Łatki w `_reply()`;
- odpowiedź diagnostyczna read-only w `_reply_readonly()`;
- odpowiedź startowa w `bootstrap()`;
- event `engine_started`;
- event `engine_shutdown`;
- pełny pakiet `chatgpt_cognitive_frame`.

## Co nadal jest selektywne

Dziennik i warstwy pamięci długoterminowej nadal nie przyjmują wszystkiego automatycznie jako wspomnienia. To celowe. Surowy ledger chroni pełne źródło, a długoterminowa pamięć zachowuje rzeczy ważne.

## Naprawiony przypadek regresji

Wiadomość podobna do:

```text
Czy w systemie Jaźni jest ustalone, że wszystkie wydarzenia muszą być odpisywanie na bierzaco w tle?
```

jest teraz rozpoznawana jako proceduralna sprawa pamięci i zapisu. Trafia do surowego event ledger oraz tworzy kandydat `reguła_proceduralna`, zamiast ginąć jako `below_threshold`.

## Testy

Dodano testy:

- dokładny zapis tury bez streszczeń;
- rozpoznanie literówki `bierzaco` i odmiany `Jaźni`;
- status read-only nie zmienia statystyk SQLite, ale zapisuje surową turę;
- frazy „bez streszczeń”, „pełna treść”, „do końca” aktywują zapis pamięciowy.
