# Komendy systemu Jaźni – inwentarz z aktywnego folderu

- Wygenerowano: 2026-06-20T00:01:10.246644+00:00
- Aktywny folder: `/mnt/data/latka_jazn_v14_8_2_4_codex`
- Wersja: `v14.8.2.6.5-eof-chat-lifecycle-contract-hotfix`
- Start file: `main.py`
- Parser `main.py` ma `allow_abbrev=False`, więc należy używać pełnych nazw flag.

## `main.py` – wszystkie wykryte argumenty

Podstawowy wzór:

```powershell
py -X utf8 main.py [flagi] [message]
```

- `--root` — Folder główny aktywnej paczki Jaźni.
- `--status`, `--status-readonly`, `--diagnostics-readonly` — Pokaż diagnostykę bez zapisu do pamięci. --status jest jawnym aliasem, nie skrótem argparse.
- `--cognitive-frame`, `--chatgpt-frame`, `--brain-frame` — Zwróć wewnętrzny pakiet poznawczy JSON dla ChatGPT, nie gotową odpowiedź użytkownikowi.
- `--debug-direct` — Pokaż techniczną ścieżkę bezpośrednią i fallback diagnostyczny zamiast rozmownej odpowiedzi.
- `--chat`, `--loop` — Uruchom stałą pętlę rozmowy: jeden JaznEngine działa przez wiele tur aż do /exit lub EOF.
- `--chat-gpt` — Uruchom główny most ChatGPT w protokole JSONL: jedna linia wejścia, jedna linia JSON wyjścia; przyjmuje `message`, `text`, `user_text`, `content`, `prompt`, format `messages[].content` albo zwykły tekst.
- `--session-id` — Jawny identyfikator sesji dla kontrolowanego carryover w --chat/--chat-gpt.
- `--no-carryover` — Zablokuj użycie poprzedniej tury nawet jeśli istnieje runtime_state.json.
- `--github-plan` — Zapisz i pokaż plan repozytoriów Latka.Jazn oraz Latka.Jazn.Memory bez wykonywania pushu.
- `--dedup-report` — Zbuduj raport duplikatów treści i SHA-256 bez usuwania plików.
- `--lexical-frame` — Pokaż raport leksykalny aktualnej Jaźni: polskie rozumienie + rozszerzona semantyka słów i fraz.
- `--nlp-frame` — Pokaż raport NLP aktualnej Jaźni: tokeny, lemma_candidates, selected_lemma, confidence i provider.
- `--runtime-preview` — Pokaż dokładną odpowiedź runtime oraz pakiet cognitive-frame/source_origin/self_state dla mostu ChatGPT.
- `--active-cache-status` — Pokaż status aktywnego rozpakowanego folderu i decyzję, czy trzeba ponownie rozpakować ZIP.
- `--project-startup-index` — Zbuduj i pokaż mapę plików oraz modułów/funkcji Jaźni przy rozruchu.
- `--topic-guard` — Pokaż raport TopicMismatchGuard dla wiadomości bez generowania pełnej odpowiedzi.
- `--dialogue-intent` — Pokaż klasyfikację aktu rozmowy v14.6.10 bez generowania odpowiedzi.
- `--module-responsibility-map` — Zbuduj semantyczną mapę odpowiedzialności modułów i funkcji.
- `--seed-requirements-ledger` — Dopisz wymagania manifestu v14.6.10 do requirements ledger.
- `--last-turn` — Pokaż ostatni turn checkpoint: exact_runtime_text, visible_text, route, template_origin i source-origin.
- `--compare-runtime-visible` — Porównaj exact runtime text z widoczną odpowiedzią ChatGPT dla ostatniej tury albo --trace-id.
- `--dictionary-lookup` — Sprawdź termin przez cache/mini-leksykon/adaptory słowników; nie udawaj lookupu online bez providera.
- `--language-resources` — Pokaż rejestr dostępnych i opcjonalnych zasobów językowych/słownikowych.
- `--polish-reasoning-frame` — Pokaż warstwowy frame Polish Reasoning: normalizacja, morfologia, semantyka, reply policy i status providerów.
- `--polish-reasoning-sources` — Pokaż rejestr źródeł/licencji/cache dla warstwy Polish Reasoning.
- `--polish-reasoning-bootstrap-plan` — Pokaż komendy lokalnej instalacji providerów NLP bez ich automatycznego pobierania.
- `--polish-morphology` — Pokaż szczegółową analizę morfologiczną v14.8.4: Morfeusz/PoliMorf, kandydaci i selected_lemma.
- `--morfeusz-status` — Pokaż status realnego providera Morfeusz2/SGJP w Polish Reasoning.
- `--polimorf-status` — Pokaż status opcjonalnego lokalnego providera PoliMorf.
- `--wsjp-lookup-plan` — Zbuduj bezpieczny plan lookupu WSJP dla terminu; nie scrapuje masowo strony.
- `--nkjp-lookup-plan` — Zbuduj bezpieczny plan lookupu NKJP/concordance dla terminu; nie pobiera pełnego korpusu.
- `--voice-source-contract` — Pokaż kontrakt: Jaźń jako źródło, ChatGPT/model jako kanał głosu.
- `--rendering-mode` — Pokaż decyzję naturalna odpowiedź vs exact runtime/diagnostyka.
- `--raw-chat-status` — Pokaż status memory/raw/chat.html i chat.html.7z bez rozpakowywania.
- `--raw-chat-status-json` — Pokaż uczciwy status raw memory/indexu jako JSON v14.8.2.6.4.
- `--conversation-archive-status` — Pokaż status conversation_archive/FTS/staging zbudowanych z raw_chats/*.html.
- `--conversation-archive-search` — Szukaj w osobnym conversation_fts i zwróć UID/provenance do archive/staging.
- `--conversation-archive-limit` — Limit trafień dla --conversation-archive-search.
- `--conversation-archive-show-snippets` — Dołącz krótkie excerpt z prywatnego archive do wyników wyszukiwania.
- `--status-json` — Pokaż startup/runtime status jako JSON bez parsowania prozy.
- `--model-adapter-status` — Pokaż status adapterów modeli: skonfigurowane/nieudawane.
- `--startup-status` — Pokaż własny kontrakt startowy runtime: lekki loader ChatGPT + obowiązki przejęte przez Jaźń.
- `--self-check` — Pokaż skrócony self-check runtime i potwierdzenie, że procedura startowa jest własnością systemu Jaźni.
- `--truth-boundary-check` — Pokaż granicę prawdy runtime/ChatGPT/pliki/pamięć/ZIP.
- `--fallback-audit` — Zbadaj tekst jako możliwy fallback, stale route albo kontrakt zamiast odpowiedzi.
- `--memory-plan` — Pokaż plan wyszukiwania pamięci i trafienia plików kanonicznych bez generowania zwykłej odpowiedzi.
- `--memory-normalization-status` — Pokaż status niedestrukcyjnego sidecara normalizacji pamięci.
- `--normalize-memory-sidecar` — Zbuduj lub zaktualizuj sidecar normalizacji pamięci bez modyfikowania aktywnej bazy rozmów.
- `--wake-state-status` — Pokaż status aktywnego wake_state z sidecara pamięci.
- `--build-wake-state` — Zbuduj wake_state z istniejących rekordów sidecara normalizacji.
- `--dedupe-memory-sidecar` — Zbuduj warstwowe grupy duplikatów w sidecarze bez kasowania rekordów źródłowych.
- `--dry-run` — Tryb kontrolny dla operacji normalizacji/wake_state bez zapisu.
- `--normalization-limit` — Opcjonalny limit rekordów dla sidecara normalizacji, używany głównie w testach i audytach.
- `--dedupe-min-group-size` — Minimalny rozmiar grupy dla warstwowej deduplikacji sidecara.
- `--write-active-runtime-marker` — Zapisz JAZN_ACTIVE_RUNTIME.json dla aktywnego folderu i cache rozpakowania.
- `--source-zip` — Opcjonalna ścieżka ZIP-a źródłowego do porównania checksum w aktywnym cache.
- `--marker-output` — Opcjonalna ścieżka pliku JAZN_ACTIVE_RUNTIME.json.
- `--record-final-reply` — Dopisz do ledgera finalną widoczną odpowiedź ChatGPT dla podanego turn_id/trace_id/timestamp_header.
- `--turn-id` — turn_id z cognitive_turn_envelope dla --record-final-reply.
- `--trace-id` — trace_id z cognitive_turn_envelope dla --record-final-reply.
- `--timestamp-header` — timestamp_header z cognitive_turn_envelope dla --record-final-reply.
- `--state-emoticon` — Emotikon stanu używany, jeśli finalny tekst wymaga dopięcia timestampu.
- `--final-text-file` — Opcjonalny plik z finalną widoczną odpowiedzią do zapisania w ledgerze.
- `--export-system` — Utwórz paczkę system-only bez memory/ i workspace_runtime/.
- `--export-memory` — Utwórz paczkę memory-only z memory/ i workspace_runtime/.
- `--export-full` — Utwórz pełną paczkę systemu wraz z pamięcią.
- `--export-nlp` — Utwórz paczkę NLP-resources-only bez pamięci i bez ciężkich modeli.
- `--export-github-source-safe` — Utwórz paczkę źródłową bez surowej pamięci i aktywnych baz SQLite.
- `--output` — Opcjonalna ścieżka ZIP dla eksportu.
- `message` — Treść wiadomości dla runtime.

## Dodatkowe moduły CLI wykryte w kodzie

### `latka_jazn/adapters/codex_session_bridge.py`

Uruchomienie modułowe: `py -X utf8 -m latka_jazn.adapters.codex_session_bridge`

- `command` — 
- `--root` — 
- `--session` — 
- `--client` — 
- `--text` — 
- `--timeout` — 
- `--poll` — 
- `--json` — 

### `latka_jazn/contracts/embedded_sources.py`

- Moduł ma `main`/`__main__`, ale nie wykryto argumentów `argparse.add_argument`.

### `latka_jazn/memory/auto_memory_update.py`

Uruchomienie modułowe: `py -X utf8 -m latka_jazn.memory.auto_memory_update`

- `--root` — 
- `--target-version` — 
- `--suffix` — 
- `--title` — 
- `--summary` — 
- `--note` — 
- `--modules` — 
- `--experience` — 
- `--memories` — 
- `--emotions` — 
- `--truth-boundary` — 
- `--tests` — 
- `--conversation-file` — Plik z pełnym tekstem rozmowy/transkryptu do odczytania przed zapisem pamięci.
- `--conversation-text` — Tekst rozmowy przekazany bezpośrednio jako argument.
- `--memory-json` — Plik JSON albo tekst JSON z gotowym payloadem pamięciowym.
- `--max-conversation-items` — 
- `--require-conversation-content` — Przerwij aktualizację, jeśli nie ma konkretnych treści rozmowy do zapisania.
- `--no-version-files` — 
- `--zip` — Utwórz ZIP w katalogu nadrzędnym root.
- `--zip-output` — 

### `latka_jazn/tools/runtime_contract_version_normalizer.py`

Uruchomienie modułowe: `py -X utf8 -m latka_jazn.tools.runtime_contract_version_normalizer`

- `--root` — 
- `--apply` — 

### `tools/bootstrap_dependencies.py`

Uruchomienie jako skrypt: `py -X utf8 tools/bootstrap_dependencies.py`

- `--root` — Katalog systemu Jaźni
- `--install` — Jeżeli brakuje py7zr i systemowego 7z, uruchom pip install -r requirements.txt

### `tools/build_conversation_archive.py`

Uruchomienie jako skrypt: `py -X utf8 tools/build_conversation_archive.py`

- `--source` — HTML source path. Defaults to memory/raw_chats/*.html.
- `--output-root` — Output root inside the project.
- `--comparison-db` — Optional simple_all_chats sqlite3 used only for comparison.
- `--report` — JSON report path. Defaults to workspace_runtime/conversation_archive_build_*.json.
- `--force` — Replace output directories if they already contain files.
- `--roles` — Comma-separated roles to archive/stage, or 'all'. Default: user,assistant.
- `--all-nodes` — Include hidden/non-visible graph nodes too.
- `--include-blank` — Keep blank messages.
- `--limit-conversations` — Debug limit per source.
- `--hard-limit-mib` — Hard maximum size per sqlite3 file.
- `--archive-soft-mib` — Soft archive shard target.
- `--fts-soft-mib` — Soft FTS shard target.
- `--staging-soft-mib` — Soft staging shard target.
- `--no-progress` — Disable progress output.

### `tools/fix_v14825_manifest_marker.py`

Uruchomienie jako skrypt: `py -X utf8 tools/fix_v14825_manifest_marker.py`

- `--dry-run` — 
- `--run-tests` — 
- `--skip-sha256sums` — 

### `tools/html_conversations_to_layered_sqlite.py`

Uruchomienie jako skrypt: `py -X utf8 tools/html_conversations_to_layered_sqlite.py`

- `--source` — HTML source path. Can be passed multiple times.
- `--output-db` — Output .sqlite3 path.
- `--force` — Overwrite output DB if it exists.
- `--all-nodes` — Include hidden/non-visible mapping nodes too.
- `--include-blank-transcript` — Keep blank user/assistant transcript messages.
- `--drop-blank-events` — Drop blank tool/system events.
- `--store-full-json` — Store full content JSON for tool/system events.
- `--summary-text-chars` — Maximum text chars kept inside content_summary_json previews. Full event text stays in text.
- `--limit-conversations` — Limit conversations per source for tests.

### `tools/html_conversations_to_simple_sqlite.py`

Uruchomienie jako skrypt: `py -X utf8 tools/html_conversations_to_simple_sqlite.py`

- `--source` — HTML source path. Can be passed multiple times.
- `--output-db` — Output .sqlite3 path.
- `--force` — Overwrite output DB if it exists.
- `--roles` — Comma-separated roles to keep, or 'all'. Default: user,assistant.
- `--all-messages` — Include hidden/non-visible mapping nodes too.
- `--include-blank` — Keep blank messages.
- `--limit-conversations` — Limit conversations per source for tests.

### `tools/memory_repair.py`

Uruchomienie jako skrypt: `py -X utf8 tools/memory_repair.py`

- `--root` — Katalog systemu Jaźni
- `--import-chat-html` — Zaindeksuj memory/raw/chat.html do SQLite
- `--force-chat-html` — Wyczyść i zaindeksuj chat.html ponownie
- `--limit-conversations` — Limit rozmów do testowego importu chat.html
- `--no-export` — Nie eksportuj SQLite do memory/exported_from_sqlite
- `--scan-duplicates` — Pokaż raport duplikatów fingerprint/dedupe_key

### `tools/rebuild_large_memory_index.py`

Uruchomienie jako skrypt: `py -X utf8 tools/rebuild_large_memory_index.py`

- `--from` — 
- `--db` — 

### `tools/rebuild_latka_memory_database.py`

Uruchomienie jako skrypt: `py -X utf8 tools/rebuild_latka_memory_database.py`

- `--root` — Project root. Default: repository root.
- `--output-db` — Output SQLite DB. Default: memory/sqlite/latka_memory_rebuilt.sqlite3
- `--report` — JSON report path. Default: reports/latka_memory_rebuild_<timestamp>.json
- `--force` — Overwrite output DB if it already exists.
- `--dry-run` — Inventory sources only; do not create a database.
- `--limit-per-source` — Limit parsed records/chunks per source for tests.
- `--no-progress` — Disable stderr progress output.
- `--no-external` — Do not include D:/Desktop/Nowy folder sources.
- `--skip-design-docs` — Do not import DOCX design documents.
- `--no-default-sources` — Use only --source entries.
- `--source` — Extra source path. Kind is inferred from extension/name.
- `--store-raw-json-text` — Also store raw JSON text next to compressed raw payloads.
- `--max-content-chars` — Optional per-message content limit. 0 means unlimited.
- `--near-dedupe` — Add review candidates for near duplicates. Exact dedupe is always enabled.
- `--canonical-policy` — Canonical promotion policy. strict keeps chats/legacy as indexed evidence; broad promotes every candidate.

### `tools/record_version_update.py`

Uruchomienie jako skrypt: `py -X utf8 tools/record_version_update.py`

- `--root` — 
- `--version` — 
- `--title` — 
- `--summary` — 
- `--modules` — 
- `--experience` — 
- `--memories` — 
- `--emotions` — 
- `--truth-boundary` — 
- `--tests` — 

### `tools/runtime_memory.py`

Uruchomienie jako skrypt: `py -X utf8 tools/runtime_memory.py`

- `--root` — Katalog systemu Jaźni
- `--text` — Treść do zapamiętania
- `--title` — Tytuł wpisu
- `--kind` — Typ wpisu dziennika
- `--source` — Źródło wpisu
- `--grounding` — Etykieta grounding
- `--confidence` — Pewność 0..1
- `--emotion` — Emocja/afekt; można podać wielokrotnie
- `--force` — Zapisz mimo niskiego progu ważności
- `--scan-duplicates` — Tylko przeskanuj duplikaty

### `tools/split_latka_memory_sqlite.py`

Uruchomienie jako skrypt: `py -X utf8 tools/split_latka_memory_sqlite.py`

- `--input-db` — Source strict SQLite database.
- `--output-dir` — Output directory for sharded SQLite files.
- `--report` — Optional JSON report path.
- `--force` — Replace output directory if it already contains files.
- `--hard-limit-mib` — Hard maximum size per sqlite3 file.
- `--text-soft-mib` — Soft target for text shards.
- `--raw-soft-mib` — Soft target for raw shards.
- `--fts-soft-mib` — Soft target for FTS shards.
- `--limit-rows` — Debug limit applied to each large shard family.
- `--no-progress` — Disable progress output.

### `tools/verify_export_package.py`

Uruchomienie jako skrypt: `py -X utf8 tools/verify_export_package.py`

- `zip_path` — 
- `--strict` — 

## Uwaga bezpieczeństwa

Nie wszystkie komendy są tylko odczytowe. Za zapisowe/destrukcyjne należy traktować szczególnie: `--normalize-memory-sidecar`, `--build-wake-state`, `--dedupe-memory-sidecar`, `--write-active-runtime-marker`, `--record-final-reply`, eksporty `--export-*`, narzędzia importu/przebudowy pamięci z `--force`, `--install`, `--zip`, `--apply` oraz narzędzia naprawcze pamięci.