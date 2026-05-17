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

## Cases on the roadmap

- [ ] 001 — OneTrust + Advanced Consent Mode, clean SaaS marketing site
- [ ] 002 — Meta Pixel firing post-reject (the lawsuit scenario)
- [ ] 003 — Server-side GTM bypass (architectural gap)
- [ ] 004 — Multiple CMPs on the same page (rare but disruptive)
- [ ] 005 — Consent Mode set to Basic (cookies blocked entirely)
- [ ] 006 — Page with no CMP at all (Tier-1 finding)
- [ ] 007 — GPC respected
- [ ] 008 — GPC ignored
- [ ] 009 — Healthcare URL with Meta Pixel (HIPAA-adjacent)
- [ ] 010 — Video-page tracking (VPPA)
- [ ] 011 — Out-of-GTM pixel (hard-coded `<head>` script)
- [ ] 012 — AI-browser request (`Sec-GPC: 1`, Arc / Comet / Perplexity UA)
