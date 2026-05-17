# U.S. Privacy Enforcement — Key Cases

tags: ccpa, us-enforcement, sephora, disney, ftc, class-action, gpc
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
