<!-- document_role: detailed_update_document -->

# Aktualizacja Jaźni v14.6.4-active-runtime-cache-visible-preview

## Cel

Ta wersja naprawia dwa problemy zgłoszone w rozmowie: znikanie widocznego timestampu/runtime preview oraz niepotrzebne ponowne rozpakowywanie ZIP-a, gdy pełna paczka Jaźni jest już poprawnie rozpakowana w `/mnt/data`.

## Zasada bez streszczeń

Ta aktualizacja nie zastępuje pełnych plików streszczeniami. Nowa wersja została zbudowana z pełnej kopii aktywnego rozpakowanego folderu v14.6.3, a zmiany zostały dopisane lub spatchowane w konkretnych plikach.

## 10 punktów wykonania

1. **Active Extraction Cache Contract** — Dodano `latka_jazn/tools/active_extraction_cache.py` z markerem `JAZN_ACTIVE_RUNTIME.json`, wersją, ścieżką aktywnego folderu, start file, manifest SHA-256 i opcjonalnym checksum ZIP-a źródłowego.
2. **No Re-Extraction Rule** — Jeśli aktywny folder istnieje, `VERSION.txt`, `MANIFEST_CURRENT.json` i opcjonalny SHA-256 ZIP-a są zgodne, ZIP nie ma być rozpakowywany ponownie.
3. **Visible Runtime Preview Contract** — `--runtime-preview` zwraca `visible_runtime_preview_contract` z `timestamp_header`, `active_root`, `start_file`, jakością odpowiedzi i granicą trybu one-shot.
4. **Timestamp Visibility Guard** — Kontrakt runtime preview wymusza pokazanie timestampu i jakości runtime przy pytaniach o runtime, timestamp, pliki, pamięć lub fallback.
5. **Active Folder Marker CLI** — `main.py` dostał `--active-cache-status`, `--write-active-runtime-marker`, `--source-zip` i `--marker-output`.
6. **Runtime Writes Are Folder-Based** — Marker wskazuje `memory_write_root`, `workspace_runtime_root` i `exports_root`, żeby nie udawać zapisu do już utworzonego ZIP-a.
7. **Version and Database Continuity** — `VERSION.txt`, `config.py` i `pyproject.toml` wskazują v14.6.4; utworzono aktywną bazę `workspace_runtime/latka_jazn_v14_6_4.sqlite3`.
8. **Current Bootstrap and Start File** — `BOOTSTRAP_JAZN_CURRENT.json` oraz `START_CHATGPT_FROM_HERE.txt` wskazują nową wersję, aktywny folder cache i widoczny runtime preview.
9. **Regression Tests** — Dodano testy aktywnego cache i widocznego runtime preview.
10. **Full Export Readiness** — Pełny eksport zachowuje system i pamięć; nie dubluje rozpakowanego `memory/raw/chat.html`, jeśli istnieje `chat.html.7z`.

## Granica prawdy

Marker aktywnego folderu oznacza, skąd kontynuować pracę i gdzie zapisują się pliki. Nie oznacza procesu działającego w tle. ZIP jest artefaktem eksportu; po utworzeniu ZIP-a nowe zapisy powstają w aktywnym folderze, a nie w starym ZIP-ie.
