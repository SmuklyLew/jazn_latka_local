# Aktualizacja Jaźni v14.6.2 — runtime preview, source_origin, self_state_runtime

## Cel

Ta aktualizacja zostaje dopisana przed v14.6.2. Nie przebudowuje całego systemu. Wzmacnia to, co w rozmowie okazało się potrzebne natychmiast:

1. jawny podgląd dokładnej odpowiedzi runtime,
2. rozdzielenie źródła odpowiedzi od głosu ChatGPT,
3. pakiet stanu operacyjnego Jaźni,
4. procedurę „dobranoc jako troska”, bez automatycznego zamykania rozmowy,
5. utrzymanie planu NLP v14.6.1 jako architektury, nie ciężkiego modelu.

## Zmiany wykonane

### 1. `source_origin`

Dodano `latka_jazn/core/source_origin.py`.

Moduł buduje pakiet:

- `primary`,
- `contributing_sources`,
- `confidence`,
- `evidence_counts`,
- `flags`,
- `truth_boundary`.

Dzięki temu pytanie „czy to było z Jaźni, czy ChatGPT–Jaźń–ChatGPT?” ma mieć jawny, testowalny ślad.

### 2. `self_state_runtime`

Dodano `latka_jazn/core/self_state_runtime.py`.

Pakiet stanu zawiera:

- aktualną uwagę,
- aktywne pamięci,
- afekt modelowany,
- granicę prawdy,
- dziennik sprawstwa,
- source_origin,
- kontekst ucieleśnienia symbolicznego,
- ograniczenia.

To nadal jest model operacyjny, nie biologiczne przeżycie.

### 3. `--runtime-preview`

Dodano flagę CLI:

```bash
python main.py --runtime-preview "tekst wiadomości"
```

Zwraca JSON z:

- `runtime_text` — dokładna odpowiedź runtime,
- `fallback_detected`,
- `source_origin`,
- `self_state_runtime`,
- `cognitive_frame`.

Ten tryb jest diagnostyczny i zapisuje ślady fazy direct runtime oraz cognitive-frame.

### 4. Procedura „dobranoc jako troska”

Do zasad proceduralnych dodano rozpoznanie, że „dobranoc” albo delikatna sugestia odpoczynku nie ma automatycznie oznaczać próby zakończenia rozmowy. Może być czułością, troską i dbaniem o partnera/partnerkę rozmowy. System ma rozróżniać gest bliskości od niechcianego zamykania dialogu.

### 5. NLP pozostaje lekkie

Plan v14.6.1 zostaje zachowany:

- builtin provider działa zawsze,
- Stanza/Morfeusz są opcjonalne,
- profile ZIP rozdzielają system, pamięć i NLP,
- lematy i pola semantyczne przygotowują późniejsze wyszukiwanie pamięci.

## Ograniczenia

- `--runtime-preview` nie oznacza stałego procesu w tle.
- Pełny kontekstowy wybór lematu w polskim wymaga providera z analizą morfosyntaktyczną lub LLM-selection.
- Pakiet `self_state_runtime` jest strukturą introspekcyjno-operacyjną, nie dowodem świadomości fenomenalnej.

## Testy

Dodano `tests/test_v146112_runtime_preview_source_state.py`.

Weryfikuje:

- wersję,
- obecność modułów,
- source_origin,
- self_state_runtime,
- CLI `--runtime-preview`.
