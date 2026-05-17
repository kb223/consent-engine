# IAB Transparency & Consent Framework (TCF) 2.2

tags: eu, tcf, cmp, iab, eprivacy, purpose-consent
related: [[gdpr]], [[enforcement/gdpr-fines]], [[concepts/dark-patterns]]

## Purpose

TCF is the IAB Europe standard for recording and transmitting user consent and legitimate interest signals for digital advertising in the EU. A TCF-compliant CMP issues a TC String encoding consent status per vendor and purpose.

Relevant for audits on EU-targeted sites that use a TCF-compliant CMP (OneTrust with TCF module, Didomi, Sourcepoint, etc.).

## TC String

Stored in the `euconsent-v2` cookie. Base64-encoded binary that encodes:
- CMP ID and version
- Per-purpose consent (Purposes 1–10)
- Per-vendor consent
- Legitimate interest claims

## Key Purposes for Advertising

| Purpose | Description | Consent Required? |
|---|---|---|
| Purpose 1 | Store and/or access information on a device | YES — no legitimate interest |
| Purpose 3 | Create a personalised ads profile | Yes |
| Purpose 4 | Select personalised ads | Yes |
| Purpose 7 | Measure ad performance | Yes (or LI where permissible) |
| Purpose 8 | Market research / audience insights | Yes |
| Purpose 10 | Develop and improve products | Yes |

**Critical:** Purpose 1 cannot rely on legitimate interest. Any vendor in the IAB Global Vendor List (GVL) that places cookies requires explicit Purpose 1 consent in the TC String.

## ePrivacy Directive Article 5(3)

Requires prior informed consent before storing cookies or accessing device storage, EXCEPT strictly necessary cookies. This applies regardless of GDPR — even with a valid LI claim under GDPR, ePrivacy still requires consent for the cookie itself.

## Audit Relevance

If a site uses a TCF CMP:
- Firing advertising pixels without Purpose 1 consent = ePrivacy violation
- Vendors in the GVL are bound to only process data when consent is granted in the TC String
- The TC String must be transmitted to ad vendors before they can set cookies

If an audit detects advertising cookies (doubleclick.net, meta pixel, etc.) firing without Purpose 1 granted in the TC String → confirmed TCF + ePrivacy violation.
