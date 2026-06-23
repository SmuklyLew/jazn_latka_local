# LATKA_JAZN v14.8.3.4.092 — manifest runtime/private memory split hotfix

## Status

Hotfix przygotowany jako delta po v14.8.3.4.091. Nie commitować v14.8.3.4.091 przed zastosowaniem tej poprawki, ponieważ kontrola `Select-String` ujawniła, że `MANIFEST_CURRENT.json` nadal zawierał wpisy plików runtime/pamięci oraz `.pytest-tmp`.

## Przyczyna

W v14.8.3.4.091 generator manifestu oznaczał część plików jako `mutable_runtime`, ale nadal dodawał je do `MANIFEST_CURRENT.json` w `files[]`. Dodatkowo wzorce nie obejmowały całego `workspace_runtime/**`, `memory/raw/**`, `memory/processed_chats/**` ani `.pytest-tmp`.

## Naprawa

- `MANIFEST_CURRENT.json` ma zawierać statyczne pliki projektu.
- `MANIFEST_RUNTIME_MUTABLE.json` ma zawierać runtime/private memory: `workspace_runtime/**`, `memory/raw/**`, `memory/raw_chats/**`, `memory/processed_chats/**`, SQLite i sidecary runtime.
- `.pytest-tmp` jest wykluczane jako artefakt testowy.
- Dodano test `tests/test_v14834_manifest_runtime_split_hotfix.py`.
- Podbito wersję do `v14.8.3.4.092`.

## Testy wykonane lokalnie w środowisku ChatGPT

- `python -m pytest -q tests/test_v14834_manifest_runtime_split_hotfix.py` → `1 passed`
- `git apply --check` na kopii bazowej v14.8.3.4.091 → OK
- `git apply` na kopii bazowej v14.8.3.4.091 → OK

## Ważne po zastosowaniu patcha

Po `git apply` trzeba uruchomić:

```powershell
py tools/refresh_current_manifest.py
```

Dopiero wtedy `MANIFEST_CURRENT.json`, `MANIFEST_RUNTIME_MUTABLE.json`, `SHA256SUMS` i `SHA256SUMS_STATIC` zostaną odświeżone według nowej polityki.

## Kontrola strukturalna zamiast szerokiego Select-String

Samo `Select-String` nadal może pokazać `memory/sqlite` i `workspace_runtime`, bo te ścieżki muszą występować w metadanych (`active_database`, `mutable_patterns`). Ważne jest, żeby nie występowały jako statyczne wpisy w `MANIFEST_CURRENT.files[]`.

```powershell
$manifest = Get-Content .\MANIFEST_CURRENT.json -Raw | ConvertFrom-Json
$manifest.files | Where-Object {
  $_.path -match '^(workspace_runtime/|memory/raw/|memory/raw_chats/|memory/processed_chats/|\.pytest-tmp/)' -or
  ($_.path -match '^memory/sqlite/' -and $_.path -match '\.sqlite3$')
} | Select-Object path, classification, mutable_runtime

$runtime = Get-Content .\MANIFEST_RUNTIME_MUTABLE.json -Raw | ConvertFrom-Json
$runtime.files | Select-Object -First 20 path, classification, hash_policy
```

Pierwsza komenda powinna nie zwrócić statycznych wpisów runtime/pamięci. Druga powinna pokazać, że te pliki są w manifestcie runtime/private memory.
