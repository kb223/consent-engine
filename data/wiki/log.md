# Wiki Operation Log

Format: `## [YYYY-MM-DD] operation | description`

---

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
