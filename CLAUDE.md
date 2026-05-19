# consent-engine — agent instructions

> Public OSS repo. The full forensic engine. See `README.md` for the user-
> facing pitch and `docs/scenarios.md` for the system flow.

## Project purpose

Forensic audit tool that compares cookie + tag enforcement against user
consent preferences. Built for enterprises facing privacy-litigation
demand letters.

## Architecture

- **Deterministic** by design. Decisions made at build time, not runtime.
- 8 independently testable tools in `src/consent_engine/tools/`.
- LLM scoped to executive-summary generation only, behind a LiteLLM wrapper.
- Knowledge base is markdown (`data/wiki/`). No vector DB, no embeddings.
- Vendor library is JSON (`data/vendor_library/vendors.json`) + the Open
  Cookie Database CSV.

## Domain context

- OneTrust categories: C0001 (essential), C0002 (analytics), C0003
  (functional), C0004 (targeting).
- OneTrust data layer variable: `OnetrustActiveGroups`.
- S2 = post-opt-out without page reload = INCONCLUSIVE. Never definitive.
- S3 = fresh browser context with consent pre-set = DEFINITIVE.
- GCS=G100 in a network request = Advanced Consent Mode active (Basic
  blocks entirely).
- Server-side GTM cannot be blocked by client-side enforcement snippets.
- GPC (Sec-GPC: 1) signal cannot be forwarded to server-side containers.

## Commands

These commands assume the developer has the repo cloned locally and has run
`uv sync` once. They're for **in-repo work** (running tests, iterating on
code, debugging the scanner). End users who just want to run an audit go
through `uvx` from PyPI instead — see the README's install one-liner.

- Install (dev clone): `uv sync --group dev`
- CLI from source: `uv run consent-engine audit <url>`
- API from source: `uv run uvicorn consent_engine.api:app --reload`
- MCP server from source: `uv run consent-engine-mcp`
- Test: `uv run pytest tests/ -v`
- Lint: `uv run ruff check src/`
- Type check: `uv run mypy src/`
- Evals: `uv run python evals/run_evals.py`

### `uv run` vs `uvx` — the distinction

- `uv run <cmd>` — runs a command using the locked dependencies of the
  current repo. Requires `uv sync` first. Used by contributors who have
  cloned the source.
- `uvx <pkg> <cmd>` — installs `<pkg>` from PyPI into a temporary venv +
  runs `<cmd>` once. No clone needed. Used by end users who just want to
  run the tool against a URL.

Both end up invoking the same `consent-engine` entrypoint. The choice is
about where the code comes from (local clone vs PyPI), not what gets run.

## When the user wants to audit a URL

Use the CLI directly (`uv run consent-engine audit <url>` for dev, or
`uvx consent-engine audit <url>` if running cold) or call the underlying
tools. Output bundle lands in `./out/<audit_id>/` with `report.html`,
`audit_result.json`, `evidence.jsonl`, `deck.marp.md`, and (auto-rendered
when `npx` is on PATH) `deck.html`.

## When the user wants to query a prior audit

If working through MCP, use the `query_evidence` tool against the
`audit_id`. The `evidence.jsonl` file in the bundle has every captured
network request with timestamp + method + status + initiator — grounding
for follow-ups.

## When adding knowledge

Knowledge lives in `data/wiki/` as markdown. Add a new page, update
`data/wiki/index.md`, ensure `tool_07_rag_retriever.py` knows which
findings should retrieve it.

## When adding a vendor

Two paths:
- Legally-annotated, lawsuit-relevant: edit
  `data/vendor_library/vendors.json` (priority).
- Standard, well-known: edit the Open Cookie DB CSV in the same folder.

## When adding an eval case

`evals/cases/NNN-<slug>.yaml`. Run
`uv run python evals/run_evals.py --add-baseline evals/cases/NNN-<slug>.yaml`
once to populate the expected block from current behavior.

## Voice

Public-facing docs and report copy: no emojis, no em dashes, no superlatives,
no marketing-speak. Plain technical English. Audience is engineers, privacy
officers, and legal counsel.
