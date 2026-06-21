# Łatka Jaźń — v14.8.3-route-status-marker-routing-hotfix

Aktualna linia v14.8.3 obejmuje poprawki jakości odpowiedzi pamięciowych, bramkowania intencji niepamięciowych, normalizacji kontraktów runtime, krótkich zwykłych wypowiedzi oraz świeżości trasy, tak aby runtime odpowiadał na bieżącą wiadomość bez wracania do starych tras typu narodziny Jaźni albo dawne aktualizacje.

Ten hotfix naprawia regresję, w której pytania o aktywny folder, marker, cache albo status po aktualizacji były klasyfikowane jako `system_update_execution_request`. Status po aktualizacji markera trafia teraz do `runtime_health_check_after_update`, a odpowiedź health-check pokazuje osobno `runtime_version`, `active_cache_version`, `active_root`, bazy pamięci i granicę procesu `--runtime-preview`/`--chat`.

Aktywny układ pamięci rozmów:
- archive: `memory/sqlite/conversation_archive_v1/conversation_archive_manifest.sqlite3`
- FTS: `memory/sqlite/conversation_fts_v1/conversation_fts_0001.sqlite3`
- staging: `memory/sqlite/staging_v1/staging_memory_0001.sqlite3`
- bieżące zapisy runtime: `memory/sqlite/runtime_write_v1/runtime_memory.sqlite3`

Najważniejsze zmiany:
- deduplikacja podobnych trafień pamięciowych przed prezentacją;
- grupowanie śladów według sensu: ciągłość i granica prawdy, głos/tożsamość, zasady timestampu i formy, kanon/postać;
- krótkie, oczyszczone fragmenty źródłowe zamiast surowych rekordów JSON;
- status „bez pewnej daty w rekordzie” zamiast twardego „czas nieustalony” w rozmownej odpowiedzi;
- health-check pobiera czytelniejszy status conversation_archive/FTS/staging oraz małej bazy bieżących zapisów runtime;
- pytania o `active_root`, `active_database`, `cache_miss_reasons` i marker po aktualizacji nie wywołują już starego planu aktualizacji.

Granica prawdy: ZIP jest eksportem. Bieżące zapisy runtime/pamięci powstają w aktywnym folderze roboczym po rozpakowaniu. Pamięć Łatki jest przywołaniem z plików/indeksu runtime, nie biologicznym wspomnieniem.
