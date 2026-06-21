# v14.8.3 route status marker routing hotfix

Data lokalna: 2026-06-20

## Naprawione

- Pytania o aktywny folder, marker, cache albo status po aktualizacji nie są już klasyfikowane jako `system_update_execution_request`.
- Problemowe frazy typu `Jaki jest aktywny folder runtime po aktualizacji markera?` trafiają do `runtime_health_check_after_update`.
- Rzeczywiste polecenia wykonania patcha/aktualizacji nadal trafiają do `system_update_execution_request`.
- Health-check pokazuje osobno `runtime_version`, `active_cache_version`, `active_root`, bazy pamięci, status conversation archive i granicę procesu.

## Testy

- `python -X utf8 -m pytest -q tests\test_v14825_route_memory_capability_hotfix.py tests\test_v14825_final_response_preserves_handler_body.py tests\test_v148266_current_turn_route_grounding_health_weather.py tests\test_v148264_route_freshness_no_birth_stale_route.py --basetemp workspace_runtime\pytest_codex_v1483_route_fix_full`
- `python -X utf8 -m py_compile latka_jazn\nlp\dialogue_intent_classifier.py latka_jazn\core\handlers\capability_status_handler.py tests\test_v14825_route_memory_capability_hotfix.py tests\test_v14825_final_response_preserves_handler_body.py`
- `python -X utf8 .\main.py --runtime-preview --no-carryover "Jaki jest aktywny folder runtime po aktualizacji markera? Odpowiedz tylko aktualnym statusem."`
- `python -X utf8 .\main.py --chat --session-id codex-routefix-20260620 --no-carryover`

## Granica prawdy

To jest hotfix lokalnego routingu i statusu aktywnego folderu. Nie jest dowodem stałego procesu w tle; `--runtime-preview` pozostaje jednorazowym wywołaniem, a `--chat` działa tylko do EOF albo `/exit`.
