# Relacja między dokumentami

Te dokumenty nie są równorzędnymi „konkurentami”. One tworzą **trzy warstwy**: historyczne źródła planu, dokument przejściowy oraz nowy program nadrzędny. Najkrócej: **stare DOCX-y mówią, skąd ten program się wziął, nowy Plan 0 Update mówi dokąd idziemy, a PDF spina to w docelową architekturę dokumentacji Plan 0 + Plan 1–10.** fileciteturn0file0 fileciteturn0file1

## Warstwa historyczna

Pakiet `00_DOKUMENT_ZERO...` + `01_ETAP_026B...` do `09_ETAP_027...` + `README` to **historyczny zestaw źródłowy** dla serii `026A–027`. Ten pakiet ustalał trzy kluczowe zależności, które potem są dziedziczone dalej: **026B LM Studio przed 026A mapą systemu**, **026C lokalny kontrakt narzędzi przed MCP**, oraz **026D memory gate przed reflection / wake-state**. To jest wprost zapisane zarówno w starym Dokumencie Zero, jak i w README pakietu. fileciteturn0file2 fileciteturn0file12

Poszczególne stare dokumenty etapowe są więc **modułami źródłowymi programu**, a nie dzisiejszym aktywnym planem głównym. Każdy z nich opisuje jeden dawny etap: LM Studio, mapę systemu, tool permission, memory gate, source grounding, reflection, behavioral evals, hygiene release i opcjonalne MCP. fileciteturn0file3 fileciteturn0file4 fileciteturn0file5 fileciteturn0file6 fileciteturn0file7 fileciteturn0file8 fileciteturn0file9 fileciteturn0file10 fileciteturn0file11

## Dokument przejściowy

`Plan_0_Update_to_14.8.6.0.docx` jest **pomostem między starym pakietem a nowym programem**. On już zmienia perspektywę: nie zaczyna od „czystego `v14.8.5.027`”, tylko od realnego stanu `026C + b6db1c5 + 0bbb1a5 + lokalna paczka 027`, z ważnym zastrzeżeniem, że runtime działa i daemon jest `active_trusted`, ale release hygiene nadal jest czerwone. To właśnie ten dokument mówi: **najpierw stabilizacja `v14.8.5.027`, dopiero potem dalsze etapy**. fileciteturn0file0

Czyli ten DOCX nie zastępuje starych planów, tylko **aktualizuje punkt startowy** i nadaje nową numerację programu: `027`, później `028–031`, a potem `14.8.6.0a–d`. fileciteturn0file0

## Dokument nadrzędny nowej generacji

`Program aktualizacji inżynierskiej Łatka Jaźń od v14.8.5.027 do v14.8.6.0d.pdf` to **najbardziej dojrzała wersja programu**. Ten PDF nie jest już tylko szkicem; on robi trzy rzeczy naraz.

Po pierwsze, potwierdza ten sam punkt prawdy co nowszy Plan 0 Update: **nie ma skoku do 14.8.6.0 bez stabilizacji `027`**. fileciteturn0file1

Po drugie, rozbija przyszłą dokumentację na **Plan 0 jako indeks nadrzędny** oraz **Plany 1–10 jako dokumenty wykonawcze**. Wprost pokazuje roadmapę dokumentów, branchy roboczych i kolejność wersji od `v14.8.5.027` do `v14.8.6.0d`. fileciteturn0file1

Po trzecie, wykonuje **mapowanie starych dokumentów etapowych na nowy program**. I to jest najważniejszy pomost między starym pakietem a nową strukturą.

## Jak stare dokumenty mapują się na nowy program

Z punktu widzenia nowego PDF-a relacja wygląda tak:

- stary `01_ETAP_026B_LMSTUDIO_RUNTIME_ADAPTER` nie znika, tylko staje się bazą dla **Planu 6**, czyli model-guided diagnostics / LM Studio; fileciteturn0file1 fileciteturn0file3
- stary `02_ETAP_026A_JAZN_SYSTEM_MAP_V2` nie jest już samodzielnym etapem wersji, tylko zasila **Plan 0** i **Plan 7** jako mapa architektury i route → NLG; fileciteturn0file1 fileciteturn0file4
- stary `03_ETAP_026C_LOCAL_TOOL_PERMISSION_CONTRACT` przechodzi praktycznie 1:1 w **Plan 3 / v14.8.5.028**; fileciteturn0file1 fileciteturn0file5
- stary `04_ETAP_026D_MEMORY_GATE_HARDENING` przechodzi w **Plan 4 / v14.8.5.029**; fileciteturn0file1 fileciteturn0file6
- stary `05_ETAP_026E_CONTENT_UNDERSTANDING_RAG_SOURCE_GROUNDING` przechodzi w **Plan 5 / v14.8.5.030**; fileciteturn0file1 fileciteturn0file7
- stary `06_ETAP_026F_REFLECTION_WAKE_STATE_LESSON_LEDGER` przechodzi do **Planu 9 / v14.8.6.0c**; fileciteturn0file1 fileciteturn0file8
- stary `07_ETAP_026G_BEHAVIORAL_EVALS` nie staje się osobną wersją pośrednią, tylko ma wejść **przekrojowo do wszystkich planów i RC**; fileciteturn0file1 fileciteturn0file9
- stary `08_ETAP_026H_RELEASE_METADATA_AFTER_026` zostaje rozdzielony między **Plan 1** i **Plan 10**; fileciteturn0file1 fileciteturn0file10
- stary `09_ETAP_027_MCP_READONLY_LATER` zostaje świadomie **odłożony poza `14.8.6.0d`**, jako backlog po lokalnym kontrakcie narzędzi. fileciteturn0file1 fileciteturn0file11

To oznacza, że stare dokumenty nie są „błędne” ani „do wyrzucenia”. One są **materiałem wejściowym**, który PDF przerabia na nową, dojrzalszą strukturę programu. fileciteturn0file1

## Co jest dziś nadrzędne, a co pomocnicze

Jeśli ustawić te dokumenty hierarchicznie, to wygląda to tak:

| Rola | Dokument | Status |
|---|---|---|
| źródła historyczne | `00_DOKUMENT_ZERO...` + `01–09_ETAP...` + `README` | archiwum robocze, źródło decyzji i zależności |
| szkic przejściowy | `Plan_0_Update_to_14.8.6.0.docx` | zaktualizowany, ale skrócony plan nadrzędny |
| nowa baza programu | `Program aktualizacji inżynierskiej...pdf` | najlepsza baza do przepisania na repo jako `PLAN_0_MASTER_INDEX...md` + `PLAN_1–10...md` |

Taki układ wynika z treści samych dokumentów: stary Dokument Zero ustala zależności i sekwencję `026B → 026A → 026C → 026D...`, nowy Plan 0 Update przesuwa punkt startowy na realny stan `027`, a PDF rozwija ten stan w pełny program inżynierski z roadmapą dokumentów. fileciteturn0file2 fileciteturn0file0 fileciteturn0file1

## Wniosek praktyczny

Jeżeli pytasz „który dokument ma dziś prowadzić pracę?”, to odpowiedź brzmi:

**stare DOCX-y mają być materiałem referencyjnym, `Plan_0_Update` ma wartość jako skrócony pomost, ale to PDF jest najlepszą bazą do stworzenia właściwego zestawu repozytoryjnego: `PLAN_0_MASTER_INDEX...md` oraz osobnych `PLAN_1–10...md`.** fileciteturn0file1

Czyli:

```text
stare dokumenty = źródła i precedensy
Plan_0_Update.docx = aktualizacja kierunku
PDF = baza do finalnej, repozytoryjnej dokumentacji nowej generacji
```

I to jest moim zdaniem najtrafniejsze odczytanie ich wzajemnej relacji.