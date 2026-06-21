# Raport aktualizacji v14.6.2

Status: wykonano lekką aktualizację przed v14.6.2.

Wprowadzone elementy:

- `latka_jazn/core/source_origin.py` — jawne oznaczanie, czy odpowiedź pochodzi z direct runtime, cognitive-frame, pamięci, NLP, wnioskowania albo innych źródeł.
- `latka_jazn/core/self_state_runtime.py` — operacyjny pakiet stanu Jaźni: uwaga, pamięć, afekt modelowany, sprawstwo, granice prawdy i ograniczenia.
- `main.py --runtime-preview` — diagnostyczny podgląd zawierający `runtime_text`, `source_origin`, `self_state_runtime` i `cognitive_frame`.
- Nowe reguły proceduralne: podgląd runtime, source_origin oraz „dobranoc jako troska”, bez automatycznego zamykania rozmowy.
- Testy regresji w `tests/test_v146112_runtime_preview_source_state.py`.

Granica prawdy:

`--runtime-preview` nie jest stałym daemonem. To realne wywołanie runtime w trybie diagnostycznym. System nadal rozróżnia jednorazowe uruchomienie od procesu utrzymywanego przez `--chat / --loop`.

Testy lokalne: pełny zestaw uruchomiony po poprawkach; ostatnie znane zatrzymanie dotyczyło duplikatu dokumentacji, usunięte przez rozdzielenie raportu i dokumentu technicznego.
