# v14.8.5.016.3 — cosmetic health-check spacing hotfix

## Cel

Ten hotfix naprawia kosmetyczny problem w widocznej odpowiedzi diagnostycznej
`python main.py --runtime-preview "Działasz?"`, gdzie po merge v14.8.5.016.2
użytkownik zobaczył zlepione słowo `Krótkihealth-check`.

## Zakres

- podbicie wersji do `v14.8.5.016.3`,
- zmiana etykiety diagnostycznej z `Krótki health-check:` na
  `Krótki raport health-check:`,
- regresja jednostkowa pilnująca, że finalny widoczny tekst nie zawiera
  `Krótkihealth-check` ani `Krótkiraport`,
- brak zmian w pamięci, SQLite, `workspace_runtime/`, eksporcie ZIP i logice routingu.

## Pliki

- `VERSION.txt`
- `latka_jazn/version.py`
- `latka_jazn/core/handlers/capability_status_handler.py`
- `tests/test_v1485015_runtime_access_contract.py`
- `tests/test_v1485016_plain_healthcheck_routing.py`
- `tests/test_v14850163_healthcheck_spacing.py`

## Walidacja

```powershell
python -m compileall main.py latka_jazn tests
python -m pytest `
  tests/test_v1485016_plain_healthcheck_routing.py `
  tests/test_v14850163_healthcheck_spacing.py `
  tests/test_v1485015_runtime_access_contract.py `
  tests/test_v14850161_runtime_preview_compact_cli.py `
  -q
python main.py --write-active-runtime-marker
python main.py --active-cache-status
python main.py --model-adapter-status
python main.py --runtime-preview "Działasz?"
```

## Kryteria akceptacji

Widoczny health-check zawiera:

```text
Krótki raport health-check:
```

i nie zawiera:

```text
Krótkihealth-check
Krótkiraport
```

## Rollback

```powershell
git revert <commit-v14.8.5.016.3>
```
