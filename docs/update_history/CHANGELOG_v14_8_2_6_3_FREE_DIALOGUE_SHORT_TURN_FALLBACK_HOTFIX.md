# v14.8.2.6.3 — free dialogue short-turn fallback hotfix

## Cel

Naprawa krótkich zwykłych tur w `--chat`, które wpadały w generyczny fallback:

- `Siemka.` → `Jestem tutaj. Zatrzymuję się przy tym zdaniu...`
- `Kiepska odpowiedź.` → ten sam fallback
- `Ojoj!` → ten sam fallback

## Zmiany

- Dodano rozpoznanie krótkich intencji rozmownych: `casual_greeting`, `casual_feedback`, `expressive_reaction`, `short_free_dialogue`.
- Rozszerzono `OrdinaryDialogueHandler` i `FreeDialogueSynthesizer`, żeby krótkie wypowiedzi dostały naturalną odpowiedź zamiast prośby o doprecyzowanie.
- Rozszerzono `RuntimeAnswerValidator`, żeby frazy `Zatrzymuję się przy tym zdaniu`, `doprecyzuj tylko kierunek` i podobne były traktowane jako niedozwolony generyczny fallback dla zwykłej rozmowy.
- Podniesiono wersję do `v14.8.2.6.3-free-dialogue-short-turn-fallback-hotfix`.

## Testy

- `tests/test_v148263_free_dialogue_short_turn_fallback_hotfix.py`
- aktualizacja testów wersji `v14.8.2.6.0`, `v14.8.2.6.1`, `v14.8.2.6.2` do prefiksu `v14.8.2.6.3`.

## Granica prawdy

Patch nie dodaje pełnego generatywnego modelu rozmowy. Naprawia najgorszy krótki fallback i wymusza naturalną, aktualną odpowiedź dla krótkich tur rozmownych.
