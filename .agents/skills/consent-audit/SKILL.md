---
name: consent-audit
description: Run a forensic consent-compliance audit on a URL. Use whenever the user asks to audit, check, or scan a website for consent / cookie / CMP / CCPA / GDPR / privacy compliance. Captures every network request, classifies violations against the lawsuit-surge wiki, produces an HTML report + Marp deck + JSON audit result + evidence log.
---

# consent-audit

A Codex skill that drives the `consent-engine` Python package to run a
forensic consent-compliance audit and explain the results.

## When to invoke

Any of these:
- "Audit https://example.com for consent compliance"
- "Run a consent check on <url>"
- "Why is <vendor> firing on <url> after reject?"
- "Is this site CCPA / GDPR compliant?"
- "Generate a forensic report for this site"

## How to run it

```bash
uvx consent-engine audit <url> --output-dir ./consent-audits
```

Output bundle: `./consent-audits/<audit_id>/`
- `report.html` — full forensic report with network evidence, vendor
  lookups, legal exposure estimates, and remediation roadmap
- `audit_result.json` — structured Pydantic model
- `evidence.jsonl` — every captured network request (timestamped)
- `deck.marp.md` — client-ready slide deck

## Interpreting findings

| Severity | What to do |
|---|---|
| **Definitive violation (S3)** | Tag fired after explicit reject. Quote the audit_id, evidence line, and legal exposure ($7,500 CCPA, $5,000 CIPA per event). Remediate this week. |
| **Server-side bypass** | sSGTM detected in front of analytics. Client-side enforcement cannot block it. Architectural risk. Brief engineering. |
| **Inconclusive (S2)** | Tag fired in ambiguous consent state. Re-run with S3 methodology before reporting. |
| **Warning** | Configuration drift, deprecated tags, or compliance edge cases. Track. |

## Follow-up questions to support

- "Why did <vendor> fire?" → call the `consent-engine-mcp` `query_evidence`
  tool with `host_contains` set, or grep `evidence.jsonl` directly.
- "What's the financial exposure?" → read the `legal_exposure` block in
  `audit_result.json`.
- "How do I remediate?" → read the `remediation` section in `report.html`
  and cross-reference `data/wiki/technical/` pages.

## Thorough audit sequence

For high-stakes audits (regulated industry, healthcare, post-demand-letter):

1. Audit with consent in **reject** (default S3 methodology).
2. Audit with consent in **accept** — confirms the CMP toggles tags as
   expected.
3. Audit with GPC set (`Sec-GPC: 1`) — confirms Global Privacy Control
   honored.
4. Re-audit weekly for 90 days post-remediation. Drift is real.

## Source

[github.com/kb223/consent-engine](https://github.com/kb223/consent-engine).
MIT license. Built by Kenneth Buchanan.
