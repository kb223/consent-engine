# Type-coverage posture — v0.5.0

> mypy strict-mode results against the v0.5.0 codebase. 2026-05-18.

## Run command

```sh
uv run mypy src/
```

`pyproject.toml` configures strict mode (`[tool.mypy] strict = true`) for the whole `src/` tree against Python 3.12.

## Summary (updated v0.5.4)

| Category | Count | Action |
|---|---|---|
| Resolved by mypy override (declared in `pyproject.toml`) | 7 | `[[tool.mypy.overrides]]` for `markdown` + `mcp.*` + per-module decorator silence for `consent_engine.mcp_server` — all landed by v0.5.4 |
| Genuine type issues fixed v0.5.0 → v0.5.4 | 6 | (1) `chat` subcommand removed [v0.5.0]; (2) `**gpc_fields` unpack refactored into explicit kwargs [v0.5.4]; (3) `cli.py` `args.func(args)` cast to int [v0.5.4]; (4) `api.py` `dict[str, Any]` annotation [v0.5.0]; (5) unused `# type: ignore` deleted [v0.5.4]; (6) mcp untyped-decorator cascade silenced [v0.5.4] |
| **Total remaining errors under `--strict`** | **0** | `uv run mypy src/` reports `Success: no issues found in 27 source files` as of v0.5.4 |

## Resolved by override

The optional `[mcp]` extra ships without type stubs (the `mcp` Python package doesn't yet publish a `py.typed` marker). 5 errors in `src/consent_engine/mcp_server.py` are stub-missing errors and decorator-cascade warnings:

- `mcp_server.py:32` — `Cannot find implementation or library stub for module named "mcp.server"`
- `mcp_server.py:33` — `Cannot find implementation or library stub for module named "mcp.server.stdio"`
- `mcp_server.py:34` — `Cannot find implementation or library stub for module named "mcp.types"`
- `mcp_server.py:45` — `Untyped decorator makes function "list_tools" untyped` (cascade from stub-missing)
- `mcp_server.py:96` — same cascade for `call_tool`

**Resolution:** Added the following block to `pyproject.toml`:

```toml
[[tool.mypy.overrides]]
module = ["mcp", "mcp.*"]
ignore_missing_imports = true
```

Same pattern as the existing `markdown` override. When the `mcp` package ships stubs, this can be removed.

## Genuine fix landed in v0.5.0

**`cli.py` `chat_with_context` import** — the `consent-engine chat` subcommand imported a function (`chat_with_context`) that does not exist in `consent_engine.llm.client`. Invocation would raise `ImportError`. Caught during the v0.5.0 audit and resolved by removing the broken subcommand entirely.

## Status as of v0.5.4 — fully clean

All four of the v0.5.0-deferred warnings closed in v0.5.4:

1. ✅ `api.py:40` — `dict[str, Any]` return annotation added.
2. ✅ `audit.py` `**gpc_fields` — refactored into explicit keyword arguments to the `AuditResult` constructor (no more `**dict[str, object]` unpack).
3. ✅ `cli.py:332` — `int(args.func(args))` cast added.
4. ✅ `audit.py` unused `# type: ignore` deleted.

Plus the per-module override for `consent_engine.mcp_server` (`disable_error_code = ["untyped-decorator"]`) silences the cascade caused by the optional `mcp` package shipping without stubs — same pattern as the existing `markdown` override.

## Why mypy was non-blocking pre-v0.5.4

The CI pipeline in `.github/workflows/ci.yml` runs `uv run mypy src/ || true` — i.e., mypy results were advisory, not gating. The decision was deliberate for the first public release: tests + ruff are the hard gates; mypy was "fix what's easy, defer what's not, ship a working tool."

**Going forward (v0.5.4+):** the codebase passes `--strict` clean. A future v0.5.x release can flip the `|| true` to a hard gate. Left advisory for now to avoid breaking external contributors whose patches might be temporarily messy.

## Reproducing this analysis

```sh
cd ~/Work/public-distribution/consent-engine
uv sync --group dev
uv run mypy src/
```

Compare output against this document. New errors should be reviewed and either fixed or added to this file with a rationale.
