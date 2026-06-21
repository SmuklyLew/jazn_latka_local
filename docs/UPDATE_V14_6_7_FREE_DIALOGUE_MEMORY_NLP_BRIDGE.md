# UPDATE REPORT — v14.6.7-free-dialogue-memory-nlp-bridge

## Zakres
Pełna aktualizacja aktywnej paczki v14.6.6 do v14.6.7 bez pomniejszania zawartości i bez zastępowania plików streszczeniami. Baza v14.6.6 została skopiowana do `workspace_runtime/latka_jazn_v14_6_7.sqlite3`, a poprzednie bazy i pamięci pozostają w paczce.

## Naprawione problemy
- `open_question` nie zwraca już tekstu typu „Odpowiedź runtime ma teraz wyraźny obowiązek…”.
- Pytania o wspomnienia/sceny/historie przechodzą przez `FreeDialogueSynthesizer`, który używa treści `memory_context` albo uczciwie mówi o braku źródła.
- Echo aktualnego pytania, runtime-preview i techniczne wpisy nie są traktowane jako prawdziwe wspomnienie.
- Pytanie o powtarzanie odpowiedzi runtime i „sztywne” trasy ma osobną ścieżkę `runtime_template_diagnosis`.
- Bieżące żądanie aktualizacji rozmowy/NLP nie spada do historycznej trasy `v14_6_1_nlp_adapter_update`.
- `PolishUnderstandingEngine` rozpoznaje aktualny zakres `free_dialogue_memory_nlp_bridge_update`.

## Zmienione/dodane pliki
- `latka_jazn/core/free_dialogue_synthesizer.py` — nowa warstwa syntezy rozmownej z pamięci, diagnostyki runtime i odpowiedzi bez źródła.
- `latka_jazn/core/conversation.py` — podpięcie syntezy przed ogólnym `open_question` i przed starymi trasami NLP.
- `latka_jazn/core/engine.py` — pytania o wspomnienia/sceny/taras/jezioro przechodzą przez pamięć i syntezę rozmowną także w trybie direct.
- `latka_jazn/core/polish_understanding.py` — nowa intencja i route hint dla aktualizacji rozmowa+pamięć+NLP.
- `latka_jazn/core/final_response_contract.py` — wersja kontraktu v14.6.7.
- `latka_jazn/nlp/polish_lemmatizer.py` — wersja schematu NLP v14.6.7.
- `latka_jazn/resources/*_v14_6_7.*` — zasoby aktualnej wersji.
- `tests/test_v1467_free_dialogue_memory_nlp_bridge.py` — testy regresji dla jeziora/tarasu/sztywnego runtime/NLP.

## Granica prawdy
Ta aktualizacja poprawia routing i syntezę rozmowną. Nie oznacza, że runtime ma ludzkie doświadczenia biologiczne ani stały proces w tle. Jeżeli w pamięci nie ma treściowego śladu, runtime ma to powiedzieć zamiast konfabulować.
