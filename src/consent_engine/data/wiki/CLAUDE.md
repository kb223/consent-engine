# Consent Compliance Wiki — Agent Schema

## Purpose
This wiki is the knowledge base for the consent-compliance-agent. It contains synthesized regulatory, enforcement, and technical guidance that the audit agent uses to generate legally grounded compliance reports.

This is NOT a vector database. It is a structured set of markdown files. The agent navigates it by reading the index, then reading relevant pages in full.

## Directory Structure

```
data/
  raw/              ← Immutable source documents (articles, research, exports). Never modified by agent.
  regulatory/       ← Original raw regulatory docs (legacy, pre-wiki). Do not modify.
  wiki/
    CLAUDE.md       ← This file
    index.md        ← Master catalog — always read this first
    log.md          ← Append-only operation history
    regulations/    ← One page per legal framework (CCPA, GDPR, state laws, etc.)
    concepts/       ← Technical and legal concepts (GPC, Consent Mode, dark patterns, CIPA)
    enforcement/    ← Enforcement cases, fines, emerging trends
    technical/      ← Google Tag architecture, audit methodology, reporting impact
```

## How to Use This Wiki in Audit Reports

### Step 1 — Read the Index
Always read `data/wiki/index.md` first to identify which pages are relevant to the audit findings.

### Step 2 — Select Pages by Audit Context
Use these mappings to select wiki pages:

| Audit Finding | Primary Pages | Secondary Pages |
|---|---|---|
| Violations in US (any state) | `regulations/ccpa.md`, `regulations/us-state-laws.md` | `concepts/gpc-signal.md`, `enforcement/us-enforcement.md` |
| GPC signal received + pixel fired | `concepts/gpc-signal.md`, `regulations/us-state-laws.md` | `enforcement/us-enforcement.md` |
| GCS=G100/G110 in network traffic | `concepts/consent-mode-v2.md`, `technical/consent-mode-impact.md` | `regulations/ccpa.md` |
| SSGTM detected | `concepts/ssgtm-risk.md`, `technical/google-tag-gateway.md` | `enforcement/emerging-trends.md` |
| EU jurisdiction | `regulations/gdpr.md`, `regulations/tcf.md` | `enforcement/gdpr-fines.md` |
| Quebec / Canada | `regulations/quebec-law25.md`, `regulations/pipeda.md` | `concepts/consent-mode-v2.md` |
| Meta Pixel / TikTok Pixel violations | `concepts/cipa-vppa.md`, `enforcement/us-enforcement.md` | `enforcement/emerging-trends.md` |
| CMP dark patterns | `concepts/dark-patterns.md` | `regulations/gdpr.md` |
| Healthcare site | `concepts/cipa-vppa.md`, `enforcement/emerging-trends.md` | `regulations/ccpa.md` |
| Video content site | `concepts/cipa-vppa.md` | `enforcement/emerging-trends.md` |
| CMP failure / race condition | `concepts/cmp-failures.md` | `concepts/consent-mode-v2.md` |
| Clean scan (no violations) | `concepts/consent-mode-v2.md`, `technical/consent-mode-impact.md` | — |

### Step 3 — Read Selected Pages in Full
Read 2-4 pages in full. Do not skim. The pages are dense but concise — full reads provide better context than partial reads.

### Step 4 — Ground the Report in Wiki Content
Executive summaries and violation descriptions must cite specific legal frameworks, fine amounts, and enforcement cases from the wiki. Avoid generic statements. Lead with the most material legal risk.

## Adding New Sources

To ingest a new source:
1. Copy the raw file into `data/raw/` (markdown preferred; PDF text exports acceptable)
2. Read the source
3. Create or update relevant wiki pages with synthesized content
4. Update `data/wiki/index.md` with any new pages
5. Append an entry to `data/wiki/log.md`

Sources from NotebookLM exports, web clips, research PDFs, and enforcement case summaries are all valid raw inputs.

## Lint (Periodic Health Check)
Run a lint when:
- A new enforcement case is announced
- A new state privacy law takes effect
- A major Google policy change occurs

Lint checks: stale dates, missing cross-links, orphaned pages, gaps in coverage for active US states.
