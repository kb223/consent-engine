# Global Privacy Control (GPC) Signal

tags: gpc, opt-out, ccpa, us-law, http-header
related: [[regulations/ccpa]], [[regulations/us-state-laws]], [[enforcement/us-enforcement]]

## What It Is

The Global Privacy Control (GPC) is a browser-level privacy signal transmitted as an HTTP request header:
```
Sec-GPC: 1
```

When present, it signals that the user does not want their data sold or shared for targeted advertising. It is a machine-readable, universal opt-out mechanism.

## Legal Status by State

| State | GPC Required | Notes |
|---|---|---|
| California | **Mandatory** | CPPA: non-compliance enforceable without prior notice |
| Colorado | Mandatory | |
| Connecticut | Mandatory (Jan 2025) | |
| Texas | Mandatory | |
| Montana | Mandatory | |
| Oregon | Mandatory (Jan 2026) | |
| New Jersey | Mandatory | |
| Virginia | Not required | |
| Iowa | Not required | |

## The Audit Rule

**If `Sec-GPC: 1` is detected in a scan AND an advertising pixel fires AND the user's IP resolves to a GPC-mandate state → confirmed violation, no exceptions.**

California's CPPA has explicitly stated GPC failure is an enforceable violation without requiring prior notice to the business.

## Fine Exposure

- California: $7,500 per intentional violation per consumer
- A site with 100K California visitors facing a GPC violation = up to $750M theoretical maximum exposure
- Sephora paid $1.2M for a relatively small-scale GPC failure (first CCPA enforcement action)

## Technical Implementation

A compliant site must:
1. Detect `Sec-GPC: 1` header on the server OR use a browser-side detection library
2. Map the GPC signal to opt-out state in the CMP
3. Fire no advertising or behavioral tracking pixels
4. Honor it within 15 business days of the signal (California)

Common failures:
- GPC signal detected but not mapped into the CMP's consent state
- CMP treats GPC as a "soft preference" rather than a binding opt-out
- Server-side GTM not receiving GPC header (stripped at server — see [[concepts/ssgtm-risk]])

## Enforcement Precedent

**Sephora (2022):** $1.2M fine. First CCPA enforcement. AG cited GPC non-compliance explicitly. Pixel-based data sharing with Meta/Google classified as "sale."

**Tillamook County Creamery (2022):** AG enforcement sweep. Advertising pixels continued firing after GPC. Mid-market brand — GPC enforcement is not limited to large tech.

**California AG's 2022 enforcement sweep** specifically targeted GPC non-compliance across multiple retailers.
