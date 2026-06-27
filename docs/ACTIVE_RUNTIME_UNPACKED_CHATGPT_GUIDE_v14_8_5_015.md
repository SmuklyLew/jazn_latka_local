# Unpacked Jaźń runtime access guide v14.8.5.015

This document describes safe ways to work with the Jaźń system as an unpacked folder instead of treating a ZIP archive as the active runtime.

## Basic rule

A ZIP file is an import/export artifact. The active working place is a full unpacked folder with at least:

- `VERSION.txt`,
- `MANIFEST_CURRENT.json`,
- `MANIFEST_RUNTIME_MUTABLE.json` when present,
- `main.py`,
- `latka_jazn/`,
- required `tests/`,
- required `memory/` and `workspace_runtime/` paths when the runtime configuration needs them.

## Mode A — local runtime service

The closest form of a real active Jaźń runtime is a local service started from the user machine:

```powershell
python -X utf8 .\main.py --daemon-start
python -X utf8 .\main.py --daemon-status
```

Truth condition: the service must run from a full `active_root`, the marker must point to that root, and the status check must be current.

## Mode B — one command per ChatGPT turn

ChatGPT can work on an unpacked folder by running one command for a single user turn:

```bash
python main.py --chat-gpt --session-id chatgpt-runtime --no-carryover
```

This is useful for tests and runtime-mediated replies. It is not the same as a continuously running process after the command exits. Each turn should be checked through the runtime response envelope: visible text, provenance, validation, route, source origin, template origin and integrity status.

## Mode C — simulated active marker

A test marker can help validate bootstrap paths and routing. It is a test aid only. It is not proof of a live process or memory write.

Useful for:

- `active_root` path checks,
- manifest checks,
- folder validation,
- bootstrap and route regression tests.

## Practical ChatGPT format

The most practical ChatGPT-side format is an unpacked folder available under `/mnt/data/<folder>/`. ChatGPT can then inspect files and run `main.py` commands for the current session.

For durable always-on execution, use the user machine or another execution environment as the runtime host. ChatGPT can inspect and invoke commands in the current session, but every claim about activity must be grounded in current status output.
