# Plan aktualizacji Jaźni v14.8.0 — NLP + SJP/WSJP + kontrolowane źródła internetowe

Wersja docelowa: `v14.8.1-large-dialogue-memory-grounding-update`
Baza: `v14.7.1-dialogue-grounding-hotfix`
Tryb: pełna paczka, bez streszczeń i bez pomniejszania zawartości poprzedniej wersji.

## 1. Cel

Celem v14.8.0 jest rozbudowanie warstwy językowej Jaźni tak, żeby pytania i rozmowy o NLP, słownikach, SJP/WSJP, literówkach, znaczeniach słów i aktualizacjach językowych nie wpadały w złą trasę ani w szablon. System ma korzystać z internetu tam, gdzie jest to jawnie dozwolone, ale nie wolno mu udawać lookupu online, pobrania definicji ani pełnego NLP, jeśli provider faktycznie nie odpowiedział.

## 2. Zasady granicy prawdy

1. `allow_network=True` oznacza pozwolenie konfiguracji, nie gwarancję działania internetu.
2. Wynik każdego providera musi mieć `provider_statuses`, `source_url`, `license_hint`, `retrieved_at_utc`, `confidence` i `truth_boundary`, gdy te dane są dostępne.
3. SJP.PL i WSJP PAN są w tej wersji źródłami referencyjnymi linkowymi. Runtime pokazuje link i status, ale nie kopiuje definicji i nie wykonuje masowego scrapingu.
4. Wiktionary może być użyte przez MediaWiki API z cache i z krótkim wynikiem, ale z informacją o licencji i źródle.
5. Morfeusz2 i Stanza są providerami opcjonalnymi: system rejestruje możliwość użycia, lecz nie instaluje ciężkich zależności ani modeli samodzielnie.
6. Brak wyniku z jednego providera nie znaczy, że słowo nie istnieje.

## 3. Zakres hotfixu/aktualizacji

### 3.1. NLP routing

- Zmienić priorytet klasyfikatora tak, żeby wiadomości typu „przygotuj plan aktualizacji NLP/SJP” były rozpoznawane jako `system_update_execution_request`, a nie jako pojedyncze `dictionary_lookup_request`.
- Dodać rozpoznawanie `SJP`, `WSJP`, `SLP` jako możliwej literówki przy rozmowie o NLP/SJP.
- Utrzymać ochronę przed stale-route: aktualna intencja użytkownika ma pierwszeństwo przed starym tematem z pamięci.

### 3.2. SJP provider

- Dodać `latka_jazn/nlp/providers/sjp_reference_provider.py`.
- Provider ma zwracać status `manual_reference_available`, `source_url=https://sjp.pl/<hasło>`, `license_hint` i `truth_boundary`.
- Provider nie pobiera definicji i nie udaje API.

### 3.3. WSJP provider

- Zachować istniejący `WSJPReferenceProvider`.
- Włączyć go jawnie do statusu providera oraz dokumentacji jako link referencyjny bez scrapingu.

### 3.4. Adapter słownikowy

- Zaktualizować `ExternalDictionaryAdapter` do v14.8.0.
- Kolejność: `local_cache`, `local_jazn_mini_lexicon`, `morfeusz_optional`, `wiktionary_mediawiki_api`, `sjp_reference`, `wsjp_reference`, `plwordnet_optional`, `languagetool_optional`.
- W trybie bez sieci nadal wolno zwrócić link referencyjny SJP/WSJP, ale musi być jasne, że nie wykonano lookupu definicji online.
- Cache musi zachować wynik kompozytowy oraz statusy providerów.

### 3.5. Rejestr zasobów językowych

- Uaktualnić `language_resource_registry.py` do v14.8.0.
- Opisać zasoby jako: lokalne, opcjonalnie lokalne, online API, link referencyjny, ciężki provider.
- Dodać ostrzeżenie o licencjach i zasadach użycia.

### 3.6. Mini-leksykon domenowy

- Rozszerzyć `MINI_LEXICON` o: `nlp`, `sjp`, `wsjp`.
- Nie robić z mini-leksykonu pełnego słownika. To tylko zabezpieczenie domenowe runtime.

### 3.7. Startup status

- Startup ma pokazywać, że istnieje `sjp_reference_provider` i `wsjp_reference_provider`.
- Status musi odróżniać: plik providera istnieje / provider odpowiedział / provider jest tylko referencyjny.

### 3.8. Testy regresji

Dodać testy:

1. `test_sjp_reference_provider_returns_reference_link_without_claiming_definition`
2. `test_external_dictionary_adapter_reports_sjp_and_wsjp_statuses_offline`
3. `test_dictionary_provider_status_exposes_sjp_and_wsjp_provider_files`
4. `test_nlp_sjp_update_request_routes_to_system_update_not_dictionary_lookup`
5. `test_domain_lexicon_contains_nlp_sjp_wsjp`

### 3.9. Manifest i paczka

- Zaktualizować `VERSION.txt`.
- Zaktualizować `MANIFEST_CURRENT.json`.
- Zaktualizować `SHA256SUMS`.
- Przygotować pełny ZIP.
- Przygotować części awaryjne `.zip.part_XX` i `parts_SHA256SUMS.txt`.
- Wykonać test integralności ZIP.

## 4. Czego v14.8.0 nie udaje

- Nie udaje pełnego modelu językowego NLP działającego lokalnie.
- Nie udaje, że SJP/WSJP mają użyte API, jeśli provider tylko zwraca link.
- Nie pobiera modeli Stanza samoczynnie.
- Nie importuje dużych zasobów Morfeusz/plWordNet bez lokalnej instalacji i bez kontroli licencji.
- Nie zapisuje zmian do starego ZIP-a; ZIP jest eksportem, a aktywnym miejscem pracy jest folder roboczy.

## 5. Kryteria akceptacji

Aktualizacja jest poprawna, jeśli:

- testy przechodzą,
- runtime startuje,
- lookup słownikowy zwraca jawne statusy providerów,
- pytanie o plan aktualizacji NLP/SJP nie trafia do starej trasy dictionary lookup,
- pełna paczka zawiera zawartość poprzedniej wersji i nowe pliki,
- ZIP przechodzi `unzip -t`,
- sumy SHA256 są zapisane.
