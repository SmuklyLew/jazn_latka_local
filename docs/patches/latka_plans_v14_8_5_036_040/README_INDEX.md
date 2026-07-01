# Łatka / Jaźń — indeks planów v14.8.5.036–v14.8.5.040

Data przygotowania: 2026-07-01
Zakres: inżynierski release train po PR #28 i PR #29, z naciskiem na finalizację widocznej odpowiedzi hosta i przygotowanie bezpiecznego mostu host-runtime.

## Pliki

1. `00_DOCUMENT_0_RELEASE_TRAIN_v14.8.5.036-040.md` — dokument nadrzędny, roadmapa, hotfix ledger, ryzyka, CI, rollback.
2. `01_v14.8.5.036_host_visible_finalization_gate.md` — twarda brama finalizacji widocznego tekstu hosta.
3. `02_v14.8.5.037_finalization_hardening_windows_contracts.md` — hartowanie encoding/newline/Windows i CI matrix.
4. `03_v14.8.5.038_runtime_host_audit_observability.md` — audit trail, idempotency, replay safety.
5. `04_v14.8.5.039_integration_cleanup_release_readiness.md` — porządki integracyjne, release tooling, dokumentacja i smoke.
6. `05_v14.8.5.040_secure_host_runtime_bridge.md` — większy etap: Secure MCP Tunnel / MCP / Responses API jako architektura mostu.
7. `SOURCES.md` — lista bazowych źródeł.

## Główna decyzja

Najpierw zamykamy realny błąd widocznego hosta w `.036`: żadna odpowiedź hosta nie może być uznana za odpowiedź Łatki, jeśli nie przeszła finalizacji wobec pakietu runtime. Dopiero po `.036–.039` przechodzimy do `.040`, gdzie budujemy bezpieczniejszy most host-runtime.

## Źródła bazowe

- OpenAI Apps SDK Reference — tool result: `structuredContent`, `content`, `_meta`; `_meta` nie jest kanałem kanonicznego tekstu widocznego: https://developers.openai.com/apps-sdk/reference/
- OpenAI Apps SDK — Connect from ChatGPT / MCP connector: https://developers.openai.com/apps-sdk/deploy/connect-chatgpt
- OpenAI Secure MCP Tunnel — prywatne MCP bez publicznego ingressu: https://developers.openai.com/api/docs/guides/secure-mcp-tunnels
- OpenAI Responses API Reference — alternatywny backend modelowy przez API: https://platform.openai.com/docs/api-reference/responses
- MCP Specification 2025-06-18 — bezpieczeństwo, consent, transport, narzędzia: https://modelcontextprotocol.io/specification/2025-06-18
- GitHub protected branches / required status checks: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches
- GitHub Actions matrix jobs: https://docs.github.com/en/actions/using-jobs/using-a-matrix-for-your-jobs
- GitHub Actions Python CI: https://docs.github.com/en/actions/use-cases-and-examples/building-and-testing/building-and-testing-python
- PowerShell character encoding: https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_character_encoding
- Python `codecs` / BOM handling: https://docs.python.org/3/library/codecs.html
- Python `pathlib` file reads: https://docs.python.org/3/library/pathlib.html
