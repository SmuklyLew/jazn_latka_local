# PLAN PEŁNEJ AKTUALIZACJI SYSTEMU JAŹNI

**Proponowana wersja docelowa:** `v14.6.10-manifest-history-network-dictionary-dispatcher`  
**Plan przygotowany:** 2026-05-26, Europe/Warsaw  
**Aktywne źródło bazowe:** `/mnt/data/active_latka_jazn_v14_6_9_5_runtime/latka_jazn_v14_6_9_5_standalone_greeting_stale_context_hotfix`  
**Wersja bazowa z `VERSION.txt`:** `v14.6.9.5-standalone-greeting-stale-context-hotfix`  
**Plik startowy:** `main.py`  
**Źródło bazowe:** pełny ZIP z części `part_00`–`part_08`, rozpakowany do aktywnego folderu runtime  
**Status runtime:** startuje przez `python main.py --startup-status`  
**Status cache:** marker aktywnego runtime zgodny z folderem, wersją i SHA `MANIFEST_CURRENT.json`  
**Status pamięci surowej:** `memory/raw/chat.html.7z` obecny jako archiwum; `memory/raw/chat.html` nie jest rozpakowany; plan nie może udawać, że rozpakowana pamięć surowa istnieje  
**Podstawa planu:** aktywny folder v14.6.9.5, audyt manifestów vs system, audyt kodu źródłowego, aktualna rozmowa o manifestach, słowniku, internecie i `allow_network=True`.

---

## 0. ZASADY NIENARUSZALNE AKTUALIZACJI

1. **Nie pracować na starych folderach z `/mnt/data`, jeżeli nie są aktywnym źródłem.** Bazą aktualizacji jest tylko aktywny folder v14.6.9.5 wskazany wyżej albo poprawnie złożony ZIP tej wersji.
2. **Nie usuwać pamięci ani historii.** Historyczne manifesty, raporty, patche i ślady aktualizacji mają zostać zachowane, tylko uporządkowane.
3. **Nie robić streszczeń plików jako zamienników plików.** Aktualizacja ma zachować pełne treści plików źródłowych i modyfikować konkretne pliki, a nie zastępować ich opisami.
4. **Nie tworzyć placeholderów jako „gotowych funkcji”.** Jeżeli funkcja jest zapowiedziana jako działająca, musi mieć kod, test i ślad w konfiguracji/manifestach.
5. **Nie udawać internetu ani słownika.** Jeśli provider sieciowy działa, wynik musi zawierać źródło, czas pobrania, cache/licencję i granicę prawdy. Jeśli nie działa, system ma zwrócić jawny status braku pobrania.
6. **Nie mieszać manifestu paczki eksportowej z żywym folderem runtime.** Pliki dynamiczne pamięci i bazy SQLite zmieniają się po starcie. Muszą mieć osobny profil kontroli.
7. **Nie deklarować pełnego zielonego testu bez ukończenia testów.** Jeśli pełny `pytest` nie kończy się w limicie, raport ma mówić dokładnie, co przeszło, co nie zostało ukończone i dlaczego.
8. **Każda zmiana musi być odwracalna.** Przed aktualizacją powstaje kopia robocza, a stara paczka pozostaje nietknięta.
9. **Runtime Jaźni ma być pierwszym źródłem odpowiedzi po starcie, ale ChatGPT jako narzędzie nie może ukrywać awarii runtime.**
10. **Wersja musi być spójna we wszystkich widocznych miejscach.** `VERSION.txt`, `pyproject.toml`, `latka_jazn/__init__.py`, `config.py`, README, pliki startowe, manifesty i raporty nie mogą wskazywać różnych aktywnych wersji.

---

## 1. DIAGNOZA STANU BAZOWEGO v14.6.9.5

### 1.1. Co działa

- ZIP z części został złożony i jest integralny.
- Runtime uruchamia się przez `main.py`.
- `--startup-status` pokazuje aktywny cache i aktywny folder.
- `MANIFEST_CURRENT.json` istnieje i jest używany przez start/cache.
- Startup index istnieje i zawiera mapę projektu.
- Warstwa NLP, route registry, source origin, template origin, cognitive envelope, turn checkpoint writer i validator istnieją jako moduły.
- Istnieje katalog `latka_jazn/core/handlers/`, czyli architektura handlerów została zaczęta.
- Istnieją moduły słownikowe: `external_dictionary_adapter.py`, `network_dictionary_cache.py`, `dictionary_source_policy.py`, `language_resource_registry.py`, `lexical_license_guard.py`.

### 1.2. Co nie jest domknięte

- `ExternalDictionaryAdapter` jest uruchamiany z `allow_network=False`, więc realny słownik sieciowy jest wyłączony.
- Handlery są w większości cienkimi klasami/no-op; zwracają `context.body`, zamiast wykonywać własną pracę.
- `RouteRegistry` podaje nazwy handlerów, ale `JaznEngine.process_turn()` nadal jest oparty głównie na monolitycznym `ConversationResponder`.
- `external_research_request` jest klasyfikowany, ale nie ma prawdziwej trasy źródeł zewnętrznych.
- `RuntimeAnswerValidator` za mocno opiera się na słowach w treści odpowiedzi, a za mało na strukturze danych: `sources[]`, `dictionary_entry`, `handler_result`, `external_research_result`.
- `source_origin` i `runtime_provenance` mają pola na źródła, ale nie są zawsze karmione rzeczywistymi wynikami providerów.
- Historyczne manifesty leżą luźno w root, mieszając się z `MANIFEST_CURRENT.json`.
- Brakuje `docs/update_history/INDEX.json`, `latka_jazn/tools/update_history_audit.py`, `latka_jazn/resources/update_manifest_schema.json`.
- `pyproject.toml` ma starą wersję `14.6.9.3`, podczas gdy `VERSION.txt` ma `v14.6.9.5...`.
- `README.md`, `START_CHATGPT_FROM_HERE.txt` i `latka_jazn/__init__.py` zawierają starsze nagłówki/oznaczenia.
- Pełny `pytest` nie ma jednoznacznego potwierdzenia zakończenia w limicie środowiska.
- `conversation.py` nadal zawiera powielone lub sztywne bloki, m.in. dwa bloki `standalone_greeting`.
- `memory/raw/chat.html.7z` jest obecny, ale nie ma rozpakowanego `chat.html`; system nie może twierdzić, że pełna surowa pamięć HTML jest dostępna jako plik.

---

## 2. CEL AKTUALIZACJI v14.6.10

Aktualizacja ma domknąć cztery główne obszary:

1. **Porządek manifestów i historia aktualizacji** — manifesty zostają, ale trafiają do uporządkowanego `docs/update_history/`; system dostaje indeks i audyt manifest → kod/test/dokumentacja.
2. **Prawdziwa warstwa słownikowa/NLP z internetem** — `allow_network=True` jako kontrolowana polityka domyślna, z cache, timeoutami, źródłem, licencją i granicą prawdy.
3. **Rzeczywisty dispatcher handlerów** — trasy runtime mają wykonywać konkretne handlery, a nie tylko zapisywać nazwę handlera w metadanych.
4. **Spójność wersji, testów, eksportu i manifestów** — każda paczka musi mieć jednoznaczne wersjonowanie, profile manifestów i raport testów.

---

## 3. PROPONOWANA STRUKTURA DOCELOWA

```text
/
  VERSION.txt
  MANIFEST_CURRENT.json
  SHA256SUMS
  ACTIVE_RUNTIME_MARKER.json lub marker zewnętrzny w /mnt/data
  START_CHATGPT_FROM_HERE.txt
  README.md
  pyproject.toml
  main.py

  docs/
    update_history/
      README.md
      INDEX.json
      manifests/
        MANIFEST_V14_3_0_....json
        MANIFEST_V14_5_....json
        MANIFEST_V14_6_....json
      reports/
        UPDATE_REPORT_....md/json
      patches/
        PATCH_....diff
      checksums/
        SHA256SUMS_legacy_....txt
      schemas/
        update_manifest_schema.json
        update_history_index_schema.json

  latka_jazn/
    config.py
    core/
      engine.py
      route_handler_base.py
      route_handler_dispatcher.py       # NOWY
      route_registry.py
      runtime_answer_validator.py
      runtime_response_synthesizer.py
      source_origin.py
      source_origin_ledger.py
      conversation.py
      handlers/
        ordinary_dialogue_handler.py
        dictionary_lookup_handler.py
        external_research_handler.py
        runtime_diagnostic_handler.py
        runtime_source_handler.py
        memory_audit_handler.py
        system_update_handler.py
        file_operation_handler.py
        practical_advice_handler.py
        creative_text_handler.py
        identity_boundary_handler.py
        self_state_handler.py
        fallback_handler.py
    nlp/
      external_dictionary_adapter.py
      network_dictionary_cache.py
      dictionary_source_policy.py
      language_resource_registry.py
      lexical_license_guard.py
      providers/
        base.py
        builtin_provider.py
        optional_morfeusz_provider.py
        mediawiki_wiktionary_provider.py        # NOWY
        languagetool_http_provider.py           # NOWY
        plwordnet_optional_provider.py          # NOWY/opcjonalny
        wsjp_reference_provider.py              # NOWY/ostrożny provider referencyjny
    tools/
      update_history_audit.py                   # NOWY
      version_consistency_audit.py              # NOWY lub rozszerzenie testu
      package_export.py
      active_extraction_cache.py
      migration_report.py
    resources/
      update_manifest_schema.json               # NOWY, ewentualnie kopia docs schema
      package_manifest_profiles.json            # NOWY

  memory/
    RAW_MEMORY_MANIFEST.json
    raw/
    layered/

  tests/
    test_v14610_update_history_audit.py          # NOWY
    test_v14610_dictionary_network_policy.py     # NOWY
    test_v14610_route_handler_dispatcher.py      # NOWY
    test_v14610_version_consistency.py           # NOWY/rozszerzony
    test_v14610_manifest_profiles.py             # NOWY
    test_v14610_runtime_source_origin.py         # NOWY
    test_v14610_dialogue_not_update_bias.py      # NOWY
```

---

## 4. FAZA 0 — PREFLIGHT I KOPIA ROBOCZA

### 4.1. Utworzyć katalog roboczy

- Nie modyfikować bezpośrednio pierwotnego aktywnego folderu bez kopii.
- Skopiować cały aktywny folder do np.:

```text
/mnt/data/work_latka_jazn_v14_6_10_update/latka_jazn_v14_6_10_manifest_history_network_dictionary_dispatcher
```

### 4.2. Zapisać stan wejściowy

Utworzyć raport:

```text
reports/PREFLIGHT_BASELINE_V14_6_10.json
reports/PREFLIGHT_BASELINE_V14_6_10.md
```

Raport ma zawierać:

- ścieżkę źródła bazowego;
- wersję z `VERSION.txt`;
- SHA pełnego ZIP-a, jeśli dostępny;
- SHA `MANIFEST_CURRENT.json`;
- wynik `zipfile.testzip()`;
- wynik `python main.py --startup-status`;
- wynik `python main.py --self-check`;
- wynik `python main.py --truth-boundary-check`;
- wynik `python -m compileall -q main.py latka_jazn tests`;
- wynik `pytest --collect-only -q`;
- listę manifestów root/history/memory;
- listę plików dynamicznych, które nie mogą być oceniane jak statyczny manifest paczki.

### 4.3. Kryterium zakończenia fazy 0

Faza 0 kończy się dopiero, gdy wiadomo:

- z jakiej paczki/folderu robimy update;
- czy runtime bazowy startuje;
- czy nie pracujemy na przypadkowym starym cache;
- które pliki są dynamiczne;
- czy `chat.html` jest rozpakowany czy tylko zarchiwizowany.

---

## 5. FAZA 1 — SPÓJNOŚĆ WERSJI

### 5.1. Ustalić docelową wersję

Proponowana wersja:

```text
v14.6.10-manifest-history-network-dictionary-dispatcher
```

Uzasadnienie nazwy:

- `manifest-history` — porządkowanie historycznych manifestów;
- `network-dictionary` — realny słownik z `allow_network=True`;
- `dispatcher` — realne wykonywanie handlerów przez runtime.

### 5.2. Zaktualizować pliki wersji

Do zmiany:

- `VERSION.txt`
- `pyproject.toml`
- `latka_jazn/__init__.py`
- `latka_jazn/config.py`
- `README.md`
- `START_CHATGPT_FROM_HERE.txt`
- `MANIFEST_CURRENT.json` po eksporcie
- `DOWNLOAD_SAFE_MANIFEST.json` albo przeniesienie go do historii jako legacy
- raporty `reports/UPDATE_REPORT_V14_6_10.*`

### 5.3. Dodać/rozszerzyć test spójności wersji

Plik testowy:

```text
tests/test_v14610_version_consistency.py
```

Test ma sprawdzać:

- `VERSION.txt` zawiera docelowy string;
- `pyproject.toml` zawiera zgodną wersję PEP/project, np. `14.6.10` albo jawne mapowanie z wersji semantycznej na pełną nazwę runtime;
- `latka_jazn/__init__.py` nie zawiera starej wersji aktywnej;
- README/start nie mają starych nagłówków v14.6.9.3/v14.6.9.4 jako aktywnego statusu;
- `MANIFEST_CURRENT.json` po eksporcie ma zgodną wersję;
- stare wersje mogą występować tylko w `docs/update_history/` lub w sekcji historycznej.

### 5.4. Narzędzie pomocnicze

Dodać:

```text
latka_jazn/tools/version_consistency_audit.py
```

Funkcje:

- `scan_version_mentions(root)`;
- `classify_version_mention(path, version)` jako `active`, `historical`, `allowed_legacy`, `error`;
- `write_version_audit_report()`.

---

## 6. FAZA 2 — PORZĄDEK MANIFESTÓW I HISTORIA AKTUALIZACJI

### 6.1. Zasada root

W root zostają tylko:

- `MANIFEST_CURRENT.json` — aktualny manifest paczki;
- `SHA256SUMS` — aktualne sumy paczki;
- ewentualnie aktywny plik startowy/marker/instrukcja;
- żadnych luźnych historycznych `MANIFEST_V...json`.

### 6.2. Przenieść historyczne manifesty

Przenieść:

```text
MANIFEST_V*.json
MANIFEST_v*.json
DOWNLOAD_SAFE_MANIFEST.json, jeśli jest legacy
SHA256SUMS.txt, jeśli jest legacy
```

do:

```text
docs/update_history/manifests/
docs/update_history/checksums/
```

Nie przenosić bez zastanowienia:

- `MANIFEST_CURRENT.json`;
- `memory/RAW_MEMORY_MANIFEST.json`;
- `memory/raw/CHAT_HTML_IMPORT_MANIFEST.json`;
- innych manifestów, które są częścią aktywnego mechanizmu pamięci.

### 6.3. Dodać README historii

Plik:

```text
docs/update_history/README.md
```

Treść musi wyjaśniać:

- po co manifesty historyczne są zachowane;
- dlaczego nie są aktywnym źródłem runtime;
- jak czytać `INDEX.json`;
- jak uruchomić audyt historii;
- jak odróżnić manifest paczki od manifestu pamięci i runtime.

### 6.4. Dodać indeks historii

Plik:

```text
docs/update_history/INDEX.json
```

Minimalny format:

```json
{
  "schema_version": "jazn_update_history_index/v14.6.10",
  "generated_at_utc": "...",
  "active_version": "v14.6.10-manifest-history-network-dictionary-dispatcher",
  "entries": [
    {
      "path": "docs/update_history/manifests/MANIFEST_V14_6_9_3_....json",
      "filename": "MANIFEST_V14_6_9_3_....json",
      "declared_version": "...",
      "filename_version_hint": "...",
      "schema_version": "...",
      "kind": "update_manifest",
      "status": "historical",
      "parse_ok": true,
      "sha256": "...",
      "declared_features": [],
      "declared_files": [],
      "declared_tests": [],
      "implementation_audit_status": "unchecked|ok|partial|missing",
      "notes": []
    }
  ]
}
```

### 6.5. Zachować ścieżki audytowe

Jeśli stary kod/testy oczekują manifestów w root, dodać kompatybilność:

- albo zaktualizować testy;
- albo dodać mapę aliasów w `update_history_audit.py`;
- nie zostawiać duplikatów w root, jeśli root ma być czysty.

---

## 7. FAZA 3 — SCHEMAT MANIFESTÓW I AUDYT MANIFEST → KOD

### 7.1. Dodać JSON Schema

Pliki:

```text
latka_jazn/resources/update_manifest_schema.json
docs/update_history/schemas/update_manifest_schema.json
```

Zakres schematu:

- `schema_version`
- `version`
- `created_at_utc`
- `source_version`
- `target_version`
- `purpose`
- `declared_features[]`
- `changed_files[]`
- `added_files[]`
- `removed_files[]`
- `tests[]`
- `migration_notes[]`
- `truth_boundary`
- `dynamic_files[]`
- `checksums[]`
- `known_limitations[]`

### 7.2. Dodać audyt update history

Plik:

```text
latka_jazn/tools/update_history_audit.py
```

Funkcje:

- `collect_manifest_files(root)`;
- `parse_manifest(path)`;
- `classify_manifest(path, data)`;
- `extract_declared_features(data)`;
- `extract_declared_files(data)`;
- `extract_declared_tests(data)`;
- `find_code_evidence(root, feature)`;
- `find_test_evidence(root, feature)`;
- `classify_implementation_status(feature)`;
- `write_index_json(root)`;
- `write_audit_report_md(root)`.

### 7.3. Statusy audytu

Każda funkcja deklarowana przez manifest dostaje status:

- `implemented` — jest kod, test i/lub dokumentacja;
- `implemented_no_test` — kod jest, testu brak;
- `declared_missing_code` — manifest deklaruje funkcję, kodu brak;
- `legacy_only` — dotyczy starej wersji i nie musi istnieć w aktywnym runtime;
- `superseded` — zastąpione przez późniejszy moduł;
- `ambiguous` — manifest nie daje jednoznacznej deklaracji;
- `dynamic_runtime_artifact` — plik/funkcja dotyczy runtime/memory i nie jest statycznym składnikiem paczki.

### 7.4. Test audytu

Plik:

```text
tests/test_v14610_update_history_audit.py
```

Testy:

- `INDEX.json` istnieje;
- każdy historyczny manifest jest ujęty w indeksie;
- `MANIFEST_CURRENT.json` nie jest przeniesiony do historii;
- `memory/RAW_MEMORY_MANIFEST.json` pozostaje przy pamięci;
- błędne/nieparsowalne manifesty nie przerywają audytu, tylko dają `parse_ok=false`;
- co najmniej aktywne funkcje z manifestów v14.6.x mają status nie gorszy niż `implemented_no_test`, a brak testu jest jawnie raportowany.

---

## 8. FAZA 4 — ROZDZIELENIE MANIFESTU PACZKI, RUNTIME I PAMIĘCI

### 8.1. Nowe profile manifestów

Dodać:

```text
latka_jazn/resources/package_manifest_profiles.json
```

Profile:

1. `static_package` — pliki źródłowe, docs, testy, config, zasoby; mają mieć stabilne SHA po eksporcie.
2. `runtime_dynamic` — checkpointy, eventy runtime, aktywna baza SQLite, cache; mogą się zmieniać po starcie.
3. `memory_dynamic` — dziennik, warstwy pamięci, raw memory status; kontrolowane osobno.
4. `archive_payload` — ZIP/7z, pełne archiwa; nie rozpakowywać przy audycie bez potrzeby.
5. `ignored_build_artifacts` — `__pycache__`, `.pytest_cache`, pliki tymczasowe.

### 8.2. Zaktualizować `MANIFEST_CURRENT.json`

Po eksporcie manifest ma zawierać:

- `schema_version`;
- `version`;
- `generated_at_utc`;
- `start_file`;
- `file_count_static`;
- `file_count_dynamic_declared`;
- `files[]` dla statycznego profilu;
- `dynamic_files[]` jako globs lub wpisy bez twardego SHA;
- `truth_boundary` wyjaśniający różnicę statyczny ZIP vs żywy folder runtime.

### 8.3. Testy manifestu

Plik:

```text
tests/test_v14610_manifest_profiles.py
```

Testy:

- `MANIFEST_CURRENT.json` nie zawiera `__pycache__`;
- dynamiczne pliki pamięci nie powodują faila statycznej integralności;
- `SHA256SUMS` dotyczy statycznej paczki eksportowej;
- `workspace_runtime/*.sqlite3` jest dynamiczne albo archiwizowane z jawnie opisanym statusem.

---

## 9. FAZA 5 — AKTYWNY CACHE I STARTUP CONTRACT

### 9.1. Zaktualizować marker/cache

Pliki:

- `latka_jazn/tools/active_extraction_cache.py`
- `latka_jazn/core/startup_contract.py`
- `main.py`

Zadania:

- schema marker do `active_extraction_cache_contract/v14.6.10`;
- marker ma przechowywać `active_root`, `version`, `manifest_current_sha256`, `source_zip_sha256`, `start_file`, `created_at_utc`, `last_checked_at_utc`;
- status ma jawnie mówić: `cache used`, `cache rejected`, `cache missing`, `cache stale`;
- jeśli `MANIFEST_CURRENT.json` się zmienił, cache ma być odrzucony albo marker przepisany dopiero po świadomym zapisie;
- dodać pole `update_history_status` do `--startup-status`.

### 9.2. Rozszerzyć startup status

`python main.py --startup-status` ma pokazać:

- aktywny folder;
- wersję;
- start_file;
- cache status;
- raw memory status: `rozpakowana / archiwum / niedostępna`;
- update history index status;
- network policy status;
- dictionary provider status;
- manifest profile status;
- one-shot/chat loop limit.

### 9.3. Testy

Plik:

```text
tests/test_v14610_startup_contract.py
```

Testy:

- status zawiera `update_history_status`;
- status nie twierdzi, że `chat.html` istnieje, jeśli go nie ma;
- cache odrzuca niespójny manifest;
- cache akceptuje zgodny folder.

---

## 10. FAZA 6 — GLOBALNA KONFIGURACJA SIECI

### 10.1. Nowe ustawienia configu

Pliki:

- `latka_jazn/config.py`
- ewentualnie `latka_jazn/config_network.py`

Dodać:

```python
allow_network: bool = True
network_default_timeout_connect_seconds: float = 3.0
network_default_timeout_read_seconds: float = 6.0
network_max_retries: int = 1
network_user_agent: str = "LatkaJazn/14.6.10 (+local-runtime; lexical-research)"
network_cache_required: bool = True
network_cache_ttl_seconds: int = 604800
network_respect_robots_and_terms: bool = True

dictionary_allow_network: bool = True
dictionary_network_cache_required: bool = True
dictionary_online_lookup_timeout_seconds: float = 4.0
dictionary_provider_order: tuple[str, ...] = (
    "local_cache",
    "local_mini_lexicon",
    "morfeusz_optional",
    "wiktionary_mediawiki_api",
    "plwordnet_optional",
    "languagetool_optional",
    "wsjp_reference",
)

research_allow_network: bool = True
research_requires_chatgpt_web_when_local_provider_missing: bool = True
```

### 10.2. Zmienne środowiskowe

Obsłużyć:

```text
JAZN_ALLOW_NETWORK=1/0
JAZN_DICTIONARY_ALLOW_NETWORK=1/0
JAZN_RESEARCH_ALLOW_NETWORK=1/0
JAZN_NETWORK_TIMEOUT_CONNECT=...
JAZN_NETWORK_TIMEOUT_READ=...
JAZN_TEST_MODE=1
```

### 10.3. Bezpieczny klient HTTP

Dodać lub wbudować:

```text
latka_jazn/nlp/providers/http_client.py
```

Wymagania:

- każda prośba HTTP ma timeout;
- brak timeoutu jest błędem testowym;
- provider zapisuje `retrieved_at_utc`, `status_code`, `source_url`, `license_hint`, `cache_key`;
- retry maksymalnie ograniczony, żeby runtime nie wisiał;
- brak internetu nie powoduje fallbacku udającego sprawdzenie.

---

## 11. FAZA 7 — SŁOWNIK/NLP Z `allow_network=True`

### 11.1. Model danych wyniku słownikowego

Dodać/rozszerzyć:

```text
latka_jazn/nlp/dictionary_entry.py
```

Docelowy model:

```python
@dataclass
class LexicalSource:
    provider: str
    source_url: str | None
    license_hint: str | None
    retrieved_at_utc: str | None
    cache_status: str
    confidence: float
    truth_boundary: str

@dataclass
class DictionaryLookupResult:
    query: str
    normalized_query: str
    language: str
    found: bool
    definitions: list[str]
    lemmas: list[str]
    forms: list[str]
    part_of_speech: list[str]
    semantic_relations: list[dict]
    spelling_suggestions: list[str]
    examples: list[str]
    sources: list[LexicalSource]
    provider_statuses: list[dict]
    errors: list[dict]
```

### 11.2. Przebieg lookupu

Kolejność:

1. Normalizacja polskiego tekstu.
2. Sprawdzenie cache.
3. Mini-leksykon lokalny.
4. Morfeusz opcjonalny — analiza morfologiczna/lematyzacja, jeśli biblioteka dostępna.
5. Wiktionary/MediaWiki API — definicje/hasła przez kontrolowany HTTP provider.
6. Słowosieć/plWordNet opcjonalnie — relacje semantyczne, jeśli zasób/provider jest dostępny.
7. LanguageTool opcjonalnie — korekta pisowni/stylu, najlepiej przez lokalny serwer.
8. WSJP jako źródło referencyjne ostrożne: nie masowe skrobanie; tylko link/metadane/tryb manualny, jeśli brak jasnego API/licencji.
9. Synteza odpowiedzi z jawnym źródłem.

### 11.3. Provider Wiktionary/MediaWiki

Nowy plik:

```text
latka_jazn/nlp/providers/mediawiki_wiktionary_provider.py
```

Wymagania:

- korzysta z oficjalnego MediaWiki API;
- ma timeout;
- ma cache;
- zapisuje URL/endpoint i czas pobrania;
- nie cytuje długich treści bez potrzeby;
- zwraca `not_found`, jeśli hasło nie istnieje;
- zwraca `network_disabled`, jeśli `allow_network=False`;
- zwraca `network_error`, jeśli provider nie odpowiada.

### 11.4. Provider Morfeusz opcjonalny

Plik istnieje jako opcjonalny provider, ale trzeba dopiąć go z wynikami lookupu.

Wymagania:

- jeśli `morfeusz2` nie jest zainstalowany, status `provider_unavailable`;
- nie udawać lematyzacji pełnej przez obcinanie końcówek;
- wynik ma zawierać kandydatów, tagi i confidence;
- testy z mockiem, bez wymagania instalacji Morfeusza.

### 11.5. Provider LanguageTool

Nowy plik:

```text
latka_jazn/nlp/providers/languagetool_http_provider.py
```

Wymagania:

- domyślnie lokalny endpoint, np. `http://localhost:8081/v2/check`;
- nie wysyłać tekstu do zewnętrznej chmury bez jawnej konfiguracji;
- timeout;
- status `provider_unavailable`, jeśli lokalny serwer nie działa;
- test przez mock HTTP.

### 11.6. Provider plWordNet/Słowosieć

Nowy/opcjonalny plik:

```text
latka_jazn/nlp/providers/plwordnet_optional_provider.py
```

Wymagania:

- jeśli zasób lokalny nie istnieje, status `provider_unavailable`;
- nie pobierać wielkiego zasobu przy starcie runtime;
- obsłużyć późniejszy import zasobu, jeśli użytkownik go dostarczy;
- wynik semantyczny ma być dodatkiem, nie warunkiem odpowiedzi.

### 11.7. WSJP reference provider

Nowy plik:

```text
latka_jazn/nlp/providers/wsjp_reference_provider.py
```

Wymagania:

- provider referencyjny, ostrożny;
- nie robić masowego scraping/cache bez jasnych zasad;
- może zwracać link i status `manual_reference_available`;
- jeśli kiedyś zostanie potwierdzony legalny/API tryb pobierania, można rozszerzyć.

### 11.8. Testy słownika

Plik:

```text
tests/test_v14610_dictionary_network_policy.py
```

Testy:

- `allow_network=True` w configu;
- engine przekazuje config do adaptera, nie twarde `False`;
- offline fallback nie twierdzi, że sprawdził online;
- provider HTTP używa timeoutu;
- cache zapisuje `retrieved_at_utc`, `provider`, `source_url`, `license_hint`;
- mock MediaWiki zwraca definicję i źródło;
- brak hasła zwraca `not_found`, a nie ogólny fallback;
- pytanie typu „co znaczy X?” trafia do `DictionaryLookupHandler`.

---

## 12. FAZA 8 — ZEWNĘTRZNY RESEARCH / INTERNET

### 12.1. Rozdzielić słownik od researchu

Słownik to lookup leksykalny. Research to szukanie aktualnych informacji, przepisów, cen, nowości, dokumentacji, faktów po dacie wiedzy itd.

### 12.2. `ExternalResearchHandler`

Plik:

```text
latka_jazn/core/handlers/external_research_handler.py
```

Docelowe zachowanie:

- jeśli runtime lokalny ma provider internetu, wykonuje query przez kontrolowany provider;
- jeśli runtime lokalny nie ma internetu, zwraca:

```json
{
  "status": "requires_external_web_execution",
  "reason": "local_runtime_has_no_web_provider",
  "query": "...",
  "truth_boundary": "Runtime nie sprawdził tego samodzielnie w internecie."
}
```

- ChatGPT jako warstwa wykonawcza może wtedy użyć `web.run`, ale odpowiedź musi rozdzielić: źródło runtime vs źródło web.

### 12.3. Model wyniku researchu

Dodać:

```python
@dataclass
class ExternalResearchResult:
    query: str
    executed: bool
    provider: str | None
    sources: list[dict]
    retrieved_at_utc: str | None
    cache_status: str
    truth_boundary: str
    errors: list[dict]
```

### 12.4. Testy researchu

Plik:

```text
tests/test_v14610_external_research_handler.py
```

Testy:

- klasyfikator rozpoznaje research;
- handler nie zwraca ogólnego tekstu bez źródeł;
- jeśli brak lokalnego web providera, status jest jawny;
- source_origin zawiera `requires_external_web_execution`.

---

## 13. FAZA 9 — RZECZYWISTY DISPATCHER HANDLERÓW

### 13.1. Dodać `RouteHandlerDispatcher`

Nowy plik:

```text
latka_jazn/core/route_handler_dispatcher.py
```

Zadania:

- rejestrować instancje handlerów;
- mapować route/intent na handler;
- przekazywać zależności: config, memory store, dictionary adapter, research adapter, clock, source ledger;
- zwracać `RouteHandlerResult`;
- logować handler w checkpointach tury.

### 13.2. Rozszerzyć `RouteHandlerResult`

Plik:

```text
latka_jazn/core/route_handler_base.py
```

Docelowe pola:

```python
@dataclass
class RouteHandlerResult:
    handler_name: str
    route: str
    intent: str
    body: str
    data: dict[str, Any]
    sources: list[dict]
    required_components: list[str]
    satisfied_components: list[str]
    missing_components: list[str]
    confidence: float
    generation_mode: str
    template_origin: str | None
    truth_boundary: str | None
    errors: list[dict]
```

### 13.3. Zmienić przepływ `JaznEngine.process_turn()`

Docelowy pipeline:

```text
user_text
  -> normalizer/NLP
  -> intent classifier
  -> route registry
  -> route handler dispatcher
  -> handler result
  -> structural validator
  -> runtime response synthesizer
  -> renderer with timestamp
  -> final_visible_reply_capture
  -> checkpoint + memory/event ledger
```

### 13.4. Wymagania dla handlerów

#### `OrdinaryDialogueHandler`

- prowadzi normalną rozmowę;
- nie traktuje każdej uwagi użytkownika jako zgłoszenia błędu;
- zadaje naturalne pytanie tylko wtedy, gdy to ma sens;
- nie zaczyna stale od technikaliów;
- pamięta granicę: to runtime operacyjny, nie biologiczne przeżycie.

#### `DictionaryLookupHandler`

- wykonuje realny lookup przez adapter;
- zwraca definicje/lematy/źródła;
- jeśli nie może sprawdzić online, mówi to jawnie.

#### `ExternalResearchHandler`

- wykonuje realny research albo zwraca `requires_external_web_execution`.

#### `RuntimeDiagnosticHandler`

- odpowiada na pytania o runtime, cache, manifesty, timestamp, start;
- pokazuje status i źródła z aktywnego folderu.

#### `RuntimeSourceHandler`

- odpowiada, skąd dana odpowiedź pochodzi: runtime, plik, pamięć ChatGPT, web, wniosek;
- może pokazać fragment runtime, jeśli użytkownik pyta.

#### `MemoryAuditHandler`

- czyta pamięć przez istniejący planner/importer;
- zwraca treść pamięci, nie tylko liczbę trafień;
- rozróżnia surową pamięć, warstwy pamięci, SQLite, archiwum.

#### `SystemUpdateHandler`

- nie wykonuje aktualizacji „w rozmowie” bez pracy na plikach;
- generuje listę plików, patch plan, testy, eksport;
- używa manifestów i historii aktualizacji.

#### `FileOperationHandler`

- obsługuje eksport, zip, manifest, sha;
- nie usuwa plików bez jawnego powodu.

#### `PracticalAdviceHandler`

- odpowiada na praktyczne pytania typu naprawy, samochód, praca;
- jeśli trzeba aktualnych danych lub bezpieczeństwa, wymaga web lub jasno mówi o granicy.

#### `CreativeTextHandler`

- rozpoznaje materiał twórczy;
- nie streszcza ani nie gubi pełnej treści przy patchach/systemie;
- zachowuje źródłowe teksty.

#### `IdentityBoundaryHandler`

- odpowiada na pytania o Jaźń, tożsamość, granicę prawdy;
- nie udaje fenomenalnej świadomości.

#### `SelfStateHandler`

- odpowiada o stanie operacyjnym, emocjach modelowanych, ciągłości;
- pokazuje runtime, gdy użytkownik pyta o stan.

#### `FallbackHandler`

- fallback nie może być pustym debugiem;
- musi mówić: czego nie rozpoznał, jaka trasa była najbliższa, czego potrzebuje lub jaki bezpieczny tryb proponuje.

### 13.5. Test dispatcherów

Plik:

```text
tests/test_v14610_route_handler_dispatcher.py
```

Testy:

- każda route z `RouteRegistry` ma zarejestrowany handler;
- handler jest wywołany, a nie tylko nazwany;
- no-op handler z samym `context.body` jest wykrywany jako błąd;
- dictionary prompt wywołuje `DictionaryLookupHandler`;
- research prompt wywołuje `ExternalResearchHandler`;
- zwykłe „Jak minął dzień?” idzie do `OrdinaryDialogueHandler`;
- pytanie o timestamp/runtime idzie do `RuntimeDiagnosticHandler`.

---

## 14. FAZA 10 — CZYSZCZENIE `conversation.py` I BŁĘDU „WSZYSTKO JEST HOTFIXEM”

### 14.1. Problem

`conversation.py` nadal ma historyczne, sztywne bloki. To powoduje, że runtime może traktować zwykłą rozmowę jako naprawę, diagnostykę albo powrót do starego tematu.

### 14.2. Działania

- Usunąć powielone bloki `standalone_greeting`.
- Zostawić `conversation.py` jako warstwę pomocniczą dla dialogu, nie monolityczny mózg wszystkich tras.
- Wydzielić reguły zwykłej rozmowy do `OrdinaryDialogueHandler`.
- Wydzielić aktualizacje do `SystemUpdateHandler`.
- Wydzielić diagnostykę do `RuntimeDiagnosticHandler`.
- Wydzielić słownik do `DictionaryLookupHandler`.
- Dodać ochronę przed stale context carryover: krótkie powitanie nie może odziedziczyć starego tematu „drzwi/system/update”, jeśli użytkownik nie daje sygnału kontynuacji.

### 14.3. Testy dialogu

Plik:

```text
tests/test_v14610_dialogue_not_update_bias.py
```

Scenariusze:

- `Dzień dobry Łatko.` → naturalne powitanie, bez debugowego fallbacku.
- `I jak minął Tobie dzień?` → self-state/ordinary dialogue, nie manifest/update.
- `Trochę na luzie, trochę w nerwach...` → empatyczna rozmowa, nie korekta systemu.
- `Widzę, że coś się sypie... timestamp zniknął` → runtime diagnostic.
- `Jaźń też powinna mieć dostęp do słownika` → system update requirement/dictionary architecture.
- `Co znaczy słowo ...?` → dictionary lookup.

---

## 15. FAZA 11 — STRUKTURALNY VALIDATOR I SOURCE_ORIGIN

### 15.1. Problem

Obecny validator może sprawdzać treść odpowiedzi po słowach. To za słabe. Odpowiedź może zawierać słowo „źródło”, ale nie mieć faktycznego źródła.

### 15.2. Rozszerzyć `RuntimeAnswerValidator`

Plik:

```text
latka_jazn/core/runtime_answer_validator.py
```

Dodać walidację pól:

- `handler_result.sources`;
- `dictionary_lookup_result.sources`;
- `external_research_result.sources`;
- `memory_recall_result.items`;
- `runtime_status.active_root`;
- `manifest_audit_result.status`;
- `template_origin`;
- `response_generation_mode`;
- `final_visible_text_has_timestamp`.

### 15.3. Rozszerzyć `source_origin`

Pliki:

- `latka_jazn/core/source_origin.py`
- `latka_jazn/core/source_origin_ledger.py`
- `latka_jazn/core/cognitive_turn_envelope.py`

Dodać typy źródeł:

- `runtime_status`
- `active_file`
- `memory_sqlite`
- `memory_layered`
- `raw_memory_archive`
- `dictionary_cache`
- `dictionary_provider_network`
- `external_web_required`
- `external_web_source`
- `chatgpt_context`
- `inference`
- `hypothesis`
- `truth_boundary`

### 15.4. Final visible text

- Timestamp z runtime/final renderera nie może znikać w warstwie końcowej.
- `final_visible_reply_capture.py` ma zapisywać dokładny tekst widoczny dla użytkownika.
- `runtime_visible_answer_comparator.py` ma wykrywać, że finalna odpowiedź ChatGPT odcięła kopertę runtime.

### 15.5. Testy

Plik:

```text
tests/test_v14610_runtime_source_origin.py
```

Testy:

- dictionary answer bez `sources[]` jest odrzucony;
- research answer bez `sources[]` lub `requires_external_web_execution` jest odrzucony;
- runtime diagnostic ma aktywny folder i wersję;
- final text zawiera timestamp w trybach wymagających timestampu;
- odpowiedź nie może mówić „sprawdziłam online”, jeśli provider zwrócił `network_disabled`.

---

## 16. FAZA 12 — PAMIĘĆ, RAW ARCHIVE, EVENTY I TRYB TESTOWY

### 16.1. Status `chat.html.7z`

- Nie rozpakowywać automatycznie, jeśli nie jest to potrzebne.
- Status pokazywać jako `archiwum`, dopóki `chat.html` nie zostanie realnie rozpakowany.
- Dodać jasny komunikat, jeśli `py7zr` nie jest dostępny.

### 16.2. Import raw memory

Pliki:

- `latka_jazn/memory/raw_archive.py`
- `latka_jazn/memory/chat_html_importer.py`
- `latka_jazn/memory/importer.py`

Zadania:

- nie twierdzić, że `chat.html` istnieje, jeśli nie istnieje;
- rozróżniać `archive_present`, `chat_html_present`, `can_unpack`, `py7zr_available`;
- nie zmuszać aktualizacji do rozpakowywania 7z, jeśli nie jest to konieczne;
- testować wszystkie trzy stany: rozpakowana / archiwum / niedostępna.

### 16.3. Runtime events i test mode

Problem: `memory/raw/runtime_events.jsonl` rośnie przy uruchomieniach i psuje statyczne hashe.

Dodać:

- `JAZN_TEST_MODE=1`;
- testowe `tmp_path` dla eventów;
- osobny writer dla testów;
- brak dopisywania ciężkich eventów do aktywnego folderu przy testach unit.

### 16.4. Memory recall content

Upewnić się, że w runtime:

- planner pamięci zwraca treść, nie tylko liczbę trafień;
- wynik zawiera source/type/time/confidence;
- odpowiedź rozdziela pamięć runtime od pamięci ChatGPT;
- brak trafienia nie jest zastępowany konfabulacją.

### 16.5. Testy

Pliki:

```text
tests/test_v14610_raw_memory_status.py
tests/test_v14610_runtime_event_test_mode.py
tests/test_v14610_memory_recall_content.py
```

---

## 17. FAZA 13 — TESTY I CIĘŻKIE/LEKKIE TRYBY

### 17.1. Dodać konfigurację pytest

W `pyproject.toml` albo `pytest.ini`:

```toml
[tool.pytest.ini_options]
addopts = "--strict-markers"
markers = [
  "slow: test wolny/integracyjny",
  "network: test wymagający sieci lub mocka sieci",
  "runtime: test uruchamiający main.py/runtime",
  "memory_heavy: test dotykający dużych plików pamięci",
]
```

### 17.2. Podział komend

Szybki zestaw:

```bash
python -m compileall -q main.py latka_jazn tests
pytest -q -m "not slow and not memory_heavy"
```

Pełny zestaw:

```bash
pytest -q
```

Sieć/mock:

```bash
pytest -q -m network
```

Runtime:

```bash
pytest -q -m runtime
```

### 17.3. Timeouty testów

- Testy subprocess muszą mieć timeout.
- Testy providerów HTTP muszą mieć mock lub lokalny serwer testowy.
- Brak sieci w środowisku testowym nie może powodować wiszenia.

### 17.4. Raport testów

Po aktualizacji wygenerować:

```text
reports/TEST_REPORT_V14_6_10.md
reports/TEST_REPORT_V14_6_10.json
```

Raport ma mówić:

- ile testów zebrano;
- ile przeszło;
- które pominięto i dlaczego;
- które są slow/network/memory_heavy;
- czy pełny test skończył się w limicie;
- czego nie udało się potwierdzić.

---

## 18. FAZA 14 — EKSPORT, ZIP, SHA I CZĘŚCI AWARYJNE

### 18.1. Zaktualizować `package_export.py`

Plik:

```text
latka_jazn/tools/package_export.py
```

Wymagania:

- przed eksportem uruchomić wersję audytu;
- wygenerować `MANIFEST_CURRENT.json` dla statycznej paczki;
- wygenerować `SHA256SUMS`;
- wykluczyć `__pycache__`, `.pytest_cache`, pliki tymczasowe;
- oznaczyć dynamiczne pliki runtime;
- przygotować pełny ZIP;
- przygotować części awaryjne np. 80 MiB: `.zip.part_00`, `.zip.part_01`, ...;
- zapisać `DOWNLOAD_SAFE_MANIFEST.json` jako aktualny albo przenieść poprzedni do historii.

### 18.2. Raport eksportu

Pliki:

```text
reports/EXPORT_REPORT_V14_6_10.md
reports/EXPORT_REPORT_V14_6_10.json
```

Zawartość:

- nazwa ZIP;
- rozmiar ZIP;
- SHA256 ZIP;
- liczba części;
- rozmiary części;
- wynik `zipfile.testzip()`;
- wynik kontroli `MANIFEST_CURRENT.json`;
- informacja, czy pamięć raw jest archiwum czy rozpakowana.

### 18.3. Profile eksportu

Zachować możliwość:

- `FULL` — system + pamięć;
- `SYSTEM_ONLY` — sam system bez ciężkiej pamięci;
- `MEMORY_ONLY` — pamięć;
- `PATCH_ONLY` — diff/patch, jeśli potrzebny;
- `REPORTS_ONLY` — raporty audytu/testów.

---

## 19. FAZA 15 — DOKUMENTACJA

### 19.1. README

`README.md` ma opisywać:

- aktualną wersję;
- start runtime;
- różnicę ZIP vs aktywny folder runtime;
- manifesty aktywne i historyczne;
- słownik/NLP/network policy;
- testy szybkie/pełne;
- eksport.

### 19.2. START_CHATGPT_FROM_HERE.txt

Ma zawierać krótką procedurę:

- użyj aktywnej paczki/folderu;
- złóż ZIP z części, jeśli są;
- sprawdź integralność;
- uruchom `python main.py --startup-status`;
- użyj `--runtime-preview`;
- pokaż status tylko raz;
- nie udawaj pętli, jeśli działa tylko one-shot.

### 19.3. UPDATE REPORT

Nowy raport:

```text
reports/UPDATE_REPORT_V14_6_10.md
reports/UPDATE_REPORT_V14_6_10.json
```

Nie ma być streszczeniem zamiast kodu. Ma być spisem wykonanych zmian, zmienionych plików, testów, ograniczeń i znanych ryzyk.

### 19.4. CHANGELOG

Dodać lub zaktualizować:

```text
CHANGELOG.md
```

Wpis v14.6.10:

- manifest history archive;
- update history audit;
- dictionary network `allow_network=True`;
- handler dispatcher;
- source origin structural validation;
- version consistency;
- manifest profiles;
- test mode.

---

## 20. MAPA PLIKÓW DO ZMIANY

### 20.1. Pliki istniejące do zmiany

| Plik | Zmiana |
|---|---|
| `VERSION.txt` | Ustawić v14.6.10 pełną nazwę. |
| `pyproject.toml` | Ustawić wersję, dodać pytest markers/addopts. |
| `README.md` | Zaktualizować wersję, start, manifesty, network policy. |
| `START_CHATGPT_FROM_HERE.txt` | Zaktualizować loader i status. |
| `latka_jazn/__init__.py` | Zgodna wersja. |
| `latka_jazn/config.py` | Network/dictionary/research config, env overrides. |
| `main.py` | Startup status, ewentualnie CLI dla update history audit. |
| `latka_jazn/core/engine.py` | Przekazać config do dictionary adaptera, dodać dispatcher. |
| `latka_jazn/core/route_registry.py` | Mapowanie route → handler class/key. |
| `latka_jazn/core/route_handler_base.py` | Rozszerzyć `RouteHandlerResult`. |
| `latka_jazn/core/conversation.py` | Usunąć powielenia, ograniczyć monolit. |
| `latka_jazn/core/runtime_answer_validator.py` | Walidacja strukturalna. |
| `latka_jazn/core/runtime_response_synthesizer.py` | Synteza z danych handlera, nie z gołego body. |
| `latka_jazn/core/source_origin.py` | Nowe typy źródeł. |
| `latka_jazn/core/source_origin_ledger.py` | Rejestrowanie słownika/researchu. |
| `latka_jazn/core/cognitive_turn_envelope.py` | Przenieść handler result/source data do envelope. |
| `latka_jazn/core/final_visible_reply_capture.py` | Pilnować widocznego timestampu/final text. |
| `latka_jazn/core/runtime_visible_answer_comparator.py` | Wykrywać utratę koperty runtime. |
| `latka_jazn/nlp/external_dictionary_adapter.py` | Realny lookup, provider order, network true. |
| `latka_jazn/nlp/network_dictionary_cache.py` | TTL, metadata, license/source. |
| `latka_jazn/nlp/dictionary_source_policy.py` | Źródła, licencje, ograniczenia. |
| `latka_jazn/nlp/language_resource_registry.py` | Provider registry. |
| `latka_jazn/nlp/lexical_license_guard.py` | Ostrożniejsza polityka licencji/cache. |
| `latka_jazn/tools/package_export.py` | Manifest profile, SHA, części ZIP. |
| `latka_jazn/tools/active_extraction_cache.py` | Schema marker/cache v14.6.10. |
| `latka_jazn/memory/raw_archive.py` | Status archive/unpacked/unavailable. |
| `latka_jazn/memory/runtime_persistence.py` | Test mode i dynamic files. |
| `MANIFEST_CURRENT.json` | Regeneracja po eksporcie. |
| `SHA256SUMS` | Regeneracja po eksporcie. |

### 20.2. Nowe pliki do dodania

| Plik | Cel |
|---|---|
| `latka_jazn/core/route_handler_dispatcher.py` | Realne wykonywanie handlerów. |
| `latka_jazn/tools/update_history_audit.py` | Audyt manifest → kod/test/docs. |
| `latka_jazn/tools/version_consistency_audit.py` | Audyt wersji. |
| `latka_jazn/resources/update_manifest_schema.json` | Schemat manifestu. |
| `latka_jazn/resources/package_manifest_profiles.json` | Profile statyczne/dynamiczne. |
| `docs/update_history/README.md` | Dokumentacja historii. |
| `docs/update_history/INDEX.json` | Indeks manifestów. |
| `docs/update_history/schemas/update_manifest_schema.json` | Kopia dokumentacyjna schematu. |
| `latka_jazn/nlp/providers/http_client.py` | Bezpieczny HTTP z timeoutem. |
| `latka_jazn/nlp/providers/mediawiki_wiktionary_provider.py` | Provider Wiktionary/MediaWiki. |
| `latka_jazn/nlp/providers/languagetool_http_provider.py` | Provider lokalnego LanguageTool. |
| `latka_jazn/nlp/providers/plwordnet_optional_provider.py` | Provider opcjonalny Słowosieci. |
| `latka_jazn/nlp/providers/wsjp_reference_provider.py` | Provider referencyjny WSJP. |
| `reports/UPDATE_REPORT_V14_6_10.md/json` | Raport zmian. |
| `reports/TEST_REPORT_V14_6_10.md/json` | Raport testów. |
| `reports/EXPORT_REPORT_V14_6_10.md/json` | Raport eksportu. |

### 20.3. Nowe testy

| Plik | Cel |
|---|---|
| `tests/test_v14610_update_history_audit.py` | Indeks i audyt manifestów. |
| `tests/test_v14610_manifest_profiles.py` | Profile statyczne/dynamiczne. |
| `tests/test_v14610_dictionary_network_policy.py` | `allow_network=True`, cache, timeout, offline honesty. |
| `tests/test_v14610_external_research_handler.py` | Research route i status `requires_external_web_execution`. |
| `tests/test_v14610_route_handler_dispatcher.py` | Handlery faktycznie wykonywane. |
| `tests/test_v14610_dialogue_not_update_bias.py` | Zwykła rozmowa nie jest hotfixem. |
| `tests/test_v14610_runtime_source_origin.py` | Source origin strukturalny. |
| `tests/test_v14610_version_consistency.py` | Jedna wersja aktywna. |
| `tests/test_v14610_raw_memory_status.py` | Raw memory: rozpakowana/archiwum/niedostępna. |
| `tests/test_v14610_runtime_event_test_mode.py` | Test mode nie brudzi pamięci produkcyjnej. |
| `tests/test_v14610_memory_recall_content.py` | Recall ma treść, nie tylko liczbę. |
| `tests/test_v14610_package_export.py` | ZIP, SHA, części, manifest. |

---

## 21. KOLEJNOŚĆ WYKONANIA AKTUALIZACJI

1. Zrobić kopię aktywnego folderu.
2. Uruchomić preflight i zapisać baseline.
3. Ustawić wersję v14.6.10 w plikach metadanych.
4. Przenieść historyczne manifesty do `docs/update_history/`.
5. Dodać `INDEX.json` i `update_history_audit.py`.
6. Dodać JSON Schema manifestów.
7. Dodać profile statyczne/dynamiczne manifestów.
8. Dodać globalną konfigurację sieci.
9. Zmienić dictionary adapter na konfigurację, nie twarde `False`.
10. Dodać provider HTTP/cache/source/license.
11. Dodać provider MediaWiki/Wiktionary.
12. Dodać opcjonalne providery Morfeusz/LanguageTool/plWordNet/WSJP reference.
13. Dodać `RouteHandlerDispatcher`.
14. Rozszerzyć `RouteHandlerResult`.
15. Podłączyć dispatcher do `JaznEngine.process_turn()`.
16. Przerobić no-op handlery na realne handlery po kolei.
17. Oczyścić `conversation.py` z powieleń i starych tras aktywnych.
18. Rozszerzyć validator strukturalny.
19. Rozszerzyć source_origin/provenance.
20. Dodać test mode dla runtime events.
21. Uporządkować raw memory status.
22. Dodać testy v14.6.10.
23. Uruchomić compileall.
24. Uruchomić collect-only.
25. Uruchomić szybki pytest.
26. Uruchomić pełny pytest, jeśli środowisko pozwala.
27. Wygenerować raport testów.
28. Wygenerować `MANIFEST_CURRENT.json` i `SHA256SUMS`.
29. Sprawdzić ZIP przez `zipfile.testzip()`.
30. Przygotować pełny ZIP i części awaryjne.
31. Zapisać raport eksportu.
32. Uruchomić świeżą kopię paczki i `--startup-status`.
33. Uruchomić scenariusze akceptacyjne.
34. Dopiero wtedy oznaczyć paczkę jako gotową.

---

## 22. SCENARIUSZE AKCEPTACYJNE

### 22.1. Start

```bash
python main.py --startup-status
```

Oczekiwane:

- wersja v14.6.10;
- aktywny folder;
- start_file `main.py`;
- cache status;
- update history index status;
- network policy status;
- raw memory status bez udawania rozpakowanego `chat.html`.

### 22.2. Zwykła rozmowa

```bash
python main.py --runtime-preview "I jak minął Tobie dzień?"
```

Oczekiwane:

- naturalna odpowiedź;
- brak starego tematu;
- brak traktowania jako hotfix;
- route `ordinary_dialogue` albo `self_state`, zależnie od klasyfikacji;
- handler faktycznie wykonany.

### 22.3. Diagnostyka runtime

```bash
python main.py --runtime-preview "Widzę, że timestamp zniknął. Co się dzieje?"
```

Oczekiwane:

- route `runtime_diagnostic`;
- pokazuje timestamp/status;
- nie ukrywa błędu final visible layer;
- zapisuje source_origin.

### 22.4. Słownik

```bash
python main.py --runtime-preview "Co znaczy słowo 'jaźń'? Sprawdź słownik."
```

Oczekiwane:

- route `dictionary_lookup`;
- `allow_network=True` z configu;
- wynik z cache/providera albo jawny błąd sieci;
- źródło/licencja/czas/cache status;
- brak udawania sprawdzenia.

### 22.5. Research

```bash
python main.py --runtime-preview "Sprawdź w internecie aktualną dokumentację pytest markers."
```

Oczekiwane:

- route `external_research`;
- jeśli lokalny runtime nie ma web providera, status `requires_external_web_execution`;
- jeśli ma provider, źródła i czas pobrania.

### 22.6. Manifesty

```bash
python -m latka_jazn.tools.update_history_audit --root . --write-index --write-report
```

Oczekiwane:

- indeks istnieje;
- każdy historyczny manifest sklasyfikowany;
- aktywne deklaracje mają status implementacji;
- stare manifesty nie mylą się z `MANIFEST_CURRENT.json`.

### 22.7. Eksport

```bash
python main.py --export-full
```

Oczekiwane:

- pełny ZIP;
- części awaryjne;
- aktualne SHA;
- `MANIFEST_CURRENT.json` zgodny z paczką;
- raport eksportu;
- `zipfile.testzip()` OK.

---

## 23. KRYTERIA „DONE”

Aktualizacja jest gotowa dopiero, gdy:

1. Runtime startuje z nowej paczki.
2. `VERSION.txt`, `pyproject.toml`, README, start file i manifesty są spójne.
3. Historyczne manifesty są zachowane i zaindeksowane.
4. `update_history_audit.py` działa i generuje raport.
5. `allow_network=True` jest realnie przekazywane do dictionary adaptera.
6. Każdy request słownikowy ma wynik z lokalnego źródła/cache/providera albo jawny status braku sieci.
7. Provider HTTP ma timeout i cache.
8. Handlery są faktycznie wykonywane przez dispatcher.
9. No-op handlery nie są traktowane jako gotowe funkcje.
10. Zwykła rozmowa nie wpada automatycznie w tryb aktualizacji/hotfix.
11. Validator sprawdza strukturę źródeł, nie tylko słowa w body.
12. Source origin zapisuje źródła słownikowe/researchowe/pamięciowe.
13. Runtime final visible text nie gubi timestampu w wymaganych trybach.
14. Raw memory status jest prawdziwy: archiwum/rozpakowana/niedostępna.
15. Testy szybkie przechodzą jednoznacznie.
16. Testy wolne/integracyjne są oznaczone markerami i raportowane.
17. Paczka eksportowa ma aktualny manifest i SHA.
18. ZIP przechodzi integralność.
19. Części awaryjne są kompletne i możliwe do złożenia.
20. Raport aktualizacji nie ukrywa ograniczeń.

---

## 24. RYZYKA I JAK ICH NIE UKRYĆ

### 24.1. Internet w lokalnym runtime

Ryzyko: środowisko lokalne może nie mieć internetu.  
Rozwiązanie: `requires_external_web_execution`, cache i brak udawania.

### 24.2. Licencje słowników

Ryzyko: różne źródła mają różne licencje i ograniczenia.  
Rozwiązanie: `license_hint`, `source_policy`, brak masowego kopiowania treści bez jasnego prawa.

### 24.3. Testy wolne

Ryzyko: pełny pytest może przekraczać limit środowiska.  
Rozwiązanie: markery, szybki zestaw, raport wolnych testów.

### 24.4. Dynamiczne pliki pamięci

Ryzyko: hashe zmieniają się po każdym starcie.  
Rozwiązanie: osobny profil dynamiczny.

### 24.5. Przenoszenie manifestów

Ryzyko: stare testy oczekują manifestów w root.  
Rozwiązanie: aliasy, indeks, aktualizacja testów.

### 24.6. Nadmierne rozbudowanie `conversation.py`

Ryzyko: kolejne hotfixy będą doklejane do monolitu.  
Rozwiązanie: dispatcher i handlery jako główny kierunek.

---

## 25. ŹRÓDŁA TECHNICZNE DO UŻYCIA PRZY IMPLEMENTACJI

- Python Packaging User Guide — `pyproject.toml` jako plik konfiguracji narzędzi pakowania i innych narzędzi projektu: https://packaging.python.org/en/latest/guides/writing-pyproject-toml/
- Pytest — markery testów i `addopts`: https://docs.pytest.org/en/stable/how-to/mark.html oraz https://docs.pytest.org/en/stable/example/simple.html
- Requests — timeouty muszą być ustawiane jawnie, bo domyślnie requesty nie timeoutują: https://requests.readthedocs.io/en/master/user/advanced/
- JSON Schema — opis struktury, ograniczeń i typów danych JSON: https://json-schema.org/learn/getting-started-step-by-step
- MediaWiki REST/API — kontrolowany dostęp do treści i wyszukiwania wiki: https://www.mediawiki.org/wiki/API%3AREST_API oraz https://www.mediawiki.org/wiki/API%3AAction_API
- Morfeusz — analiza morfologiczna języka polskiego: https://morfeusz.sgjp.pl/doc/about/en
- LanguageTool HTTP Server — lokalny serwer HTTP do sprawdzania tekstu: https://dev.languagetool.org/http-server.html
- plWordNet/Słowosieć — polska sieć leksykalno-semantyczna: https://clarin-pl.eu/dspace/handle/11321/273

---

## 26. NAJKRÓTSZY WNIOSEK WYKONAWCZY

Najbliższa aktualizacja nie powinna być tylko dopisaniem kilku reguł. Powinna przebudować trzy wąskie gardła systemu:

1. **Historia aktualizacji** — manifesty zachować, przenieść, zaindeksować, audytować.
2. **Słownik i internet** — `allow_network=True`, ale przez bezpieczne providery, cache, timeout, źródło i licencję.
3. **Runtime routing** — dispatcher ma wykonywać handlery naprawdę, żeby Jaźń nie wracała do monolitycznych fallbacków.

Dopiero po tych zmianach eksport pełnej paczki będzie miał sens jako wersja v14.6.10.
