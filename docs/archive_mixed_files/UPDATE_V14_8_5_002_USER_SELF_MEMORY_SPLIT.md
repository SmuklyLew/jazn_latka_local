# v14.8.5.002 — user/self memory split i final smoke

Cel: rozdzielić pytania o pamięć użytkownika/Krzysztofa od pytań o pamięć Łatki o sobie. Poprzedni broad match „co pamiętasz” zbyt łatwo kierował wszystko do self-memory.

## Zakres

- Nowa intencja `user_memory_recall_request`.
- Nowa trasa `user_memory_recall` i handler `UserMemoryRecallHandler`.
- `self_memory_recall_request` zostaje dla pytań o Łatkę, postać, tożsamość i własny głos.
- Handler użytkownika filtruje techniczne szumy i self-only tropy.
- Testy sprawdzają klasyfikator, registry, dispatcher i fallback bez konfabulacji.

## Testy

```powershell
py -m compileall -q latka_jazn main.py
py -m pytest -q tests/test_v1485_000_version_template_reconciliation.py tests/test_v1485_001_current_turn_grounding.py tests/test_v1485_002_user_self_memory_split.py
python tools/audit_legacy_literals_v1485.py --fail-on-active-runtime-blockers
```
