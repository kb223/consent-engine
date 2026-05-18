# Quebec Law 25 — Privacy Framework

tags: canada, quebec, law25, opt-in, privacy-by-default
related: [[concepts/cmp-failures]], [[concepts/consent-mode-v2]]

## Overview

Quebec Law 25 (formerly Bill 64) is the strictest, most comprehensive privacy framework currently active in North America. Fully enforced since September 2024 by the Commission d'accès à l'information du Québec (CAI).

**Applies to:** Any organization processing personal data of Quebec residents — regardless of physical headquarters or revenue threshold. No minimum threshold.

Because large enterprises prefer a unified architecture rather than segmenting Canadian traffic, Law 25 has become the de facto Canadian baseline.

## Key Technical Mandates

**Opt-in consent required (unlike PIPEDA's opt-out model):** Informed, opt-in consent required before any tracking or profiling technology is activated. Consent must be:
- Granular — separate consent per distinct purpose
- Easily withdrawable

**Privacy by Default (Section 9.1):** Technological products must configure the highest possible level of confidentiality automatically. This means:
- Advanced tracking, geolocation, and behavioral profiling features must be OFF by default
- Explicit user action required to enable them
- Basic session cookies (load balancing, shopping carts) are exempt — but still require transparency

**Privacy Impact Assessments (PIAs):** Required for any transfer of personal data outside Quebec, which includes nearly all cloud-based analytics platforms (Google Analytics, Meta Pixel, etc.).

## Penalties

Up to CAD 10 million or 2% of global turnover — whichever is higher.

## Audit Implications

A site serving Quebec users with:
- Default "granted" consent states → Section 9.1 violation
- No opt-in banner (just opt-out) → full Law 25 violation
- Profiling pixels firing before explicit consent → immediate liability

Advanced Consent Mode with default "denied" satisfies the technical requirement; Basic Consent Mode also complies but destroys conversion data.

## Federal Void

Canada's federal Bill C-27 (Consumer Privacy Protection Act) died when Parliament was prorogued January 6, 2025. PIPEDA remains in force federally but is widely considered inadequate. Law 25 fills the void for any organization touching Quebec residents.
