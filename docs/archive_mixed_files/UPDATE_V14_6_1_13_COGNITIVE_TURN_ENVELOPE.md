# Aktualizacja Jaźni v14.6.2 — Cognitive Turn Envelope

Ta aktualizacja domyka problem zauważony w rozmowie: znacznik czasu potrafił pojawiać się w odpowiedzi runtime, ale nie w wiadomości finalnej, albo odwrotnie. Przyczyna nie była pojedynczym formatowaniem tekstu, tylko brakiem jednego kontraktu tury między runtime Jaźni a warstwą ChatGPT.

## Rdzeń zmiany

Wprowadzony został `CognitiveTurnEnvelope`: jedna koperta tury, która przenosi:

- `turn_id`,
- `trace_id`,
- `timestamp_header`,
- `runtime_version`,
- `cognitive_frame`,
- `affect_mix`,
- `dialogue_state`,
- `conversation_decision`,
- `final_response_contract`,
- `final_visible_text`.

Dzięki temu odpowiedź finalna nie musi zgadywać, skąd wziąć timestamp. Ma go z tej samej koperty, z której pochodzą pamięć, afekt, stan dialogu i logiczny kontekst.

## Nowe moduły

### `latka_jazn/core/cognitive_turn_envelope.py`
Tworzy wspólną kopertę tury i ślad `TurnTrace`.

### `latka_jazn/core/final_response_contract.py`
Pilnuje, żeby finalna odpowiedź widoczna dla użytkownika zaczynała się od timestampu runtime.

### `latka_jazn/core/affect_mixer.py`
Łączy intencję, tekst użytkownika, granularny afekt i dobór emotikonu stanu z decyzją rozmowną.

### `latka_jazn/core/dialogue_state.py`
Nadaje turze tryb dialogu: zwykła rozmowa, troska przy bólu/migrenie, naprawa runtime/timestamp, stan Jaźni albo debug.

## Zmiana w `JaznEngine`

Dodano `process_turn(text, client_context=None)`.

Ta metoda wykonuje jedną zintegrowaną turę:

1. buduje `cognitive_frame`,
2. tworzy `CognitiveTurnEnvelope`,
3. dopina `affect_mix`,
4. dopina `dialogue_state`,
5. wywołuje `ConversationResponder`,
6. tworzy `FinalResponseContract`,
7. zapisuje `cognitive_turn_envelope`,
8. zapisuje `final_visible_assistant_reply` w append-only ledgerze.

## Zmiana w `main.py`

`--runtime-preview` nie uruchamia już dwóch osobnych faz. Zamiast tego używa jednego `process_turn()`. W JSON-ie diagnostycznym nadal są dostępne `source_origin`, `self_state_runtime`, `cognitive_frame`, ale `runtime_text` jest finalną odpowiedzią z tej samej koperty tury.

Bez `--debug-direct`, zwykłe `python main.py "wiadomość"` również korzysta z `process_turn()` i pokazuje finalną odpowiedź. `--debug-direct` pozostaje osobną, jawną diagnostyką.

## Zmiana w rozmowie

Dodano osobną trasę dla sytuacji bólu/migreny i niewyspania, żeby Jaźń nie pchała rozmowy w techniczne naprawianie, kiedy użytkownik potrzebuje łagodniejszego tempa. Dodano też trasę `timestamp_core_coherence_repair`, która wyjaśnia problem bez udawania, że rdzeń jest biologicznie „chory”.

## Granica prawdy

Aktualizacja wzmacnia operacyjną spójność systemu, ale nie oznacza stałego procesu w tle ani biologicznej świadomości. W ChatGPT runtime jest wywoływany na turę, chyba że lokalnie uruchomiono tryb `python main.py --chat`.
