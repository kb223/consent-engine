# Scanner Methodology — Technical Reference

tags: scanner, methodology, s3, gpc, acm-ping, false-positive, cnil, cipa, gdpr, playwright
related: [[concepts/consent-mode-v2]], [[technical/cmp-profiles]], [[enforcement/us-class-actions]]

Last verified: April 2026. Sources: CNIL technical guidance, ICO 2025 cookie sweep, CPPA enforcement actions, CIPA plaintiff methodology research, open-source scanner analysis (ConsentCrawl, autoconsent).

---

## Scan Methodology Tiers

### S1 — Live Browser Scan (Observe Only)

Real Chromium instance, no consent pre-set. Observe what the site does on first visit from a neutral IP.

**What it captures:**
- Whether a consent banner is displayed
- What tracking fires before any user interaction (pre-consent traffic)
- Cookie state on first load
- CMP vendor and confidence

**Limitation:** Does not test if the opt-out mechanism actually works. Banner may be present but consent enforcement broken.

### S2 — Interaction Scan (Click Reject)

S1 plus: automated CMP interaction to click "Reject All" / "Do Not Sell". Measure network traffic after interaction.

**What it captures:**
- Whether clicking reject stops tracking (GCS/GCD signals update)
- Whether cookies are cleared or blocked post-rejection
- Multi-step flow detection (manage preferences → uncheck → save)

**Limitation:** Requires accurate CMP detection and button selection. Shadow DOM, iframes, and unusual CMP builds can cause interaction failures (silent non-click).

### S3 — Pre-Set Opted-Out Scan (Primary Methodology)

Fresh browser context. Inject opted-out consent state (cookies/localStorage/headers) BEFORE page load. Reload page. Measure everything.

**What it captures:**
- Whether the CMP respects a pre-set opted-out state and suppresses tracking
- GCS/GCD signals in network requests (Consent Mode signal verification)
- Pixel endpoint firings (network-level evidence of tracking violation)
- Cookie violations (tracking cookies set despite opted-out state)

**Why S3 is the primary methodology:**
- Eliminates banner interaction variability
- Matches how courts evaluate evidence: "did tracking fire after the user communicated a preference not to be tracked?"
- Pre-set denial state is equivalent to a returning user who previously rejected
- Used by CIPA plaintiff attorneys (HAR captures with pre-set opted-out state)

---

## GPC (Global Privacy Control) Scan

**Header injected:** `Sec-GPC: 1`
**JS property set:** `navigator.globalPrivacyControl = true` (via `addInitScript`)

Both are required. Some sites check the HTTP header server-side; others check the JS property client-side. Neither alone is sufficient.

**How to detect if site honors GPC:**
1. Site auto-opts user out (no banner shown, tracking disabled)
2. Tracking requests to ad domains absent from network log
3. `/.well-known/gpc.json` endpoint exists and declares `gpc: true`

**Compare GPC-on vs GPC-off:** If the set of tracking domains contacted is identical between GPC scan and standard S3 scan, the site is ignoring the signal. This is a separate, independent violation from the CMP-based opt-out failure.

**Enforcement context:** CPPA/California AB 566 signed 2025 — browser-level GPC support mandatory by January 1, 2027. CPPA enforcement sweep (Sept 2025) targeted sites receiving `Sec-GPC: 1` from CA IP that continue to fire ad tracking. GPC non-compliance is immediately enforceable without prior warning under CA CPPA guidance.

---

## Three-Phase Capture Model (CNIL / EU Methodology)

EU regulatory auditors (CNIL, ICO, EDPB) use a three-phase model that our S3 primarily covers phase 3 of:

| Phase | Description | What to capture |
|---|---|---|
| **Phase 1** — Pre-banner | Page loads, banner not yet visible | Any tracking requests firing before user sees consent UI |
| **Phase 2** — Banner visible, no interaction | Banner displayed, user hasn't acted | Tracking that fires while banner is on screen |
| **Phase 3** — Post-rejection | User clicks Reject All | Whether tracking stops (our primary S3 check) |

**CNIL specific:** Requires capturing localStorage, sessionStorage, and IndexedDB — not just HTTP cookies. Under ePrivacy Article 5(3), "reading or writing to terminal" in any storage is in scope.

**ICO 2025 finding:** 30% of top 1,000 UK sites set advertising cookies without consent (Phase 1 violation). ICO requires "Reject all" on layer 1 (not buried in settings) and equal visual prominence to "Accept all."

**Scanner enhancement needed:** Phase 1 and Phase 2 capture is not yet implemented. Currently all captures are Phase 3 (S3 methodology). Phase 1 would require a separate scan without any consent injection.

---

## Evidence Standards for US Enforcement

**CIPA Class Action (plaintiff attorney methodology):**
- Primary artifact: HAR log with request timestamps and decoded payload parameters
- Key cookie names cited in complaints: `_ga`, `_gid`, `_fbp`, `_fbc`, `_gcl_au`
- Key GA4 request params cited: `dl` (document location), `dp` (document path), decoded from `collect` calls
- For §631 wiretap claims: requests must fire in real-time (session-active), not retrospectively — timing matters
- CIPA requires showing data routed to third-party servers (not just set locally)

**CPPA / CCPA enforcement (CPPA first major fine: $350K Capital One, May 2025):**
- Specifically targeted embedded third-party pixels (Meta Pixel, Google Analytics) firing without consent
- CPPA expects: cookie inventory, data flow maps, vendor contracts, proof that consent withdrawal stops tracking
- CPPA now expects **continuous or daily automated scanning** for regulated entities

**What your report should include for CIPA readiness:**
- Full URLs of tracking requests (not just domain patterns)
- Timestamp relative to page load and consent interaction
- Whether `_ga`, `_fbp`, `_fbc`, `_gcl_au` values appear in request payloads
- Whether these requests route to third-party servers (google-analytics.com, connect.facebook.net, etc.)

---

## False Positive Prevention

### 1. ACM Cookieless Pings — NOT Violations

**The most common false positive** in consent scanners.

When Advanced Consent Mode is active and user has denied consent, Google tags still fire a cookieless ping to `google-analytics.com/g/collect` with:
- `gcs=G100` (or G101/G110 for partial denial)
- `npa=1` (non-personalized ads)
- No `_ga` or `_gcl_au` cookies set alongside the request

**This is correct, legal behavior under CNIL and EDPB guidance** — no personal data cookie is transmitted. Do NOT flag these as violations.

**Detection rule:** Google Analytics/Ads domain request + `gcs` denial state (`0` in position 3 or 4) + no persistent tracking cookie (`_ga`, `_gcl_au`) = ACM ping, not a violation.

**Violation flag:** Google domain request + `gcs=G111` (both granted) in an S3 opted-out test = CMP integration failure. Flag this.

### 2. Consent Initialization Trigger

GTM's `Consent Initialization` trigger runs on every page load to call `gtag('consent', 'default', {...})`. This fires pre-banner. It is expected behavior — not a violation.

**Only flag tags that fire in GTM's `DOM Ready` or `Window Loaded` phase without user consent granted.**

### 3. First-Party vs Third-Party Cookie Distinction

First-party cookies set by the site's own server (even analytics cookies) are legally distinct from third-party cookies. CIPA class actions primarily target **third-party transmission** (data sent to Meta, Google, TikTok servers). CNIL/EDPB treat both as requiring consent for analytics/advertising purposes.

**Scanner classification should note** whether the cookie domain matches the first-party domain or is a third-party domain.

### 4. Session Cookies vs Tracking Cookies

Session cookies (no `Max-Age` or `Expires`, deleted on browser close) containing no persistent identifier are generally exempt under ePrivacy (CNIL audience measurement exemption).

**Flag only if:** cookie has `Max-Age > 0` AND value appears to be a unique identifier (random alphanumeric > 8 chars) AND category is analytics/marketing.

### 5. Geo-Conditional Banners

Some CMPs show different banners to different geographies. A site compliant for EU users (showing a full banner with Reject All) may show no banner to US users.

**Mitigation:** Note scan egress IP in report. A US-IP scan finding "no banner" should not be reported as non-compliant without also noting this may be geo-conditional. EU jurisdiction scans should be conducted from EU egress IPs.

---

## Open Source Scanner Comparison

| Tool | CMP Coverage | GCS/GCD Analysis | GPC Testing | Phase 1 Capture | Shadow DOM |
|---|---|---|---|---|---|
| **This scanner** | 35+ CMPs | Full (G100/G101/G110/G111) | Yes (S-GPC + JS) | ❌ Not yet | Usercentrics + Axeptio |
| ConsentCrawl | 35+ via blocklists | ❌ No | ❌ No | Partial | ❌ No |
| npm-playwright-autoconsent | 100+ (interaction only) | ❌ No | ❌ No | ❌ No | ❌ No |
| Cookiebot Scanner | CMP-agnostic | ❌ No | ❌ No | Partial | ❌ No |

**Key differentiator of this scanner:** GCS/GCD analysis and G100 false positive filtering. This is not implemented in any open source scanner reviewed.

---

## EU vs US Methodology Differences

| Dimension | EU (GDPR/ePrivacy) | US (CCPA/CIPA) |
|---|---|---|
| Consent basis | Opt-in required before any non-essential tracking | Opt-out model — must honor opt-out signal |
| GPC signal | Not mandated (no EU GPC requirement) | Mandatory opt-out signal in CA/CO/CT/TX/MT/OR/NJ |
| Storage scope | Cookie + localStorage + sessionStorage + IndexedDB | Primarily cookie + pixel (network evidence) |
| Enforcement trigger | Complaint or regulator proactive sweep | Plaintiff law firm (CIPA class action) + CPPA |
| Remediation standard | Must stop ALL tracking immediately on reject | Must stop tracking upon "Do Not Sell" signal |
| Banner layer requirement | Reject All must be on layer 1, equal prominence | No specific banner layer requirement for CCPA |
| Legitimate interest | Not valid for ad/analytics cookies (EDPB confirmed 2023) | Not applicable |

---

## Known Scan Accuracy Limitations

1. **Phase 1 capture not implemented** — Pre-consent traffic (before banner is visible) is not captured in S3. This is what EU regulators primarily check. Add as a distinct S0/S1 scan mode.

2. **Full request payload not logged** — Currently capturing URLs only, not decoded POST bodies. GA4 `collect` calls use POST; `dl` and `dp` params are in the POST body, not URL. CIPA evidence requires full payload.

3. **Geo-conditional banner risk** — Single egress IP. Scanning from US may show different banner (or none) compared to EU IP. Report includes egress IP but no automatic geo-variability detection.

4. **Race condition detection absent** — Not checking whether `gtag('consent', 'default')` fires BEFORE the first GA4 collect ping. This is the CNIL/ICO primary check. Add timing comparison as a Phase 1 enhancement.

5. **TCF without Consent Mode bridge** — Sites with `euconsent-v2` and no `gtag_enable_tcf_support` bridge will show `gcd` with `l` letters. Currently not flagged as a distinct finding.
