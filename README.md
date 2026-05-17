# consent-engine

> Forensic agent that compares cookie + tag enforcement against user consent
> preferences. Built for enterprises facing privacy-litigation demand letters.

[![CI](https://github.com/kb223/consent-engine/actions/workflows/ci.yml/badge.svg)](https://github.com/kb223/consent-engine/actions/workflows/ci.yml)
![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue)
![MIT License](https://img.shields.io/badge/license-MIT-green)

Scans any web page with consent pre-set to **reject all** (S3 forensic
methodology), captures every network request, then asks five questions:

1. What fires pre-consent (on landing)?
2. What fires post-accept?
3. What fires post-reject?
4. Is GPC (Global Privacy Control) being honored?
5. Is Consent Mode (Basic or Advanced) wired correctly?

Returns a structured audit result, an HTML report, an executive summary, and
a client-ready Marp slide deck.

## Why "engine" not "agent"

The audit is **deterministic**. Decisions are made at build time, not at
runtime. The LLM writes the executive summary; everything else is code.
That distinction (credit to [Fred Pike's "Consent Chaos" talk at MeasureSummit
May 2026](https://www.youtube.com/results?search_query=fred+pike+consent+chaos+measuresummit))
is the thing that makes the output legally defensible instead of
plausibly-correct.

| | Agentic | Deterministic |
|---|---|---|
| When decisions are made | At runtime | At build time |
| Behavior | Probabilistic, flexible | Reproducible |
| Spec | Implicit | Explicit |
| Testability | Hard to test, hard to prove | Easy to test, debug, verify |

The eight-tool pipeline below is all deterministic. A small agentic chat
surface (`consent-engine chat`) sits on top for "why is this tag firing"
follow-up questions, grounded in the audit result + raw network log.

## Architecture

```
        ┌──────────────────────────────────────────────────────────┐
        │                  POST /audit  { url }                    │
        └─────────────────────────────┬────────────────────────────┘
                                      ▼
   ┌──────────────────────────────────────────────────────────────────┐
   │ tool_01  GTM container parser (JSON / live network interception) │
   │ tool_02  Violation classifier (S2 inconclusive vs S3 definitive) │
   │ tool_03  Playwright browser scanner (consent pre-set)            │
   │ tool_04  HAR analyzer                                            │
   │ tool_05  Vendor library lookup (custom + Open Cookie DB)         │
   │ tool_06  Server-side GTM detector                                │
   │ tool_06b Pixel detector (out-of-GTM tracking)                    │
   │ tool_07  Knowledge-base retriever (markdown wiki, no vector DB)  │
   │ tool_08  Report + slide deck generator (LLM exec summary only)   │
   └─────────────────────────────────────┬────────────────────────────┘
                                         ▼
              ┌────────────────────────────────────────────────┐
              │  audit_result.json  +  report.html  +  deck.md │
              └────────────────────────────────────────────────┘
```

Full flow with sample inputs/outputs: see `docs/scenarios.md`.

## Three ways to run it

### 1. CLI

```sh
uvx consent-engine audit https://example.com
# Writes: ./out/<audit_id>/report.html
#         ./out/<audit_id>/audit_result.json
#         ./out/<audit_id>/evidence.jsonl   ← every captured network request
#         ./out/<audit_id>/deck.marp.md
```

Install: `pip install consent-engine` or `uvx consent-engine` (zero-install).

### 2. Claude Code skill

```sh
mkdir -p ~/.claude/skills && cp -r .claude/skills/consent-audit ~/.claude/skills/
```

Then in any Claude Code conversation:

> Audit https://example.com for consent compliance.

The skill drives the engine, surfaces findings inline, and lets you ask
follow-up questions grounded in the captured evidence.

### 3. MCP server

```sh
uvx consent-engine-mcp
# Then add to Claude Desktop config:
#   "consent-engine": { "command": "uvx", "args": ["consent-engine-mcp"] }
```

Exposes `audit_url`, `read_audit_result`, and `query_evidence` as MCP tools.

### 4. FastAPI service

```sh
docker build -t consent-engine . && docker run -p 8080:8080 consent-engine
# POST http://localhost:8080/audit { "url": "https://example.com" }
```

Drop-in Cloud Run / Fly / Railway deployable.

## Real-world stakes

This isn't an academic project. Demand-letter law firms have built a pipeline
around exactly the failure modes this tool detects:

> "We went to your website, clicked decline, and yet we saw tags firing,
> traffic going to LinkedIn, to Google Analytics, to Meta. You have violated
> our privacy. Pay us $10,000, $15,000, $25,000, $50,000." — Fred Pike,
> describing the inbound wave that drove him to build a similar tool.

CCPA fines are **$2,500 per non-intentional violation, $7,500 per intentional
violation**. CIPA (California Invasion of Privacy Act) wiretap claims are
running **$5,000 per violation** in active class actions against retailers,
healthcare systems, and B2B SaaS marketing sites. See
`data/wiki/enforcement/lawsuit-surge.md` for the case file.

## Develop

```sh
uv sync
uv run playwright install chromium

uv run pytest tests/ -v       # one happy-path test per tool
uv run ruff check src/        # lint clean
uv run mypy src/              # types clean
```

## Customize for your stack

The audit engine is configurable by data, not code:

- **Add a new CMP** (the system ships with OneTrust): drop a detector in
  `src/consent_engine/tools/cmp_detector.py` and a regional behavior profile
  in `data/wiki/concepts/`.
- **Add a vendor** to the lawsuit-annotated library:
  edit `data/vendor_library/vendors.json` (priority lookup) or the
  Open Cookie Database CSV (fallback).
- **Add jurisdictional context** (a new state, country, or sector): drop a
  markdown page in `data/wiki/regulations/` and update
  `data/wiki/index.md`.

No vector database, no embeddings, no fine-tuning. The whole knowledge layer
is markdown — version it like any other code.

## What this doesn't do

- **Does not submit anything anywhere.** It's a read-only forensic tool.
- **Does not modify your GTM container.** Use the companion
  [`gtm-ga4-sync`](https://github.com/kb223/gtm-ga4-sync) for tag provisioning.
- **Does not produce legal advice.** Outputs are evidence for legal counsel.

## License

MIT. See `LICENSE`.

## Credits

Built by [Kenneth Buchanan](https://kennethjbuchanan.com).

Architecture decisions credit Fred Pike's "Consent Chaos: Using AI to Build
Consent Systems That Still Break" at MeasureSummit, May 2026 — particularly
the agentic-vs-deterministic split, the glass-box reporting pattern, and the
per-audit chat surface. Lawsuit-surge documentation pulls from Stephanie
Balaconis (Lifesight), Denis Golubovskyi (Stape), and Phil Pearce's
MeasureSummit talks on attribution, signal quality, and the consent
enforcement landscape.

The Open Cookie Database (~3,200 entries) is included under the project's
permissive license.
