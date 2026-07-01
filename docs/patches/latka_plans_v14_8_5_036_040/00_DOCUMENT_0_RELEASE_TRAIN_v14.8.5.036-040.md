# Dokument 0 — Release Train v14.8.5.036–v14.8.5.040

## 1. Cel dokumentu

Dokument 0 jest nadrzędnym dokumentem sterującym dla serii patchy:

- `v14.8.5.036-host-visible-finalization-gate`
- `v14.8.5.037-finalization-hardening-windows-contracts`
- `v14.8.5.038-runtime-host-audit-observability`
- `v14.8.5.039-integration-cleanup-release-readiness`
- `v14.8.5.040-secure-host-runtime-bridge`

Ma być utrzymywany jako żywy dokument. Hotfixy nie są dopisywane wyłącznie na końcu. Każdy hotfix trafia do sekcji patcha, którego dotyczy, oraz do rejestru ryzyk, macierzy testów i changelogu.

## 2. Problem strategiczny

Po PR #28 i PR #29 helper `--chat-gpt` potrafi zapisać `host_visible_reply` do runtime, także przy Windows PowerShell UTF-16 input. Nadal jednak istnieje większy problem: końcowa widoczna odpowiedź hosta ChatGPT może ominąć twardą finalizację i wyjść bez timestampu. To jest naruszenie kontraktu widocznego tekstu, nie błąd samego timestampu w runtime.

Problem trzeba rozwiązać warstwowo:

1. `.036` — host finalization gate: widoczny tekst nie przechodzi bez walidacji.
2. `.037` — hartowanie platformowe i CI, szczególnie Windows/PowerShell/encoding.
3. `.038` — trwały audit i replay/idempotency.
4. `.039` — release readiness, dokumentacja, smoke i operator runbooks.
5. `.040` — bezpieczny most host-runtime: Secure MCP Tunnel / MCP, z copy-paste helperem jako fallback.

## 3. Zasady nadrzędne

| Zasada | Wymaganie |
|---|---|
| Prawda runtime przed stylem | Nie wolno udawać odpowiedzi Łatki bez potwierdzonego runtime i finalizacji. |
| Exact visible text | `final_visible_text` musi być ostatecznym tekstem widocznym lub jawnie odrzuconym. |
| Timestamp jako contract, nie ozdobnik | Brak timestampu w finalnym tekście to contract violation. |
| Traceability | Każda zmiana musi mieć PR, test, dokument patcha i wpis w Document 0. |
| Secure by default | `.040` preferuje Secure MCP Tunnel, nie publiczny ingress. |
| Fallback retained | Copy-paste/helper zostaje nawet po MCP jako tryb awaryjny. |

## 4. Release train

| Wersja | Cel | Status wejściowy | Exit criteria |
|---|---|---|---|
| `.036` | Host-visible finalization gate | helper działa, ale host może ominąć finalizację | host text bez timestampu jest repair/reject i auditowany |
| `.037` | Hartowanie platformowe | znane edge-cases Windows/PowerShell | matrix Windows/Linux zielony, BOM/CRLF testy |
| `.038` | Audit i idempotency | helper zapisuje, ale audyt jest ograniczony | każdy accept/repair/reject ma trwały audit i replay safety |
| `.039` | Release readiness | dokumentacja rozproszona | spójne docs/patches, runbooks, package smoke |
| `.040` | Secure host-runtime bridge | copy-paste/manual jako fallback | MCP/Secure Tunnel scaffold, exact content contract, security model |

## 5. Hotfix ledger — zasada wstawiania

Każdy hotfix ma być wstawiony w odpowiednim miejscu, nie tylko na końcu dokumentu.

### Szablon hotfix note

```md
### Hotfix note — v14.8.5.0XX-hotfix-name
- Dotyczy patcha:
- Trigger / objaw:
- Przyczyna:
- Zakres kodu:
- Zmienione testy:
- Czy zmienia kontrakt:
- Czy zmienia runbook:
- Co zamknięte:
- Co nie domknięte:
- PR / commit:
- Rollback:
```

### Hotfix registry

| Hotfix | Dotyczy | Status | Co zamyka | Co zostaje |
|---|---|---|---|---|
| `v14.8.5.036a-*` | `.036` | puste | puste | puste |
| `v14.8.5.037a-*` | `.037` | puste | puste | puste |
| `v14.8.5.038a-*` | `.038` | puste | puste | puste |
| `v14.8.5.039a-*` | `.039` | puste | puste | puste |
| `v14.8.5.040a-*` | `.040` | puste | puste | puste |

## 6. Ryzyka

| ID | Ryzyko | Patch | Mitigacja | Test dowodowy |
|---|---|---|---|---|
| R1 | Host wypuści tekst bez timestampu | `.036` | Gate repair/reject | `missing_timestamp -> repaired` i `foreign_timestamp -> rejected` |
| R2 | Mismatch turn/trace | `.036` | twarda walidacja | `turn_id mismatch -> reject` |
| R3 | Encoding Windows/PowerShell | `.037` | BOM-aware input + CI Windows | UTF-8, UTF-8 BOM, UTF-16LE BOM |
| R4 | Duplicate/replay finalizacji | `.038` | idempotency key | same payload idempotent, different payload conflict |
| R5 | Brak traceability release | `.039` | docs + changelog + release smoke | docs smoke, package smoke |
| R6 | Publiczne wystawienie runtime | `.040` | Secure MCP Tunnel default | auth/replay/security tests |
| R7 | Exact text ukryty w `_meta` | `.040` | `content`/`structuredContent` exact text | MCP tool result contract test |

## 7. CI baseline

Minimalne checki wymagane na `master`:

```yaml
strategy:
  matrix:
    os: [ubuntu-latest, windows-latest]
    python-version: ['3.12', '3.13', '3.14']
```

Joby:

- `compile-smoke`
- `unit-host-finalization`
- `unit-windows-encoding`
- `integration-chatgpt-helper`
- `audit-idempotency`
- `docs-smoke`
- `package-smoke`
- `security-contract` dla `.040`

## 8. Rollout SOP

1. Branch per patch: `work/v14.8.5.0XX-short-name`.
2. `git status --short --branch` przed zmianami.
3. Implementacja + targeted tests.
4. Dokument patcha w `docs/patches/`.
5. Update Document 0 w odpowiednich sekcjach.
6. PR z checklistą i wynikami testów.
7. GitHub Actions green.
8. Merge.
9. Pull master.
10. Runtime smoke: `--bridge-discovery`, `--model-adapter-status`, `--chat-gpt`, `--host-finalize`.
11. Jeśli paczka: ZIP/SHA256/manifest/reload daemon.

## 9. Rollback SOP

1. Zatrzymać daemon.
2. Wrócić do ostatniego znanego dobrego commita albo folderu runtime.
3. Jeśli merge na `master` jest wadliwy: `git revert -m 1 <merge_commit>` albo hotfix PR.
4. Wykonać smoke testy.
5. W Document 0 dodać hotfix/rollback note w sekcji patcha.

## 10. Struktura dokumentacji

```text
docs/
  architecture/
    host-runtime-bridge/
      README.md
      secure-mcp-tunnel-threat-model.md
      final-visible-text-contract.md
  patches/
    v14.8.5.036_host_visible_finalization_gate.md
    v14.8.5.037_finalization_hardening_windows_contracts.md
    v14.8.5.038_runtime_host_audit_observability.md
    v14.8.5.039_integration_cleanup_release_readiness.md
    v14.8.5.040_secure_host_runtime_bridge.md
  releases/
    v14.8.5.036-040_DOCUMENT_0.md
    CHANGELOG_v14.8.5.md
  runbooks/
    reload_package.md
    host_finalize_copy_paste.md
    secure_mcp_tunnel.md
  tests/
    ci_matrix_contract.md
```

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
