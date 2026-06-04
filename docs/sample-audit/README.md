# Sample audit - `ulta.com`

> Captured 2026-06-04 from consent-engine v0.6.15 against `https://www.ulta.com`.
> Committed here so cold readers can see what an audit bundle looks like before
> running the tool themselves.
>
> This is a point-in-time public-surface scan of a well-known US brand. It is
> not an endorsement, customer reference, legal conclusion, or claim about the
> brand's current production state. The audit result reports deterministic
> technical findings observed during this specific run. Public websites and
> consent configurations change frequently.
>
> This sample was selected because it exercises the strongest public-demo
> surface: OneTrust detection, post-opt-out pixels, Google Consent Mode signal
> analysis, GPC testing, tracking inventory, and enforcement-theme mapping.

## Files

| File | What it is |
|---|---|
| [`report.html`](report.html) | Full HTML forensic report. Open in a browser. This is the primary deliverable. |
| [`deck.html`](deck.html) | Rendered Marp slide deck (`deck.marp.md` → HTML via `@marp-team/marp-cli`). Open in a browser. |
| [`deck.marp.md`](deck.marp.md) | Marp markdown source for the deck. |
| [`audit_result.json`](audit_result.json) | Structured audit data. Pydantic-validated. |
| [`evidence.jsonl`](evidence.jsonl) | Per-request forensic log. One JSON object per line: `{url, method, timestamp, status_code, request_type, initiator}`. |
| [`executive_summary.md`](executive_summary.md) | Deterministic template summary (no LLM key set during sample run). |

## Live

- https://kb223.github.io/consent-engine/sample-audit/report.html
- https://kb223.github.io/consent-engine/sample-audit/deck.html

## How this was generated

```sh
uvx --refresh consent-engine audit https://www.ulta.com
```

The other bundle files are produced by the same command. The `deck.html` file
is auto-rendered when `npx` is on PATH.

## What this sample shows

- Jurisdiction detection: `US`
- CMP detection: `OneTrust`
- Methodology: `s3_consent_wiring_broken`
- Google Consent Mode state after opt-out: `G111`
- Findings: `37`
- Confirmed technical findings: `34`
- Pixel endpoints observed after opt-out: `27`
- Tracking inventory rows: `55`
- GPC result: not respected in this run; baseline pixel activity moved from `27` to `25`
- sGTM: not detected

Public websites change frequently. Re-running the command later may produce a
different inventory, methodology result, or evidence set.

## Try another public target

Run your own scan when you need current evidence. Good comparison targets:

- `https://onetrust.com` - CMP vendor baseline
- `https://www.kohls.com` - OneTrust site with high inventory output in the June 2026 batch
- `https://www.lowes.com` - TrustArc site with high pixel and inventory output in the June 2026 batch
