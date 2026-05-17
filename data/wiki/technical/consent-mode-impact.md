# Consent Mode — Reporting Impact and Business Case

tags: consent-mode, data-loss, modeling, smart-bidding, ga4, reporting
related: [[concepts/consent-mode-v2]], [[concepts/cmp-failures]]

## Why Compliance ≠ Data Destruction

The compliance argument and the commercial argument for proper Consent Mode implementation are aligned, not in tension:
- Without proper consent signals: advertising data is both legally questionable AND commercially degraded
- Properly implemented Consent Mode V2 satisfies GDPR requirements AND preserves advertising performance
- An audit finding of "CMP present but Consent Mode not implemented" is simultaneously a legal risk AND a business performance problem

## Conversion Data Loss Estimates

Sites that implement consent banners WITHOUT Consent Mode V2:
- EU/UK sites: **30–50% of conversions go unattributed**
- Sites with cookie walls: up to **60% unattributed** in opt-in jurisdictions
- Advanced Consent Mode with modeling: recovers approximately **65–80%** of lost conversions
- Basic Consent Mode: no recovery — conversions simply absent from reports

## Impact on Google Ads Performance

Incomplete conversion data due to missing consent signals:
1. Smart Bidding algorithms receive degraded training data
2. Target CPA and Target ROAS models underperform vs. full-data baselines
3. Audience lists shrink (remarketing pool reduced by denied-consent users)
4. Conversion lag reporting becomes unreliable
5. **Estimated revenue impact: 15–35% reduction in ROAS for EU traffic without CMv2**

## GA4 Blended Reporting (Behavioral Modeling)

GA4 uses behavioral modeling to fill gaps from denied-consent users. Requirements:
- Site must have **1,000+ daily consenting users** as a modeling baseline
- Without this threshold: denied-consent user data is simply absent
- This creates systematic bias toward reporting on consenting demographics only

**Practical implication:** Small/mid-size sites may not qualify for modeling at all. Their only options are Basic Consent Mode (clean data, just less of it) or accepting a degraded data picture.

## Network Evidence Interpretation

**If audit captures BOTH:**
1. `gcs=G100` (consent denied) in a network request
2. A conversion event URL in the same scan

→ Site is using Advanced Consent Mode AND firing conversion pings for denied users. The conversion is modeled, not real — but the data IS being sent to Google for behavioral modeling. Under GDPR, sending any data to Google for modeling after consent denial may require a documented legal basis (e.g., legitimate interest analysis for aggregate modeling).

**Basic Mode Evidence in Network Traffic:**
- No `gcs=` parameter in any Google requests
- Zero requests to analytics.google.com or doubleclick.net when opted out
- Tags fully blocked — no data reaches Google

**Advanced Mode Evidence:**
- `gcs=G100` present in requests
- analytics.google.com/g/collect still fires after opt-out
- Tag NOT blocked — sends cookieless ping

## The 23% Reality (vs. 65% Promise)

The commercial promise of Advanced Consent Mode: recovers 65% of lost data via modeling.
The empirical reality: only **23% of implementations** successfully recover this data.

Why: implementation failures (default granted states, race conditions — see [[concepts/cmp-failures]]) and insufficient conversion volume.

**Use in reports:** A client with a broken CMP implementation doesn't just have legal risk — they're also losing the modeling benefit they thought they were getting.

## Regulatory Framing for Executive Summaries

When writing about Advanced Consent Mode findings:
- Finding `gcs=G100` is NOT a pass — it's a nuanced finding requiring documentation
- The data flow to Google for modeling requires a defensible legal basis
- The site should have documented their legal basis for ACM pings in their privacy policy/DPA
- If no documentation exists: treat as an open compliance risk alongside the legal review recommendation
