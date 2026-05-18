# Changelog

All notable changes to consent-engine. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.6] — 2026-05-17 — render-deck subcommand + contact-page CTA

### Added
- `consent-engine render-deck <audit_id>` shells out to
  `@marp-team/marp-cli` (via `npx --yes`) to convert the per-audit
  `deck.marp.md` into a browsable `deck.html`. Requires Node.js + npx
  on PATH. Prints a clear fallback command if Node is missing.

### Changed
- Audit report CTA points to `https://kennethjbuchanan.com/contact`
  with button copy "Get in Touch" instead of a scoping-call link.
- Marp deck "Next step" line now points to the same contact page.

## [0.1.5] — 2026-05-17 — fix evidence.jsonl crash on network_requests

### Fixed
- `consent-engine audit <url>` crashed with `AttributeError: 'str' object
  has no attribute 'model_dump'` because `ScanResult.network_requests` is
  `list[str]` but the CLI, API, and MCP server all called `.model_dump()`
  on each item as if it were a Pydantic model.
- Fixed in all three call sites: `cli.py`, `api.py`, `mcp_server.py`.
  Each URL string now serializes as `{"url": "<url>"}` in evidence.jsonl.

### Verified
- Built wheel locally, installed in a clean venv, ran a real audit
  end-to-end against a live URL. Confirmed report.html, audit_result.json,
  evidence.jsonl, and deck.marp.md all write without error.

## [0.1.4] — 2026-05-18 — actually fix the data paths

### Fixed
- v0.1.3 shipped with the path-fix edits silently reverted. The wheel
  bundled the data files correctly but `tool_05_vendor_library`,
  `tool_07_rag_retriever`, and `tool_08_report_generator` still computed
  `Path(__file__).parent.parent.parent.parent / "data" / ...` which
  resolved to nonexistent locations in the installed venv.
- Caught a fifth stale path reference at `tool_08:_WIKI_ENFORCEMENT_PATH`
  that the prior fix missed.

### Verified
- Built wheel locally, extracted it, walked every Path computation from
  the installed code, and confirmed all 5 resources (vendors.json,
  open-cookie-database.csv, wiki tree, templates dir, enforcement md
  file) resolve to real files inside the wheel. Source-level grep
  confirms zero remaining `.parent.parent.parent.parent` references in
  `src/`.

## [0.1.3] — 2026-05-17 — bundle data files into the wheel

### Fixed
- `consent-engine audit <url>` crashed with `FileNotFoundError: Vendor
  library not found at <venv>/lib/python3.X/data/vendor_library/vendors.json`
  because the vendor library JSON, the markdown wiki, and the Jinja2 audit
  templates lived at the repo root and never made it into the wheel.
- Same root cause would have hit Tool 7 (wiki retrieval) and Tool 8
  (report generation) on the next audit call.

### Changed
- Relocated `data/` and `templates/` into `src/consent_engine/` so they're
  co-located with the Python package. Single source of truth.
- Updated `tool_05_vendor_library`, `tool_07_rag_retriever`, and
  `tool_08_report_generator` path computations to use the new in-package
  layout (`Path(__file__).parent.parent / "data" / ...`).
- Added explicit `[tool.hatch.build]` include rules so `.json`, `.csv`,
  `.md`, and `.j2` files get bundled in the wheel.

### Verified
- Built the wheel locally and confirmed all 6 critical resources
  (vendors.json, open-cookie-database.csv, wiki/index.md, lawsuit-surge.md,
  audit_report.html.j2, audit_deck.marp.md.j2) ship inside the wheel at
  paths that match the production code's `Path(__file__).parent.parent`
  resolution. Avoids another trial-and-error round.

## [0.1.2] — 2026-05-17 — Playwright auto-install

### Fixed
- `consent-engine audit <url>` crashed with `BrowserType.launch:
  Executable doesn't exist…` on first run because Playwright's Chromium
  binaries ship separately from the Python wheel. Now auto-downloads
  on first audit (~140 MB, one-time, user-level cache shared across
  uvx environments).

### Added
- `consent_engine.audit.ensure_chromium_installed()` — idempotent
  helper that detects whether Playwright Chromium is already cached
  and shells out to `python -m playwright install chromium` if not.
  Called at the top of `run_audit()`.

## [0.1.1] — 2026-05-17 — CLI bug fix

### Fixed
- `consent-engine audit <url>` crashed with `ImportError: cannot import
  name 'classify'` because the CLI was calling a fictional top-level
  classify() function instead of orchestrating the eight tools properly.
  Same bug in the MCP server and the FastAPI surface.

### Added
- `consent_engine.audit.run_audit(url) -> AuditBundle` — single entry point
  that owns the full pipeline (scan → per-vendor classify → sSGTM detect →
  pixel detect → jurisdiction detect → GTM parse → HAR analyze → assemble
  AuditResult → wiki retrieve → LLM exec summary → HTML report + Marp deck)
- `consent_engine.audit.run_audit_sync()` for callers outside an event loop
- `executive_summary.md` written alongside the other bundle artifacts

### Changed
- CLI, MCP server, and FastAPI surface now all call `run_audit()` instead
  of their three (broken) inlined orchestrations. Single source of truth.

## [0.1.0] — 2026-05-16 — initial public release

### Added
- Eight-tool deterministic audit pipeline:
  - tool_01 GTM container parser (live interception or JSON upload)
  - tool_02 violation classifier (S2 inconclusive vs S3 definitive)
  - tool_03 Playwright browser scanner with consent state pre-set
  - tool_04 HAR analyzer
  - tool_05 vendor library lookup (custom + Open Cookie Database)
  - tool_06 server-side GTM detector
  - tool_06b out-of-GTM pixel detector
  - tool_07 markdown wiki retriever (no vector DB)
  - tool_08 report + Marp deck generator (LLM exec summary only)
- CLI: `consent-engine audit <url>` + `consent-engine chat <audit_id>`
- MCP server: `consent-engine-mcp` (Claude Desktop / Code integration)
- Claude Code skill at `.claude/skills/consent-audit/SKILL.md`
- Evals harness skeleton at `evals/` with golden-case YAML format
- Glass-box reporting: every captured network request persisted to
  `evidence.jsonl` per audit, queryable from CLI + MCP
- Lawsuit-surge knowledge base page at
  `data/wiki/enforcement/lawsuit-surge.md`
- End-to-end scenarios doc at `docs/scenarios.md` with Mermaid diagram

### Design decisions
- Deterministic by default. LLM scoped to executive-summary generation
  only. Credit to Fred Pike (MeasureSummit May 2026) for the explicit
  framing.
- Markdown wiki replaces vector DB. Karpathy LLM-wiki pattern. Zero
  embeddings, zero Pinecone, zero fine-tuning. The whole knowledge layer
  is version-controlled markdown.
- Multi-tier vendor library: custom legally-annotated entries take
  precedence, then the Open Cookie Database (~3,200 entries), then
  flagged for manual review.
