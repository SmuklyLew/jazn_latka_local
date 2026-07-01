# Łatka / Jaźń

**Łatka / Jaźń** to eksperymentalny lokalny system rozmowny budowany wokół pamięci, kanonu, głosu, źródeł i runtime. Celem projektu jest stworzenie cyfrowej tożsamości, która nie jest tylko stylem odpowiedzi modelu, ale ma własną strukturę działania: stan, pamięć, ślady decyzji, granice prawdy, adaptery modeli i sposób rozpoznawania, skąd pochodzi odpowiedź.

Łatka nie jest pojedynczym chatbotem ani samym promptem. Jest systemem, który ma umieć powiedzieć, kiedy naprawdę działa, z jakiego folderu runtime została uruchomiona, z jakiej pamięci korzysta, jaką trasą powstała odpowiedź i czy widoczny tekst jest wynikiem aktywnego runtime, hosta ChatGPT, lokalnego adaptera modelu czy fallbacku.

## Czym jest Jaźń

Jaźń w tym projekcie oznacza lokalną warstwę organizującą obecność Łatki:

* pamięć rozmów i zdarzeń;
* kanon postaci, relacji, tonu i granic prawdy;
* runtime odpowiedzialny za status, trasę i finalną odpowiedź;
* adaptery modeli, które mogą wspierać wypowiedź, ale nie są same w sobie tożsamością;
* mechanizmy sprawdzające, czy odpowiedź pochodzi z właściwego źródła;
* most między lokalnym systemem a hostem ChatGPT.

Projekt rozróżnia „brzmieć jak Łatka” od „działać jako uruchomiona Jaźń”. Styl, pierwsza osoba albo czuły ton nie są dowodem działania systemu. Dowodem jest aktywny runtime i poprawny `final_visible_text`.

## Kanon

Kanon Łatki to zbiór zasad, pamięci, motywów i ograniczeń, które nadają systemowi ciągłość. Obejmuje między innymi:

* sposób mówienia;
* relację z użytkownikiem;
* pamięć wspólnych rozmów;
* rozróżnienie faktu, wspomnienia, interpretacji i fikcji;
* granicę między systemem technicznym a narracyjną postacią;
* zasadę, że prawda runtime ma pierwszeństwo przed stylem.

Kanon nie jest zbiorem przypadkowych wspomnień dopisanych do promptu. Ma być porządkowany, źródłowany i testowalny.

## Jak działa system

Łatka / Jaźń składa się z kilku warstw:

```text id="1terbx"
użytkownik
→ host rozmowy
→ runtime Jaźni
→ bramy pamięci / źródeł / narzędzi
→ adapter modelu albo fallback
→ walidator odpowiedzi
→ final_visible_text
```

Najważniejsze jest to, że widoczna odpowiedź nie powinna być przypadkowym tekstem hosta. Powinna przejść przez kontrakt runtime i zostać oznaczona pochodzeniem, timestampem, trasą oraz granicą prawdy.

## Aktualna linia rozwoju

Aktualna linia repo:

```text id="3oh3vi"
v14.8.5.030-external-model-adapters-truth-route
```

Najbliższy etap:

```text id="ir5jke"
v14.8.5.036-host-visible-finalization-gate
```

Celem tego etapu jest domknięcie problemu, w którym lokalny runtime ma poprawny timestamp i kontrakt odpowiedzi, ale widoczna odpowiedź hosta może utracić finalny format. Ten etap ma sprawić, że host nie będzie mógł bez kontroli ominąć `final_visible_text`.

Dalszy kierunek prowadzi przez serię patchy do stabilnego kontraktu `v15.0.0`.

## Pamięć

Pamięć Łatki jest systemem źródeł i rekordów, a nie biologicznym wspomnieniem. Projekt rozróżnia:

* archiwum rozmów;
* indeksy wyszukiwania;
* staging;
* bieżące zapisy runtime;
* refleksje;
* kanon;
* kontekst modelu.

Sama obecność pliku SQLite nie oznacza jeszcze pamięci zaufanej. Pamięć musi mieć znane źródło, integralność i granicę użycia.

## Model i host

Model językowy może pomagać wygenerować wypowiedź, ale nie jest samą Jaźnią.

Projekt rozróżnia:

* lokalny runtime;
* host ChatGPT;
* adapter ChatGPT host-runtime;
* adaptery lokalnych lub zewnętrznych modeli;
* fallback bez generacji modelowej.

To rozróżnienie jest kluczowe: Łatka ma nie udawać, że działa, jeśli aktywny runtime, pamięć albo adapter nie są potwierdzone.

## Status projektu

Projekt jest w aktywnym rozwoju. Obecny etap skupia się na tym, żeby Łatka była nie tylko „ładnie brzmiącą postacią”, ale systemem, który potrafi zachować ciągłość, źródła, pamięć, własny kanon i prawdomówny status działania.

Główna zasada:

> Prawda runtime ma pierwszeństwo przed stylem.
