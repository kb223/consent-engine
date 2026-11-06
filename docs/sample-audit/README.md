# Sample audit - anonymized US fashion retailer

> Captured 2026-11-05 from consent-engine v0.6.17 against a real US fashion
> retailer's public site. Committed here so cold readers can see what an audit
> bundle looks like before running the tool themselves.
>
> The site is anonymized. Its domain appears as `www.retailer.example`, and store,
> account and pixel identifiers are removed. Query strings, first-party URL paths
> and raw POST bodies are stripped from the evidence, so the evidence log shows
> which hosts were contacted but can't be replayed. The report and deck were
> regenerated from the anonymized data.
>
> This is a point-in-time technical scan, not a legal conclusion or a claim about
> any company's current production state. It ran from outside the US, with the
> opt-out state set by the scanner rather than by clicking a banner. Sites can
> behave differently by location, and public sites change often.
>
> This sample shows the definitive `s3_consent_wiring_broken` path: Google Consent
> Mode stayed in a `G111` granted state after opt-out, pixels fired, and GPC
> testing, tracking inventory and enforcement-theme mapping are all populated.

## Files

| File | What it is |
|---|---|
| [`report.html`](report.html) | Full HTML forensic report. Open in a browser. This is the primary deliverable. |
| [`deck.html`](deck.html) | Rendered Marp slide deck (`deck.marp.md` → HTML via `@marp-team/marp-cli`). Open in a browser. |
| [`deck.marp.md`](deck.marp.md) | Marp markdown source for the deck. |
| [`audit_result.json`](audit_result.json) | Structured audit data. Pydantic-validated. |
| [`evidence.jsonl`](evidence.jsonl) | Per-request forensic log. One JSON object per line: `{url, method, timestamp, status_code, request_type, initiator}`. |
| [`executive_summary.md`](executive_summary.md) | Deterministic template summary (no LLM involved). |

## Live

- https://kb223.github.io/consent-engine/sample-audit/report.html
- https://kb223.github.io/consent-engine/sample-audit/deck.html

## How this was generated

```sh
uvx --refresh consent-engine audit https://www.example.com
```

The raw output was then anonymized as described above, and the report and deck
were regenerated from the anonymized data. The `deck.html` file is auto-rendered
when `npx` is on PATH.

## What this sample shows

- Jurisdiction detection: `US`
- CMP detection: `Shopify`
- Methodology: `s3_consent_wiring_broken`
- Google Consent Mode state after opt-out: `G111`
- Findings: `10`
- Confirmed technical findings: `7`
- Pixel endpoints observed after opt-out: `8`
- Tracking inventory rows: `18`
- GPC result: not respected in this run; pixel activity moved from `9` to `4`
- sGTM: detected

Run your own scan when you need current evidence. Results change as sites change.
