# U.S. State Privacy Laws — 2026 Landscape

tags: us-law, state-privacy, gpc, targeted-advertising, opt-out
related: [[ccpa]], [[gpc-signal]], [[enforcement/us-enforcement]]

## Overview

As of 2026, 20+ U.S. jurisdictions enforce comprehensive consumer privacy laws. All share a common thread: consumers have the right to opt out of sale or sharing of personal information for targeted advertising. Businesses must honor that right.

**Targeted advertising** (consistent definition across all state laws): displaying ads based on personal data obtained from the consumer's activities across non-affiliated websites. This directly covers Meta Pixel retargeting, Google Ads remarketing, LinkedIn Insight Tag, TikTok Pixel.

## States with GPC Mandate (Critical for Audits)

The following states require honoring the Global Privacy Control (`Sec-GPC: 1`) as a valid opt-out:

| State | Law | GPC Required | Enforcement |
|---|---|---|---|
| California | CCPA/CPRA | Yes — mandatory, no notice required | CPPA + AG |
| Colorado | CPA | Yes | AG |
| Connecticut | CTDPA | Yes (as of Jan 2025) | AG |
| Texas | TDPSA | Yes | AG |
| Montana | MCDPA | Yes | AG |
| Oregon | OCPA | Yes (as of Jan 2026) | AG |
| New Jersey | NJDPA | Yes | AG |

**Audit rule:** If `Sec-GPC: 1` is detected AND the user's IP resolves to any GPC-mandate state AND an advertising pixel fires → confirmed violation, per-consumer fine exposure.

## Active State Laws Summary (2026)

| State | Law | Effective | GPC | Fine/Violation |
|---|---|---|---|---|
| California | CCPA/CPRA | 2020/2023 | Yes | $7,500 intentional |
| Colorado | CPA | Jul 2023 | Yes | AG discretion |
| Connecticut | CTDPA | Jul 2023 | Yes (Jan 2025) | AG, 60-day cure |
| Virginia | CDPA | Jan 2023 | No | AG only |
| Texas | TDPSA | Jul 2024 | Yes | AG, 30-day cure |
| Montana | MCDPA | Oct 2024 | Yes | AG, 60-day cure |
| Oregon | OCPA | Jul 2024 | Yes (Jan 2026) | AG |
| Iowa | ICDPA | Jan 2025 | No | AG |
| New Hampshire | NHPA | Jan 2025 | No | AG |
| New Jersey | NJDPA | Jan 2025 | Yes | AG |
| Indiana | IDPL | Jan 2026 | No | AG |
| Rhode Island | RI HB 7787 | Jan 2026 | TBD | AG — very low threshold (35K consumers) |
| Maryland | MODPA | Oct 2025 | No | Opt-in for sensitive data |
| Tennessee | TIPA | Jul 2025 | No | AG |

## 2026 Key Legislative Developments

- **Rhode Island:** Exceptionally low applicability threshold — 35,000 consumers, or 10,000 if 20%+ revenue from data sales. Most businesses qualify.
- **Connecticut (Jul 2026):** Lowered threshold to 35,000 residents; expanded sensitive data to include neural + biometric data; requires disclosure if consumer data is used to train LLMs.
- **Oregon/Minnesota Q1 2026:** 30-day cure period expired. Violations immediately actionable.
- **California:** Delete Act (SB 362) — data brokers must access CPPA deletion mechanism every 45 days.

## Common Compliance Requirements (All States)

1. Privacy notice disclosing data sale/sharing practices
2. Opt-out mechanism — easy to find and use
3. Honor opt-out within 45 days (most states)
4. Data processing agreements with service providers
5. Data protection assessments for targeted advertising (high-risk processing)

## Enforcement Priority

California CPPA has publicly stated GPC non-compliance is immediately actionable with no cure period. The 2022 Sephora and Tillamook enforcement actions established that mid-market brands are targets, not just large tech. Per-consumer fine calculations mean a site with 100K California visitors facing an intentional GPC violation = up to $750M in theoretical maximum exposure.
