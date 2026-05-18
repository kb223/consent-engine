# Handoff brief — consent-engine, May 2026

> Hi Claude Code. The Cowork-Claude session that built this repo can't
> actually run it (sandboxed Linux, no Playwright Chromium, Python 3.10).
> That's why five releases have shipped with runtime bugs Cowork-Claude
> "verified" without ever executing an audit. **You can actually run it.
> Please do — for real, end-to-end — before tagging another release.**
>
> Kenneth's voice: no emojis, no em dashes, no "passionate" / "thrilled" /
> superlatives. Read `CLAUDE.md` in this repo for project context. Read
> `~/Work/CLAUDE.md` for broader operating rules (RSC vs Bounteous,
> publishing posture, etc.).

## Repo state

- GitHub: <https://github.com/kb223/consent-engine> (public, MIT)
- PyPI: <https://pypi.org/project/consent-engine/> (Trusted Publishing
  configured; tag push → auto-publish via `.github/workflows/release.yml`)
- Versions published so far (all broken in different ways):
  - 0.1.0 — initial; CLI called a fictional `classify()` function
  - 0.1.1 — fix #1; crashed because Playwright Chromium wasn't installed
  - 0.1.2 — fix #2; auto-install Chromium; bundle data files not yet fixed
  - 0.1.3 — fix #3 attempt; path-fix Edit calls silently failed; "verified"
    by checking path math instead of installed code (don't trust verification
    summaries without an actual run)
  - 0.1.4 — fix #3 for real; now hits the bug below
- Author email on commits: `kennethbuchanan@outlook.com`
- One-time PyPI Trusted Publisher setup is already done by Kenneth

## The bug to fix (paste from Kenneth, 2026-05-17)

```
$ uvx --refresh consent-engine audit https://www.onetrust.com/
Scanning https://www.onetrust.com/ (this takes ~30s)…
Traceback (most recent call last):
  File ".../consent_engine/cli.py", line 46, in _audit_command
    f.write(json.dumps(req.model_dump(mode="json"), default=str) + "\n")
                       ^^^^^^^^^^^^^^
AttributeError: 'str' object has no attribute 'model_dump'
```

Root cause: `ScanResult.network_requests` is declared as `list[str]` in
`src/consent_engine/models/scan_result.py`:

```python
class ScanResult(BaseModel):
    network_requests: list[str] = []  # All request URLs observed during scan
```

Three call sites assume Pydantic objects and call `.model_dump()` on each
list item:

- `src/consent_engine/cli.py::_audit_command`
- `src/consent_engine/api.py::audit`
- `src/consent_engine/mcp_server.py::_audit_url`

Look for the pattern:

```python
with (audit_dir / "evidence.jsonl").open("w") as f:
    for req in bundle.scan_result.network_requests:
        f.write(json.dumps(req.model_dump(mode="json"), default=str) + "\n")
```

## Two paths

### Tactical fix (recommended for v0.1.5 tonight)

Treat each URL string as a single field in a JSONL row:

```python
with (audit_dir / "evidence.jsonl").open("w") as f:
    for url in bundle.scan_result.network_requests:
        f.write(json.dumps({"url": url}) + "\n")
```

Three places. Bump version to 0.1.5 in `src/consent_engine/__init__.py` and
`pyproject.toml`. Update `CHANGELOG.md`. Run the wheel smoke test (see
below). Commit, tag, push.

### Architectural fix (for v0.2.0 later)

The README markets the evidence log as "every captured network request,
timestamped, queryable". Right now it's a flat list of URL strings — much
less rich than promised.

Extend the scanner to capture structured request data. Suggested model:

```python
class NetworkRequest(BaseModel):
    url: str
    method: str               # GET / POST / ...
    timestamp: datetime
    status_code: int | None   # None if request didn't complete
    request_type: str         # script / image / xhr / fetch / document / ...
    response_headers: dict[str, str] = {}
    initiator: str | None = None
```

Then update `tool_03_browser_scanner` to wire Playwright's `page.on("response", ...)`
event to build these models. This is real work, not a one-line fix. Out of
scope for v0.1.5 — flag it as a roadmap item and ship the tactical fix
first.

## Required verification before tagging the next release

Past Cowork-Claude versions "verified" without running an audit. Don't
repeat that. The verification rule is:

```bash
# 1. Build wheel locally
cd ~/Work/public-distribution/consent-engine
python3 -m build --wheel --outdir /tmp/ce-wheel-vN.N.N

# 2. Install in a real venv with Python 3.12+
python3.12 -m venv /tmp/ce-venv && source /tmp/ce-venv/bin/activate
pip install /tmp/ce-wheel-vN.N.N/*.whl
playwright install chromium

# 3. Run an actual audit against a real URL
consent-engine audit https://example.com
# Must print "Audit complete: ./out/<audit_id>/" without traceback.
# Must produce report.html, audit_result.json, evidence.jsonl, deck.marp.md.

# 4. Only after that succeeds: bump version, commit, tag, push
```

If any step errors, fix and re-run from step 1. **No "I traced through it,
looks fine" allowed.** Actually launch the browser and load a page.

## Release flow (works today)

```bash
# Bump version in two places
sed -i '' 's/__version__ = "0.1.4"/__version__ = "0.1.5"/' src/consent_engine/__init__.py
sed -i '' 's/^version = "0.1.4"/version = "0.1.5"/' pyproject.toml

# Update CHANGELOG.md (add a new section at top under "## [0.1.5] ...")

# Run the verification above

# Commit + tag + push
git add -A
git commit -m "fix(cli): evidence.jsonl was crashing on list[str] (v0.1.5)"
git tag v0.1.5
git push && git push origin v0.1.5
```

The `.github/workflows/release.yml` workflow triggers on tag push and
publishes to PyPI via Trusted Publishing (no API tokens needed).

After PyPI lands the new version (~2 minutes), Kenneth verifies with:

```bash
uvx --refresh consent-engine audit https://www.onetrust.com/
```

## Files you'll touch

- `src/consent_engine/cli.py` (line ~45-50)
- `src/consent_engine/api.py` (the audit endpoint)
- `src/consent_engine/mcp_server.py` (`_audit_url` function)
- `src/consent_engine/__init__.py` (version)
- `pyproject.toml` (version)
- `CHANGELOG.md` (new top section)

## Repo conventions (read CLAUDE.md for full list)

- Ruff + mypy must pass: `uv run ruff check src/` and `uv run mypy src/`
- Eight-tool architecture is deterministic by design; LLM only writes the
  executive summary in `generate_executive_summary()`
- Knowledge base is markdown (`src/consent_engine/data/wiki/`); no vector DB
- Vendor library is JSON + Open Cookie DB CSV
  (`src/consent_engine/data/vendor_library/`)
- All non-Python resources live under `src/consent_engine/` and are bundled
  via `[tool.hatch.build]` rules in `pyproject.toml`

## Watch for these landmines (every prior release found one)

1. **Edit tool failures.** If a Read-then-Edit fails silently in your
   session, the file doesn't get touched. Always re-grep after editing to
   confirm the change is on disk before committing.
2. **Data path computations.** Every loader uses
   `Path(__file__).parent.parent / "data" / ...`. If you see
   `parent.parent.parent.parent` anywhere in `src/`, that's the old broken
   pattern. Three places had this bug; all should be fixed now but check:
   `grep -rn 'parent.parent.parent.parent' src/`.
3. **PyPI caching.** `uvx --refresh` re-queries the registry; without it
   uv serves stale metadata for ~10 min.
4. **Made-up function names.** The Cowork-Claude session that built the
   CLI imagined `classify()` and `generate_report()` signatures that
   didn't exist. The real ones are `classify_finding()` (per-vendor) and
   `generate_report(audit_result, wiki_pages, executive_summary, ...)`.
   The full orchestration is in `consent_engine/audit.py::run_audit()`.
5. **PyPI versions are permanent.** Each broken release burns a version
   number forever. v0.1.0 through v0.1.4 will live on PyPI even though
   they're broken. The next fix is v0.1.5, not "republish 0.1.4".

## Out-of-scope for tonight (flagged for next pass)

- Demo GIF for README
- Weekly eval CI workflow (`.github/workflows/evals.yml`)
- Agent sweeps (Security, ADA, Senior dev) per Fred Pike's MeasureSummit
  Lesson 3 — should land in `scripts/agent_sweeps/`
- Case studies (`case-studies/` directory) — anonymized signal recovery,
  sGTM migration, consent-mode rollout

When v0.1.5 ships clean, prompt Kenneth to:
1. Take a screenshot of `out/<audit_id>/report.html` rendering in a
   browser. That's his Monday LinkedIn visual.
2. Submit the Google Cloud FDE II application (window closes ~May 18).
   Cover letter at `~/Work/kjb/jobs/fde/cover-letters/Cover_Letter_Google_Cloud.docx`.
3. Ship the LinkedIn launch post drafted at
   `~/Work/linkedin-automation/drafts/2026-W21.md` Monday 7am MST.

## How to start

```
@HANDOFF.md please ship v0.1.5 per the brief. Verify by running a real
audit end-to-end before tagging.
```

Good luck.
