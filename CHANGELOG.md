# Changelog

All notable changes to consent-engine. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.8] — 2026-05-17 — revert v0.1.7 patchright swap

### Reverted
- All three scanner files (`tool_03_browser_scanner`, `cmp_detector`,
  `cmp_clicker`) are back on `playwright.async_api`. Reverted the
  `python -m patchright install chromium` change in
  `ensure_chromium_installed()`. Removed the explicit `patchright`
  dependency declaration.

### Why
The v0.1.7 swap broke 7 scanner tests. Patchright's runtime patches
interfered with `document.cookie` writes from page JS and with the
CMP detector's `page.evaluate()` calls — `detected_cmp` came back as
`None` for known OneTrust/CookieYes pages, and `test_cookie` writes
never made it into `context.cookies()`. For a forensic compliance
tool, that is a worse regression than the bot-detection gain was
worth.

### What we already have (and forgot to credit)
`tool_03_browser_scanner` ships a hand-written `_STEALTH_INIT_SCRIPT`
that is *stronger* than patchright's runtime patches:
- `navigator.webdriver` reads as `undefined` (patchright sets it to
  `false`, which still trips `'webdriver' in navigator` checks).
- Realistic `navigator.plugins` (PluginArray, 5 entries) instead of
  the headless default of 0.
- `window.chrome.runtime` injection — absence is one of the strongest
  headless tells.
- `navigator.permissions.query` returns `prompt` (not `denied`) for
  notifications.
- Realistic `navigator.hardwareConcurrency`, `navigator.languages`.

Plus `_STEALTH_LAUNCH_ARGS` with `--disable-blink-features=AutomationControlled`
and `_STEALTH_UA` set to a real Mac Chrome user-agent. And the
Scrapling/Camoufox fallback in `tool_03_browser_scanner` auto-engages
on bot-challenge detection. That cascade was already production-grade
before v0.1.7.

## [0.1.7] — 2026-05-17 — patchright tier-1 stealth + self-annealing fallback

### Changed
- Browser automation now uses `patchright.async_api` instead of
  `playwright.async_api` across all three scanner files (tool_03_browser_scanner,
  cmp_detector, cmp_clicker). Patchright is a drop-in Playwright fork that
  patches the runtime to hide common automation fingerprints — most notably
  `navigator.webdriver` reads as `false` instead of `true`, defeating the
  single most common bot-detection check. Same API surface, same Chromium
  cache (`~/Library/Caches/ms-playwright/`), no behavior change for clean sites.
- `ensure_chromium_installed()` now shells out to
  `python -m patchright install chromium`. Existing Playwright Chromium
  caches are reused automatically.

### Stealth cascade
The full self-annealing flow is now:
1. **Tier 1 — patchright** (this release). Fast, drop-in stealth.
2. **Tier 2 — Scrapling/Camoufox fallback** (already present in
   tool_03_browser_scanner). Auto-triggers when `bot_detection_encountered`
   is set on the primary scan. Firefox-based, heavier fingerprint
   randomization via apify-fingerprint-datapoints.

The cascade requires no flags. Every scan starts with patchright; if the
page returns a Cloudflare/PerimeterX/DataDome challenge, the scanner
escalates to Camoufox automatically and tags `scan_mode_used="stealthy"`
on the returned `ScanResult` so downstream callers can see which tier
resolved the page.

### Added
- `patchright>=1.48.0` declared as an explicit dependency (was previously
  pulled in only transitively via `scrapling[fetchers]`).

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
