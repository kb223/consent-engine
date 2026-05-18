# CMP Dark Patterns — Regulatory Violations

tags: dark-patterns, cmp, ux, gdpr, consent, ftc
related: [[regulations/gdpr]], [[concepts/cmp-failures]], [[enforcement/gdpr-fines]]

## What Are Dark Patterns

Dark patterns are UI/UX design choices that manipulate users into granting consent they would not otherwise give. Regulators across the EU, US, and Canada have declared specific patterns to be per se violations.

A joint review by the FTC, ICPEN, GPEN (80+ privacy regulators, 27 consumer protection authorities) identified specific interface patterns as potential legal violations.

## Prohibited Dark Patterns (2026 Regulatory Consensus)

**Asymmetric Choice Architecture (most common violation)**
- Large, contrasted, easily clickable "Accept All" button
- "Reject All" buried as a low-contrast text link, or in a secondary menu requiring multiple clicks
- Google fined €150M (CNIL 2022) specifically for this: rejecting cookies required more clicks than accepting
- Article 7 GDPR: withdrawal must be as easy as giving consent

**Pre-Consent Cookie Drops**
- Advertising cookies placed before any user interaction with the banner
- Meta fined €60M (CNIL 2022): cookies fired before user interacted with consent banner
- ePrivacy Directive: no cookies before affirmative consent action

**Bundled Consent**
- Consent embedded in terms of service or service access conditions
- Amazon fined €746M: consent was pre-ticked and bundled with ToS
- GDPR: consent must be a "separate, freely given act"

**Language / Branding Mismatch**
- Consent banner in different language than the site (e.g., English banner for French-speaking Quebec users)
- Law 25: consent is invalid if not in the user's language
- Banner visually distinct from parent site, causing user confusion

**Drip Consent / Progressive Nudging**
- Showing banner repeatedly until user "accepts"
- Using countdown timers or urgency language to pressure consent

**Hidden Reject Path**
- "Manage preferences" → multiple screens → individual toggle for each purpose → no "reject all" button
- CNIL has fined for reject paths requiring 5+ clicks vs. 1-click accept

## 2026 Regulatory Standard

Regulators now demand **total parity in choice architecture:**
- Reject option must be equally prominent, accessible, and instantaneous as Accept
- India's upcoming DPDP Act: consent must be withdrawable via "single-click"
- Regulators use automated tools to verify that clicking "Reject All" actually stops network trackers — backend verification, not just UI review

## Audit Evidence

Dark patterns detectable in a browser audit:
1. Screenshot the CMP — count clicks required to Accept vs. Reject
2. Check cookie jar immediately after page load (before any CMP interaction) — any non-essential cookies = violation
3. Check network requests before CMP interaction — any advertising requests = violation
4. Verify "Reject All" actually stops advertising network requests (network tab before/after)
