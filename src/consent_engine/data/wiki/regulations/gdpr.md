# GDPR — Consent Requirements

tags: eu, gdpr, consent, eprivacy, lawful-basis
related: [[tcf]], [[enforcement/gdpr-fines]], [[concepts/dark-patterns]]

## Article 4(11) — Definition of Consent

Consent must be:
- **Freely given** — cannot be bundled with terms of service or conditional on service access
- **Specific** — separate consent per processing purpose (analytics ≠ advertising)
- **Informed** — clear explanation of what data is processed and why
- **Unambiguous** — pre-ticked boxes do not constitute valid consent. Continued browsing ≠ consent.

## Article 6 — Lawful Basis for Processing

For advertising cookies and tracking pixels that profile users for targeted advertising, the only valid basis is:
- **6(1)(a): Consent** — required for behavioral advertising

**Legitimate Interest (6(1)(f)) is NOT valid for behavioral advertising.** This was confirmed by the LinkedIn €310M ruling (Oct 2024). Any site claiming LI for ad pixels is non-compliant under current EU enforcement posture. See [[enforcement/gdpr-fines]].

## Article 7 — Conditions for Consent

- Controller must demonstrate consent was given (accountability burden)
- Request must be clearly distinguishable from other matters
- **Withdrawal must be as easy as giving consent** — asymmetric UX (easy Accept, hard Reject) is a violation
- Right to withdraw at any time must be preserved

## ePrivacy Directive Article 5(3)

Applies BEFORE GDPR for cookies and device storage access. Requires prior informed consent for any cookie placement except strictly necessary cookies — regardless of GDPR basis.

**Key point:** Even if a company has a valid GDPR legitimate interest claim, the ePrivacy Directive still independently requires consent for the cookie placement. GDPR and ePrivacy are separate obligations.

## Enforcement Context

Supervisory authorities (CNIL, Irish DPC, ICO, etc.) have fined for:
- Dropping analytics/advertising cookies before consent obtained
- Pre-ticked opt-in boxes
- Not honoring "Reject All" signals
- Requiring consent as condition of website access
- Legitimate interest claimed for behavioral advertising (now systematically rejected)

## Audit Signal Mapping

| Finding | GDPR Implication |
|---|---|
| Cookies set before CMP interaction | Article 6 + ePrivacy violation |
| "Reject All" harder to click than "Accept All" | Article 7 violation — asymmetric UX |
| LI claimed as basis for ad pixels | Non-compliant per LinkedIn €310M precedent |
| TCF CMP present — Purpose 1 consent not granted | ePrivacy Directive + TCF violation |
| No consent basis documented for analytics | Article 6 violation |
