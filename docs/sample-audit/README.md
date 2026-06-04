# Sample audit - `apple.com`

> Captured 2026-06-04 from consent-engine v0.6.14 against `https://www.apple.com`.
> Committed here so cold readers can see what an audit bundle looks like before
> running the tool themselves.
>
> This is a point-in-time public-surface scan of a well-known US brand. It is
> not an endorsement, customer reference, legal conclusion, or claim that Apple
> has a confirmed consent violation. The audit result reports zero confirmed
> violations and two findings that require further investigation because the CMP
> opt-out state could not be independently verified.
>
> The v0.6.14 `tracking_inventory` and `enforcement_themes` fields are populated
> in `audit_result.json`, so this sample shows the inventory and enforcement-map
> output added in the current release.

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
uvx --refresh consent-engine audit https://www.apple.com
```

The other bundle files are produced by the same command. The `deck.html` file
is auto-rendered when `npx` is on PATH.

## What this sample shows

- Jurisdiction detection: `US`
- Methodology: `s3_inconclusive_unknown_cmp`
- Findings: `2`, both `requires_further_investigation`
- Confirmed violations: `0`
- Tracking inventory rows: `2`
- GPC result: inconclusive because baseline pixel count was `0`

Public websites change frequently. Re-running the command later may produce a
different inventory, methodology result, or evidence set.

## Try another public target

Run your own scan when you need current evidence. Good comparison targets:

- `https://onetrust.com` - CMP vendor baseline
- `https://www.ibm.com` - large enterprise site with broader inventory output
- `https://www.apple.com` - the sample target committed here
