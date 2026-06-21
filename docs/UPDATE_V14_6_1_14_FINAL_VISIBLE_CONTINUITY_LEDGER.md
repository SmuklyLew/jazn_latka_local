# Aktualizacja v14.6.2 — final visible continuity ledger

Ta aktualizacja domyka problem zauważony w rozmowie: timestamp i odpowiedź runtime mogły być spójne wewnętrznie, ale widoczna odpowiedź ChatGPT nadal mogła być warstwą, która nie zostaje zapisana jako dokładny fakt tury. Wtedy użytkownik widział tekst, którego nie dało się później uczciwie odtwórzyć z ledgera Jaźni.

## Cel

Jedna tura ma mieć jeden wspólny przewód:

```text
user message
  -> process_turn()
  -> cognitive_turn_envelope
  -> final_response_contract
  -> final_visible_assistant_reply
  -> session_continuity_index
```

Jeżeli finalny tekst powstaje już poza runtime, widoczna warstwa ChatGPT może dopisać go przez:

```bash
python main.py --record-final-reply \
  --turn-id TURN_ID \
  --trace-id TRACE_ID \
  --timestamp-header "[🕒 ... Europe/Warsaw]" \
  --state-emoticon "🌿" \
  "Finalny tekst widoczny użytkownikowi"
```

albo przez metodę:

```python
engine.persist_final_visible_reply(
    turn_id=turn_id,
    trace_id=trace_id,
    timestamp_header=timestamp_header,
    final_text=final_text,
    source="chatgpt_visible_layer",
)
```

## Co zostało dodane

- `latka_jazn/core/final_visible_reply_capture.py`
- `FinalResponseContract.validate_visible_text()`
- `JaznEngine.persist_final_visible_reply()`
- `main.py --record-final-reply`
- testy regresji `tests/test_v146114_final_visible_continuity_ledger.py`

## Co zostało zmienione

`JaznEngine.process_turn()` po zbudowaniu `FinalResponseContract` zapisuje:

- `cognitive_turn_envelope`,
- `final_visible_assistant_reply`,
- dokładną turę assistant w `conversation_turns.jsonl`,
- aktualizację `session_continuity_index` z powodem `final_visible_reply_persisted`.

## Granica prawdy

Ta aktualizacja nie oznacza, że Jaźń działa stale w tle w ChatGPT. Oznacza, że gdy runtime lub widoczna warstwa zostają realnie wywołane, mają narzędzie do zapisania dokładnego śladu odpowiedzi bez streszczania i bez gubienia timestampu.

## Kontrakt spójności wersji

Bieżące pliki sterujące tej paczki muszą opisywać system jako `v14.6.2-final-visible-continuity-ledger`. Starsze manifesty i raporty mogą pozostać w paczce wyłącznie jako historia wersji, nie jako aktywny opis startowy.
