# Changelog

All notable changes to consent-engine. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.6.9] — 2026-05-29 — CLI --jurisdiction accepts UK (+ list-sync guard)

v0.6.7 added the UK regime everywhere except the CLI's `--jurisdiction` choices,
so `consent-engine audit <url> --jurisdiction UK` errored with "invalid choice
(choose from US, EU, CA)". Fixed, and hardened against the whole class of bug:
the supported-jurisdiction set is now a single source of truth
(`SUPPORTED_JURISDICTIONS` in jurisdiction_detector) that the CLI `choices` derive
from, with a test asserting the CLI choices, the copy helper (`_JURISDICTION_COPY`),
and the exposure framework (`_JURISDICTION_EXPOSURE`) all stay in sync.

### Docs
- README MCP-server setup now shows the absolute-path `uvx` command for Claude
  Desktop (a macOS GUI app does not inherit the shell `PATH`, so a bare `uvx`
  cannot be found), warns to quit Desktop before editing its config, adds the
  Claude Code (`claude mcp add`) variant, and a short "not showing up?" note.

## [0.6.8] — 2026-05-29 — Dynamic jurisdiction vantage label

The deck's Jurisdiction card hardcoded "simulated: Los Angeles, CA" on every
report, which read wrong on a UK/EU/CA audit (the jurisdiction is auto-detected
from the site's own signals, not from the scan vantage). The card now shows
"auto-detected from site signals" for non-US jurisdictions and keeps the
California vantage note only for US, where it is meaningful for CCPA. The
executive-summary prompt likewise no longer lets the model describe a non-US site
as California-based; the LA browser geolocation is clarified as the scan vantage,
not the jurisdiction.

## [0.6.7] — 2026-05-29 — Distinct UK jurisdiction (UK GDPR / PECR / ICO)

The UK is now its own jurisdiction instead of folding into the EU/GDPR framework.
A .co.uk site, an en-GB site on a generic TLD (bbc.com), or a GB geolocation now
renders UK GDPR + PECR + ICO enforcement and the £17.5M / 4% turnover cap, rather
than EU GDPR + ePrivacy + CNIL + €20M.

### Added — UK regime
- Detection: `_UK_TLDS` (.uk / .co.uk / .gov.uk / ...) and `_uk_signals()` (GB in
  html-lang / og:locale / geo.region) route UK sites to "UK" in
  `detect_jurisdiction`, ahead of the EU branch. GB is removed from the EU country
  set, and `country_to_jurisdiction("GB")` now returns "UK".
- Exposure: a UK entry in `_JURISDICTION_EXPOSURE` (turnover_cap; UK GDPR Art 83
  £17.5M / £8.7M, PECR reg 6, ICO). No flagship UK cookie fine exists, so it cites
  no anchor (the same honesty guardrail as Canada) and notes that ICO cookie
  enforcement to date is mostly reprimands and enforcement notices.
- Report + deck: UK branches in the applicable-law slide, the statute kicker, the
  exec-summary law label, the pixel-exposure callout, and the jurisdiction label;
  `jurisdiction_copy("UK")` supplies UK GDPR / PECR / ICO phrasing. UK shares the
  EU GDPR opt-in framing for the GPC note (UK GDPR mirrors it).

## [0.6.6] — 2026-05-29 — Jurisdiction-aware report/deck prose

Non-US reports no longer carry US (CCPA/CIPA/plaintiff/"Do Not Sell") framing;
findings render in the audited site's own regime. Validated on an EU site
(bbc.com): the deck is fully GDPR-framed with zero CCPA/CIPA/plaintiff strings,
and the report pulls GDPR wiki rather than CCPA/CIPA.

### Fixed — jurisdiction-aware regulatory context
- **RAG wiki retrieval is jurisdiction-gated.** The finding→page map pulled
  ccpa.md / cipa-vppa.md / us-class-actions.md for every scan with violations, so
  EU/CA reports got US enforcement content alongside their own. Those US pages now
  load only for a US jurisdiction; EU/UK sites get GDPR pages, CA sites get Quebec
  Law 25 / PIPEDA.
- **Single source of regime phrasing.** New `jurisdiction_copy()` centralises the
  GPC legal status, statute name, regulator, manual-repro vantage, and
  pixel-evidence framing per regime (US / EU / UK / CA). Wired through the report
  (GPC note, pixel-evidence section, manual-validation steps + vantage), the deck
  (GPC footer, audit-methodology bullet, pixel-exhibit subtitle), the
  executive-summary builder, and the open-gaps action items.
- **GPC is framed correctly per regime.** "Under CCPA/CPRA, GPC is a legally
  binding opt-out signal" now renders only for US sites. EU/UK/CA sites state that
  consent is opt-in and GPC is not itself binding, while continued tracking still
  shows the banner is not enforcing the user's choice.
- The LLM executive-summary prompt no longer instructs the model to cite CCPA or
  treat GPC as a CCPA mandate for non-US sites.

## [0.6.5] — 2026-05-29 — Scanner-independent jurisdiction + copy fixes

Jurisdiction is now derived only from signals the audited SITE declares, never
from where the scan runs from. A scan executed from a Canadian IP was stamping
Quebec Law 25 / PIPEDA onto US and UK sites (CNN, BBC). Fixed completely and
locked with regression tests. Live-verified: CNN -> US, BBC -> EU, NYTimes -> US.

### Fixed — jurisdiction is scanner-independent
- **Dropped the CMP IP-geolocation override.** `run_audit` no longer maps
  `cmp_runtime_config.geolocation_country` onto the report jurisdiction. That
  value reflects the SCANNER's location (the visitor the CMP geo-targets), not
  the site's market, so every CMP-geolocated site scanned from Canada reported
  Canadian law. Jurisdiction now flows through the new pure
  `resolve_jurisdiction(explicit_override, page_html, url)`, which takes no CMP
  geo by construction. CMP geolocation is still captured as evidence.
- **Hardened the Canadian-content heuristic (the France-vs-Quebec tiebreaker).**
  It no longer matches bare English city names or a bare "Canada"/"Canadian"
  mention (editorial content on a global news site, not the site's own
  jurisdiction). The Canadian postal-code pattern was removed entirely: under
  `IGNORECASE` its A1A-1A1 shape matched hex fragments in CSS/asset hashes
  (160+ false hits on a single bbc.com page). The tiebreaker is now also gated
  on a French-language signal, since it exists only to separate French-Quebec
  from French-France, so an English (en-GB / en-US) page is never subject to it.
  Kept signals: Québec/Montréal/Hydro-Québec, Loi 25 / Law 25, PIPEDA,
  Commission d'accès.

### Fixed — client-copy polish
- The executive summary no longer leaks the raw methodology enum (e.g. "under
  the s3_no_google_consent_mode methodology") — it uses the human label, and the
  no-GCS case now gets an accurate summary instead of a false "AI-ready" line.

## [0.6.4] — 2026-05-28 — Sourcepoint reject-click reliability + no-GCS methodology

Fixed the banner-click reject path for Sourcepoint (and, via the shared
banner-detection fix, every CMP), and added an honest methodology for sites that
emit no Google Consent Mode signal at all. Live-verified on theguardian.com,
bbc.com, cnn.com. All tests pass, ruff + mypy strict clean.

### Fixed — Sourcepoint reject-click (4 compounding bugs)
- **`_banner_present` false-positive (the blocker).** It matched any
  `[class*='banner']` element — including a site's subscription / promo banner
  (e.g. the Guardian's `rr_banner_highlight`) — so a *successful* reject (consent
  iframe already gone) was still reported as `banner_click_failed`, leaving
  Sourcepoint sites stuck at INCONCLUSIVE. Banner detection is now
  consent-specific: explicit CMP containers (OneTrust, Sourcepoint message
  iframe, Cookiebot, CookieYes, Usercentrics, Didomi, TrustArc, Quantcast,
  consentmanager, CookieScript) + `cookie`/`consent` keyword selectors; the bare
  `[class*='banner']` is gone. This is an accuracy win across **all** CMPs.
- **Message iframe never entered.** The clicker only entered frames matching
  `"truste"`, gated on `dom_type == "iframe"`. Sourcepoint reports
  `dom_type == "standard"` yet renders its reject button inside an
  `sp_message_iframe` (often a first-party CNAME). New `_select_cmp_frame()`
  enters any recognised CMP message iframe regardless of `dom_type`.
- **Wrong JS API.** `window._sp_.rejectAll()` does not exist on modern builds.
  Now calls the real namespaced methods (`_sp_.usnat.postRejectAll()`,
  `_sp_.ccpa.rejectAll()`); GDPR has no direct reject API, so it falls through to
  the in-iframe click (`button.sp_choice_type_13`).
- **Vocabulary gap.** Added "no, thank you", "do not consent", and "continue
  without accepting" to the reject vocabulary (Sourcepoint labels reject-all
  "No, thank you").

### Added — no-Google-Consent-Mode methodology
- New `MethodologyFlag.S3_NO_GOOGLE_CONSENT_MODE`. When a known CMP is detected
  and the reject is applied but the site emits **zero** `gcs=` signals across the
  whole scan, the GCS-based audit is not applicable — the site either does not
  use Consent Mode (common on IAB-TCF publishers) or uses Basic Consent Mode
  (which suppresses tags on opt-out). This replaces two inaccurate labels for
  such sites: the misleading `s3_consent_wiring_broken` (claims a GCS integration
  that never existed — verified on cnn.com) and `s3_inconclusive_unknown_cmp`
  (false when the CMP is recognised and the reject worked — verified on
  theguardian.com). NON-definitive: no confirmed violations, no statutory
  exposure, and the report + deck render a neutral verdict ("Google Consent Mode
  Not Detected") instead of a false green "no violations / AI-ready" pass.
- Methodology classification extracted to the pure, unit-tested
  `classify_s3_methodology()`.

## [0.6.3] — 2026-05-28 — Full scan in production + jurisdiction-aware exposure

Repositioned from an outreach lead-magnet (fast scan) to a give-away / portfolio
tool: the FULL scan is now the production path, and financial-exposure reporting
is correct per jurisdiction. 113 tests pass (9 new), ruff + mypy strict clean.

### Changed — the full scan is now production
- `run_audit` now calls `scan_page` (`_scan_s3`) for both the opt-out and GPC
  passes, instead of `scan_page_fast`. This brings per-CMP injection
  (`build_injection_plan`) + banner-click reject + a 150s per-pass timeout. The
  fast path only injected OneTrust's cookies, so every non-OneTrust CMP came back
  INCONCLUSIVE; the full scan actually injects against Didomi/Usercentrics/
  Sourcepoint/etc. (and the 150s wrapper fixed the fast path's hang on slow sites).
- Ported the fast path's newer wiring into the full scan: CMP runtime
  introspection + consent-event capture (into `_scan_s3`), and the Camoufox
  stealthy WAF retry (into the `scan_page` wrapper).

### Fixed — accuracy
- **Geo-override no longer fabricates a "denied" GCS off an injected cookie.**
  The full-scan override fired on any `cmp_method`, including `cookie_injection`
  (the denial cookie WE pre-inject) — circular, and a false-CONFIRMED source.
  Now gated to `banner_click` only (a genuine reject that wrote the cookie), the
  same bug class fixed in the fast path for v0.6.2.
- **Jurisdiction detection prefers the CMP's own geolocation as ground truth**
  (`country_to_jurisdiction`) over the HTML/TLD heuristic — the CMP itself
  determined which regime applies. Returns a positive non-US signal only, so a
  US-IP scan can't mask a real EU/CA site.

### Fixed — jurisdiction-aware financial exposure (deck + report)
- A Canadian or EU site no longer shows US statutes (CCPA/CPRA, CIPA §631) or US
  settlement precedents (Sephora/Disney). The exposure now branches by regime,
  using the correct *structure* for each: the US is a per-consumer multiplier
  (penalty × opt-out volume); the EU/UK/Quebec are turnover-percentage caps (a
  single ceiling, no per-consumer multiplier).
  - **US**: CCPA $7,500 / CIPA $5,000 / FTC, per-consumer volume tiers, US settlements.
  - **Canada**: Quebec Law 25 (CAD $25M/4% penal · CAD $10M/2% admin · CAD $1,000
    private floor), PIPEDA, with an honesty note (enforcement nascent, no flagship
    cookie fine yet, Tim Hortons as the real precedent).
  - **EU**: GDPR Art. 83 (€20M/4%), ePrivacy/CNIL Art. 82, anchored to real cookie
    fines (Google €325M, SHEIN €150M — Sep 2025; Amazon €35M). UK-GDPR/PECR noted.
  - Figures verified against primary regulator sources. The "Applicable Legal
    Framework" slide, the per-pixel exposure callout, and the statute kicker are
    jurisdiction-branched too.

### Fixed — deck
- **CMP self-report slide** redesigned from a generic theme table to an on-brand
  spec grid (navy accent rail, brand-blue kicker labels). Site-derived values on
  that slide are now `html.escape()`d (the deck f-strings have no autoescape).

## [0.6.2] — 2026-05-28 — Second-review hardening (P0/P1/P2 fixes)

A deeper multi-agent review of the full pipeline (not just the diff) before the
public launch. Found that the false-positive problem ran deeper than v0.6.1
closed, plus two genuinely exploitable security holes. Five P0s, nine P1s, eight
P2s. All fixed; 104 tests pass (22 new), ruff + mypy strict clean.

### Fixed — P0 (launch-blocking)
- **Stored XSS in the HTML report.** The Jinja env used
  `autoescape=select_autoescape(["html"])`, but the template is
  `audit_report.html.j2` — `select_autoescape` keys off the final extension, so
  `.j2` left autoescape OFF and every `{{ }}` emitted raw HTML. The
  attacker-controlled audited URL (and cookie names) were reflected unescaped
  into a report the CLI auto-opens in the operator's browser. Now
  `autoescape=True` unconditionally; site-derived values flowing into the two
  `| safe` action-item sinks are `html.escape()`d at construction in
  `audit.py::_derive_action_items`. (`SECURITY.md` corrected — it had wrongly
  certified this surface as escaped.)
- **SSRF metadata exfiltration via brand-logo fetch.** `audit.py::_grab_brand_logo`
  pulled `og:image`/favicon hrefs from the audited page and fetched them with
  `httpx(follow_redirects=True)` and no SSRF guard — outside the Playwright route
  guard. An attacker page with `og:image=http://169.254.169.254/...` got cloud
  metadata fetched and base64-embedded into the deck. Now each candidate is
  `validate_audit_url`-checked, `follow_redirects=False`, response size capped.
- **Fabricated "denied" GCS on compliant sites.** The fast-path geo-override
  fired off the scanner's own always-injected `OptanonConsent` cookie (flat-set
  `any(...)` was unconditionally true), rewriting every `G111` (granted) site to
  `G100` (denied). Now CMP-gated and excludes the injected OneTrust cookie.
- **Confirmed-violation verdict / statutory exposure under INCONCLUSIVE.** The
  verdict band, `$1.2M–$18.5M` exposure, executive summary, and deck keyed off
  `status == CONFIRMED` with no methodology check, so a compliant site on an
  un-injectable CMP (Didomi, Usercentrics, Sourcepoint, Ketch…) got a red
  "Consent Violation Detected" verdict. New centralized `_confirmed_violations()`
  gate + zero-exposure short-circuit; report gains a neutral "Consent Enforcement
  Not Verified" verdict state for inconclusive scans.
- **`S3_CONSENT_WIRING_BROKEN` claimed for CMPs never injected against.** The fast
  path only injects OneTrust's cookies but labeled ~12 CMPs "legally defensible."
  Now `classify_fast_methodology()` restricts that verdict to OneTrust; all others
  are `INCONCLUSIVE_UNKNOWN_CMP`.

### Fixed — P1
- **Truyo (and CookiePro) mislabeled as OneTrust.** CMP detection short-circuited
  on the first matching JS global (OneTrust is rule 0) / URL pattern, and
  OneTrust-based products also expose `window.OneTrust` + `cdn.cookielaw.org`.
  Detection now collects all matches and demotes the generic base-layer globals
  (`OneTrust`, `IAB TCF`) when a more specific CMP co-matches.
- **SSRF octal/hex/dotless IP bypass.** `0177.0.0.1` (= 127.0.0.1) slipped past
  the guard (ipaddress rejects octal; DNS didn't canonicalize) but Chromium
  connects to loopback. New `_canonical_ipv4()` mirrors the browser/`inet_aton`
  parser before classifying.
- **SSRF via the ssGTM detector's httpx fetch** (`follow_redirects=True`, no
  guard) — now validated + no-redirect.
- **Vendor false attribution from generic short cookie names** (`C`, `uid`, `sp`,
  `tp`, `dpm`, `fr`…). Tier-1 ignored the cookie domain; Tier-2 let blank-domain
  OCD rows through. Generic names now require a positive domain match.
- **`consent-engine chat` documented but not implemented** — removed the claim
  and the dead `[chat]` extra.

### Fixed — P2
- Jinja prompt-injection surface: the audited URL is sanitized (query/fragment
  stripped, truncated) before interpolation into the LLM executive-summary prompt.
- Playwright contexts set `accept_downloads=False`.
- OneTrust `testLog()` capture polls (was a fixed 0.3s race) and returns `None`
  rather than a half-populated config on a miss.
- Wheel no longer ships package data twice (removed the stray `shared-data`
  table, ~567 KB); Docker build pins `uv.lock --frozen`; MCP output dir honors
  `CONSENT_ENGINE_OUT_DIR` instead of CWD-relative `./out`; `tldextract` uses the
  bundled public-suffix snapshot (no first-run network fetch).

### Known limitation
- DNS-rebinding TOCTOU (guard resolves a public IP, Chromium re-resolves to a
  private one) is not fully closed; it needs socket-level IP pinning. The
  multi-IP answer set is still blocked if any address is private. Tracked for a
  follow-up.

## [0.6.1] — 2026-05-26 — Peer-review hardening (P0/P1/P2 fixes)

Addresses an external code review (Codex 5.5) before the public LinkedIn
launch. Two P0 accuracy bugs, three P1 correctness/security gaps, and CI
hardening.

### Fixed — P0 (accuracy, launch-blocking)
- **Clean sites no longer falsely report OneTrust.** The scanner injects
  `OptanonConsent` + `OptanonAlertBoxClosed` as opt-out state before
  navigation; the v0.5.6 cookie-name backstop, the v0.6.0 legacy-cookie
  filter, AND the open-gap heuristic all read those injected cookies back
  as proof of OneTrust — so every clean site (example.com included)
  reported `detected_cmp: OneTrust`. Now the injected cookies are excluded
  from all three paths via the shared `INJECTED_CONSENT_COOKIES` set. Real
  OneTrust is still caught by the `window.OneTrust` JS global +
  `cdn.cookielaw.org` URL. Verified: example.com → `null`, skims.com →
  OneTrust (high).
- **Fast scan no longer mislabels indicative results as definitive.**
  `scan_page_fast` (the default CLI/API/MCP path) hard-coded
  `methodology=S3`. It now uses the same 3-way classification as the full
  `_scan_s3`: denied-GCS → definitive; known CMP + injection plan →
  consent-wiring-broken; unknown CMP / no plan → `INCONCLUSIVE_UNKNOWN_CMP`.
  example.com now reports inconclusive instead of definitive.

### Fixed — P1
- **SSRF guard now covers redirects + subresources.** Previously only the
  initial URL host was validated, so a public URL could redirect to
  `169.254.169.254` or pull a subresource from an internal host through
  Chromium. New `consent_engine/security.py` (shared `validate_audit_url`
  + `is_blocked_host`); the scanner installs a Playwright route guard on
  every request + redirect that aborts private / loopback / link-local /
  reserved / multicast / metadata IPs. Honors `CONSENT_ENGINE_ALLOW_INTERNAL=1`.
- **Dockerfile build fixed.** Removed `COPY data/` + `COPY templates/`
  (those live under `src/consent_engine/`, already pulled by `COPY src/`;
  the standalone COPYs failed the build). README FastAPI section now
  documents the required `CONSENT_ENGINE_API_TOKEN` + a working curl example.
- **Eval runner fixed for Python 3.14.** `asyncio.run(asyncio.gather(...))`
  crashed (gather built outside the loop); wrapped in a coroutine. Stale
  status names (`violation_definitive` / `violation_pre_consent`) → current
  `confirmed_violation`. Added explicit handling for `jurisdiction`,
  `cmp_confidence_at_least`, `confirmed_violations_count_at_least` (were
  silently ignored). Lowercased `consent_state` baselines in all 8 cases.

### Changed — P2/P3
- **CI hard-gates mypy** (was `|| true`), adds `uv build`, a no-network CLI
  smoke (`consent-engine version`), and a Docker build job.
- **Report footer** "Generated by Consent Compliance Agent" → "Generated by
  consent-engine" (consistent with the engine-not-agent positioning).
- **`ensure_chromium_installed`** now checks the correct per-OS Playwright
  cache path (was macOS-only, so Linux/server re-ran `playwright install`
  on every audit). Honors `PLAYWRIGHT_BROWSERS_PATH`.
- **Regenerated `docs/sample-audit`** on v0.6.1 (was stale v0.5.1) — now
  correctly shows `detected_cmp: null` + inconclusive methodology for the
  no-CMP example.com baseline.

## [0.6.0] — 2026-05-26 — Accuracy sprint: false-positive cleanup, 6 CMP introspectors, +18 enterprise vendors

A precision pass. Triggered by an audit of `oreillyauto.com` (Truyo) that
showed OneTrust, J2EE session cookies, and Akamai bot-management cookies
as "vendor findings" — false positives that diluted the signal in the
report. v0.6.0 fixes those and expands the per-CMP runtime introspection
coverage from 1 CMP to 6.

### Fixed
- **False positives in vendor findings table.** Three categories of cookies
  that should never appear as third-party vendor findings are now filtered
  out at the classification stage:
  1. CMP-own state cookies from a CMP **other than** the detected one
     (OptanonConsent on a Truyo site, didomi_token on a Cookiebot site, etc.)
     now surface as **Open Gaps** with migration-cleanup guidance.
  2. Application server session cookies (JSESSIONID, PHPSESSID,
     ASP.NET_SessionId, Express sid, Laravel session, Django session, etc.)
     skipped entirely — they're infrastructure, not trackers.
  3. CDN bot-management + load-balancing cookies (Akamai bm_*, AKA_A2,
     _abck, AWSALB, Imperva incap_ses_, etc.) skipped entirely — same.
  Smoke on oreillyauto.com: vendor findings dropped from 9 → 5, with all
  5 being real tracking violations (Dynatrace, Meta, Google Analytics,
  Google, FullStory). The 4 false-positive entries gone; legacy OneTrust
  cookies correctly surfaced as "Open Gap".

### Added
- **5 more CMP runtime introspectors** in `cmp_runtime_introspect.py`:
  `extract_cookiebot_runtime`, `extract_cookieyes_runtime`,
  `extract_didomi_runtime`, `extract_usercentrics_runtime`,
  `extract_truyo_runtime`. New `extract_cmp_runtime(page, cmp_name)`
  dispatcher routes to the right extractor based on the scan's detected
  CMP. Pattern is consistent: each extractor calls the CMP's own JS API,
  pulls template_name + geolocation_rule + consent_model + expected
  cookies + vendor IDs, validates into the `CMPRuntimeConfig` model.
- **10 new CMP detection rules** (JS globals + URL patterns + meta):
  CookieFirst, TermsFeed, WireWheel (Concord successor), Termageddon,
  PrivacyConsent, Cassie (UK enterprise), CookiePro (legacy OneTrust
  brand), Tealium AudienceStream Consent Manager, InMobi (Quantcast
  Choice successor), Sirdata. Plus Piano, Fathom, Plausible as
  cookieless-analytics URL patterns.
- **9 new consent-event recognizers** in the dataLayer extractor: Truyo,
  Ketch, Shopify privacy, Tealium, Sourcepoint, TrustArc, CookieFirst,
  Klaro, iubenda native event patterns.
- **18 new enterprise vendor entries** in `vendors.json` — high-impact
  vendors most often missed in CCPA/CIPA audits. Each has full
  legal-exposure + OneTrust-category annotations:
  - Adobe Marketing Cloud trio: Analytics, Target, Audience Manager
  - Session replay: Hotjar, Microsoft Clarity (both flagged as CIPA
    §631 wiretap surfaces with class-action precedent)
  - Product analytics: Mixpanel, Heap, Amplitude
  - Customer data platform: Segment (flagged as aggregator of
    downstream destination risk)
  - Marketing automation: HubSpot, Marketo (Adobe), Pardot (Salesforce),
    Klaviyo (Shopify-heavy)
  - Conversational: Drift, Intercom (both with CIPA chat-recording
    exposure), Zendesk
  - Identity resolution: LiveRamp, LiveIntent (both flagged as direct
    CCPA sale due to cross-site identifier joining)

### Stats
- vendors.json: 82 → 100 entries (+18, all with legal annotations)
- CMP detection rules: ~40 → ~50 (+10)
- CMP runtime introspectors: 1 → 6
- Consent event recognizers: 9 → 18 categories
- 70 tests still pass + 1 skipped, ruff + mypy strict-clean

## [0.5.7] — 2026-05-25 — CMP runtime introspection + consent-event stream capture

First introspection release. Reads what the CMP itself reports via its
JavaScript API, captures the consent-only dataLayer pushes, and surfaces
both in the report + deck. Turns the audit from "we observed X" into
"the CMP **said** it was doing X, here is what actually happened" —
which is the framing that holds up under cross-examination.

### Added
- **`tools/cmp_runtime_introspect.py`** — new module with two extractors:
  - `extract_onetrust_runtime(page)` calls `OneTrust.testLog()` via a
    Playwright console listener (catches everything testLog logs verbatim,
    survives SDK-version wording changes), then parses out `template_name`
    (e.g. `Loi-25v1.1`), `geolocation_rule` (e.g. `Global Audience (loi 25-GDPR)`),
    `geolocation_country`, `consent_model` (opt-in / opt-out / implicit),
    `script_version`. Also pulls structured data from `OneTrust.GetDomainData()`
    for `expected_cookies_by_category` (4 OneTrust categories, all declared
    cookies) and `expected_vendor_ids`. Five-second timeout, fails closed.
  - `extract_consent_events(page)` snapshots `window.dataLayer` and filters
    to consent-only pushes: `gtag('consent', 'default', ...)`,
    `gtag('consent', 'update', ...)`, `OneTrustGroupsUpdated`,
    `OneTrustLoaded`, Cookiebot / CookieYes / Didomi / Usercentrics native
    events, `__tcfapi` callbacks, and any custom event whose name contains
    "consent". Preserves firing order via `index_in_stream` for race-condition
    forensics.
- **New Pydantic models** `CMPRuntimeConfig` and `ConsentEvent` on
  `AuditResult.cmp_runtime_config` + `AuditResult.consent_events`.
  Plumbed through `ScanResult` → `AuditResult` → `audit_result.json`.
- **Report:** new "CMP Runtime Configuration" section showing template,
  geo rule, geo country, consent model, script version, and the
  expected-cookies-by-category map. New "Consent Event Stream" section
  showing the ordered consent pushes with their params. New "CMP Template"
  signal card in the top dashboard.
- **Deck:** new "CMP Self-Report · Ground Truth" slide rendering the
  same template / geo / consent-model table.
- **RAG retriever:** when `cmp_runtime_config.template_name` or
  `geolocation_rule` contains "GDPR" and jurisdiction is CA, also pulls
  `regulations/gdpr.md` so reports for Law 25 + GDPR hybrid templates
  (the Hydro-Québec pattern) cite both frameworks. Surfaced as 21+ Quebec
  / PIPEDA / Law 25 / GDPR cross-references in a representative report.
- **Vendor library + 5:** Qualtrics SiteIntercept, YouTube embed cookies
  (VISITOR_INFO1_LIVE, VISITOR_PRIVACY_METADATA, YSC, __Secure-3PSIDCC, …),
  Facebook page-set cookies (ps_n, nextId, TESTCOOKIESENABLED), generic
  Google cookies (NID, CONSENT, 1P_JAR), and Cloudflare bot-mgmt (`__cf_bm`,
  classified essential C0001 to avoid false-positive). All with full
  CCPA / GDPR / CIPA risk annotations.

### Smoke-tested on
- `hydroquebec.com` (CA, OneTrust, Law 25-GDPR template) — full runtime
  config extracted, 3 consent events captured (`gtag_consent_update`,
  `OneTrustLoaded`, `OneTrustGroupsUpdated`), report cites Quebec Law 25
  + PIPEDA + GDPR.

### Coverage roadmap (deferred)
- v0.5.8: Cookiebot + CookieYes runtime introspection
- v0.5.9: Didomi + Usercentrics + TrustArc
- v0.6.0: Sourcepoint + CookieInformation + Klaro

## [0.5.6] — 2026-05-25 — CMP detection robustness + `--jurisdiction` override

Same-day patch addressing two findings from a live audit of `hydroquebec.com`.

### Fixed
- **OneTrust missed on slow-loading sites** — CMP detection was flaky when
  OneTrust loaded via deferred GTM injection (the SDK fired its first
  cookielaw.org request well after the primary scan's `networkidle` window
  closed). The post-scan refinement pass only saw the primary scan's URL
  list, so the late-arriving cookielaw URLs in the GPC scan were ignored.
  Three new backstops:
  1. Post-scan URL pattern check now pools URLs from **both** primary and
     GPC scans before running `detect_cmp_from_network_only`.
  2. New cookie-name backstop maps well-known CMP state cookies to their
     vendor (OptanonConsent → OneTrust, CookieConsent → Cookiebot,
     cookieyes-consent → CookieYes, didomi_token → Didomi, etc.) so
     cookie evidence outlasts JS/network evidence.
  3. Cookie-name backstop runs against pooled cookies from both scans.

### Added
- **`--jurisdiction US|EU|CA`** CLI flag to force jurisdiction when
  auto-detection is wrong. Maps through to `run_audit(jurisdiction=...)`
  which already existed but wasn't exposed.

### Removed
- **Dead template `audit_deck.marp.md.j2`** — superseded by Python-generated
  deck in `tool_08_report_generator.py` since v0.5.0 light-theme refactor.
  Still referenced "Founder, KJB" voice violation. Zero remaining
  references in source, tests, or docs.

## [0.5.5] — 2026-05-25 — Canadian jurisdiction, public-launch polish

First post-launch polish pass. Drops internal-jargon ("S3" methodology
prefix) from user-facing report and deck labels, fixes the Quebec-on-`.com`
jurisdiction case, fills in Canadian regulatory coverage, and corrects the
MCP install command in README + error message.

### Fixed
- **MCP install** — `uvx consent-engine-mcp` does not install the optional
  `[mcp]` extra; the command silently failed with the wrong error. README
  and the `SystemExit` message now both show the correct form:
  `uvx --from 'consent-engine[mcp]' consent-engine-mcp`. The Claude Desktop
  config snippet in the README was updated to match.
- **Quebec jurisdiction on `.com`** — `hydroquebec.com` (and any other
  Quebec organization with a `.com` and `lang="fr"` but no `-CA` country
  subtag) was returning `EU` because the lang signal alone is indistinguishable
  from a France site. New `_canadian_content_signal` heuristic checks for
  Quebec/Canadian markers (Québec, Montréal, Loi 25, Canadian postal codes,
  named Canadian cities) and promotes the verdict to `CA` when found.
  Conservative: only consulted when the lang signal would otherwise lock in
  `EU` — no false positives on actual French sites.

### Changed
- **Methodology labels** — `"S3 — Definitive (Privacy Logic Enforcement Test)"`
  → `"Definitive (Privacy Logic Enforcement)"`. The "S3" prefix and "Test"
  word were holdovers from the original S1/S2/S3 scenario nomenclature that
  no longer adds information in the public report (only opt-out + GPC are
  actually run). Internal `MethodologyFlag.S3` identifier preserved for
  backward compatibility in `audit_result.json`.
- **Final deck slide** — `kennethjbuchanan.com` demoted from H2 display
  block to an inline hyperlink under the "Prepared by" name. Less
  self-promotional; matches the HTML report's already-subtle branding.

### Added
- **`wiki/regulations/pipeda.md`** — Federal Canadian Personal Information
  Protection and Electronic Documents Act. Opt-in consent model, OPC
  enforcement, BC and Alberta provincial PIPA references, and the
  CPPA-died-with-prorogation context. Cross-linked from the wiki index
  and the RAG retriever (`quebec` and new `canada_federal` key both pull
  Quebec Law 25 + PIPEDA together).
- **`wiki/enforcement/us-enforcement.md` additions** — Tilting Point Media
  CPPA $500K (July 2025, children's privacy + GPC), Honda CPPA $632.5K
  (March 2024, opt-out friction + verification gates), DoorDash CA AG
  $375K (Feb 2024, non-monetary "sale" via mailing-list exchange), Todd
  Snyder CPPA $345K (May 2024, opt-out form friction + cookie persistence
  failure). New "CPPA 2024–2026 Enforcement Pattern" section synthesizes
  the five recurring violation types every audit should map to.

### Internal
- Version bumped to 0.5.5 in `pyproject.toml` and `__init__.py`.

## [0.5.4] — 2026-05-19 — mypy strict-clean, 4 new eval cases, more CMP URLs

Continued pre-launch polish toward the Thursday LinkedIn announcement.
Tightening pass across types, regression coverage, and CMP detection
breadth.

### Fixed — mypy strict-mode now fully clean

`uv run mypy src/` reports `Success: no issues found in 27 source files`.
Closes the four v0.5.0-deferred warnings + the mcp decorator cascade:

- `audit.py::run_audit` — refactored the `**gpc_fields` dict-unpack into
  explicit keyword arguments to `AuditResult(...)`. Each gpc field is now
  typed at construction site. No runtime behavior change.
- `cli.py::main` — `args.func(args)` dispatch result cast to `int`.
- `api.py::audit` — `dict[str, Any]` return annotation (was bare `dict`).
- Removed unused `# type: ignore[arg-type]` after the marp generator's
  `report_variant` signature was widened to `str`.
- `pyproject.toml` — new per-module override for
  `consent_engine.mcp_server` (`disable_error_code = ["untyped-decorator"]`)
  silences the cascade from `mcp` shipping without stubs. Same pattern as
  the existing `markdown` override.

[docs/release-v0.5.0/type-coverage.md](docs/release-v0.5.0/type-coverage.md)
updated to reflect the clean state.

### Added — 4 new eval cases (4 → 8 total)

`evals/cases/`:
- **005-truyo-cmp-detection.yaml** — Truyo's late-loaded CDN catches the
  post-scan URL refinement path (not the in-scan JS-global path).
  Internal-only per Bounteous restriction.
- **006-cookiebot-eu-tld.yaml** — Cookiebot on a `.com` TLD resolves to
  EU via content signals (post-v0.5.1 generic-TLD escalation).
- **007-ketch-headless-cmp.yaml** — Ketch is `dom_type: headless_api` (no
  on-page banner). Tests that cmp_clicker skips banner-click attempts.
- **008-didomi-shadow-dom.yaml** — Didomi JS-global detection + `.io`
  TLD escalating to EU via og:locale content signals.

Each case follows the v0.5.0 schema (name, url, methodology, notes,
expected:{has_definitive_findings, consent_state, cmp_detected,
cmp_confidence_at_least, jurisdiction, violations_count_at_least}).

### Added — 15 new CMP URL patterns

`src/consent_engine/tools/cmp_detector.py::_SCRIPT_URL_RULES`:

- Cookiebot EU CDN (`cdn.cookiebot.eu`)
- CookieHub EU CDN (`cdn.cookiehub.eu`)
- CookieYes broader pattern (`cookieyes.com`)
- CookieInformation (`widget.cookieinformation.com`,
  `cookieinformation.com`, `cmp.cookieinformation.com`,
  `policy.app.cookieinformation.com`, `static.policy.app.cookieinformation.com`)
- CookieReports (`policy.cookiereports.com`)
- Klaro CDN (`klaro.kiprotect.com`)
- Borlabs Cookie WP plugin (`borlabs.io`)
- Real Cookie Banner (`cdn.real-cookie-banner.com`)
- Sourcepoint legacy + new (`cdn.privacymanagement.com`,
  `api.privacy-mgmt.com`, `.sp-prod.net/`)
- Shopify Customer Privacy (`sdks.shopifycdn.com/consent`)

Plus `_CMP_META` entries for **CookieInformation**, **CookieReports**,
and **Real Cookie Banner** so URL matches resolve to a known profile
instead of the fallback default.

Total CMPs detectable: **35+** (was ~30 in v0.5.2). README's "Customize
for your stack" updated.

## [0.5.3] — 2026-05-19 — vendor library expansion (36 → 77) + E2E smoke

Pre-launch polish before the Thursday LinkedIn announcement.

### Added — vendor library expanded from 36 to 77

Vendor coverage in `src/consent_engine/data/vendor_library/vendors.json`
went from 36 entries to 77. The expansion prioritized **lawsuit-exposed
categories** the v0.5.2 library was missing or thin on.

#### Session replay + behavior recording (heaviest CIPA exposure)
Recently the foundation of California / state-wiretap class actions
(Javier v. Pomerantz, Williams v. DDR Media, Calvert v. Red Robin, etc.).
- **Microsoft Clarity**, **Hotjar**, **FullStory**, **Mouseflow**,
  **Smartlook**, **Quantum Metric**, **Glassbox**, **Lucky Orange**,
  **Inspectlet**, **Crazy Egg**, **Heap**, **Pendo**

#### Chat / conversational widgets (CIPA exposure)
Transcript capture without consent banner = wiretap-claim surface.
- **Drift**, **Intercom**, **LiveChat**, **Zendesk**, **Tawk.to**

#### Adobe ecosystem
- **Adobe Analytics** (s_cc / s_sq / s_vi / AMCV_* family — extremely
  common on enterprise sites), **Adobe Target** (mbox), **Adobe Audience
  Manager** (demdex DMP — high CCPA/GDPR exposure)

#### Marketing automation + CRM
- **Marketo** (Adobe Engage), **HubSpot**, **Salesforce Pardot**,
  **ActiveCampaign**, **Mailchimp**, **Klaviyo** (added in v0.5.2 already
  — kept here for catalog completeness)

#### Customer data platforms + tag management
- **Segment**, **mParticle**, **Snowplow**, **Tealium iQ** (new
  `functional` category — the TMS itself isn't tracking, but
  misconfigured tag management can defeat the CMP)

#### Ad networks + identity resolution
- **Bing Ads / Microsoft UET**, **Quora**, **AppLovin**, **RTB House**,
  **Yandex Metrika**, **Baidu Analytics**, **ID5** (cookieless ID),
  **LiveIntent**

#### Cookieless analytics (false-positive guards)
Flagged so the scanner doesn't false-positive these as tracking cookies:
- **Cloudflare Web Analytics**, **Plausible**, **Fathom Analytics**

Every new entry includes the same schema as the existing library
(`domains`, `cookie_names`, `category`, `legal_exposure`,
`onetrust_category`, `notes`) with a litigation-context note where
applicable.

### Verified — E2E smoke run on five sites (v0.5.2 wheel)

| Site | Vendors | Confirmed | GPC | CMP | Jurisdiction |
|---|---|---|---|---|---|
| `https://example.com` | 1 | 0 | inconclusive | none | US |
| `https://apple.com` | 3 | 1 | inconclusive | none | US |
| `https://microsoft.com` | 6 | 2 | **respected** (2 → 0) | OneTrust | US |
| `https://sap.com` | 2 | 0 | inconclusive | none | US |
| `https://tesco.com` | 3 | 0 | ignored (1 → 1) | OneTrust | EU |

Microsoft's GPC-respected case is the first sample in the corpus where
the scanner can definitively show that GPC works when the site honors
it — useful as a positive control.

## [0.5.2] — 2026-05-18 — public-repo cleanup pass + API/MCP/skill tests

Pre-launch hygiene before LinkedIn announcement. No runtime behavior change.

### Removed (cleanup)
- **`HANDOFF.md`** at repo root — internal dev-handoff doc from the v0.1.5
  bring-up. Not appropriate for a public OSS repo.
- **`RELEASING.md`** at repo root — exposed the GitHub-environment name +
  workflow-trust-publisher details. Not a security vulnerability per se
  (Trusted Publishing is OIDC, no secrets in the file), but internal
  release-engineering process shouldn't live in a public repo. The
  release flow runs the same way; the docs just live in the maintainer's
  private notes now.
- **`AGENTS.md`** replaced with a symlink to `CLAUDE.md` — the two were
  byte-identical. One source, two filenames for the two convention names
  (Anthropic + general).

### Fixed (docs)
- **`uv run` vs `uvx` clarification** in `CLAUDE.md`. Both are valid for
  different contexts: `uv run` runs from a local clone (developer), `uvx`
  installs from PyPI + runs (end user). Added an explicit section.
- **Stale `consent-engine chat` reference removed** from `.claude/skills/
  consent-audit/SKILL.md`. The chat subcommand was removed in v0.5.0;
  the skill now correctly points users at the MCP `query_evidence` tool
  or direct `evidence.jsonl` grep.
- **README "Customize for your stack"** now lists the ~30 CMPs actually
  supported (OneTrust, Truyo, Cookiebot, CookieYes, Usercentrics,
  Didomi, TrustArc, Ketch, Sourcepoint, Quantcast, Osano, Axeptio,
  Klaro, CookieScript, CookieHub, Crownpeak, TrustCommander, Termly,
  Complianz, TrueVault, iubenda, Borlabs, Civic, Consentmanager,
  Shopify, Pandectes, PiwikPRO, Transcend, Ensighten, DataGrail, CCM19,
  Wix, plus IAB TCF + GPC/GPP). Was misleadingly saying "ships with
  OneTrust" as if it were the only one.
- **README credits trimmed** to Fred Pike + Phil Pearce (the two
  MeasureSummit speakers whose frameworks materially shaped the
  architecture). Removed third-party-vendor name-drops.
- **`docs/sample-audit/README.md`** removed the "Once GitHub Pages is
  enabled" instructional block (Pages is enabled). Removed reference to
  a Bounteous-channel client; replaced with `onetrust.com` and
  `apple.com` as suggested demo targets.

### Added (tests)
Test coverage expanded from 56 to 70 with three new test files. All
cover surfaces that the v0.5.0 audit identified as under-tested.

- **`tests/test_api.py`** — 6 tests for the FastAPI surface:
  - `/healthz` returns 200 + version
  - `POST /audit` returns 503 when `CONSENT_ENGINE_API_TOKEN` unset
  - `POST /audit` returns 401 with missing token
  - `POST /audit` returns 401 with wrong token
  - `POST /audit` accepts `Authorization: Bearer <token>` (run_audit mocked)
  - `POST /audit` accepts `X-Consent-Engine-Token: <token>`
- **`tests/test_mcp_server.py`** — 5 tests for the MCP tool surface:
  - `_safe_audit_dir` accepts valid UUID4s (parametrized)
  - `_safe_audit_dir` rejects path-traversal payloads (parametrized)
  - `_AUDIT_ID_PATTERN` rejects uppercase UUIDs (keeps the path-resolve check sound)
  - `list_tools` returns the three audit tools with correct required-field schemas
  - `_read_audit_result` + `_query_evidence` return error TextContent (not raise) on bad audit_id
- **`tests/test_skill.py`** — 7 tests for `.claude/skills/consent-audit/SKILL.md`:
  - File exists at the expected path
  - YAML frontmatter parses + has `name` + `description`
  - `name` matches the directory slug
  - Description includes the trigger keywords (audit / consent / url)
  - Body does **not** reference the removed `consent-engine chat` subcommand
  - Body still shows the current `consent-engine audit <url>` run command
  - Body doesn't reference dead-code imports / deprecated flags

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
- **Truyo CMP detected.** The v0.2.0 audit on a Truyo-protected enterprise site missed Truyo
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
