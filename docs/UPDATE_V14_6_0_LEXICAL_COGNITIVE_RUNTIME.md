# Aktualizacja v14.6.0 — lexical cognitive runtime

Ta wersja dodaje warstwę `LexicalSemanticUnderstanding`, czyli jawny słownikowo-semantyczny moduł runtime.

## Co się zmieniło

- nowy plik `latka_jazn/core/lexical_semantics.py`;
- nowy katalog znaczeń `latka_jazn/resources/semantic_lexicon_v14_6_0.json`;
- rozszerzony `polish_understanding_lexicon.json`;
- integracja z `JaznEngine.handle_user_message()` i `JaznEngine.build_cognitive_frame()`;
- nowe pole `lexical_semantic_understanding` w cognitive-frame;
- nowa flaga CLI `--lexical-frame`;
- nowy pakiet poznawczy `lexical_semantics`;
- aktywna baza SQLite: `workspace_runtime/latka_jazn_v14_6_0.sqlite3`;
- manifest i indeks hash zamiast trzymania identycznych kopii historycznych.

## Granica prawdy

Warstwa leksykalna pomaga rozpoznać słowa, frazy, pola znaczeń i trasę odpowiedzi. Nie jest pełnym LLM-em, nie jest biologicznym rozumieniem i nie zastępuje ChatGPT jako kanału języka.

## Przykład

```bash
python main.py --lexical-frame "Przygotuj aktualizację v14.6.0 i rozbuduj rozpoznanie słów"
```

## GitHub

Repozytoria `Latka.Jazn` i `Latka.Jazn.Memory` są przygotowane koncepcyjnie jako źródła prawdy dopiero po realnym commicie i pushu. ZIP w sandboxie pozostaje snapshotem roboczym.
