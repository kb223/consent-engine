# Sample audit — `example.com`

> Captured 2026-05-18 from consent-engine v0.5.1 against `https://example.com`. Committed here so cold readers can see what a clean audit looks like before running the tool themselves.

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
uvx --refresh consent-engine audit https://example.com
```

That's the whole thing. ~30 seconds. The other 5 files are produced by the same command. The `deck.html` is auto-rendered when `npx` is on PATH.

## Why `example.com` and not a more interesting target

`example.com` is RFC 2606 reserved, has no tracking, and produces a deterministic clean-pass audit. It's the safest demo target — no risk of a future page change invalidating this sample.

For more interesting demo runs (vendor leaks, GPC ignored, multi-jurisdiction), try these on your own machine:

- `https://onetrust.com` — the CMP vendor itself; well-configured, useful baseline
- `https://canadiantire.ca` — 17 vendors, 11 confirmed violations, jurisdiction CA, OneTrust CMP
- `https://tesco.com` — UK retailer on `.com`; jurisdiction detected as EU (per the v0.5.1 fix)
- `https://apple.com` — large enterprise site, sophisticated stack

Run any of those yourself to see the violation-heavy variant.
