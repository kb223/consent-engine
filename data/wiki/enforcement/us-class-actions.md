# US Privacy Enforcement — Live Database

tags: ccpa, ftc, cipa, vppa, class-action, us-enforcement, live-data
source: CourtListener REST API + FTC RSS
last_updated: 2026-04-22
total_cases: 0
related: [[enforcement/us-enforcement]], [[regulations/ccpa]], [[concepts/cipa-vppa]], [[concepts/gpc-signal]]

## Overview

Live US privacy enforcement data from federal court dockets (CourtListener) and FTC press releases.
Covers CCPA, CIPA (California wiretap), VPPA, COPPA, and FTC Act privacy enforcement actions.
Last refreshed: 2026-04-22.

---

## Key Enforcement Principles (Always Cite First)

These are established by settled cases — use these in every US audit report:

| Principle | Case | Amount | Statute |
|---|---|---|---|
| GPC = mandatory opt-out, pixel data = "sale" | Sephora (CA AG, 2022) | $1.2M | CCPA/CPRA |
| Health data + ad pixels = maximum exposure | Aspen Dental (FTC/state AGs) | $18.5M | CMIA + CCPA |
| COPPA: default-on data collection for minors | Epic/Fortnite (FTC, 2022) | $275M | COPPA |
| Dark UX patterns carry FTC enforcement risk | Epic/Fortnite (FTC, 2022) | $245M | FTC Act |
| Pixel-as-sale: no money needed to be a "sale" | Multiple CA AG actions | Varies | CCPA §1798.140(t) |
| CIPA §631: recording web sessions = wiretap | Multiple district courts | $5K/violation | CIPA |
| VPPA: pixel shares video viewing = violation | Pending — circuit split | Class exposure | VPPA |

---

## Fine Exposure Reference (US)

| Statute | Fine / Damages | Basis | Private Right of Action? |
|---|---|---|---|
| CCPA/CPRA | $2,500 (unintentional) / $7,500 (intentional) per violation | Per consumer | Yes (data breach only) |
| CPRA §1798.100 | $7,500 per intentional violation | Per consumer | AG enforcement |
| CIPA §631 | $5,000 per violation | Per incident | Yes — no actual damages required |
| CIPA §632.7 | $5,000 per violation | Per call/session | Yes |
| VPPA | $2,500 per violation | Per disclosure | Yes — no actual damages required |
| COPPA | $51,744 per violation | Per child | FTC enforcement only |
| FTC Act §5 | Up to $51,744/day | Per day of violation | FTC enforcement only |
| BIPA (Illinois) | $1,000 (negligent) / $5,000 (intentional) | Per violation | Yes — largest class exposure |

---

## Federal Privacy Class Actions (CourtListener, 0 cases)

| Case Name | Court | Filed | Cause / Nature |
|---|---|---|---|

---

## Recent Privacy Enforcement News

Sourced from FTC press releases RSS, California AG RSS, and IAPP News RSS.

| Source | Title | Date |
|---|---|---|
| CA AG | Attorney General Bonta Opposes Federal Effort to Strip Housing Support for  | Tue, 21 Apr 2026 |
| CA AG | Attorney General Bonta Opposes EPA’s Proposed Emission Standards for Marine | Tue, 21 Apr 2026 |
| CA AG | Attorney General Bonta Continues Opposition to Trump Administration’s Manda | Tue, 21 Apr 2026 |
| CA AG | Attorney General Bonta: California Hits Historic Lows for Gun Violence, Our | Tue, 21 Apr 2026 |
| CA AG | Attorney General Bonta Files Lawsuit Against City of Poway over CEQA Violat | Mon, 20 Apr 2026 |
| CA AG | Naming Names: Attorney General Bonta Secures Public Access to Evidence in A | Mon, 20 Apr 2026 |
| CA AG | Attorney General Bonta Secures Important Victory in Lawsuit Challenging HUD | Mon, 20 Apr 2026 |
| CA AG | Supporting Healthier Communities: Attorney General Bonta Announces 2026–202 | Mon, 20 Apr 2026 |
| CA AG | Attorney General Bonta Secures Critical Win in Nexstar/Tegna Merger Challen | Fri, 17 Apr 2026 |
| CA AG | Attorney General Bonta Warns Californians About Hidden Risks of Deferred-In | Fri, 17 Apr 2026 |

---

## State-Level Enforcement Highlights

These are manually curated — no structured state-level API exists.
Update this section when new state AG settlements are announced.

| State | Case | Year | Amount | Statute | Key Principle |
|---|---|---|---|---|---|
| California | Sephora | 2022 | $1.2M | CCPA/CPRA | First CCPA action; GPC is binding opt-out |
| California | Tillamook Creamery | 2022 | Settlement | CCPA | GPC applies to mid-market brands |
| California | DoorDash | 2024 | $375K | CCPA | Sharing consumer data via marketing co-op = "sale" |
| Texas | Google | 2024 | $1.375B | DTPA/CUBI/biometric | Location tracking + biometric data without consent |
| Indiana | Meta | 2023 | $270M | Consumer protection | Misleading privacy representations |
| Multi-state | Google/Geofencing | 2022 | $391.5M | State AG (40 states) | Location data retained after opt-out |
| Multi-state | T-Mobile | 2022 | $350M | State AG (various) | Data breach + inadequate security |
| Illinois | Facebook | 2021 | $650M | BIPA | Facial recognition without consent |

---

## Highest-Risk Fact Patterns (Audit Report Triggers)

When these patterns appear in a scan, cite these cases:

**Meta/Facebook Pixel on health-adjacent site:**
→ Aspen Dental ($18.5M), Disney/Hulu class actions, HIPAA-adjacent exposure

**TikTok Pixel firing post-decline:**
→ TikTok GDPR €345M (children's data), CCPA pixel-as-sale doctrine, CIPA wiretap theory

**Session recorder (FullStory, Hotjar, Clarity) loading pre-consent:**
→ CIPA §631(a) wiretap theory, Javier v. Assurance IQ precedent

**GPC signal not honored:**
→ Sephora $1.2M (first CCPA action, GPC as lead violation), immediately enforceable under CPRA

**LinkedIn Insight Tag on EU-facing site:**
→ LinkedIn €310M (legitimate interest rejected for behavioral advertising)

---

## Refresh

Run `uv run python scripts/ingest_us_enforcement.py` to refresh from CourtListener + FTC RSS.
State-level entries above require manual updates from AG press release monitoring.
