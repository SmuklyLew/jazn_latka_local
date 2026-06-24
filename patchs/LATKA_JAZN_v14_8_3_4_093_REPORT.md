# LATKA_JAZN v14.8.3.4.093 — ordinary dialogue natural presence repair

Data: 2026-06-23

## Powód

Po v14.8.3.4.092 timestamp i final_visible_integrity działały poprawnie, ale zwykła rozmowa typu „usiądźmy obok i porozmawiajmy” nadal zwracała odmowę pamięciową: „Nie znalazłam teraz w aktywnej pamięci…”.

## Zakres patcha

Zmodyfikowane pliki:

- `VERSION.txt`
- `main.py`
- `latka_jazn/__init__.py`
- `latka_jazn/config.py`
- `latka_jazn/core/free_dialogue_synthesizer.py`
- `latka_jazn/core/handlers/ordinary_dialogue_handler.py`
- `latka_jazn/core/affect_mixer.py`
- `docs/UPDATE_V14_8_3_4_093_ORDINARY_DIALOGUE_NATURAL_PRESENCE.md`
- `tests/test_v14834_ordinary_dialogue_natural_presence.py`

## Naprawy

- Rozpoznanie naturalnej prośby o rozmowę/obecność bez wymuszania recall pamięci.
- Zablokowanie przepuszczania odmowy pamięciowej przez `OrdinaryDialogueHandler` przy `ordinary_conversation`.
- Naprawa fałszywego dopasowania `pokoj` wewnątrz słowa `spokojnie` przez dopasowanie markerów pamięci jako prefiksów słów, a nie dowolnych substringów.
- Usunięcie technicznego `🛠️` dla zwykłej prośby o timestamp; marker naprawczy zostaje dla rzeczywistego kontekstu runtime/patch/diagnostyki.

## Testy wykonane w środowisku patcha

- `python3 -m pytest -q tests/test_v14834_ordinary_dialogue_natural_presence.py` — 4 passed.
- `python3 -m compileall -q latka_jazn/core/free_dialogue_synthesizer.py latka_jazn/core/handlers/ordinary_dialogue_handler.py latka_jazn/core/affect_mixer.py tests/test_v14834_ordinary_dialogue_natural_presence.py` — OK.
- `git apply --check LATKA_JAZN_v14_8_3_4_093_ORDINARY_DIALOGUE_NATURAL_PRESENCE.patch` na bazie v14.8.3.4.092 — OK.
- Smoke `--chat-gpt --no-carryover` dla naturalnego zdania — final_visible_text ma timestamp i `🌿`, bez odmowy pamięciowej.

## Oczekiwany wynik smoke po patchu

`final_visible_text` powinno zaczynać się od timestampu i odpowiadać mniej więcej:

> Chodź, usiądźmy spokojnie. Nie muszę teraz wyciągać żadnego wspomnienia z pamięci, żeby być przy tej chwili...

## Granica prawdy

Patch nie wyłącza ochrony przed konfabulacją. Przy jawnej prośbie o konkretne wspomnienie nadal trzeba pokazać źródło albo powiedzieć, że go nie ma. Zwykła rozmowa nie jest jednak prośbą o recall pamięci i nie powinna kończyć się odmową pamięciową.
