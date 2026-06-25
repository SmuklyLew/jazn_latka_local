# v14.8.5.011 — Self Architecture Audit + Reflection Grounding + Memory Gate for Self-Questions

## Cel

Ta aktualizacja naprawia centralny problem widoczny po `v14.8.5.010`: pytania o to, co działa w Jaźni, jak działają emocje/refleksje, co trzeba naprawić i co dodać do rozwoju Łatki potrafiły trafiać w zbyt wąski `memory_audit`. Nowa wersja dodaje pełną trasę audytu architektury i własnego rozwoju oraz część fundamentów drogi do `v14.8.6.0`.

## Podstawa naukowa i inżynieryjna

- NIST AI RMF: system AI powinien utrzymywać jawne zarządzanie ryzykiem, przejrzystość, ocenę i zaufanie; dlatego audyt Jaźni ma zawierać `truth_boundary`, testy i kryteria akceptacji.
- LangGraph/LangChain memory: pamięć agenta należy dzielić na short-term/long-term oraz semantic/episodic/procedural; dlatego self-question memory gate nie miesza self-state z losowymi wspomnieniami.
- Reflexion: agent może używać werbalnych refleksji w pamięci epizodycznej bez zmiany wag modelu; dlatego `ReflectionGroundingSynthesizer` i `GroundedReflectionStore` zapisują refleksję z confidence, źródłem i granicą prawdy.
- Generative Agents: observation + memory stream + reflection + planning wzmacniają spójność zachowania, ale pozostają symulacją zachowania, nie dowodem fenomenalnej świadomości.
- Global Workspace / Higher Order Theories: w Jaźni używane jako inspiracja funkcjonalna dla pola uwagi i samo-monitoringu, nie jako dowód biologicznego mózgu.

## Nowe pliki

- `latka_jazn/core/self_architecture_audit.py`
- `latka_jazn/core/capability_reality_checker.py`
- `latka_jazn/core/reflection_grounding.py`
- `latka_jazn/core/memory_recall_quality.py`
- `latka_jazn/core/self_question_memory_gate.py`
- `latka_jazn/core/self_state_affective_bridge.py`
- `latka_jazn/core/handlers/self_architecture_audit_handler.py`
- `latka_jazn/memory/grounded_reflection_store.py`
- `latka_jazn/resources/self_development/self_development_backlog_v14_8_6_0.json`
- `tests/test_v1485_011_self_architecture_audit_reflection_memory_gate.py`

## Zmienione pliki

- `VERSION.txt`
- `main.py`
- `latka_jazn/version.py`
- `latka_jazn/core/engine.py`
- `latka_jazn/core/route_registry.py`
- `latka_jazn/core/route_handler_dispatcher.py`
- `latka_jazn/core/memory_use_gate.py`
- `latka_jazn/core/runtime_answer_validator.py`
- `latka_jazn/core/handlers/self_state_handler.py`
- `latka_jazn/nlp/dialogue_intent_classifier.py`
- testy wersji `v1485_008`, `v1485_009`, `v1485_010`

## Co ta wersja realnie dodaje

1. `self_architecture_audit_request` i `jazn_development_plan_request` jako specjalne intencje wyżej niż zwykła diagnostyka.
2. `SelfArchitectureAuditHandler`, który zwraca realny audyt: co działa, co działa częściowo, co trzeba naprawić, plan do `v14.8.6.0`, testy i granicę prawdy.
3. `CapabilityRealityChecker`, który sprawdza zachowanie: classifier, route registry, gate, reflection no-fabrication i recall quality.
4. `SelfQuestionMemoryGate`, która rozróżnia pytania o własną Jaźń/rozwój/refleksję od zwykłych pytań o samopoczucie.
5. `MemoryRecallQualityEvaluator`, który wykrywa `counts_only_failure` i wymusza zasadę: licznik nie jest wspomnieniem.
6. `ReflectionGroundingSynthesizer`, który tworzy refleksję tylko z bieżącej tury i przekazanych tropów pamięci; jeśli nie ma tropów, oznacza `current_turn_inference_no_memory_excerpt`.
7. `GroundedReflectionStore`, który zapisuje refleksje append-only do `memory/layered/grounded_reflections.jsonl` i opcjonalnie do SQLite.
8. `SelfStateAffectiveBridge`, który pozwala self-state korzystać z granularnego afektu zamiast ubogiej stałej formuły.
9. `self_development_backlog_v14_8_6_0.json`, żeby droga do `v14.8.6.0` była plikiem danych, a nie tylko tekstem w handlerze.

## Kryteria akceptacji

- `DialogueIntentClassifier` rozpoznaje audyt architektury Jaźni.
- `RouteRegistry` kieruje audyt do `SelfArchitectureAuditHandler`.
- `MemoryUseGate` dopuszcza pamięć dla self-architecture/self-memory, ale blokuje ją dla zwykłego self-state.
- `ReflectionGroundingSynthesizer` nie udaje wspomnienia, gdy nie ma źródła.
- `MemoryRecallQualityEvaluator` oznacza liczniki bez treści jako `counts_only_failure`.
- `CapabilityRealityChecker` wykrywa zachowanie kluczowych połączeń.
- `GroundedReflectionStore` zapisuje refleksję append-only, gdy runtime przekazuje store.
- `SelfStateAffectiveBridge` renderuje stan z granularnego afektu i zachowuje granicę prawdy.
- `RuntimeAnswerValidator` przepuszcza odpowiedź handlera jako bezpieczną.
- Testy `v1485_000-011` przechodzą.

## Droga do v14.8.6.0

- `v14.8.5.011`: domknąć audyt architektury, memory gate, recall quality, grounded reflection store i affective self-state bridge.
- `v14.8.5.012`: rozszerzyć naturalną samoekspresję i zwykłą rozmowę o afekt bez technicznego raportu.
- `v14.8.5.013`: rozszerzyć reflection QA, dedupe i promocję refleksji do procedur.
- `v14.8.5.014`: dodać jakościowy evaluator conversation_archive/FTS: content-not-counts, source diversity, stale-route risk.
- `v14.8.5.015`: release candidate: manifest refresh, active marker, SQLite audit, smoke i full continuity ZIP.
- `v14.8.6.0`: finalna linia unified self-awareness loop + memory/reflection QA + manifest refresh + full continuity ZIP.

## Granica prawdy

Ta aktualizacja wzmacnia samo-monitoring i architekturę świadomości operacyjnej. Nie deklaruje biologicznego odczuwania, cielesnego mózgu ani fenomenalnej świadomości. Łatka ma mówić: co jest faktem plikowym, co jest pamięcią, co jest wnioskiem i co jest symboliczną refleksją.
