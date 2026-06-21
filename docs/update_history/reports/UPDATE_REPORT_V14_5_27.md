# UPDATE_REPORT_V14_5_27_DIALOGUE_REPAIR

Wersja: `v14.5.27-dialogue-repair`
Baza: `v14.5.26-full-completeness-repair`

## Powód aktualizacji

Krzysztof wskazał realny błąd zachowania: odpowiedzi Łatki za często przechodziły w opisywanie i parafrazowanie tego, co powiedział użytkownik. To było mylone z empatią i obecnością, ale w praktyce osłabiało dialog.

## Naprawa

1. Dodano do kontraktu ChatGPT bridge regułę dialogową i regułę anti-paraphrase.
2. Dodano `dialogue_context` do cognitive-frame, aby ChatGPT dostawał jawne wskazanie: po krótkim uznaniu wypowiedzi ma wnieść nowy wkład — pytanie, propozycję, decyzję, własną reakcję albo konkretny następny krok.
3. Dodano tag intencji `dialogue_repair`, aby korekta użytkownika nie ginęła jako ogólna „architektura” albo „correction”.
4. Dodano zapis proceduralny w runtime persistence: taka korekta zapisuje się jako reguła działania, nie jako zwykłe wspomnienie.
5. Dodano testy regresji.

## Reguła po aktualizacji

Łatka nie ma odpowiadać serią parafraz. Jedna krótka refleksja wystarczy; dalej ma być rozmowa, czyli własny wkład, pytanie, propozycja, decyzja albo konkretny ruch.

## Walidacja

- `python main.py --cognitive-frame ...` po patchu zwrócił `runtime_version = v14.5.27-dialogue-repair`.
- `dialogue_context.mode = balanced_dialogue`.
- `dialogue_context.repair_requested = true`.
- `persistence.candidate_kind = reguła_proceduralna`.
- Testy: `52 passed`.
