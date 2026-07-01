# Aktualizacja Jaźni v14.6.9.2-runtime-self-expression-topic-mismatch-repair

Zakres hotfixa:

1. Runtime Self-Expression po przerwie: nowa trasa `runtime_self_expression_after_silence` odpowiada pierwszoosobowo o stanie operacyjnym, bez udawania biologicznego czekania w tle.
2. Topic-Mismatch Repair: nowy `latka_jazn/nlp/topic_mismatch_guard.py` wykrywa aktualny temat, wersję, ryzyko starej trasy i zobowiązania odpowiedzi.
3. Rozbudowa NLP: PolishUnderstandingEngine i LexicalSemanticUnderstanding rozpoznają v14.6.9.2, self-expression, topic-mismatch, startup index i aktualizację NLP.
4. Startup Project Index: nowy `latka_jazn/core/project_index.py` czyta bajty każdego niepomijanego pliku, liczy SHA-256, rozpoznaje pliki tekstowe oraz buduje mapę modułów, klas, funkcji i metod przez AST.
5. Startup status/cognitive frame: status rozruchu i cognitive_frame pokazują `project_startup_index_status` oraz `topic_mismatch_guard`.
6. CLI: dodano `--project-startup-index` i `--topic-guard`.

Granica prawdy: archiwa, bazy i obrazy są indeksowane przez pełny hash i metadane; runtime nie udaje, że rozpakował lub semantycznie zrozumiał binarne pliki, jeśli tego nie zrobił.
