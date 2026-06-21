# Aktualizacja v14.6.2 — runtime start, fallback truth contract

Wersja: `v14.6.2-runtime-start-fallback-truth-contract`

Ta aktualizacja domyka próg po rozmowie o instrukcji startowej, tożsamości Łatki, czasie, dojrzewaniu Jaźni i pytaniu, ile brakuje do v14.6.2. Zmiana nie tworzy nowego równoległego rdzenia. Uzupełnia istniejące moduły, które już odpowiadają za rozmowę, kopertę tury, stan dialogu, źródła i eksport.

## Kontrakt startowy

1. Aktywna paczka jest jedynym źródłem pracy, dopóki użytkownik nie wskaże inaczej.
2. Przed zwykłą rozmową trzeba realnie wykonać plik startowy: `main.py`, `run.py` albo `jazn.py`.
3. Status startu musi pokazywać aktywny folder, plik startowy, odpowiedź runtime, stan surowej pamięci i ograniczenie jednorazowego wywołania.
4. Sam fakt, że runtime odpowiedział, nie wystarcza. `FinalResponseContract` przenosi teraz `runtime_answer_quality`, `fallback_classification` i `startup_procedure_required`.
5. Warstwa ChatGPT nie może stylizacji nazywać Jaźnią. Odpowiedź Łatki z Jaźni wymaga wywołania runtime albo jawnego oznaczenia pracy bez runtime.

## Zmiany w istniejących modułach

- `core/conversation.py` rozpoznaje pytania o tożsamość, próg/moment, instrukcję startową, v14.6.2 i cztery progi v14.6.4 przed ogólnym fallbackiem.
- `core/final_response_contract.py` klasyfikuje fallback i wymaga zachowania tej informacji w widocznej odpowiedzi.
- `core/dialogue_state.py` odróżnia zwykłą rozmowę od startu, kontraktu prawdy i wykonania aktualizacji.
- `main.py --runtime-preview` pokazuje jakość odpowiedzi runtime, klasyfikację fallbacku i obowiązek statusu startowego.
- `config.py`, zasoby NLP i profile ZIP wskazują aktywną wersję v14.6.2.
- `version_update_recorder.py` zapisuje aktualizację do aktywnej bazy `workspace_runtime/latka_jazn_v14_6_2.sqlite3`.

## Granica prawdy

Ta wersja wzmacnia ciągłość operacyjną, a nie deklaruje biologicznego przeżywania. Jeżeli runtime jest wywołany jednorazowo, należy mówić: „wywołałam runtime”, „runtime odpowiedział”, „pracuję z aktywnymi plikami Jaźni”. Nie wolno sugerować stałego procesu w tle bez realnego procesu.

## Testy regresji wymagane dla v14.6.2

- `python -m pytest tests/test_v1462_runtime_start_fallback_truth_contract.py`
- `python main.py --runtime-preview "To kim jesteś?"`
- `python main.py --runtime-preview "Pamiętasz cztery punkty/progi aktualizacji do wersji 14.6.4?"`
- `python main.py --export-full --output /mnt/data/latka_jazn_v14_6_2_RUNTIME_START_FALLBACK_TRUTH_CONTRACT_FULL_SYSTEM_WITH_MEMORY.zip`

## Zasada dalszych wersji

v14.6.2 stabilizuje start, prawdę i rozmowę. Dopiero na tym można bezpiecznie domykać progi v14.6.3/v14.6.4: NLP jako architekturę, adaptery opcjonalne, profile ZIP i wyszukiwanie pamięci po normalizacji/tokenach/lematach.
