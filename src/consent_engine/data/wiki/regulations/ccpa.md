# CCPA/CPRA — California Consumer Privacy Act

tags: california, us-law, gpc, opt-out, sale-sharing
related: [[us-state-laws]], [[gpc-signal]], [[enforcement/us-enforcement]]

## Core Rights

**§1798.120 — Right to Opt Out of Sale**
California consumers may direct any business to not sell their personal information. The business must:
- Post a "Do Not Sell My Personal Information" link on homepage
- Honor opt-out within 15 business days
- Not sell after receiving a valid opt-out request

**CPRA Extension — Sharing for Cross-Context Behavioral Advertising (effective 2023)**
Opt-out rights now cover "sharing" — defined as disclosing personal information for cross-context behavioral advertising, even with no money exchanged. This directly covers:
- Passing user identifiers (cookies, device IDs) to ad platforms
- Meta Pixel / Facebook retargeting
- Google Ads conversion tracking
- LinkedIn Insight Tag, TikTok Pixel when fired post-opt-out
- Third-party audience syndication

**Key interpretation:** A business does not need to receive money for a data transfer to be classified as a "sale." Passing cookies or behavioral data to any ad platform = sale under CCPA/CPRA.

## Global Privacy Control (GPC)

CPRA regulations require businesses to honor the `Sec-GPC: 1` HTTP header as a valid opt-out of sale and sharing. This is mandatory, not optional.

**Enforcement action:** The California Privacy Protection Agency (CPPA) has explicitly stated that failure to honor GPC is an enforceable violation without requiring prior notice to the business.

**States that mandate GPC:** California, Colorado, Connecticut, Texas, Montana, Oregon.

If an advertising pixel fires after receiving `Sec-GPC: 1` from a California user → confirmed CPRA violation, per-consumer fine exposure.

## Penalties

| Violation Type | Fine |
|---|---|
| Unintentional violation | Up to $2,500 per consumer |
| Intentional violation | Up to $7,500 per consumer |
| Class action (actual damages) | Statutory + actual damages |

Enforced by: California Privacy Protection Agency (CPPA) + Attorney General.

**Applicability thresholds:** Businesses with $25M+ revenue, or that process 100,000+ consumer records annually, or derive 50%+ of revenue from selling personal data.

## Audit Signal Mapping

| Network Evidence | CCPA Implication |
|---|---|
| Advertising pixel fires → user opted out via CMP | Potential CPRA violation (sharing for behavioral advertising) |
| Advertising pixel fires → `Sec-GPC: 1` received | Confirmed CPRA violation — GPC is mandatory opt-out |
| Meta Pixel / TikTok Pixel transmitting behavioral data post-opt-out | "Sale" under CCPA regardless of monetary exchange |
| GCS=G100 with conversion event | ACM ping — gray area, requires defensible LI analysis |

## Key Precedent

**Sephora (Oct 2022, $1.2M):** First CCPA enforcement action. AG cited pixel-based data sharing with Meta/Google as constituting "sale." Also failed to honor GPC. Established that GPC non-compliance = per-violation fine. See [[enforcement/us-enforcement]].

**Tillamook County Creamery (2022):** AG enforcement sweep — advertising pixels continued after GPC signal. Demonstrates mid-market brands are targets, not just large tech.
