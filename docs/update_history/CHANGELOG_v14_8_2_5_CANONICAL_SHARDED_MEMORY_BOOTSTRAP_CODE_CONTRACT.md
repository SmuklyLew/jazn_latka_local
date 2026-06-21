# v14.8.2.5 canonical sharded memory + bootstrap code contract

Data UTC: 2026-06-12T00:11:02.846603+00:00

- Kanoniczna baza pamięci/runtime: `memory/sqlite/chat_context.sqlite3`.
- Kanoniczna baza audytu: `memory/sqlite/chat_context_audit.sqlite3`.
- `workspace_runtime` zostaje cache/checkpoint/workspace, nie źródłem pamięci kanonicznej.
- Dodano manifesty logicznych shardów.
- Dodano `AuditContextStore` i `BootstrapContractRepository`.
- Treści bootstrap/AGENTS/README/CONTRACT są osadzone w kodzie i nie są gotowymi odpowiedziami dialogowymi.
