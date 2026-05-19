# Type-coverage posture — v0.5.0

> mypy strict-mode results against the v0.5.0 codebase. 2026-05-18.

## Run command

```sh
uv run mypy src/
```

`pyproject.toml` configures strict mode (`[tool.mypy] strict = true`) for the whole `src/` tree against Python 3.12.

## Summary

| Category | Count | Action |
|---|---|---|
| Resolved by mypy override (declared in `pyproject.toml`) | 5 | Add `[[tool.mypy.overrides]]` for `mcp.*` (matches existing `markdown` pattern) — landed in v0.5.0 |
| Genuine type issues fixed in v0.5.0 | 1 | `chat` subcommand removed (`cli.py:245` broken import) |
| Generic-type warnings — fix in v0.5.1 | 5 | `api.py` `dict` return type, `audit.py` `**gpc_fields` unpack, `cli.py` int cast, audit.py unused type-ignore |
| Optional-dep stubs | 0 | None outstanding |
| **Total remaining errors** | **~5** | All non-blocking; documented as v0.5.1 work |

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

## Remaining warnings (deferred to v0.5.1)

These are non-blocking — they don't affect runtime behavior or correctness, they're code-quality items:

1. **`api.py:40`** — `Missing type arguments for generic type "dict"`. Should be `dict[str, Any]`. Already partially fixed in the v0.5.0 token-gate refactor; final cleanup in v0.5.1.
2. **`audit.py` `**gpc_fields`** — unpacks a `dict[str, object]` into a Pydantic constructor. Type-correct at runtime but mypy flags the `object` values. Fix in v0.5.1 by typing `gpc_fields` as a `TypedDict`.
3. **`cli.py:332`** — `Returning Any from function declared to return "int"`. The argparse `args.func(args)` dispatch returns whatever the subcommand returns; explicitly cast to `int`.
4. **`audit.py:464`** — Unused `# type: ignore` comment from an earlier fix. Delete.

## Why mypy is non-blocking for v0.5.0

The CI pipeline in `.github/workflows/ci.yml` runs `uv run mypy src/ || true` — i.e., mypy results are advisory, not gating. The decision was deliberate for the first public release: tests + ruff are the hard gates; mypy is "fix what's easy, defer what's not, ship a working tool." Type strictness can ratchet up over v0.5.x releases.

## Reproducing this analysis

```sh
cd ~/Work/public-distribution/consent-engine
uv sync --group dev
uv run mypy src/
```

Compare output against this document. New errors should be reviewed and either fixed or added to this file with a rationale.
