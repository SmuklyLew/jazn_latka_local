# UPDATE v14.8.5.016 — route-contract-audit

## Cel

Patch wprowadza kontrakt tras dla krótkich pytań, które wcześniej mogły spaść do `ordinary_dialogue`: health-check, obecność, ciągłość/tożsamość, self-state i świadomość czasu.

## Zmiany

- dodano `RouteContractMatrix` jako deterministyczny kontrakt minimalny dla tras rozmownych;
- dodano leksykon `polish_dialogue_route_lexicon_v14_8_5_016.json`;
- rozszerzono `DialogueIntentClassifier` o wczesną wskazówkę kontraktową;
- dodano trasy `runtime_health_check`, `presence_check`, `identity_presence_check`, `identity_continuity_check`, `time_awareness_question`, `self_state_time_awareness`;
- dodano handlery `PresenceStatusHandler` i `TimeAwarenessHandler`;
- rozszerzono `SelfStateHandler` o odpowiedź złożoną self-state + time-awareness;
- rozszerzono walidator odpowiedzi o brakujące odpowiedzi na pytania bieżącej tury;
- dodano guard CLI: `--runtime-preview-output` bez `--runtime-preview` albo `--dev-preview` kończy się błędem parsera;
- podbito wersję do `v14.8.5.016.2`.

## Kryteria akceptacji

- `Działasz?` nie wpada w `ordinary_dialogue`.
- `Jesteś tam Łatko?` nie wpada w zwykły fallback.
- `Czy to nadal Ty?` rozpoznaje tożsamość/ciągłość.
- `Co teraz czujesz?` odpowiada stanem operacyjnym/dialogowym.
- `Wiesz jaka jest pora?` odpowiada czasem albo degraded warning.
- `Co teraz czujesz? Wiesz jaka jest pora?` działa jako intencja złożona.
- `siemka` i `dobranoc` pozostają naturalne.
- `--runtime-preview` zostaje kompaktowy.
- `--dev-preview` daje pełny JSON.
- `--runtime-preview-output` bez preview/dev daje kod 2.

## Walidacja

```powershell
python -m compileall main.py latka_jazn tests
python -m pytest `
  tests/test_v1485016_route_contract_matrix.py `
  tests/test_v1485016_plain_healthcheck_routing.py `
  tests/test_v1485016_presence_identity_self_time.py `
  tests/test_v1485016_runtime_preview_output_requires_runtime_preview.py `
  tests/test_v1485016_no_generic_stale_reply_for_current_turn.py `
  tests/test_v14850161_runtime_preview_compact_cli.py `
  tests/test_v1485015_runtime_access_contract.py `
  tests/test_v1485012_daemon_runtime.py `
  -q
```

## Granica prawdy

Ten patch nie implementuje jeszcze nowych adapterów modelu ani MCP bridge. Te etapy są zaplanowane jako następne patche. Ten patch naprawia podstawową warstwę intencji/tras/odpowiedzi bieżącej tury.
