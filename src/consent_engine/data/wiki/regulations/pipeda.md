# PIPEDA — Federal Canadian Privacy Law

tags: canada, pipeda, federal, opt-out, opc
related: [[regulations/quebec-law25]], [[concepts/gpc-signal]], [[concepts/consent-mode-v2]]

## Overview

The Personal Information Protection and Electronic Documents Act (PIPEDA) is Canada's federal private-sector privacy law. Enforced by the Office of the Privacy Commissioner of Canada (OPC). In effect since 2001; last meaningfully amended in 2015 (Digital Privacy Act).

**Applies to:** Federally regulated organizations (banks, telcos, airlines, interprovincial trucking) plus any organization in a province *without* substantially similar provincial legislation. Three provinces have their own substantially similar laws and supersede PIPEDA for intra-provincial activity:

- **Quebec** — Law 25 (strictest in North America; see `[[regulations/quebec-law25]]`)
- **British Columbia** — Personal Information Protection Act (BC PIPA)
- **Alberta** — Personal Information Protection Act (AB PIPA)

PIPEDA still applies to **interprovincial and international** data flows even where a provincial law governs intra-provincial activity. In practice this means almost every Canadian-facing site needs to satisfy PIPEDA *and* whichever provincial law is strictest in their user base — usually Quebec Law 25.

## Consent Model — Opt-In, Not Opt-Out

PIPEDA requires **meaningful consent** before collecting, using, or disclosing personal information. The OPC's 2018 *Guidelines for Obtaining Meaningful Consent* clarify what "meaningful" means for digital advertising and analytics:

- **Form must match sensitivity.** Sensitive data (health, financial, biometric, children, precise location) requires **express opt-in**. Low-sensitivity data may use implied consent if the purpose is obvious to a reasonable person.
- **Purposes must be specific.** Bundled consent for "marketing, analytics, and partner sharing" is invalid — each material purpose must be separately disclosed and consented.
- **Withdrawal must be as easy as granting.** A one-click reject is required if a one-click accept exists.
- **No pre-checked boxes.** Implied consent ≠ silence-as-consent for online tracking.

This is materially stricter than CCPA (US opt-out model) and aligns with GDPR's opt-in requirement — though enforcement intensity has historically been weaker than EU regulators.

## Key Obligations

| Principle | What it means for a website |
|---|---|
| **Accountability** | Appoint a Privacy Officer; document data flows for tracking + advertising vendors |
| **Identifying Purposes** | Disclose every distinct purpose at or before collection (in plain language, not buried in a 4,000-word policy) |
| **Consent** | Obtain meaningful consent before tags fire; allow withdrawal at any time |
| **Limiting Collection** | Don't collect more than the disclosed purpose requires (no "fingerprint everything just in case") |
| **Limiting Use** | Don't repurpose data without re-consent (e.g., transactional email list re-used for retargeting) |
| **Safeguards** | Reasonable security against unauthorized access; mandatory breach notification since 2018 |
| **Openness** | Privacy policy must be public, current, and reflect actual data practices |
| **Individual Access** | Respond to access requests within 30 days |
| **Challenging Compliance** | A clear complaint pathway to the Privacy Officer; OPC backstop |

## Penalties

PIPEDA's enforcement teeth are weaker than Quebec Law 25 or GDPR. The OPC can:

- Investigate complaints and issue findings (binding only after Federal Court order)
- Negotiate compliance agreements
- Refer matters to Federal Court for damages

Fine maximums are statutory **CAD 100,000 per offence** for breach-notification or recordkeeping failures, but most resolutions are settlements, not fines. Federal Bill C-27 (the Consumer Privacy Protection Act, CPPA) would have raised fines to **CAD 25M or 5% of global turnover**, with administrative monetary penalties enforceable directly by the OPC — but the bill **died on the order paper when Parliament was prorogued January 6, 2025**. As of mid-2026, no successor bill has been passed.

## Why PIPEDA Still Matters Even Though Quebec Law 25 Is Stricter

1. **Federal pre-emption clause.** PIPEDA applies to federally regulated organizations (banks, telcos, airlines) regardless of province. A Canadian bank operating in Quebec answers to PIPEDA on its core regulated activity *and* Law 25 on its consumer marketing.
2. **Interprovincial data flows.** Any movement of personal data across provincial borders falls under PIPEDA jurisdiction, including cloud analytics platforms hosting Canadian user data on US servers.
3. **OPC sweep authority.** The OPC runs joint enforcement sweeps with provincial regulators and Global Privacy Enforcement Network (GPEN) members — including the FTC, ICO, and CNIL. A PIPEDA finding can cascade internationally.

## Audit Implications

A Canadian-facing site (any jurisdiction "CA") with:

- **Default-granted Consent Mode** → opt-in failure (PIPEDA + Quebec Law 25)
- **Banner with "accept all" but no equally-prominent "reject all"** → meaningful-consent failure under both PIPEDA and Law 25
- **Server-side GTM stripping GPC signal** → "limiting use" + "openness" principle violations
- **Vendor list disclosed only inside a 4,000-word policy** → "identifying purposes" failure
- **Pixels firing before consent banner appears** → no consent at all, full violation

For an audit landing in jurisdiction CA, lead the report with **Quebec Law 25 risk** (stricter penalties, more aggressive regulator) and reference PIPEDA as the federal floor. If the site is bank/telco/airline, surface PIPEDA as the *primary* framework.

## Provincial Laws — BC PIPA and Alberta PIPA

Both are substantially similar to PIPEDA and apply to most private-sector activity within their respective provinces. Key differences:

- **BC PIPA:** Slightly more prescriptive consent rules; explicit reference to "deemed consent" for low-sensitivity transactions. Enforced by the Office of the Information and Privacy Commissioner for BC.
- **Alberta PIPA:** Closer to PIPEDA; same federal-style consent model. Enforced by the Office of the Information and Privacy Commissioner of Alberta.

Quebec Law 25 is meaningfully stricter than both and is the binding ceiling for any organization touching Quebec residents. For most audit reports, Quebec Law 25 is the operative legal framework when jurisdiction is "CA" unless explicit BC/Alberta-only scope is established.

## References

- *Personal Information Protection and Electronic Documents Act*, S.C. 2000, c. 5.
- OPC, *Guidelines for Obtaining Meaningful Consent* (2018), https://www.priv.gc.ca/en/privacy-topics/collecting-personal-information/consent/gl_omc_201805/
- OPC, *PIPEDA Fair Information Principles* (Schedule 1), https://www.priv.gc.ca/en/privacy-topics/privacy-laws-in-canada/the-personal-information-protection-and-electronic-documents-act-pipeda/p_principle/
- *Bill C-27 (CPPA) — Status: died on order paper, January 6, 2025.*
