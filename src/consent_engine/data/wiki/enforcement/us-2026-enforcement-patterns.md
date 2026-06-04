# US Privacy Enforcement Patterns, 2025-2026

tags: us, enforcement, ccpa, gpc, opt-out, vendor-governance, sensitive-data, minors
related: regulations/ccpa.md, regulations/us-state-laws.md, concepts/gpc-signal.md, concepts/dark-patterns.md
source: primary regulator releases and orders listed below
last_updated: 2026-06-03

## Why this matters

Recent US privacy enforcement has shifted from reviewing policies in isolation to testing whether privacy mechanisms actually work. Regulators are checking opt-out flows, Global Privacy Control handling, tracking pixels, contracts with advertising vendors, sensitive-context sharing, and whether companies maintain an inventory of deployed tracking technologies.

The practical takeaway for consent-engine is direct: a report should not stop at "cookies fired." It should map observed network facts to the enforcement pattern they resemble and produce a tracking-technology inventory that privacy, legal, and engineering teams can review.

## Enforcement patterns to test

| Pattern | What to test | Why it matters |
|---|---|---|
| Opt-out mechanism failure | Reject-all flow, Do Not Sell or Share link, logged-in and logged-out state | California actions against Honda, Todd Snyder, Tractor Supply, Healthline, Disney, and others focus on whether opt-outs actually suppress sale/sharing activity. |
| GPC / universal opt-out failure | `Sec-GPC: 1`, `navigator.globalPrivacyControl`, and network traffic under the signal | California, Connecticut, Colorado, Oregon, Minnesota, and other states treat universal opt-out signals as enforceable or soon-enforceable privacy choices. |
| Consent asymmetry and friction | Equal ease of accept vs reject, no verification for opt-out, no account creation requirement | Honda and Todd Snyder show that privacy UX and request mechanics can be standalone enforcement issues. |
| Vendor contract gaps | Whether ad-tech, analytics, and pixel vendors have purpose-limited CCPA contract terms | Healthline and Tractor Supply both included vendor-contract allegations, not only technical tracking allegations. |
| Sensitive-context sharing | Health, location, driving, video-viewing, financial, student, and child contexts | Healthline and GM show heightened risk when ad-tech or data-broker sharing touches sensitive context or precise location/driving data. |
| Minors and teens | Under-13, 13-15, student, game, streaming, and child-directed contexts | Jam City, Tilting Point, Roku, and related actions focus on child and teen data, affirmative opt-in, and default protections. |
| Inventory and scanning | Current list of cookies, pixels, SDKs, server-side endpoints, owners, purposes, and contracts | Tractor Supply required scanning digital properties to inventory tracking technologies. This makes inventory an enforcement artifact, not just a technical appendix. |

## Case signals

| Matter | Regulator source | Consent-engine implication |
|---|---|---|
| Honda, March 12, 2025 | CPPA decision and announcement | Flag consent asymmetry, excessive opt-out verification, and authorized-agent friction. |
| Todd Snyder, May 6, 2025 | CPPA decision and announcement | Treat broken privacy portal configuration as an enforcement issue even when a CMP exists. |
| Tractor Supply, September 30, 2025 | CPPA decision and announcement | Generate a tracking inventory and flag missing or ineffective GPC/opt-out mechanisms plus vendor contract review. |
| Healthline, July 1, 2025 | California Attorney General complaint and judgment | Flag health-context pages where advertising pixels or sale/sharing risk remain after opt-out or under GPC. |
| Joint GPC sweep, September 9, 2025 | CPPA, California AG, Colorado AG, Connecticut AG | Test GPC as its own scenario, not merely as a browser preference note. |
| Connecticut TicketNetwork, July 8, 2025 | Connecticut Attorney General settlement | Privacy notices and rights mechanisms must be readable, configured, and operable. |
| Disney, February 11, 2026 | California Attorney General settlement | Logged-in account state and cross-device opt-out propagation matter for streaming and account-based services. |
| General Motors, May 8, 2026 | California Attorney General and partners | Driving and precise-location data sold to brokers should be treated as sensitive-context sharing. |
| Jam City and Tilting Point | California Attorney General enforcement actions | App and game tracking need child and teen data controls, not only web-banner controls. |
| Minnesota MCDPA, 2025-2026 | Minnesota Attorney General guidance and updates | Universal opt-out mechanisms, sensitive data consent, and privacy-procedure warning letters are active enforcement themes. |

## Report language guardrails

Use these themes as risk mapping, not as a legal conclusion. The report should say that evidence maps to an enforcement pattern or requires review. It should not say that a company violated a statute unless the engine has deterministic evidence and the existing methodology gate classifies the finding as confirmed.

For public reports, prefer this framing:

- "Mapped enforcement pattern: GPC / universal opt-out failure."
- "Observed tracking technology likely requires sale/sharing and contract review."
- "Sensitive-context page detected. Advertising or behavioral tracking should be blocked unless a specific consent and purpose basis exists."
- "Inventory generated from scan evidence. Review quarterly and after tag releases."

Avoid this framing unless counsel has reviewed it:

- "Illegal sale."
- "Regulatory violation proven."
- "Will be fined."
- "Dark pattern confirmed."

## Primary sources

- CPPA, Honda settlement announcement, March 12, 2025: https://cppa.ca.gov/announcements/2025/20250312.html
- CPPA, Todd Snyder decision announcement, May 6, 2025: https://www.cppa.ca.gov/announcements/2025/20250506.html
- CPPA, joint GPC investigative sweep, September 9, 2025: https://cppa.ca.gov/announcements/2025/20250909.html
- CPPA, Tractor Supply decision announcement, September 30, 2025: https://cppa.ca.gov/announcements/2025/20250930.html
- California Attorney General, Healthline settlement, July 1, 2025: https://oag.ca.gov/news/press-releases/attorney-general-bonta-announces-largest-ccpa-settlement-date-secures-155
- California Attorney General, Disney settlement, February 11, 2026: https://oag.ca.gov/news/press-releases/california-wont-let-it-go-attorney-general-bonta-announces-275-million
- California Attorney General, GM location and driving data settlement, May 8, 2026: https://oag.ca.gov/node/622991
- Connecticut Attorney General, TicketNetwork settlement, July 8, 2025: https://portal.ct.gov/ag/press-releases/2025-press-releases/attorney-general-tong-announces-settlement-with-ticketnetwork
- Connecticut Attorney General, CTDPA universal opt-out guidance: https://portal.ct.gov/ag/sections/privacy/the-connecticut-data-privacy-act/
- Minnesota Attorney General, MCDPA launch guidance, July 28, 2025: https://www.ag.state.mn.us/Office/Communications/2025/07/28_MCDPA.asp
- Minnesota Attorney General, MCDPA status update, February 5, 2026: https://www.ag.state.mn.us/Office/Communications/2026/02/05_MCDPA.asp
- Florida Attorney General, Roku enforcement action, October 14, 2025: https://www.myfloridalegal.com/newsrelease/attorney-general-james-uthmeiers-office-parental-rights-files-enforcement-action
