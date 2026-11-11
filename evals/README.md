# Evaluation harness

> Goal: prove the audit engine is reliable enough to put a name on. Fred
> Pike's MeasureSummit slide: "Claude will not write a deterministic system
> of this complexity by itself. Human verification is mandatory." This is
> the human verification.

## Structure

```
evals/
├── cases/
│   ├── 001-onetrust-clean.yaml          # site that should pass
│   ├── 002-meta-pixel-post-reject.yaml  # known violation
│   ├── 003-ssgtm-bypass.yaml            # architectural gap
│   └── ...
├── run_evals.py                         # the runner
└── README.md                            # this file
```

Each case YAML defines:

```yaml
name: "OneTrust + Advanced Consent Mode, clean"
url: "https://example-clean-site.com"
expected:
  violations_count: 0
  has_definitive_findings: false
  cmp_detected: onetrust
  consent_mode_state: "advanced"
  notes: |
    Audit run with C0001 only. No tags should fire post-reject.
```

## Running

```sh
uv run python evals/run_evals.py
```

Output: per-case pass/fail, latency p50/p95, $ per audit (LLM tokens),
and a roll-up that goes into the README badge.

## Adding cases

1. Find a site that exhibits the pattern you want to test (clean,
   violating, edge case).
2. Capture the expected outcome.
3. Write the YAML.
4. Run `python evals/run_evals.py --add-baseline cases/NNN-<slug>.yaml`
   to populate the baseline `expected:` block from the current behavior.
5. Commit. CI re-runs the suite on every PR.

## Target

- **Definitive-violation detection**: 100% recall on the curated case set
  (we cannot afford false negatives — that's the lawsuit).
- **False-positive rate**: < 5% on clean sites.
- **Latency p95**: < 30s per audit.
- **Cost p95**: < $0.10 per audit (LLM tokens for executive summary).

## Seeded cases

- [x] 001 — OneTrust marketing site (definitive violations expected; Fred Pike's MeasureSummit demo)
- [x] 002 — Anthropic marketing site (should mostly pass)
- [x] 003 — example.com (negative control, must report zero violations)
- [x] 004 — Cresta marketing site (B2B SaaS breadth case)

## On the roadmap (add as you encounter them)

- [ ] 005 — Meta Pixel firing post-reject (the lawsuit scenario)
- [ ] 006 — Server-side GTM bypass (architectural gap)
- [ ] 007 — Multiple CMPs on the same page (rare but disruptive)
- [ ] 008 — Consent Mode set to Basic (cookies blocked entirely)
- [ ] 009 — Page with no CMP at all (Tier-1 finding)
- [ ] 010 — GPC respected vs ignored (paired case)
- [ ] 011 — Healthcare URL with Meta Pixel (HIPAA-adjacent)
- [ ] 012 — Video-page tracking (VPPA)
- [ ] 013 — Out-of-GTM pixel (hard-coded `<head>` script)
- [ ] 014 — AI-browser request (`Sec-GPC: 1`, Arc / Comet / Perplexity UA)

## Offline fixtures

`freeze_fixture.py` turns saved audits into offline fixtures with stable request
IDs. Fixtures hold real scan data, so `evals/fixtures/` is gitignored. Never
commit it.

```bash
uv run python evals/freeze_fixture.py freeze --selection evals/fixtures/selection.tsv
uv run python evals/freeze_fixture.py check
uv run python evals/freeze_fixture.py labels --cap 9
```

`labels` won't overwrite an existing sheet, so hand labels stay safe.

## Fixture tools

`fixture_tools.py` gives an agent read-only access to one fixture. It holds the
tool definitions (`TOOLS`) and the functions behind them, and it never calls a
model.

| Tool | Returns |
|---|---|
| `list_findings` | Finding IDs, vendors, engine status |
| `get_finding` | One finding and its linked request IDs |
| `query_evidence` | Saved requests matching a URL or host filter |
| `get_request` | One request with its full URL |
| `lookup_vendor` | Category, exposure, request domains |
| `lookup_enforcement_pattern` | How a pattern was mapped for this audit |

Every result has a `status`, so "nothing matched" (`no_match`) stays separate
from `scan_failed`, `evidence_unavailable`, `not_checked` and `not_mapped`.

```python
fixture = load_fixture("fx-01")
block = tool_result_block(fixture, tool_use.id, tool_use.name, tool_use.input)
```

`finding_schema.py` holds `FINDINGS_SCHEMA`, the JSON shape an agent returns. It
guarantees shape only. Whether a cited request exists is an eval check.

## Investigator agent

`investigate.py` runs the agent on a fixture. It calls the Claude API, so it
needs credentials and costs money.

```bash
uv run python evals/investigate.py fx-01
uv run python evals/investigate.py --all --model claude-sonnet-5-5 --runs 3
```

Results go to `out/investigator/<model>/<fixture>.run<n>.json`, which is
gitignored. Each result records the outcome, the tool calls, the full
transcript, token usage and an estimated cost.

## Scorecard

`score.py` scores saved runs. It is offline and free to run.

```bash
uv run python evals/score.py out/investigator/claude-opus-5-5
```

| Section | Needs labels | Fails the run |
|---|---|---|
| Evidence checks: coverage, real and returned citations, cited strong verdicts | No | Yes |
| Reported checks: non-citable requests, unknown cookies, escalation, blocked wording | No | No |
| Verdict stability across repeated runs | No | No |
| Agreement, false positives, escalation accuracy | Yes | No |

A run that didn't complete is counted as not scored. The command exits non-zero
if any run failed an evidence check or didn't complete. Label metrics are
skipped until `evals/fixtures/labels.csv` has verdicts in it.
