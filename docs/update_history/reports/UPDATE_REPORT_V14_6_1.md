# Update report v14.6.1

Wersja: `v14.6.1-nlp-adapter-zip-profiles`

Zakres wykonany:

1. Dodano bezpieczną warstwę `latka_jazn/nlp/`.
2. Dodano jawny raport `polish_nlp` do cognitive-frame.
3. Rozbudowano `LexicalSemanticUnderstanding` tak, aby korzystał z wyników `PolishLemmatizationEngine`.
4. Dodano opcjonalne adaptery Stanza i Morfeusz2 bez wymagania ich instalacji.
5. Dodano profile eksportu: system, memory, nlp, full, github_source_safe.
6. Aktywna baza SQLite została przeniesiona do `workspace_runtime/latka_jazn_v14_6_2.sqlite3`.
7. Dodano testy regresji dla NLP i eksportu NLP.

Granica prawdy: v14.6.1 nie udaje pełnej lematyzacji kontekstowej. To fundament dla kolejnych kroków.
