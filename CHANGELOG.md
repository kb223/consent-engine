# Changelog

All notable changes to consent-engine. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.5.1] — 2026-05-18 — jurisdiction fix + release artifacts + demo URL

### Fixed
- **Jurisdiction detection on `.com` UK/global brands.** The `.com` TLD was
  short-circuiting the content-signal check, so `https://tesco.com` (Tesco
  PLC, a UK retailer) returned "US" instead of "EU." The detector now
  consults `og:locale`, `<html lang="xx-XX">` country subtags, and
  `<meta name="geo.region">` for generic-TLD sites before defaulting to US.
  Hreflang tags stay skipped in this path — they were the original reason
  for the short-circuit (shipping-list noise on US-primary .com sites) and
  are still ignored for generic TLDs.
- **CA-before-EU precedence on country subtags.** A page declaring
  `<html lang="fr-CA">` (Quebec French) was returning "EU" because the
  primary `fr` lang code matched EU before the `CA` country subtag was
  checked. CA wins now when both fire — the country subtag is more
  specific than the primary-lang heuristic.

### Added
- **`docs/release-v0.5.0/`** release-artifacts folder. The auditable record
  behind every v0.5.0 claim:
  - [`security-audit.md`](docs/release-v0.5.0/security-audit.md) — internal
    HIGH/MED/LOW punch list with closure status per item.
  - [`cve-scan.md`](docs/release-v0.5.0/cve-scan.md) — dependency CVE posture,
    Jinja2 floor-bump rationale.
  - [`type-coverage.md`](docs/release-v0.5.0/type-coverage.md) — mypy run
    output + accepted-warnings rationale.
  - [`e2e-smoke-test.md`](docs/release-v0.5.0/e2e-smoke-test.md) — full
    smoke-test command sequence + verified output.
  - [`jurisdiction-validation.md`](docs/release-v0.5.0/jurisdiction-validation.md)
    — five-site validation matrix (US / UK / CA / EU / Quebec-French) with
    the two bugs caught and fixed.
- **`docs/sample-audit/`** — a committed sample audit (against
  `https://example.com`) so cold readers can see what `report.html` +
  `deck.html` + `evidence.jsonl` look like without running the tool first.
  Linked from the README under "See a finished audit before running."

### Verified
- Jurisdiction detector — all 9 unit cases pass (US / UK / CA / EU / Quebec
  French / hreflang-shipping-list-noise / etc).
- 56-test suite green.
- Ruff clean.
- `uvx --refresh consent-engine audit https://tesco.com` now produces an
  EU/GDPR-framed report (was US/CCPA in v0.5.0).

## [0.5.0] — 2026-05-18 — FDE-portfolio public release

Cornerstone release. Internal security audit closed all HIGH + MED findings;
new SECURITY.md + CONTRIBUTING.md ship at repo root; broken `chat`
subcommand removed; defaults hardened.

### Security — HIGH findings closed
- **SSRF guard** (`audit.py::_validate_audit_url`). Every `run_audit()` call
  resolves the target hostname and rejects: non-`http(s)` schemes, known
  cloud-metadata hosts (AWS / GCP / Azure / Alibaba), and any A/AAAA record
  that resolves to a private / loopback / link-local / reserved / multicast IP.
  Override with `CONSENT_ENGINE_ALLOW_INTERNAL=1` for self-hosters auditing
  their own staging.
- **FastAPI authentication** (`api.py::_require_token`). The `POST /audit`
  endpoint now requires a bearer token via `CONSENT_ENGINE_API_TOKEN`. If the
  env var is unset, the route returns `503 Service Unavailable`. The v0.1.x
  unauthenticated default is **closed**. `uvicorn` binds `127.0.0.1` by
  default; override with `CONSENT_ENGINE_HOST=0.0.0.0` only after setting
  the token. Constant-time compare via `secrets.compare_digest`.

### Security — MED findings closed
- **Path-traversal guards** on `audit_id` inputs. New `_validate_audit_id`
  in `cli.py` and `_safe_audit_dir` in `mcp_server.py` reject non-UUID4
  audit_ids before resolving paths under `./out/`. Defense-in-depth via
  `Path.resolve().is_relative_to(...)` containment check on the MCP side.
- **Dependency hygiene**: `jinja2>=3.1.6` (was `>=3.1.0`) — closes the
  installer-floor exposure to CVE-2025-27516.

### Fixed
- **`consent-engine chat` subcommand removed.** Imported a function
  (`chat_with_context`) that doesn't exist in `consent_engine.llm.client`,
  causing an `ImportError` on invocation. Drop the broken subcommand; will
  re-add as part of a proper RAG-over-evidence build later.

### Added
- **SECURITY.md** at repo root — threat model, v0.5.0 mitigations, known
  limitations, coordinated-disclosure policy.
- **CONTRIBUTING.md** at repo root — local setup, lint + type-check, how to
  add a vendor / wiki page / CMP detection rule / eval case, PR guidelines.
- **mypy override** for `mcp.*` (`pyproject.toml`) — the optional `[mcp]`
  extra ships without type stubs, mirrors the existing `markdown` override.

### Verified
- 56-test suite green locally + in CI.
- Ruff clean on `src/` + `tests/`.
- Smoke test: `uvx --refresh consent-engine audit https://example.com` exits
  0 in <90s, all 5 output artifacts produced + auto-rendered deck.html +
  auto-open works. SSRF guard rejects `http://localhost:8080/`,
  `http://169.254.169.254/`, `file:///etc/passwd` with `ValueError`.

## [0.4.2] — 2026-05-18 — LLM disabled by default + README setup section

### Changed
- **LLM call now skipped by default.** `generate_executive_summary()` checks
  the environment for `GEMINI_API_KEY` / `ANTHROPIC_API_KEY` / `OPENAI_API_KEY`
  / `GOOGLE_APPLICATION_CREDENTIALS` and only invokes LiteLLM when one is
  present. With no key set (the OSS-default shipping state), the function
  skips the LLM entirely and uses the deterministic template summary — no
  provider-probe warnings, no Vertex/Bedrock/SageMaker tracebacks. The
  template summary is hand-tuned and reads cleanly on its own.

### Added
- **README "Optional: unlock LLM-written executive summaries" section**
  documenting the four env-var paths to enable LLM prose summaries, what
  LiteLLM is and why we use it, and how to override the default model
  targets. Users can plug in any LiteLLM-supported provider without
  changing code.

## [0.4.1] — 2026-05-18 — auto-render + auto-open + quieter CLI

### Added
- **Auto-render deck** at the end of every `consent-engine audit` run. The
  CLI now calls `@marp-team/marp-cli` directly (best-effort; if Node/npx
  isn't on PATH it silently skips and falls back to the v0.3.x manual
  rendering instructions).
- **Auto-open report + deck** in the system default browser when the audit
  finishes. macOS uses `open`, Linux uses `xdg-open`, Windows uses
  `start`, anything else falls back to Python's `webbrowser`. Opt out
  with `--no-open` if running in CI / a remote shell / a test harness.

### Changed
- **LiteLLM noise suppressed.** `LITELLM_LOG=ERROR` and
  `LITELLM_DROP_PARAMS=true` are now set in `consent_engine/__init__.py`
  before LiteLLM is imported anywhere. Stops the Bedrock / SageMaker /
  Vertex-AI startup probes from emitting tracebacks to stderr when the
  user is only configured for one of those providers.
- **Default LLM models switched to direct Gemini API.** `default_audit_model`
  and `default_classify_model` no longer point at `vertex_ai/...` (which
  requires GCP service-account credentials). Now point at
  `gemini/gemini-2.5-pro` and `gemini/gemini-2.5-flash`, which read a
  `GEMINI_API_KEY` env var. The deterministic fallback in
  `generate_executive_summary()` still handles the "no key set" case
  cleanly — the audit always completes.

## [0.4.0] — 2026-05-18 — structured evidence.jsonl (Tier-2 foundation)

The first Tier-2 release. Lays the data foundation that side-by-side,
compare-audits, multi-page, and banner-click all need. Side-by-side and
compare-audits will land in v0.4.x as separate releases — this is just
the structured-evidence plumbing.

### Added
- **New `NetworkRequest` Pydantic model** in `models/scan_result.py`.
  Captures per-request `url`, `method`, `timestamp`, `status_code`,
  `request_type` (script / image / xhr / fetch / document / etc — from
  Playwright's `resource_type`), and `initiator` (the frame URL that
  triggered the request).
- **`ScanResult.request_log: list[NetworkRequest]`** runs parallel to the
  existing `network_requests: list[str]` so existing detectors (Tool 6
  sSGTM, Tool 6b pixel detection) keep reading the flat URL list
  unchanged while the rich log is available for downstream consumers.
- **Two module-level helpers** in `tool_03_browser_scanner.py`
  (`_capture_request`, `_capture_response_status`) wire Playwright
  `page.on("request")` and `page.on("response")` to populate both lists
  atomically. Status code is filled in once the response lands. All six
  scan paths (S1, S3, S3 banner-click, GPC, JS-consent-mode, and the
  Scrapling/Camoufox stealthy fallback) now capture both shapes.
- **Evidence.jsonl writers** in `cli.py`, `api.py`, and `mcp_server.py`
  now emit one structured row per request when `request_log` is
  populated — `{timestamp, method, url, status_code, request_type,
  initiator}` — and fall back to the prior `{"url": "..."}` flat
  format only when the log is empty (so audits from old wheels still
  serialize cleanly).

### Why this matters
The flat URL log let v0.1–v0.3 power vendor detection and pixel
endpoint analysis, but it lost everything else: when each tag fired,
which page triggered it, whether it succeeded. Side-by-side opt-in vs
opt-out (v0.4.3) needs the timestamp + status to align two runs.
Compare-audits (v0.4.4) needs all of it to diff remediation progress.
This release makes that downstream work tractable.

## [0.3.4] — 2026-05-18 — fix ci.yml ruff failures from v0.3.0+

### Fixed
- 8 ruff `F541` lint errors in `tool_02_violation_classifier.py` (f-strings
  without placeholders) that were introduced when the ACM classifier copy
  was refined in v0.3.0. The release-publish workflow (`release.yml`) was
  fine — its `test` job runs pytest only — but the separate `ci.yml`
  workflow (which runs ruff on every push/PR) had been failing red since
  v0.3.0. This is a no-op runtime fix (just `f""` → `""` for strings with
  no interpolation) so all CI runs since v0.2.1 are now green.

## [0.3.3] — 2026-05-18 — dynamic enterprise recovery math + slide-6 alignment

### Changed — recovery formula now enterprise-scale by default
- **Brand-tier auto-estimation.** `_estimate_brand_tier()` scores each audit
  from observable signals (vendor count, pixel-endpoint diversity, sGTM
  presence, enterprise CMP) and maps to one of five tiers:
  Global Enterprise ($10M/mo, 7× ROAS), National Enterprise ($2M/mo, 6×),
  Mid-Large / Multi-Channel ($500K/mo, 5.5×), Mid-Market ($100K/mo, 5×),
  SMB ($20K/mo, 4×). Used as the default `monthly_ad_spend` when the
  buyer hasn't passed `--monthly-ad-spend`. Replaces the prior flat
  $50K mid-market anchor that produced peanut numbers for national
  enterprise scans.
- **Formula now returns recovered conversion value, not "ad spend not wasted."**
  New math:
  `monthly_recovered = (ad_spend × ROAS) × 35% US-opt-out-market × signal_gap × 50% recapture`
  Replaces the prior `ad_spend × 25% CA × signal_gap × 50%` which only ever
  returned a fraction of a fraction of ad spend. The new output reflects
  what's actually at stake: ad-attributable revenue lost to the leak, not
  the slice of spend wasted.
- **Recovery panel in the HTML report** now renders the tier label, the
  ROAS multiplier, the derived ad-attributable revenue, and a clearer
  formula footnote so buyers can sanity-check the math against their own
  numbers.

### Fixed — slide 6 (Financial Exposure Estimate) alignment + overflow
- Applied the `.compact` slide class (introduced in v0.3.2) so this slide
  gets the same tighter 56px padding the GPC slide uses.
- Unified both rows of cards (statutory rates + scenarios) on identical
  `flex: 1 1 0; min-width: 0` sizing + matched padding so the columns
  align and `align-items: stretch` produces equal-height cards.
- Reduced bottom-row value font (1.5em → 1.05em) and dropped
  `white-space: nowrap` so the high-traffic range
  ($42.0M–$420.0M) wraps cleanly inside its card instead of pushing the
  row past the slide bounds. Top-row font dropped 2.1em → 1.7em to
  match.

## [0.3.2] — 2026-05-18 — deck polish + session-continuity methodology note

### Fixed
- **Slide 3 "Findings at a Glance" — G100 GCS code chip legibility.**
  The chip was rendering with a leftover `#1f2937` (dark navy) inline
  background from the old dark theme, making the text unreadable on the
  new cream background. Swapped to the light-theme treatment:
  `#faf8f2` background, `#14182b` text, `#e7e3d8` border. Now matches the
  rest of the inline `<code>` styling.
- **Slide 7 "GPC Compliance" — content cut off at the bottom.** The slide
  had standard 88px bottom padding plus a verbose description paragraph
  and a wide CCPA/CPRA enforceability footer that pushed past the slide
  bounds. Added a `.compact` section class (56px padding, smaller H1/H2)
  + trimmed the verbose description ("Sec-GPC: 1 header +
  navigator.globalPrivacyControl asserted on every request" replaces the
  longer prior paragraph) + compressed the footer. Slide now fits.
- **Closing slide — duplicate "Consent Compliance Intelligence" line.**
  The `_closing_kicker` was already saying "CONSENT COMPLIANCE
  INTELLIGENCE" above the H1, and the H2 right below was repeating
  "Consent Compliance Intelligence." Replaced the kicker with
  "PREPARED BY" and the H2 with the contact URL
  (`kennethjbuchanan.com`).

### Added
- **Wiki update — session-continuity methodology note.** The
  `concepts/consent-mode-v2.md` page now distinguishes the two cookie-
  behavior questions under ACM:
  1. *Fresh-context denied — should cookies be SET?* No (per Google).
     The scanner tests this via S3.
  2. *Session-continuity withdrawal — should previously-granted cookies
     be CLEARED on revoke?* Per Google: not read by default, deleted
     only if `ads_data_redaction=true`. The scanner does NOT currently
     test this — recording the scope gap so buyers can interpret findings
     correctly.

## [0.3.1] — 2026-05-18 — ACM rule re-verified against Google official docs

### Changed
- **Wiki page `concepts/consent-mode-v2.md` re-verified** against five
  official Google sources. Added a *Source Verification* table mapping
  each load-bearing claim ("no cookies written when consent denied",
  cookieless-pings-not-cookies, `_gcl_au` behavior under denied
  `ad_storage`, `ads_data_redaction` semantics, URL passthrough as the
  cookieless alternative) to direct quotes from the corresponding
  Google docs page. Plus a *Scanner classifier implication* paragraph
  documenting why `_ga` + GCS=G100 on a fresh-context scan is the
  scanner's flagged config error and not "ACM working as designed."
- Wiki ships inside the wheel (`data/wiki/**/*.md` via hatch
  `tool.hatch.build` includes), so this update lands in the audit
  pipeline immediately — the wiki retriever (`tool_07_rag_retriever`)
  picks it up for any GCS=G100 finding.

### Sources cross-checked (all official Google domains)
- developers.google.com/tag-platform/security/concepts/consent-mode
- developers.google.com/tag-platform/security/guides/consent
- support.google.com/analytics/answer/13802165 (Consent mode reference)
- support.google.com/analytics/answer/10000067 (About consent mode)
- support.google.com/google-ads/answer/13802165 (Consent mode reference – Ads)

### Outcome
Scanner classifier in `tool_02_violation_classifier.py` is verified
correct against Google's spec. No behavior change — only documentation
strengthening so the buyer's compliance team can cite the actual
Google pages, not the project's own wiki, when discussing findings.

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
