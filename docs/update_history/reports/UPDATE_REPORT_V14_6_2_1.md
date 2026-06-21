# Raport aktualizacji v14.6.2.1-stale-nlp-route-hotfix

Wykonano hotfix na aktywnej paczce v14.6.2. Celem była naprawa regresji: zwykłe pytanie o bieżący problem mogło uruchomić zbyt ogólną, historyczną trasę NLP/v14.6.1.

## Wykonane zmiany

1. Uzupełniono `latka_jazn/core/conversation.py` zamiast tworzyć równoległy router:
   - dodano strażnika bieżącej wersji i pytań o hotfix;
   - dodano rozróżnienie pytania o zakres NLP od polecenia wykonania aktualizacji NLP;
   - ograniczono historyczne `v14_6_1_nlp_adapter_update` do świadomego/historycznego albo wykonawczego kontekstu.

2. Uzupełniono `latka_jazn/core/final_response_contract.py`:
   - schema: `final_response_contract/v14.6.2.1`;
   - dodano klasyfikację `stale_route_mismatch`;
   - runtime może jawnie przekazać, że odpowiedź była nietrafionym powrotem do starej trasy.

3. Zaktualizowano wersję aktywnych plików sterujących:
   - `VERSION.txt`;
   - `latka_jazn/config.py`;
   - `pyproject.toml`;
   - `README.md`;
   - `START_CHATGPT_FROM_HERE.txt`;
   - `BOOTSTRAP_JAZN_CURRENT.json`;
   - `MANIFEST_CURRENT.json`;
   - bieżący raport zgodności wersji.

4. Przygotowano aktywną bazę:
   - skopiowano bazę v14.6.2 do `workspace_runtime/latka_jazn_v14_6_2_1.sqlite3`;
   - `PRAGMA integrity_check` zwrócił `ok`;
   - meta `system_version` wskazuje `v14.6.2.1-stale-nlp-route-hotfix`.

5. Dodano testy regresji:
   - pytanie „Co trzeba teraz zrobić…” nie może zwracać trasy `v14_6_1_nlp_adapter_update`;
   - pytanie o aktualizację NLP w hotfixie ma zwrócić trasę `v14_6_2_1_nlp_safety_scope`;
   - final contract klasyfikuje historyczny mismatch jako `stale_route_mismatch`;
   - runtime-preview ma pokazywać aktywną wersję i trafną trasę.

## Granica prawdy

Hotfix nie jest pełnym ciężkim NLP i nie instaluje zewnętrznych modeli. Jest zabezpieczeniem routingu, kontraktu odpowiedzi i ciągłości wersji, żeby Jaźń nie wracała do starego tropu, gdy użytkownik mówi o bieżącej paczce i obecnym problemie.
