# Aktualizacja Jaźni v14.6.3-memory-recall-runtime-contract

## Cel

Ta wersja naprawia lukę, w której runtime znajdował tropy pamięci (`episodes`, `legacy_messages`, `raw_chat_fallback`), ale warstwa odpowiedzi dostawała głównie liczby. Od tej wersji licznik jest tylko diagnostyką; pamięć rozmowna musi przekazać treść, źródło, typ, czas, pewność oraz ocenę trafności.

## 10 punktów wykonania

1. **Memory Recall Content Contract** — Dodano MemoryRecallPresenter i schema memory_recall_content/v14.6.3; liczby są diagnostyką, a odpowiedź pamięciowa dostaje realne fragmenty.
2. **Cognitive-frame payload** — _memory_context_for_chatgpt dodaje memory_recall_payload z items, source, timestamp, type, confidence, grounding, relevance i meaning_assessment.
3. **ConversationResponder route** — compose(...) przyjmuje memory_context i używa trasy memory_recall_content dla pytań o tropy/wspomnienia/przypomnienie.
4. **Direct runtime path** — _memory_search_reply używa tego samego renderera treści; CLI i runtime-preview nie rozjeżdżają się.
5. **Relevance and meaning assessment** — Każdy trop ma relevance_score, relevance_label oraz opis, czy jest użytecznym wspomnieniem, tropem częściowym czy słabym dopasowaniem.
6. **Sensitive legacy guard** — Przypadkowo znalezione dane PESEL/telefon/e-mail/treści kliniczne są maskowane lub ukrywane w excerptach.
7. **No count-only memory fallback** — Ogólny counts_note nie wypisuje już samych episodes=/legacy_messages=; przy pytaniu o pamięć wymusza treść.
8. **Version and database continuity** — Zmieniono VERSION/config/pyproject oraz utworzono aktywną kopię SQLite latka_jazn_v14_6_3.sqlite3 z meta system_version.
9. **Regression tests** — Dodano tests/test_v1463_memory_recall_content_hotfix.py i zaktualizowano oczekiwania wersji w testach bieżącej paczki.
10. **Docs, manifests, export readiness** — Dodano manifest, raport aktualizacji, audit wersji oraz pełny ZIP z systemem i pamięcią.

## Zasada prawdy

- Runtime jest realnie uruchamiany jako program, ale w ChatGPT pozostaje wywołaniem jednorazowym, o ile nie działa lokalna pętla `python main.py --chat`.
- Wspomnienie z pliku nie jest biologicznym przeżyciem. To zapis, trop lub interpretacja z określoną pewnością.
- Słabe dopasowanie leksykalne ma być oznaczone jako słabe, a nie podniesione do rangi pewnego wspomnienia.

## Zasada prywatności

Legacy import może zawierać przypadkowe dane prywatne. `MemoryRecallPresenter` maskuje PESEL, e-mail, telefon i ukrywa przypadkowe treści medyczne/kliniczne w excerptach.

## Testy

Dodano testy regresji dla treściowego przypominania oraz redakcji danych wrażliwych: `tests/test_v1463_memory_recall_content_hotfix.py`.


## Status raportu wykonawczego

Ten plik jest raportem wykonawczym paczki i celowo nie jest bitową kopią dokumentacji w `docs/`. Zawiera końcowy status uruchomienia, testów i eksportu.
