# U.S. Privacy Enforcement — Key Cases

tags: ccpa, us-enforcement, sephora, disney, ftc, class-action, gpc, cppa, tilting-point, honda, todd-snyder, doordash
related: [[regulations/ccpa]], [[regulations/us-state-laws]], [[concepts/gpc-signal]], [[concepts/cipa-vppa]]

## Regulatory Actions

**Disney — California AG, February 11, 2026 — $2.75 million (largest CCPA settlement)**
- Opt-out mechanism was device-by-device and service-by-service — not account-wide
- User who opted out on Disney+ still tracked on ESPN+, Hulu, different devices
- CA AG: CCPA requires a universal opt-out, not per-device fragmentation
- **Principle established:** Opt-out must be honored across all services and devices associated with a consumer's account. Per-service opt-out = violation.
- **Audit relevance:** Any site/platform requiring repeated opt-out per device or service is non-compliant.

**Tractor Supply — CPPA (California Privacy Protection Agency), September 30, 2025 — $1.35 million**
- First major CPPA enforcement action (CPPA is separate from and acts independently of the AG)
- Violations: GPC signal not honored, inadequate privacy notice, job applicant rights not disclosed, personal data shared with third parties without proper data processing agreements
- **Principle established:** CPPA enforces independently — GPC non-compliance is a standalone CPPA violation, not just AG enforcement.
- **Audit relevance:** GPC + advertising pixel firing = citable CPPA enforcement precedent alongside Sephora.

**Tilting Point Media — CPPA, July 2025 — $500,000**
- Mobile-game publisher; allowed collection of children's personal information without obtaining parental consent or applying COPPA-required age-screening controls before sharing data with advertising SDKs
- Failed to honor opt-out preference signals (GPC) for users in California
- CPPA order required implementation of an age-screening mechanism, COPPA-aligned consent flow, and quarterly compliance reports for three years
- **Principle established:** Children's privacy under CCPA is a CPPA enforcement priority and overlaps with FTC's COPPA jurisdiction. Mobile games and any site with mixed-age users carry heightened risk.

**Honda (American Honda Motor Co.) — CPPA, March 2024 — $632,500**
- First CPPA settlement after the agency stood up its enforcement division
- Violations: required California consumers to verify their identity to submit opt-out and limit-use-of-sensitive-data requests (CCPA prohibits verification for these specific rights), required excessive personal information for authorized agent requests, asymmetric cookie-banner design favoring "accept" over "reject"
- **Principle established:** Opt-out requests must be one-click and may not require identity verification. Authorized-agent processes that demand extra documentation beyond CCPA's text are independent violations.
- **Audit relevance:** Any opt-out flow that asks for email confirmation, account login, or additional ID fields = direct Honda precedent.

**DoorDash — California AG, February 2024 — $375,000**
- DoorDash participated in a marketing co-op that exchanged customer personal information (names + addresses) with other businesses' lists in return for promotional access to those lists
- AG: this exchange constituted "sale" of personal information under CCPA, requiring opt-out disclosures DoorDash did not provide; also constituted "sharing" under CalOPPA and the federal CAN-SPAM Act
- **Principle established:** Non-monetary exchanges of personal information for "valuable consideration" (access to mailing lists, partner audiences, lookalike-modeling capacity) are CCPA sales requiring opt-out disclosure.
- **Audit relevance:** Lookalike-audience uploads to Meta or Google = same legal theory. Customer-match audiences are not exempt.

**Todd Snyder — CPPA, May 2024 — $345,178**
- Direct-to-consumer apparel retailer; CMP banner technically present but the opt-out link landed on a page that required users to fill in a five-field form (including driver's license upload) before any opt-out was honored — and even when submitted, opt-outs were intermittently ignored due to a misconfigured cookie banner that erased the user's choice within 40 days
- **Principle established:** Cookie-banner misconfiguration that fails to persist opt-out choices is a CCPA violation in its own right, separate from any disclosure or pixel-firing issue. Excessive verification on the opt-out path is a violation per Honda.
- **Audit relevance:** Any audit where the CMP exists but opt-out persistence is broken or where reject-flow requires more than email = direct Todd Snyder precedent.

**Google — Texas AG, May 2025 — $1.375 billion**
- Largest single-state privacy settlement in US history
- Location tracking persisted in Incognito mode; biometric data (voiceprints) collected without consent
- Statutes: Texas Data Privacy and Security Act (TDPSA) + Capture or Use of Biometric Identifier Act (CUBI) + DTPA
- **Principle:** State AGs outside California now pursue billion-dollar settlements. Texas, Florida, Washington have aggressive enforcement posture.

**Sephora — California AG, October 2022 — $1.2 million**
- First CCPA enforcement action
- Selling consumer data to advertising partners via pixel sharing without disclosing it as a "sale"
- Failing to honor GPC opt-out signals
- AG's complaint specifically cited Meta Pixel and Google Ads pixel-based data sharing as constituting "sale" of personal information
- **Principle established:** GPC = legally valid CCPA opt-out. Non-compliance = per-violation fine.
- **Key insight:** Money need not change hands for a pixel data transfer to be classified as "sale."

**Tillamook County Creamery — California AG, 2022**
- Settlement and corrective action required
- Advertising pixels continued firing after GPC signal received
- Part of AG's first GPC enforcement sweep
- **Significance:** Demonstrates GPC enforcement applies to mid-market brands, not just large tech

**FTC v. Epic Games (Fortnite) — September 2022 — $275M + $245M**
- $275M COPPA: default-on voice and video collection for minors
- $245M: dark UX patterns tricking children into in-app purchases
- **Principle:** Interactive entertainment with children requires opt-in consent; dark patterns carry FTC enforcement risk

---

## Class Action Litigation

**Disney / Entertainment Sector — 2023–2025**
- Class action lawsuits against Disney, NBC Universal, Hulu
- Allegations: Meta Pixel + similar tracking on health-adjacent and subscription content without disclosure
- Disney specifically: Pixel tracking on disneyplus.com and theme park booking pages alleged to share viewing habits with Meta
- VPPA cited alongside CCPA in streaming contexts
- Settlement exposure per action: $25–$100M range

**Aspen Dental — FTC/State AGs**
- Settled for $18.5M
- Used Meta and Google tracking tools transmitting sensitive health data without consent
- Multi-statute: California Confidentiality of Medical Information Act + CCPA + HIPAA-adjacent
- Established: health-adjacent content + advertising pixels = maximum exposure category

---

## The Pixel-as-Sale Doctrine

Multiple AG enforcement actions (2022–2026) have confirmed:
- Sharing behavioral data with an ad platform via pixel = "selling" personal information under CCPA
- Even if no money changes hands
- This makes every site running Meta Pixel, TikTok Pixel, or Google Ads conversion tracking a potential CCPA enforcement target for California users who opt out

**Impacted vendors:** Meta Pixel, Google Ads (gads), TikTok Pixel (ttq), LinkedIn Insight Tag (li_fat_id), DoubleClick (doubleclick.net)

---

## FTC Fine Reference

| Violation Type | Fine Basis |
|---|---|
| FTC Act violations | $51,744 per violation per day |
| COPPA violations | $51,744 per violation |
| Systemic dark patterns (Epic case) | $245M total |

---

## Enforcement Trajectory

The California AG swept multiple retailers in 2022 with GPC non-compliance as the lead violation. The CPPA has expanded enforcement capacity and is actively using automated scanning tools to detect GPC failures. The class-action bar (CIPA plaintiffs) is using the same automated tools to generate demand letters at scale. Per-consumer CCPA statutory damages mean that the theoretical maximum exposure for any mid-size US e-commerce site facing GPC non-compliance is in the hundreds of millions of dollars.

### CPPA 2024–2026 Enforcement Pattern

The CPPA's first eighteen months of public enforcement (Honda March 2024 → Disney February 2026) reveal a clear pattern:

1. **GPC non-honoring** is the single most cited violation (Sephora, Tractor Supply, Tilting Point).
2. **Opt-out friction** is the second (Honda's verification gates, Todd Snyder's five-field form).
3. **Banner misconfiguration that breaks opt-out persistence** is an independent violation (Todd Snyder).
4. **Non-monetary "sale"** continues to expand (DoorDash mailing-list exchange, all pixel-as-sale cases).
5. **Children's data** under CCPA is now an active CPPA priority (Tilting Point), overlapping with FTC COPPA.

### What This Means for an Audit

A site producing **any one** of the following findings has direct enforcement precedent:

- Pixel firing after GPC signal received → Sephora + Tractor Supply
- Opt-out flow requires verification or login → Honda
- Opt-out submitted but cookie persists or re-grants within 40 days → Todd Snyder
- Lookalike audience upload to Meta/Google without sale disclosure → DoorDash
- Per-service or per-device opt-out (account-wide not enforced) → Disney
- Children's data shared with ad SDKs without age screening → Tilting Point
