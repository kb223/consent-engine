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

The eight-tool pipeline below is all deterministic.

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
# Note the [mcp] extra — the MCP SDK is an optional dependency.
uvx --from 'consent-engine[mcp]' consent-engine-mcp
```

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "consent-engine": {
      "command": "uvx",
      "args": ["--from", "consent-engine[mcp]", "consent-engine-mcp"]
    }
  }
}
```

Exposes `audit_url`, `read_audit_result`, and `query_evidence` as MCP tools.

### 4. FastAPI service

The `/audit` endpoint requires a bearer token. It returns `503` until you set
`CONSENT_ENGINE_API_TOKEN` (this is deliberate — it refuses to run an
unauthenticated public audit endpoint).

```sh
docker build -t consent-engine .
docker run -p 8080:8080 -e CONSENT_ENGINE_API_TOKEN=your-secret-token consent-engine

# Then call it with the token:
curl -X POST http://localhost:8080/audit \
  -H "Authorization: Bearer your-secret-token" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

Drop-in Cloud Run / Fly / Railway deployable. Set `CONSENT_ENGINE_API_TOKEN`
as a secret in your platform's environment config.

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

## See a finished audit before running

A committed sample audit lives at [`docs/sample-audit/`](docs/sample-audit/) — open `report.html` and `deck.html` in a browser to see what the tool produces without installing it first.

Once GitHub Pages is enabled for this repo, the live demo URLs are:
- https://kb223.github.io/consent-engine/sample-audit/report.html
- https://kb223.github.io/consent-engine/sample-audit/deck.html

## Release artifacts

[`docs/release-v0.5.0/`](docs/release-v0.5.0/) is the auditable record behind every v0.5.0 release claim: security audit punch list, dependency CVE scan, type-coverage rationale, end-to-end smoke test, jurisdiction-detection validation matrix. Read it before evaluating the release quality.

## Optional: unlock LLM-written executive summaries

By default, consent-engine ships with the LLM call **disabled**. The audit
runs the full deterministic pipeline (scan → classify → wiki retrieval → HTML
report + Marp deck) and writes a templated executive summary that's
hand-tuned to be readable. No LLM, no API keys, no LiteLLM provider-probe
warnings on stderr. This is the OSS-shipping default.

If you want the LLM-written prose summary instead — slightly sharper framing,
adapted per-audit to the actual findings + wiki citations — set **any one** of
these env vars before running:

```sh
# Gemini direct (recommended — generous free tier, simple auth)
export GEMINI_API_KEY="..."

# OR Anthropic (best at legal/compliance nuance)
export ANTHROPIC_API_KEY="..."

# OR OpenAI
export OPENAI_API_KEY="..."

# OR Vertex AI (requires a GCP service-account JSON)
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/sa.json"
```

The engine uses [LiteLLM](https://github.com/BerriAI/litellm) under the hood
to route to whatever provider you've configured — no SDK swap required. The
default model targets are `gemini/gemini-2.5-pro` (audit) and
`gemini/gemini-2.5-flash` (executive summary classification), but you can
override either via the `default_audit_model` / `default_classify_model`
fields on `consent_engine.config.Settings`. Or just set
`LITELLM_LOG=ERROR` and pick any model string LiteLLM understands.

The audit pipeline always falls back to the deterministic template if the
LLM call fails for any reason — so if your key is rate-limited or invalid,
the audit still completes cleanly.

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

- **Add a new CMP**: the system ships with **35+ CMP detectors** out of the
  box (OneTrust, Truyo, Cookiebot, CookieYes, Usercentrics, Didomi, TrustArc,
  Ketch, Sourcepoint, Quantcast, Osano, Axeptio, Klaro, CookieScript,
  CookieHub, Crownpeak, TrustCommander, Termly, Complianz, TrueVault,
  iubenda, Borlabs, Civic, Consentmanager, Shopify Customer Privacy,
  Pandectes, PiwikPRO, Transcend, Ensighten, DataGrail, CCM19, Wix,
  CookieInformation, CookieReports, Real Cookie Banner, plus IAB TCF +
  GPC/GPP). Add a new one by dropping a detector in
  `src/consent_engine/tools/cmp_detector.py` (JS-global, URL-pattern, and
  DOM-selector tiers) and a regional behavior profile in `data/wiki/concepts/`.
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

Architecture credit to **Fred Pike** (Northwoods) for the agentic-vs-
deterministic split + the glass-box reporting pattern, and to **Phil Pearce**
for the 67%-of-Consent-Mode-v2-implementations-fail-basic-compliance
baseline. Both presented at MeasureSummit, May 2026.

The Open Cookie Database (~3,200 entries) is included under the project's
permissive license.
