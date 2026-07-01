# Źródła i uzasadnienie architektoniczne

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

## Decyzje wynikające ze źródeł

1. `final_visible_text` musi trafić do kanału widocznego dla modelu/użytkownika (`content` albo `structuredContent`), a nie tylko do `_meta`, bo `_meta` jest kanałem komponentu/UI i nie powinien być traktowany jako jedyne źródło kanonicznej odpowiedzi.
2. Secure MCP Tunnel jest preferowany dla `.040`, bo pozwala utrzymać prywatny serwer MCP bez publicznego ingressu. Publiczny tunel traktujemy jako tryb development/debug.
3. Responses API jest równoległym wariantem backendu modelowego, ale nie rozwiązuje samo z siebie problemu hosta ChatGPT i finalizacji widocznego tekstu w tej konkretnej rozmowie.
4. GitHub Actions matrix + required checks są konieczne, bo błędy Windows/PowerShell encoding nie ujawniają się w samym Linux CI.
5. Windows PowerShell 5.1 i operatory `>` / `Out-File` wymagają testów UTF-16LE BOM; helper musi czytać wejścia BOM-aware.
