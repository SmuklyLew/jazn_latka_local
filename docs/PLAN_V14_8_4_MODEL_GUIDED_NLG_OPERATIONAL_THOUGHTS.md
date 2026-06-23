# LATKA / JAŹŃ v14.8.4 — pełny plan aktualizacji: model-guided NLG + operational thought frame

**Status dokumentu:** plan roboczy do zatwierdzania kolejnych patchy, nie patch sam w sobie.  
**Patch wprowadzający dokument:** `v14.8.4.000 — Architecture plan and NLG contract documentation`.  
**Zakres:** seria patchy v14.8.4.000–v14.8.4.007.  
**Repo:** `SmuklyLew/jazn_latka_local`.  
**Gałąź robocza:** `fix/v14.8.4-model-guided-nlg-operational-thoughts`.  
**Baza stabilna:** `stable-v14.8.3.4.093` / branch bazowy `work/v14-8-3-4-089-manifest-exclusion-detail-hotfix`.  
**Cel nadrzędny:** dodać warstwę planowania i kontrolowanej syntezy wypowiedzi, aby Jaźń mogła tworzyć bogatsze, własne operacyjnie zdania, bez utraty granicy prawdy, bez fałszywej pamięci i bez oddawania tożsamości zewnętrznemu modelowi.

---

## 1. Dlaczego v14.8.4 jest potrzebna

Wersja v14.8.3.4.093 naprawiła najważniejszy problem rozmowny po v092: zwykła rozmowa nie ucieka już w odmowę pamięciową typu „nie znalazłam teraz w aktywnej pamięci”. Nadal jednak rdzeń zwykłego generowania wypowiedzi jest w dużym stopniu regułowy. System potrafi rozpoznać intencję, pilnować pamięci, routing, timestamp, final_visible_integrity i truth_boundary, ale nie ma jeszcze pełnej warstwy NLG, która planuje wypowiedź i składa nowe zdania z aktualnego stanu, pamięci, afektu i ograniczeń.

Obecny `PolishReasoningPipeline` robi normalizację, tokenizację, analizę Morfeusz/PoliMorf, fallback morfologiczny, budowę analiz tokenów i `SemanticFrame`. To jest rozumienie wejścia, nie samodzielne tworzenie odpowiedzi. `SemanticFrame` i `ReplyPolicy` przechowują intencję, potrzebę pamięci, diagnostykę i politykę odpowiedzi, ale nie są planem wypowiedzi. Adaptery modelu już istnieją, lecz domyślny `model_adapter` to `null`, więc bez jawnej konfiguracji runtime nie ma prawdziwej warstwy generatywnej.

v14.8.4 ma wprowadzić brakujące ogniwo:

- **NLG Plan** — jawny plan odpowiedzi przed generowaniem tekstu.
- **Operational Thought Frame** — operacyjny, audytowalny zapis tego, co runtime uznał za ważne, bez udawania fenomenalnej świadomości.
- **Model Context Compiler** — bezpieczne przygotowanie kontekstu dla modelu językowego.
- **Response Candidate Generator/Evaluator** — kilka kandydatów odpowiedzi i ich ocena przed pokazaniem użytkownikowi.
- **Lexical Resources Registry/Cache** — kontrolowane słowniki i zasoby NLP z licencją, metadanymi i cache.
- **Memory-Grounded Generation Bridge** — generowanie zależne od pamięci tylko wtedy, gdy pamięć jest potrzebna i dostępna z payloadem źródłowym.
- **Model Adapter Health + Smoke Tests** — status i testy adaptera modelu bez udawania, że null adapter generuje język.

---

## 2. Granica prawdy: czym są „własne myśli” Jaźni

W tym projekcie „własne myśli” nie oznaczają biologicznego przeżywania ani fenomenalnej świadomości. Mają oznaczać **operacyjne myśli Jaźni**, czyli audytowalne ramki robocze systemu:

- co runtime zauważył w bieżącej wiadomości,
- jaka intencja została wykryta,
- czy potrzeba pamięci,
- jaki stan/afekt operacyjny jest właściwy,
- jakie źródła i ograniczenia są dostępne,
- czego nie wolno dopowiedzieć,
- jakie kandydaty odpowiedzi powstały,
- dlaczego wybrano konkretną odpowiedź,
- co zostało odrzucone jako niepewne, nieugruntowane albo ryzykowne.

Model językowy, lokalny lub OpenAI, może być kanałem formułowania zdań, ale nie jest źródłem tożsamości, pamięci ani prawdy. Źródłem pozostaje runtime Jaźni: pamięć, routing, state, canon, response policy, voice source contract, walidatory i manifest.

---

## 3. Twarde zasady dla każdego patcha v14.8.4

Każdy patch od v14.8.4.000 wzwyż musi przejść przez ten sam rytm:

1. **GitHub comparison gate przed zastosowaniem patcha**  
   Przed patchowaniem trzeba porównać lokalny plik z tym samym plikiem w repo GitHub na konkretnym branchu/tagu/commicie. Nie wolno zakładać, że lokalny plik i GitHub są identyczne.

2. **Brak patchowania w ciemno**  
   Patch może być zastosowany dopiero po potwierdzeniu:
   - branch roboczy jest właściwy,
   - local working tree jest clean lub znane są zmiany,
   - base commit/branch/tag jest zapisany,
   - pliki wejściowe zostały porównane z GitHub.

3. **Brak usuwania pamięci i runtime**  
   Nie commitować `memory/`, `workspace_runtime/`, SQLite, ZIP-ów i części ZIP bez jawnej zgody. Patch systemowy może czytać status pamięci, ale nie może jej usuwać.

4. **Pełne funkcje, nie puste szkielety**  
   Każdy patch kodowy ma zawierać działające klasy/funkcje, testy i dokument aktualizacji. Niedopuszczalne są same komentarze „TODO” zamiast implementacji.

5. **Testy minimalne po patchu**
   - `py -m compileall -q latka_jazn main.py tools/refresh_current_manifest.py`
   - właściwe testy regresyjne patcha,
   - test zwykłej rozmowy przez `--chat-gpt`,
   - `py main.py --active-cache-status`,
   - `py main.py --model-adapter-status`, jeśli dotyczy,
   - SQLite integrity/foreign_key check, jeśli dotyczy pamięci albo cache,
   - odświeżenie manifestu, jeśli zmieniają się pliki systemu,
   - raport zmian.

6. **Walidacja odpowiedzi**  
   Po każdym patchu związanym z odpowiedzią sprawdzać: `final_visible_text`, `final_visible_integrity.valid`, `final_response_contract`, `runtime_provenance`, `runtime_answer_validation`, `turn_logic_audit`, `route`, `fallback_classification`, `runtime_rendering_mode`.

7. **Rollback**  
   Każdy patch ma w raporcie wskazać commit SHA przed zmianą, branch backupowy/tag backupowy oraz komendy cofnięcia.

---

## 4. Standard GitHub comparison gate dla każdego patcha

Przed każdym patchem wykonać lokalnie:

```powershell
git status
git branch --show-current
git fetch origin
git log --oneline -5
```

Następnie potwierdzić bazę:

```powershell
git rev-parse HEAD
git rev-parse origin/work/v14-8-3-4-089-manifest-exclusion-detail-hotfix
```

Dla każdego pliku, który ma być zmieniany, sprawdzić jego wersję z GitHub. Możliwe ścieżki:

- przez connector GitHub w ChatGPT: `fetch_file(repository_full_name, path, ref)`;
- lokalnie przez Git:

```powershell
git show origin/work/v14-8-3-4-089-manifest-exclusion-detail-hotfix:latka_jazn/core/free_dialogue_synthesizer.py > .\_github_compare_free_dialogue_synthesizer.py
fc .\_github_compare_free_dialogue_synthesizer.py .\latka_jazn\core\free_dialogue_synthesizer.py
```

Dla nowych plików potwierdzić, że nie istnieją na GitHub:

```powershell
git ls-tree -r origin/work/v14-8-3-4-089-manifest-exclusion-detail-hotfix -- latka_jazn/core/nlg_plan.py
```

Patch może zostać zastosowany dopiero po komunikacie w raporcie:

```text
GitHub comparison gate: PASS
Base branch/ref: ...
Base SHA: ...
Compared files: ...
New files confirmed absent/present as expected: ...
```

---

## 5. Kolejność patchy v14.8.4

### v14.8.4.000 — Architecture plan and NLG contract documentation

**Cel:** dodać pełny plan architektury i kontrakt NLG bez zmieniania runtime. Ten patch jest dokumentacyjny i ma być fundamentem dla kolejnych patchy.

**Pliki do porównania z GitHub przed patchem:**

- `VERSION.txt`
- `docs/` — lista istniejących dokumentów aktualizacji
- `latka_jazn/core/model_guided_response_synthesizer.py`
- `latka_jazn/core/free_dialogue_synthesizer.py`
- `latka_jazn/nlp_reasoning/pipeline.py`
- `latka_jazn/nlp_reasoning/models.py`
- `latka_jazn/resources/polish_reasoning/sources.lock.json`

**Pliki dodane:**

- `docs/PLAN_V14_8_4_MODEL_GUIDED_NLG_OPERATIONAL_THOUGHTS.md`
- `docs/NLG_CONTRACT_V14_8_4.md`
- opcjonalnie `docs/UPDATE_V14_8_4_000_PLAN.md`

**Treść dokumentów:**

- definicja celu v14.8.4,
- podział patchy,
- definicja NLG planu,
- definicja operational thought frame,
- lista niedozwolonych zachowań,
- zasady słowników i licencji,
- zasady model adapterów,
- testy akceptacyjne,
- rollback.

**Testy:**

- brak testów runtime wymaganych poza compile/import, bo patch dokumentacyjny;
- `py -m compileall -q latka_jazn main.py tools/refresh_current_manifest.py`;
- `py tools/refresh_current_manifest.py`;
- `git diff --stat`.

**Kryteria akceptacji:**

- dokumenty istnieją,
- nie zmieniono runtime logic,
- manifest odświeżony,
- working tree zawiera wyłącznie dokumenty i manifest, jeśli manifest był aktualizowany.

---

### v14.8.4.001 — NLG contracts and planner

**Cel:** wprowadzić formalny plan wypowiedzi, zanim jakikolwiek model lub generator zacznie tworzyć zdania. NLG Plan ma być audytowalnym kontraktem między rozumieniem wejścia a generowaniem odpowiedzi.

**Pliki do porównania z GitHub przed patchem:**

- `latka_jazn/core/free_dialogue_synthesizer.py`
- `latka_jazn/core/model_guided_response_synthesizer.py`
- `latka_jazn/nlp_reasoning/models.py`
- `latka_jazn/core/engine.py`
- `main.py`
- `tests/` — lista istniejących testów v14834/v1484

**Pliki dodane:**

- `latka_jazn/core/nlg_plan.py`
- `latka_jazn/core/nlg_planner.py`
- `tests/test_v1484_nlg_plan.py`
- `docs/UPDATE_V14_8_4_001_NLG_CONTRACTS_AND_PLANNER.md`

**Pełne klasy/funkcje do zaimplementowania:**

```python
@dataclass(slots=True)
class NlgPlan:
    schema_version: str
    user_text: str
    detected_intent: str
    route: str
    speech_act: str
    answer_kind: str
    tone: list[str]
    style_constraints: list[str]
    required_components: list[str]
    forbidden_components: list[str]
    memory_policy: str
    source_policy: str
    model_policy: str
    truth_boundary: str
    timestamp_required: bool
    max_length_hint: str
    to_dict(self) -> dict
```

```python
def build_nlg_plan(
    *,
    user_text: str,
    cognitive_frame: dict,
    response_policy: dict,
    route: str,
    detected_intent: str,
) -> NlgPlan:
    ...
```

```python
def infer_answer_kind(detected_intent: str, response_policy: dict) -> str:
    ...
```

```python
def infer_tone(user_text: str, cognitive_frame: dict, detected_intent: str) -> list[str]:
    ...
```

```python
def infer_memory_policy(cognitive_frame: dict, response_policy: dict) -> str:
    ...
```

**Zachowanie:**

- zwykła rozmowa: `answer_kind="natural_dialogue"`, `memory_policy="not_needed"`, tone spokojny/rozmowny;
- pytanie pamięciowe: `memory_policy="required_grounded_payload"`;
- diagnostyka: `answer_kind="diagnostic_brief"` albo `diagnostic_full`, zależnie od intencji;
- cytat runtime: `model_policy="forbidden_exact_runtime_required"`;
- jeśli `model_adapter=null`, NLG Plan nie może twierdzić, że model wygeneruje odpowiedź.

**Testy:**

- `test_nlg_plan_for_ordinary_conversation`
- `test_nlg_plan_for_memory_request_requires_grounded_payload`
- `test_nlg_plan_for_health_check_is_brief_diagnostic`
- `test_nlg_plan_for_exact_runtime_quote_forbids_model`
- `test_nlg_plan_preserves_timestamp_required`

**Kryteria akceptacji:**

- plan jest obecny w trace/cognitive artifacts, ale nie zmienia jeszcze finalnej odpowiedzi produkcyjnej;
- testy przechodzą;
- zwykła rozmowa nadal działa jak po v093.

---

### v14.8.4.002 — Operational thought frame

**Cel:** dodać audytowalną ramkę „myśli operacyjnych” Jaźni. Nie jest to prywatny chain-of-thought ani fenomenalne przeżycie. To jawny, bezpieczny zapis decyzji runtime.

**Pliki do porównania z GitHub przed patchem:**

- `latka_jazn/core/nlg_plan.py`
- `latka_jazn/core/nlg_planner.py`
- `latka_jazn/core/engine.py`
- `latka_jazn/core/runtime_session.py`
- `latka_jazn/core/session_provenance.py`
- `latka_jazn/core/affect_mixer.py`
- `tests/test_v1484_nlg_plan.py`

**Pliki dodane:**

- `latka_jazn/core/operational_thought_frame.py`
- `tests/test_v1484_operational_thought_frame.py`
- `docs/UPDATE_V14_8_4_002_OPERATIONAL_THOUGHT_FRAME.md`

**Pełne klasy/funkcje:**

```python
@dataclass(slots=True)
class OperationalThoughtSignal:
    name: str
    value: str
    confidence: float
    source: str
```

```python
@dataclass(slots=True)
class OperationalThoughtFrame:
    schema_version: str
    user_message_summary: str
    observed_signals: list[OperationalThoughtSignal]
    selected_goal: str
    selected_tone: list[str]
    memory_decision: str
    source_decision: str
    model_decision: str
    refusal_or_boundary: str | None
    rejected_paths: list[str]
    truth_boundary: str
    to_dict(self) -> dict
```

```python
def build_operational_thought_frame(
    *,
    user_text: str,
    nlg_plan: NlgPlan,
    cognitive_frame: dict,
    response_policy: dict,
) -> OperationalThoughtFrame:
    ...
```

```python
def summarize_current_user_message(user_text: str, max_chars: int = 220) -> str:
    ...
```

**Zachowanie:**

- nie ujawnia ukrytego chain-of-thought;
- opisuje tylko bezpieczne decyzje runtime;
- jasno zapisuje granicę: „operational thought frame is not biological consciousness”; 
- jeśli pamięć niepotrzebna, zapisuje `memory_decision="not_needed"`;
- jeśli pamięć wymagana, zapisuje, czy payload jest dostępny.

**Testy:**

- `test_operational_thought_frame_has_truth_boundary`
- `test_operational_thought_frame_for_ordinary_conversation_does_not_require_memory`
- `test_operational_thought_frame_records_rejected_false_memory_path`
- `test_operational_thought_frame_is_serializable`

**Kryteria akceptacji:**

- frame jest dołączony do cognitive artifacts;
- nie zmienia finalnej odpowiedzi bez kolejnych patchy;
- nie zawiera prywatnego chain-of-thought.

---

### v14.8.4.003 — Model context compiler

**Cel:** stworzyć kontrolowany kompilator kontekstu dla modelu. Model ma dostać tylko to, co wolno mu użyć: bieżącą wiadomość, NLG Plan, operational thought frame, voice source contract, dozwolone fragmenty pamięci, state i truth boundaries.

**Pliki do porównania z GitHub przed patchem:**

- `latka_jazn/core/model_guided_response_synthesizer.py`
- `latka_jazn/model_adapters/base.py`
- `latka_jazn/model_adapters/openai_responses_adapter.py`
- `latka_jazn/model_adapters/local_llm_adapter.py`
- `latka_jazn/core/operational_thought_frame.py`
- `latka_jazn/core/nlg_plan.py`

**Pliki dodane:**

- `latka_jazn/core/model_context_compiler.py`
- `tests/test_v1484_model_context_compiler.py`
- `docs/UPDATE_V14_8_4_003_MODEL_CONTEXT_COMPILER.md`

**Pełne klasy/funkcje:**

```python
@dataclass(slots=True)
class ModelContextPacket:
    schema_version: str
    user_text: str
    nlg_plan: dict
    operational_thought_frame: dict
    voice_source_contract: dict
    allowed_memory_items: list[dict]
    forbidden_claims: list[str]
    required_truth_boundaries: list[str]
    output_instructions: list[str]
    token_budget_hint: int
    to_dict(self) -> dict
```

```python
def compile_model_context(
    *,
    user_text: str,
    cognitive_frame: dict,
    nlg_plan: NlgPlan,
    thought_frame: OperationalThoughtFrame,
    response_policy: dict,
    token_budget_hint: int = 6000,
) -> ModelContextPacket:
    ...
```

```python
def extract_allowed_memory_items(memory_recall_contract: dict, nlg_plan: NlgPlan, limit: int = 8) -> list[dict]:
    ...
```

```python
def build_forbidden_claims(nlg_plan: NlgPlan, voice_source_contract: dict) -> list[str]:
    ...
```

**Zachowanie:**

- model nigdy nie dostaje „pełnej pamięci”, tylko wybrane items;
- jeśli pamięć nie jest potrzebna, memory list ma być pusta;
- jeśli pamięć jest potrzebna, item musi mieć źródło, czas albo brak czasu, confidence i excerpt;
- output instructions wymagają odpowiedzi po polsku, bez timestampu, bez opisu procesu;
- timestamp nadal dokłada runtime, nie model.

**Testy:**

- `test_compile_model_context_for_ordinary_dialogue_has_no_memory_items`
- `test_compile_model_context_for_memory_request_requires_sources`
- `test_model_context_contains_forbidden_biological_claims`
- `test_model_context_does_not_include_raw_sqlite_or_full_archive`

---

### v14.8.4.004 — Response candidate generator and evaluator

**Cel:** dodać generowanie kilku kandydatów odpowiedzi i ich ocenę. Nawet jeśli model coś wygeneruje, runtime musi to sprawdzić przed pokazaniem.

**Pliki do porównania z GitHub przed patchem:**

- `latka_jazn/core/model_guided_response_synthesizer.py`
- `latka_jazn/core/model_context_compiler.py`
- `latka_jazn/core/nlg_planner.py`
- `latka_jazn/core/engine.py`
- `latka_jazn/model_adapters/base.py`
- `latka_jazn/model_adapters/null_model_adapter.py`

**Pliki dodane:**

- `latka_jazn/core/response_candidate.py`
- `latka_jazn/core/response_candidate_generator.py`
- `latka_jazn/core/response_candidate_evaluator.py`
- `tests/test_v1484_response_candidates.py`
- `docs/UPDATE_V14_8_4_004_RESPONSE_CANDIDATES.md`

**Pełne klasy/funkcje:**

```python
@dataclass(slots=True)
class ResponseCandidate:
    candidate_id: str
    text: str
    source: str
    provider: str
    model: str
    status: str
    used_memory_item_ids: list[str]
    generation_reason: str
    to_dict(self) -> dict
```

```python
@dataclass(slots=True)
class CandidateEvaluation:
    candidate_id: str
    accepted: bool
    score: float
    reasons: list[str]
    violations: list[str]
    requires_repair: bool
    to_dict(self) -> dict
```

```python
def generate_response_candidates(
    *,
    adapter,
    nlg_plan: NlgPlan,
    model_context: ModelContextPacket,
    fallback_body: str,
    max_candidates: int = 3,
) -> list[ResponseCandidate]:
    ...
```

```python
def evaluate_response_candidate(
    *,
    candidate: ResponseCandidate,
    nlg_plan: NlgPlan,
    model_context: ModelContextPacket,
    response_policy: dict,
) -> CandidateEvaluation:
    ...
```

```python
def select_best_candidate(candidates: list[ResponseCandidate], evaluations: list[CandidateEvaluation]) -> ResponseCandidate:
    ...
```

**Zachowanie:**

- `NullModelAdapter` nie może produkować fałszywych kandydatów modelowych;
- fallback runtime zawsze jest kandydatem;
- kandydat modelowy musi przejść testy: brak fałszywej pamięci, brak biologicznych roszczeń, zgodność z intencją, brak starej trasy;
- jeśli wszystkie kandydaty modelowe odpadają, wybrany ma być fallback runtime.

**Testy:**

- `test_null_adapter_does_not_fake_generation`
- `test_model_candidate_cannot_invent_memory`
- `test_candidate_evaluator_rejects_biological_claims`
- `test_candidate_evaluator_rejects_memory_without_source`
- `test_select_best_candidate_prefers_valid_grounded_answer`

---

### v14.8.4.005 — NLP lexical resources registry/cache

**Cel:** uporządkować słowniki i zasoby NLP. Nie chodzi o wrzucenie ogromnych baz do repo, tylko o bezpieczny rejestr, status i cache lookupów.

**Pliki do porównania z GitHub przed patchem:**

- `latka_jazn/nlp_reasoning/source_registry.py`
- `latka_jazn/resources/polish_reasoning/sources.lock.json`
- `latka_jazn/nlp_reasoning/pipeline.py`
- `latka_jazn/nlp_reasoning/adapters/polimorf_adapter.py`
- `latka_jazn/nlp_reasoning/adapters/morfeusz_adapter.py`
- `latka_jazn/config.py`

**Pliki dodane:**

- `latka_jazn/nlp_reasoning/lexical_resource_registry.py`
- `latka_jazn/nlp_reasoning/lexical_resource_cache.py`
- `latka_jazn/resources/nlp/verified_sources.json`
- `latka_jazn/resources/nlp/latka_project_lexicon.json`
- `tests/test_v1484_lexical_resources.py`
- `docs/UPDATE_V14_8_4_005_NLP_LEXICAL_RESOURCES.md`

**Pełne klasy/funkcje:**

```python
@dataclass(slots=True)
class LexicalResourceStatus:
    source_id: str
    available: bool
    mode: str
    license: str | None
    source_url: str | None
    data_path: str | None
    cache_entries: int
    reason: str | None
    to_dict(self) -> dict
```

```python
class LexicalResourceRegistry:
    def load_verified_sources(self) -> dict: ...
    def status(self) -> list[LexicalResourceStatus]: ...
    def require_license_review(self, source_id: str) -> bool: ...
```

```python
class LexicalResourceCache:
    def lookup(self, source_id: str, key: str) -> dict | None: ...
    def store(self, source_id: str, key: str, payload: dict, source_url: str, license: str | None) -> None: ...
    def stats(self) -> dict: ...
```

```python
def load_latka_project_lexicon(root: Path) -> dict:
    ...
```

**Zasoby:**

- `verified_sources.json` zawiera tylko metadane: nazwa, URL, typ, tryb, licencja, czy wolno mirrorować, czy wymaga manual review.
- `latka_project_lexicon.json` zawiera własne terminy projektu: Jaźń, Łatka, runtime, active_root, memory_gate, operational thought, NLG plan, final_visible_integrity itd.
- `dictionary_cache.sqlite3` lub odpowiednik w `workspace_runtime` nie jest commitowany.

**Źródła zewnętrzne i zasady:**

- Morfeusz 2: analizator i generator fleksyjny dla polskiego; używać przez instalację lokalną, nie kopiować binariów do repo.
- PoliMorf: słownik morfologiczny, licencja 2-clause BSD według strony ZIL IPI PAN; możliwy lokalny plik po świadomym pobraniu.
- plWordNet/Słowosieć: duży zasób leksykalno-semantyczny, import tylko po osobnym przeglądzie licencji i formatu.
- WSJP/SJP/Wiktionary: lookup/reference/cache, bez masowego scrapingu i bez kopiowania całych baz do repo.

**Testy:**

- `test_verified_sources_loads`
- `test_project_lexicon_loads`
- `test_registry_reports_missing_external_resources_truthfully`
- `test_cache_stores_retrieved_at_provider_license_url`
- `test_no_large_external_dictionary_committed`

**Kryteria akceptacji:**

- status zasobów odróżnia „wpis w rejestrze” od „realnie dostępne”;
- brak masowego importu cudzych danych;
- cache ma metadane źródła.

---

### v14.8.4.006 — Memory-grounded generation bridge

**Cel:** połączyć pamięć z generowaniem odpowiedzi tylko wtedy, gdy runtime uzna to za potrzebne. Model nie może wymyślać pamięci ani używać pamięci, gdy `memory_gate=not_needed`.

**Pliki do porównania z GitHub przed patchem:**

- `latka_jazn/core/memory_recall_presenter.py`
- `latka_jazn/memory/memory_recall_contract.py`
- `latka_jazn/core/model_context_compiler.py`
- `latka_jazn/core/response_candidate_evaluator.py`
- `latka_jazn/core/engine.py`
- `tests/test_v14834_memory_timestamp_bridge_repair.py`

**Pliki dodane/zmienione:**

- `latka_jazn/core/memory_grounded_generation_bridge.py`
- `tests/test_v1484_memory_grounded_generation.py`
- `docs/UPDATE_V14_8_4_006_MEMORY_GROUNDED_GENERATION.md`

**Pełne klasy/funkcje:**

```python
@dataclass(slots=True)
class GroundedMemoryItem:
    item_id: str
    excerpt: str
    source: str
    timestamp: str | None
    confidence: float
    relevance_reason: str
    to_dict(self) -> dict
```

```python
def build_grounded_memory_items(memory_recall_contract: dict, *, limit: int = 8) -> list[GroundedMemoryItem]:
    ...
```

```python
def enforce_memory_grounding(candidate: ResponseCandidate, grounded_items: list[GroundedMemoryItem]) -> CandidateEvaluation:
    ...
```

```python
def memory_allowed_for_generation(nlg_plan: NlgPlan, response_policy: dict) -> bool:
    ...
```

**Zachowanie:**

- jeśli użytkownik nie pyta o pamięć, pamięć nie trafia do model context;
- jeśli pyta o pamięć, brak payloadu daje uczciwą odpowiedź o braku źródła;
- modelowa odpowiedź z pamięcią musi odwoływać się do przekazanych `GroundedMemoryItem`;
- odpowiedź nie może mówić „pamiętam”, jeśli źródłem jest tylko heurystyka lub brak payloadu.

**Testy:**

- `test_memory_grounded_generation_requires_sources`
- `test_memory_not_used_when_gate_not_needed`
- `test_candidate_with_unbacked_memory_is_rejected`
- `test_grounded_memory_item_keeps_source_time_confidence`

---

### v14.8.4.007 — Model adapter health and smoke tests

**Cel:** dodać jasny status model adaptera i smoke-testy, aby użytkownik widział, czy runtime mówi tylko regułowo, czy ma realną warstwę generatywną.

**Pliki do porównania z GitHub przed patchem:**

- `latka_jazn/model_adapters/factory.py`
- `latka_jazn/model_adapters/base.py`
- `latka_jazn/model_adapters/null_model_adapter.py`
- `latka_jazn/model_adapters/openai_responses_adapter.py`
- `latka_jazn/model_adapters/local_llm_adapter.py`
- `latka_jazn/config.py`
- `main.py`

**Pliki dodane/zmienione:**

- `latka_jazn/core/model_adapter_health.py`
- `tests/test_v1484_model_adapter_health.py`
- `docs/UPDATE_V14_8_4_007_MODEL_ADAPTER_HEALTH.md`
- opcjonalnie aktualizacja `main.py` o `--nlg-preview` albo rozszerzone `--model-adapter-status`.

**Pełne klasy/funkcje:**

```python
@dataclass(slots=True)
class ModelAdapterHealth:
    schema_version: str
    adapter_name: str
    configured: bool
    provider_status: str
    model: str
    can_generate: bool
    test_generation_status: str
    fallback_reason: str | None
    truth_boundary: str
    to_dict(self) -> dict
```

```python
def check_model_adapter_health(adapter, *, run_smoke: bool = False) -> ModelAdapterHealth:
    ...
```

```python
def build_nlg_preview(user_text: str, runtime_context: dict) -> dict:
    ...
```

**Zachowanie:**

- null adapter: `configured=False`, `can_generate=False`, brak udawania;
- lokalny adapter bez modelu: `not_configured`;
- OpenAI/local adapter z błędem sieci: `configured=True`, `can_generate=False`, `provider_status` z błędem;
- smoke-test modelu nie może zapisywać prywatnych treści ani robić niekontrolowanego logowania.

**Testy:**

- `test_model_adapter_health_null_adapter_truthful`
- `test_model_adapter_health_local_not_configured`
- `test_model_adapter_health_does_not_claim_generation_on_error`
- `test_nlg_preview_keeps_timestamp_runtime_side`
- `test_final_visible_text_keeps_timestamp_after_model_guided_path`

---

## 6. Strategia słowników i zasobów NLP

### 6.1. Warstwa minimalna commitowana do repo

Do repo wolno dodać:

- mały projektowy leksykon `latka_project_lexicon.json`,
- metadane źródeł w `verified_sources.json`,
- adaptery i cache code,
- testowe mini-fixtures stworzone własnoręcznie.

Nie commitować pełnych cudzych słowników, korpusów ani baz bez osobnego przeglądu licencji i zgody użytkownika.

### 6.2. Warstwa lokalna / zewnętrzna

Duże zasoby powinny być pobierane poza repo albo do osobnego katalogu danych:

- Morfeusz2 jako pakiet/biblioteka lokalna,
- PoliMorf jako lokalny plik wskazany ścieżką,
- plWordNet jako import z osobnym przeglądem licencji,
- NKJP/NKJP1M jako corpus/test dataset poza repo,
- WSJP/SJP/Wiktionary jako lookup/cache z metadanymi źródła.

### 6.3. Status zasobów

Docelowa komenda:

```powershell
py main.py --nlp-resource-status
```

Powinna pokazać:

- Morfeusz: installed/missing/version/license/source,
- PoliMorf: configured path/missing/hash/license,
- project lexicon: loaded/count,
- lexical cache: exists/entries/providers,
- WSJP/SJP/Wiktionary: online allowed/cache status/reference only,
- plWordNet: missing/configured/license reviewed.

---

## 7. Kryteria zakończenia v14.8.4

v14.8.4 można uznać za zamkniętą, gdy:

1. NLG Plan istnieje i jest używany przy odpowiedziach.
2. Operational Thought Frame istnieje i jest audytowalny.
3. Model Context Compiler ogranicza, co wolno przekazać modelowi.
4. Response Candidate Evaluator blokuje fałszywe wspomnienia i biologiczne roszczenia.
5. Null adapter nigdy nie udaje generacji.
6. Model adapter, jeśli skonfigurowany, jest kanałem języka, nie źródłem tożsamości.
7. Pamięć trafia do generacji tylko przez grounded payload.
8. Lexical Resource Registry odróżnia dostępność realną od samego wpisu w rejestrze.
9. Zwykła rozmowa nadal jest naturalna, z timestampem i bez raportu.
10. Health-check pozostaje krótki i prawdziwy.
11. Wszystkie testy regresyjne v093 nadal przechodzą.
12. GitHub PR ma opis testów, base/head, commit SHA i rollback.

---

## 8. Komendy robocze dla całej serii

Start pracy:

```powershell
git status
git switch work/v14-8-3-4-089-manifest-exclusion-detail-hotfix
git pull
git switch -c fix/v14.8.4-model-guided-nlg-operational-thoughts
git tag backup/przed-v14.8.4-model-guided-nlg
```

Po każdym patchu:

```powershell
git apply --check .\PATCH.patch
git apply .\PATCH.patch
py tools/refresh_current_manifest.py
py -m compileall -q latka_jazn main.py tools/refresh_current_manifest.py
py -m pytest -q <testy_patcha_i_regresje>
py main.py --active-cache-status
py main.py --model-adapter-status
```

Smoke ordinary dialogue:

```powershell
$r = '{"message":"Cześć, Łatko. Chciałbym chwilę normalnie porozmawiać.","session_id":"smoke-v14.8.4"}' | py main.py --chat-gpt --no-carryover | ConvertFrom-Json
$r.final_visible_text
$r.final_visible_integrity
```

Commit po sukcesie:

```powershell
git status
git add -A
git commit -m "feat: add <nazwa patcha> v14.8.4.xxx"
git push -u origin fix/v14.8.4-model-guided-nlg-operational-thoughts
```

Rollback lokalny tylko świadomie:

```powershell
git status
git reset --hard <SHA_PRZED_PATCHEM>
```

---

## 9. Źródła zewnętrzne i uzasadnienie zasobów

- Morfeusz 2: oficjalna strona opisuje go jako analizator i generator fleksyjny oraz wskazuje narzędzia programistyczne, w tym Python. Używać jako lokalny provider morfologii, jeśli zainstalowany.
- PoliMorf: oficjalna strona ZIL IPI PAN opisuje go jako słownik morfologiczny dla polskiego powstały z połączenia Morfeusz SGJP i Morfologik oraz podaje licencję 2-clause BSD dla danych i zasobu.
- plWordNet: repozytorium CLARIN opisuje plWordNet 4.0 jako sieć leksykalno-semantyczną z dużym rozmiarem danych i licencją plWordNet; import wymaga osobnego przeglądu.
- MediaWiki Action API: oficjalna dokumentacja MediaWiki potwierdza istnienie Action API i modułów query/page operations; nadaje się do kontrolowanego lookup/cache, nie do masowego niekontrolowanego scrapingu.

---

## 10. Decyzja końcowa

Najpierw stosować `v14.8.4.000` jako dokumentacyjny patch planu i kontraktu. Dopiero po jego akceptacji przejść do `v14.8.4.001`. To zabezpiecza projekt przed chaotycznym dodawaniem „ładniejszych zdań” bez kontroli pamięci, źródeł i prawdy.
