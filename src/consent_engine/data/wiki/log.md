# Wiki Operation Log

Format: `## [YYYY-MM-DD] operation | description`

---

## [2026-05-18] verify | ACM cookie behavior re-checked against Google official docs

Triggered by Kenneth's pushback on whether cookies-in-anonymous-state under
Advanced Consent Mode count as a violation. Fact-checked via WebSearch
against the official Google sources listed below; all five confirmed the
"no cookies written when consent denied" rule that the scanner's classifier
relies on.

Sources cross-checked (all from official Google domains):
- https://developers.google.com/tag-platform/security/concepts/consent-mode
- https://developers.google.com/tag-platform/security/guides/consent
- https://support.google.com/analytics/answer/13802165 (Consent mode reference)
- https://support.google.com/analytics/answer/10000067 (About consent mode)
- https://support.google.com/google-ads/answer/13802165 (Consent mode reference – Ads)

Page updated: `concepts/consent-mode-v2.md` — added a *Source Verification*
section with direct quotes mapped to each load-bearing claim, and a
*Scanner classifier implication* paragraph explaining why `_ga` + GCS=G100
on a fresh-context scan is a real config error (not "ACM working as
designed").

Outcome: scanner classification stands. Wiki is now the auditable record.

## [2026-04-08] ingest | Initial wiki build — 9 regulatory source docs

Sources ingested from `data/regulatory/`:
- ccpa-opt-out.md → regulations/ccpa.md
- gdpr-consent.md → regulations/gdpr.md
- us-state-privacy-laws.md → regulations/us-state-laws.md
- tcf-overview.md → regulations/tcf.md
- google-consent-mode.md → concepts/consent-mode-v2.md
- google-tag-gateway.md → technical/google-tag-gateway.md
- consent-mode-reporting-impact.md → technical/consent-mode-impact.md
- enforcement-cases.md → enforcement/gdpr-fines.md + enforcement/us-enforcement.md
- 2026-privacy-engineering-research.md → regulations/quebec-law25.md + concepts/cipa-vppa.md + concepts/cmp-failures.md + concepts/dark-patterns.md + enforcement/emerging-trends.md

Pages created: 13 wiki pages across 4 categories
Tool 7 (RAG retriever) replaced with wiki file reader — Pinecone dependency removed

## 2026-04-09 — EnforcementTracker ingest
- Records fetched: 3,074
- Consent-related: 1,229
- Output: enforcement/live-fines-db.md
- Source: https://www.enforcementtracker.com/data4sfk3j4hwe324kjhfdwe.json

## 2026-04-09 — US enforcement ingest
- CourtListener cases: 0
- FTC press release items: 0
- Output: enforcement/us-class-actions.md

## 2026-04-09 — US enforcement ingest
- CourtListener cases: 0
- FTC press release items: 0
- Output: enforcement/us-class-actions.md

## 2026-04-09 — US enforcement ingest
- CourtListener cases: 0
- News items (FTC + CA AG + IAPP): 10
- Output: enforcement/us-class-actions.md

## 2026-04-09 — US enforcement ingest
- CourtListener cases: 0
- News items (FTC + CA AG + IAPP): 10
- Output: enforcement/us-class-actions.md

## 2026-04-22 — US enforcement ingest
- CourtListener cases: 0
- News items (FTC + CA AG + IAPP): 10
- Output: enforcement/us-class-actions.md

## 2026-04-22 — EnforcementTracker ingest
- Records fetched: 3,082
- Consent-related: 1,234
- Output: enforcement/live-fines-db.md
- Source: https://www.enforcementtracker.com/data4sfk3j4hwe324kjhfdwe.json
