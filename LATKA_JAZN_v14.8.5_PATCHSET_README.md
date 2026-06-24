# Łatka / Jaźń — patchset v14.8.5.000–003

Baza docelowa: branch `fix/v14.8.4-model-guided-nlg-operational-thoughts`, po commicie `02519a5 chore: update split zip helper`.

Uwaga: patche przygotowano lokalnie na rozpakowanym repo, którego lokalny commit bazowy ma inny SHA (`2649148`) niż GitHub (`02519a5`), ale odpowiada temu samemu krokowi logicznemu: `chore: update split zip helper` po `ff1c657`. Patche zostały zweryfikowane przez `git apply --check` i sekwencyjne zastosowanie na świeżym worktree z tej bazy.

## Kolejność stosowania

```powershell
git status
git branch --show-current
git log --oneline -5

git tag backup/before-v14.8.5.000-patchset
git push origin backup/before-v14.8.5.000-patchset

# 1
git apply --check .\LATKA_JAZN_v14.8.5.000_VERSION_TEMPLATE_RECONCILIATION.patch
git apply .\LATKA_JAZN_v14.8.5.000_VERSION_TEMPLATE_RECONCILIATION.patch
py -m compileall -q latka_jazn main.py tools/audit_legacy_literals_v1485.py
py -m pytest -q tests/test_v1485_000_version_template_reconciliation.py
python tools/audit_legacy_literals_v1485.py --fail-on-active-runtime-blockers

git add -A
git commit -m "feat: reconcile version templates v14.8.5.000"

# 2
git apply --check .\LATKA_JAZN_v14.8.5.001_CURRENT_TURN_GROUNDING.patch
git apply .\LATKA_JAZN_v14.8.5.001_CURRENT_TURN_GROUNDING.patch
py -m compileall -q latka_jazn main.py
py -m pytest -q tests/test_v1485_000_version_template_reconciliation.py tests/test_v1485_001_current_turn_grounding.py
python tools/audit_legacy_literals_v1485.py --fail-on-active-runtime-blockers

git add -A
git commit -m "feat: add current turn grounding v14.8.5.001"

# 3
git apply --check .\LATKA_JAZN_v14.8.5.002_USER_SELF_MEMORY_SPLIT.patch
git apply .\LATKA_JAZN_v14.8.5.002_USER_SELF_MEMORY_SPLIT.patch
py -m compileall -q latka_jazn main.py
py -m pytest -q tests/test_v1485_000_version_template_reconciliation.py tests/test_v1485_001_current_turn_grounding.py tests/test_v1485_002_user_self_memory_split.py
python tools/audit_legacy_literals_v1485.py --fail-on-active-runtime-blockers

git add -A
git commit -m "feat: split user and self memory recall v14.8.5.002"

# 4
git apply --check .\LATKA_JAZN_v14.8.5.003_MANIFEST_REFRESH.patch
git apply .\LATKA_JAZN_v14.8.5.003_MANIFEST_REFRESH.patch
py -m compileall -q latka_jazn main.py tools/audit_legacy_literals_v1485.py
py -m pytest -q tests/test_v1485_000_version_template_reconciliation.py tests/test_v1485_001_current_turn_grounding.py tests/test_v1485_002_user_self_memory_split.py
python tools/audit_legacy_literals_v1485.py --fail-on-active-runtime-blockers
py main.py --active-cache-status
py main.py --model-adapter-status

git add -A
git commit -m "chore: refresh manifests for v14.8.5.002"
```

## Opcja jednego dużego patcha

Zamiast czterech patchy można zastosować jeden combined patch:

```powershell
git apply --check .\LATKA_JAZN_v14.8.5.000-003_COMBINED.patch
git apply .\LATKA_JAZN_v14.8.5.000-003_COMBINED.patch
py -m compileall -q latka_jazn main.py tools/audit_legacy_literals_v1485.py
py -m pytest -q tests/test_v1485_000_version_template_reconciliation.py tests/test_v1485_001_current_turn_grounding.py tests/test_v1485_002_user_self_memory_split.py
python tools/audit_legacy_literals_v1485.py --fail-on-active-runtime-blockers
py main.py --active-cache-status
py main.py --model-adapter-status
```

## Co robi patchset

- v14.8.5.000: centralizuje wersję w `latka_jazn/version.py`, aktualizuje schema_version/source_origin w aktywnych modułach, usuwa stare aktywne literalne wersje z main/runtime/szablonów i dodaje audyt legacy literals.
- v14.8.5.001: dodaje `TurnContextResolver` i `CurrentTurnGrounding`, integruje je z engine/validator, blokuje carryover starej aktualizacji do zwykłej rozmowy.
- v14.8.5.002: dodaje `user_memory_recall_request`, `UserMemoryRecallHandler` i rozdziela pamięć użytkownika od self-memory Łatki.
- v14.8.5.003: odświeża `MANIFEST_CURRENT.json` i `MANIFEST_RUNTIME_MUTABLE.json` do v14.8.5.002.

## Testy wykonane lokalnie

- `python -m compileall -q latka_jazn main.py tools/audit_legacy_literals_v1485.py` — OK.
- `pytest -q tests/test_v1485_000_version_template_reconciliation.py tests/test_v1485_001_current_turn_grounding.py tests/test_v1485_002_user_self_memory_split.py` — 13 passed.
- `python tools/audit_legacy_literals_v1485.py --fail-on-active-runtime-blockers` — OK.
- `python main.py --model-adapter-status` — runtime_version `v14.8.5.002`, null adapter truthful fallback.
- `python main.py --active-cache-status` — runtime_version `v14.8.5.002`, active root wykryty, marker missing but `should_reuse_existing_extraction=true`.
- `--chat-gpt` smoke: `Dzień dobry`, `Co tam?`, `Co pamiętasz o Krzysztofie?`, `Co pamiętasz o sobie jako Łatce?` — trasy: greeting, ordinary_dialogue, user_memory_recall, self_memory_recall. Jeden wsadowy smoke z czterema liniami przekroczył limit czasu środowiska po trzeciej odpowiedzi, więc self-memory sprawdzono osobno i przeszło.

## Rollback

Przed commitem:

```powershell
git restore .
```

Po commitach lokalnych:

```powershell
git reset --hard backup/before-v14.8.5.000-patchset
```

Po pushu nie robić force-push bez decyzji. Bezpieczniej użyć revert:

```powershell
git revert <commit_sha>
git push
```
