# Consent Compliance Wiki — Master Index

Last updated: 2026-04-11
Total pages: 15

---

## Regulations

| Page | Summary |
|---|---|
| [regulations/ccpa.md](regulations/ccpa.md) | CCPA/CPRA — opt-out rights, GPC mandate, pixel-as-sale doctrine, fines up to $7,500/consumer |
| [regulations/gdpr.md](regulations/gdpr.md) | GDPR Articles 4/6/7 — consent definition, LI invalid for ad cookies, ePrivacy Directive |
| [regulations/us-state-laws.md](regulations/us-state-laws.md) | 20+ US state laws — GPC mandate states, 2026 amendments, fine schedule by state |
| [regulations/tcf.md](regulations/tcf.md) | IAB TCF 2.2 — TC String, Purpose 1 consent requirement, ePrivacy |
| [regulations/quebec-law25.md](regulations/quebec-law25.md) | Quebec Law 25 — strictest NA law, opt-in required, CAD 10M fines, extraterritorial |
| [regulations/pipeda.md](regulations/pipeda.md) | PIPEDA — Canadian federal floor, opt-in for sensitive data, OPC enforcement, CPPA reform dead |

---

## Concepts

| Page | Summary |
|---|---|
| [concepts/consent-mode-v2.md](concepts/consent-mode-v2.md) | GCS/GCD parameters, Basic vs Advanced Mode, 67% failure rate, March 2024 mandate |
| [concepts/gpc-signal.md](concepts/gpc-signal.md) | Sec-GPC: 1 header — mandatory opt-out in CA/CO/CT/TX/MT/OR/NJ, enforcement precedent |
| [concepts/ssgtm-risk.md](concepts/ssgtm-risk.md) | Server-side GTM consent bypass — how to detect, GPC stripping, legal liability |
| [concepts/cipa-vppa.md](concepts/cipa-vppa.md) | CIPA wiretapping litigation + VPPA video tracking — $5K/violation, 4K lawsuits in 2024 |
| [concepts/dark-patterns.md](concepts/dark-patterns.md) | Prohibited CMP UX patterns — asymmetric choice, pre-consent drops, bundled consent |
| [concepts/cmp-failures.md](concepts/cmp-failures.md) | Root causes of 67% Consent Mode failure rate — race conditions, default granted, direct pixels |

---

## Enforcement

| Page | Summary |
|---|---|
| [enforcement/gdpr-fines.md](enforcement/gdpr-fines.md) | GDPR landmark fines — Meta €1.2B, Amazon €746M, LinkedIn €310M, Google/CNIL €150M |
| [enforcement/us-enforcement.md](enforcement/us-enforcement.md) | US cases — Sephora $1.2M (GPC), Aspen Dental $18.5M (health), Epic $520M (dark patterns) |
| [enforcement/emerging-trends.md](enforcement/emerging-trends.md) | Pixel-as-sale, LI rejection, server-side bypass, health data, children's data, LLM disclosure |

---

## Technical

| Page | Summary |
|---|---|
| [technical/google-tag-gateway.md](technical/google-tag-gateway.md) | GTG vs custom SSGTM — how to distinguish compliant from non-compliant server-side setup |
| [technical/consent-mode-impact.md](technical/consent-mode-impact.md) | Data loss estimates (30–50%), ROAS impact, modeling reality (23% vs 65% promise) |
| [technical/cmp-profiles.md](technical/cmp-profiles.md) | 35+ CMP technical profiles — JS globals, cookie names, JS APIs, shadow DOM, injection values (April 2026) |
| [technical/scanner-methodology.md](technical/scanner-methodology.md) | Pre-set opted-out scan methodology, baseline vs opt-out vs GPC passes, false positive patterns, EU vs US scanner differences |

---

## Quick Reference: Audit Finding → Wiki Pages

| Audit Finding | Read These Pages |
|---|---|
| US violations / pixel fires after opt-out | ccpa → us-state-laws → gpc-signal → us-enforcement |
| GPC signal + pixel fired | gpc-signal → ccpa → us-enforcement |
| GCS=G100 in network | consent-mode-v2 → consent-mode-impact |
| GCS=G101/G110 partial opt-out | consent-mode-v2 → cmp-profiles → ccpa |
| Unknown CMP detected | cmp-profiles → cmp-failures |
| CMP JS API fails / shadow DOM | cmp-profiles → cmp-failures |
| SSGTM detected | ssgtm-risk → google-tag-gateway → emerging-trends |
| EU jurisdiction | gdpr → tcf → gdpr-fines |
| Quebec / Canada | quebec-law25 → pipeda → consent-mode-v2 |
| Canada (non-Quebec, federal floor) | pipeda → quebec-law25 → consent-mode-v2 |
| Meta/TikTok pixel violations | cipa-vppa → us-enforcement → emerging-trends |
| Health-adjacent site | cipa-vppa → emerging-trends → ccpa |
| Video content + pixels | cipa-vppa → us-enforcement |
| Dark patterns / UX issues | dark-patterns → gdpr → gdpr-fines |
| CMP failure / race condition | cmp-failures → consent-mode-v2 |
| Clean scan | consent-mode-impact → consent-mode-v2 |
| enforcement/live-fines-db.md | Live GDPR Fines DB | Live enforcement data from EnforcementTracker (3,000+ cases) | consent, fines, gdpr, enforcement |
| enforcement/us-class-actions.md | US Privacy Class Actions | Live federal dockets + FTC actions + state AG table | ccpa, cipa, vppa, ftc, class-action |
