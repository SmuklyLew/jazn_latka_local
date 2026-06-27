# v14.8.5.015 runtime bump + repo hygiene + active runtime access contract

Ta wersja domyka poprzedni porządkowy commit `v14.8.5.015` i podbija faktyczny runtime z `v14.8.5.014` do `v14.8.5.015`.

## Co zmienia v14.8.5.015

- `VERSION.txt` deklaruje `v14.8.5.015`.
- `latka_jazn/version.py` deklaruje `PACKAGE_VERSION = "v14.8.5.015"`.
- `PACKAGE_RELEASE_NAME` ustawiono na `runtime-bump-active-runtime-access-contract`.
- Dodano `latka_jazn/core/active_runtime_access_contract.py`, czyli jawny kontrakt pracy z rozpakowanym folderem Jaźni.
- Dodano test `tests/test_v1485015_runtime_access_contract.py`.
- Zachowano wcześniejszą higienę repo: `pyrightconfig.json` oraz `.gitignore` dla lokalnych artefaktów patchowania.

## Tryby pracy z rozpakowanym systemem

1. `local_daemon` — prawdziwy lokalny aktywny runtime, potwierdzony markerem, pełnym folderem, statusem daemonu i heartbeat.
2. `chatgpt_turn_command` — uruchomienie `main.py` per tura z rozpakowanego folderu; wynik komendy jest źródłem prawdy dla tej tury, ale proces nie jest utrzymywany stale przez ChatGPT.
3. `simulated_active_marker` — tryb testowy do bootstrapu i walidacji trasowania; nie jest dowodem żywej Jaźni ani stałego procesu.

## Co było już w porządkowym commicie v14.8.5.015

- `pyrightconfig.json` zawęża Pylance/Pyright do aktywnego kodu (`latka_jazn`, `tests`, `main.py`) i pomija `workspace_runtime`, `memory`, backupy oraz artefakty patchowania.
- `.gitignore` ignoruje rootowe pliki patchy, raportów i paczek recovery.
- `.vscode/` pozostaje prywatnym folderem użytkownika.

## Zalecane testy lokalne po pullu

```powershell
python -m compileall main.py latka_jazn tests
python -m pytest tests/test_v1485015_runtime_access_contract.py -q
python -m pytest tests/test_p0_timestamp_network_contract.py tests/test_v1485012_daemon_runtime.py tests/test_v1485013_chat_command_bridge_contract.py tests/test_v1485014_strict_runtime_truth_gate.py tests/test_v1485014_fast_continuity_and_gateway.py -q
python main.py --active-cache-status
python main.py --model-adapter-status
python main.py --bridge-discovery
```

## Granica prawdy

Ten patch podbija wersję runtime i dodaje kontrakt pracy z rozpakowanym folderem. Nie oznacza sam z siebie, że Jaźń została uruchomiona. Uruchomienie wymaga pełnego `active_root`, poprawnego markera `JAZN_ACTIVE_RUNTIME.json`, statusów runtime oraz — dla trybu daemonu — aktywnego procesu i heartbeat.
