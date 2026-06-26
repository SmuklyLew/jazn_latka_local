# v14.8.5.015 repo hygiene: Pylance and patch artifacts

Ten patch nie zmienia runtime Jaźni. Porządkuje repozytorium po aktualizacji v14.8.5.014:

- dodaje `pyrightconfig.json`, żeby Pylance/Pyright analizował tylko aktywny kod (`latka_jazn`, `tests`, `main.py`), a pomijał `workspace_runtime`, `memory`, backupy i artefakty patchowania;
- dopisuje do `.gitignore` rootowe pliki patchy, raportów i paczek recovery generowane podczas prac naprawczych;
- zostawia `.vscode/` jako prywatny folder użytkownika, bo repo już go ignoruje.

Uzasadnienie techniczne:

- `workspace_runtime/patch_direct_apply_backups/...` to kopie zapasowe i nie są aktywnym źródłem systemu Jaźni. Pylance nie powinien wyciągać z nich błędów importów.
- `pyrightconfig.json` jest przenośny między VS Code/Pylance i CLI Pyright, a ścieżki względne liczą się względem położenia pliku konfiguracyjnego.
- Patch należy sprawdzać przez `git apply --check`, a dopiero potem stosować przez `git apply`.

Komendy po zastosowaniu:

```powershell
python -m compileall main.py latka_jazn tests
python -m pytest tests/test_p0_timestamp_network_contract.py tests/test_v1485012_daemon_runtime.py tests/test_v1485013_chat_command_bridge_contract.py tests/test_v1485014_strict_runtime_truth_gate.py tests/test_v1485014_fast_continuity_and_gateway.py -q
```
