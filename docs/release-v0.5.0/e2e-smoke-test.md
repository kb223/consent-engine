# End-to-end smoke test — v0.5.0

> Run 2026-05-18 against the freshly-built v0.5.0 wheel installed in a clean Python 3.12 venv.

## Run

```sh
# Build the wheel
cd ~/Work/public-distribution/consent-engine
uv build --wheel --out-dir /tmp/ce-wheel-0.5.0

# Install into a clean venv
rm -rf /tmp/ce-venv && python3.12 -m venv /tmp/ce-venv
source /tmp/ce-venv/bin/activate
pip install --quiet /tmp/ce-wheel-0.5.0/*.whl

# Run a real audit
cd /tmp && rm -rf out
consent-engine audit https://example.com --no-open
```

## Result

```
Audit complete: out/5716dec1-2ffd-48fc-853b-818a0dc5de90
  Report:    out/5716dec1-2ffd-48fc-853b-818a0dc5de90/report.html
  Deck:      out/5716dec1-2ffd-48fc-853b-818a0dc5de90/deck.marp.md
  Evidence:  out/5716dec1-2ffd-48fc-853b-818a0dc5de90/evidence.jsonl
  Findings:  1 vendor (0 confirmed violations)
  GPC:       inconclusive (baseline 0 pixels → 0 under GPC)
  Deck HTML: out/5716dec1-2ffd-48fc-853b-818a0dc5de90/deck.html
```

Exit code: 0. Time: ~28 seconds (cold first-run includes Playwright Chromium check). All 6 expected artifacts present:

- `report.html` (35.1 KB) — full forensic report
- `audit_result.json` (1.8 KB) — structured audit data
- `evidence.jsonl` (169 B) — structured per-request log (v0.4.0+)
- `deck.marp.md` (23.8 KB) — Marp slide source
- `executive_summary.md` (119 B) — deterministic template summary (no LLM key set, v0.4.2 fallback)
- `deck.html` (180 KB) — auto-rendered via `@marp-team/marp-cli`

## Structured evidence verification

First row of `evidence.jsonl`:

```json
{"url": "https://example.com/", "method": "GET", "timestamp": "2026-05-18T...", "status_code": 200, "request_type": "document", "initiator": "about:blank"}
```

Confirms the v0.4.0 structured-evidence schema (timestamp + method + status + initiator + type) is shipping in v0.5.0 with no regression.

## Side checks

| Check | Result |
|---|---|
| `consent-engine version` | `consent-engine 0.5.0` |
| `grep -c "data:image" deck.marp.md` | ≥ 1 (brand-logo auto-grab from v0.3.x active) |
| `report.html` parses via Python's `html.parser` | clean |
| No LiteLLM provider-probe warnings on stderr | confirmed (v0.4.1 silenced) |
| No traceback noise on stdout | confirmed |
| Auto-open in default browser | macOS `open` invoked (skipped via `--no-open` for headless CI smoke; manually verified in interactive mode) |

## SSRF guard live-test

```sh
consent-engine audit http://localhost:6379/
# ValueError: Refusing to scan internal/private IP 127.0.0.1 (for host 'localhost').
#             Set CONSENT_ENGINE_ALLOW_INTERNAL=1 to override.

consent-engine audit http://169.254.169.254/
# ValueError: Refusing to scan known cloud-metadata host: 169.254.169.254. ...

consent-engine audit file:///etc/passwd
# ValueError: Only http/https URLs allowed; got scheme 'file'. ...
```

All three rejected with actionable `ValueError`. SSRF guard from H1 is live and effective.

## CI parity

The `release.yml` workflow's `test` job runs the same `uv run pytest` against the same Python 3.12 + Playwright Chromium environment. The smoke test above is the human-readable equivalent of what the CI gate validates before publishing to PyPI.

## Reproducing

The full command sequence at the top of this document is copy-pasteable. Any reviewer can verify in under 5 minutes (3 min for the Playwright Chromium download, ~30s for the audit itself).
