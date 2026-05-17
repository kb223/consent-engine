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

- Install: `uv sync`
- CLI: `uv run consent-engine audit <url>`
- API: `uv run uvicorn consent_engine.api:app --reload`
- MCP server: `uv run consent-engine-mcp`
- Test: `uv run pytest tests/ -v`
- Lint: `uv run ruff check src/`
- Type check: `uv run mypy src/`
- Evals: `uv run python evals/run_evals.py`

## When the user wants to audit a URL

Use the CLI directly (`uv run consent-engine audit <url>`) or call the
underlying tools. Output bundle lands in `./out/<audit_id>/` with
`report.html`, `audit_result.json`, `evidence.jsonl`, `deck.marp.md`.

## When the user wants to query a prior audit

Use `consent-engine chat <audit_id>` or, if working through MCP, the
`query_evidence` tool against the audit_id. The evidence.jsonl has every
captured network request — grounding for follow-ups.

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
