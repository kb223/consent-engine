# Changelog

All notable changes to consent-engine. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.3.0] — 2026-05-18 — light-theme deck, GPC always, brand-logo grab, ACM clarity

### Changed
- **Marp deck switched to a light theme.** Replaced the navy dark scheme with
  a warm-cream (`#f6f4ee`) background, near-black headlines (`#14182b`),
  KJB blue (`#3d6abb`) accents, and KJB navy (`#2b3954`) for section markers.
  Same Source Serif 4 + Inter typography. All inline marp styles updated in
  the same pass (`color:#f9fafb` → `color:#14182b`, `background:#111927` →
  `background:#ffffff`, `'Outfit'` / `'Raleway'` → `'Inter'`, dark borders →
  light borders) so embedded HTML chunks render legibly on the new bg.
- **GPC tested in every audit.** Removed the `--with-gpc` opt-in flag.
  Every `consent-engine audit` run now does the two-pass S3 + GPC scan and
  populates the GPC compliance panel. The flag is kept as a no-op for
  backward-compat with v0.2.x callers.
- **ACM classifier copy refined.** When `_ga` / `_ga_<id>` cookies are
  observed alongside GCS=G100, the finding is still `confirmed_violation`,
  but the note + remediation copy now clarify the actual mechanic: the
  cookieless-ping layer of Advanced Consent Mode IS working (GCS=G100 means
  pings carry no client identifier), but the cookie-suppression layer is
  broken — per Google's docs and the project's own
  [consent-mode-v2 wiki page](src/consent_engine/data/wiki/concepts/consent-mode-v2.md),
  denied `analytics_storage` should suppress both pings AND cookies. New
  remediation language calls out the fix path: GA4 admin → Consent Mode =
  Advanced + GTM GA4 Configuration tag's Additional Consent Settings cover
  all four storage signals.

### Added
- **Brand-logo auto-grab.** `_grab_brand_logo()` in `audit.py` fetches the
  customer's brand mark for the deck cover slide via a five-source
  cascade: (1) `<link rel="apple-touch-icon">`, (2)
  `<link rel="apple-touch-icon-precomposed">`, (3) `<link rel="icon">`
  largest-sized variant, (4) `<meta property="og:image">`, (5) Google's
  `s2/favicons?domain=X&sz=128` service as last-resort guaranteed return.
  Embedded as a `data:` URL so the rendered deck.html is fully self-
  contained (no runtime fetch needed). "Fool-proof" because Google's
  favicon service always returns something for any domain.

## [0.2.1] — 2026-05-17 — Truyo detection, deck restyle (for real), CI gate, sales flags

### Fixed
- **Truyo CMP detected.** The v0.2.0 audit on oreillyauto.com missed Truyo
  (the actual CMP) and labeled the site as having "OneTrust cookies present
  but no CMP detected." Two root causes: (1) the URL fallback in
  `cmp_detector` only matched `cmp.truyo.com` while O'Reilly's deployment
  serves from `truyoproductionuscdn.truyo.com`; (2) the in-scan detector
  ran at networkidle, before Truyo's late-loaded CDN scripts appeared in
  network_requests. Broadened the URL pattern to `.truyo.com/` and added a
  **post-scan CMP refinement** call from `run_audit()` that re-checks the
  full network_requests list after the scan completes.
- **Marp deck restyle landed where it actually lives.** v0.2.0 restyled
  `templates/audit_deck.marp.md.j2` but that file is dead — Marp markdown is
  generated **inline** in `tool_08_report_generator.generate_marp_slides()`,
  and that inline CSS still used the old `Outfit/Raleway` + `#0d1117` palette.
  Rewrote the inline `<style>` block with the KJB navy `#2b3954` +
  blue `#3d6abb` palette and Anthropic-style typography (Source Serif 4 for
  headlines + big numbers, Inter 300 for body, generous padding, restrained
  chrome). Decks now render the way v0.2.0 promised.

### Added
- **Pre-publish test gate** in `.github/workflows/release.yml`. The new
  `test` job runs `uv run pytest tests/ -q` against Python 3.12 with
  Playwright Chromium installed; the `build` job now `needs: test`. The
  v0.1.7 mistake (broken release shipped because tests weren't run) can't
  happen again without explicitly removing this gate.
- **`--firm-name "Acme LLC"`** flag whitelabels the HTML report with a
  confidentiality line at the top: "Audit prepared for Acme LLC."
- **`--variant signal|compliance`** flag picks the report framing.
  `compliance` (default) is the existing legal/risk framing. `signal`
  unlocks the recoverable-revenue math block aimed at the CMO buyer.
- **`--monthly-ad-spend N`** flag plumbs self-reported ad spend through to
  `estimate_recoverable_revenue()`. Activates per-vendor signal recovery
  dollarization (monthly + annual recoverable ranges, formula breakdown).
  Only effective when paired with `--variant signal`.

## [0.2.0] — 2026-05-17 — KJB-branded report, GPC scan, auto-remediation

### Added
- **`--with-gpc` flag** on `consent-engine audit`. Runs a second scan with
  `Sec-GPC: 1` asserted on every request + `navigator.globalPrivacyControl`
  injected, then compares pixel-firing counts against the primary S3 scan.
  Populates the GPC panel in the HTML report with a clear respected /
  ignored / inconclusive verdict, the baseline and post-GPC pixel counts,
  and a CCPA/CPRA enforceability note.
- **Auto-derived remediation steps** for every `confirmed_violation`
  finding. Vendor-specific copy for Meta, Google Analytics, Google Ads,
  Dynatrace, and Dynamic Yield; sensible fallback for the rest. Each step
  uses the buyer's GTM-container vocabulary (`ad_storage`,
  `analytics_storage`, `ads_data_redaction`, consent settings). Rendered
  in a new **Remediation Steps** section of the HTML report.
- **Auto-populated open gaps** for items that need a human eye: OneTrust
  cookies present but no JS API detected (async-load slip-through),
  GCS=G111 + requires_investigation findings (CMP overriding our
  injection), server-side GTM presence, and GPC-not-respected verdicts.
  Rendered in a new **Open Gaps** section.

### Changed (visual)
- **Marp deck restyled** to Anthropic-style typography with the locked
  KJB palette: Source Serif 4 for headlines + big numbers, Inter 300 for
  body, single-idea slides, navy `#2b3954` background, KJB blue `#3d6abb`
  accent, off-white `#e8edf5` body, generous padding. Replaces the prior
  cyan/sky scheme.
- **HTML report restyled** with the same Anthropic + KJB system in a
  light variant: warm-cream `#f6f4ee` background, navy headlines,
  KJB blue accents, Inter throughout, restrained card borders, no heavy
  shadows. The CTA block now uses the KJB navy as a dark inversion at
  the bottom of the report.

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
