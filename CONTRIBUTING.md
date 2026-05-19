# Contributing to consent-engine

Thanks for considering a contribution. This project is MIT-licensed and welcomes external PRs.

## Project posture

- **Deterministic by design.** The audit pipeline is eight standalone tools (see `docs/scenarios.md`). The LLM is scoped to executive-summary generation only. Don't add LLM calls to other tools without discussion.
- **Wiki-grounded.** Regulatory + technical claims in the report come from `src/consent_engine/data/wiki/`. New claims need a wiki entry first, with a citation.
- **Test gate is real.** `release.yml` runs `uv run pytest` before publishing to PyPI. If your PR breaks tests, the release pipeline will halt — please run tests locally first.

## Local setup

```sh
git clone https://github.com/kb223/consent-engine.git
cd consent-engine
uv sync --group dev
uv run playwright install chromium
uv run pytest tests/ -q
```

If you hit `BrowserType.launch: Executable doesn't exist`, run `uv run playwright install chromium` again — the first install can take ~2 minutes.

## Lint + type-check before opening a PR

```sh
uv run ruff check src/ tests/
uv run mypy src/                       # advisory; some warnings are documented
uv run pytest tests/ -q
```

A PR with `ruff` errors will fail CI. mypy warnings are advisory in v0.5.0 (see `docs/release-v0.5.0/type-coverage.md`) — please don't add new ones if you can avoid it.

## Adding a vendor

Two files, depending on whether the vendor has legal-litigation significance or is a standard cookie:

### Legally-annotated, lawsuit-relevant

Edit `src/consent_engine/data/vendor_library/vendors.json`:

```json
{
  "name": "Meta",
  "cookie_names": ["_fbp", "_fbc", "fr"],
  "category": "targeting",
  "legal_exposure": "high",
  "onetrust_category": "C0004",
  "notes": "Lead defendant in 47+ CIPA cases filed Jan-Mar 2026 (citation: wiki/enforcement/lawsuit-surge.md)."
}
```

`legal_exposure` values: `"high" | "medium" | "low" | "unknown"`. Cite the source in `notes` — preferably an entry in `data/wiki/enforcement/`.

### Standard / well-known

Add to the Open Cookie Database CSV at `src/consent_engine/data/vendor_library/open-cookie-database.csv`. Match the existing column structure.

## Adding a wiki page

The wiki is `src/consent_engine/data/wiki/`. Pages are markdown with light front matter.

1. Create the page under the right subdir: `regulations/`, `concepts/`, `enforcement/`, or `technical/`.
2. Update `src/consent_engine/data/wiki/index.md` with the new entry.
3. Append a line to `src/consent_engine/data/wiki/log.md` per the wiki schema:
   ```markdown
   ## [YYYY-MM-DD] add | <description>
   ```
4. If the page documents a new audit signal (e.g. a new CMP, a new statute), update `src/consent_engine/data/wiki/CLAUDE.md`'s mapping table so the report generator picks it up.

The full wiki schema lives in `src/consent_engine/data/wiki/CLAUDE.md`.

## Adding a CMP detection rule

Edit `src/consent_engine/tools/cmp_detector.py`:

- **JS-global detection**: add a tuple to `_JS_GLOBAL_RULES`.
- **URL-pattern fallback** (for CMPs that load past `networkidle`): add to `_SCRIPT_URL_RULES`.
- **DOM fallback** (last resort): add to `_DOM_SELECTOR_RULES`.
- Add a test case to `tests/tools/test_tool_03_browser_scanner.py` or create a fixture page in `tests/tools/conftest.py`.

Tier the confidence per the existing rules: `"high"` (JS global confirmed), `"medium"` (URL or cookie matched), `"low"` (DOM selector matched).

## Adding an eval case

`evals/cases/NNN-<slug>.yaml`. Run

```sh
uv run python evals/run_evals.py --add-baseline evals/cases/NNN-<slug>.yaml
```

once to populate the expected block from current behavior.

## PR guidelines

- **Branch**: any name. Open against `main`.
- **One concern per PR**: easier to review, easier to revert.
- **Commit messages**: Conventional Commits (`fix:`, `feat:`, `docs:`, `refactor:`). The CHANGELOG entry should describe user-visible behavior, not the diff.
- **CHANGELOG.md**: bump it in the same PR if your change is user-visible.
- **Tests**: add or update tests for any behavior change. Smoke-test against `https://example.com` if you touch the scanner or audit pipeline.
- **Security-sensitive changes**: SSRF, path-traversal, auth, or XSS-adjacent changes need an explicit `## Security review` block in the PR description.

## Voice + copy rules (for user-facing strings)

- No emojis in CLI output, report copy, or comments.
- Plain technical English. The audience is engineers, privacy officers, and legal counsel.
- See [README.md](README.md) "Voice" section for the full rules.

## What we won't accept

- Browser-fingerprint randomization for the purpose of bypassing anti-abuse controls on sites you don't own.
- Auto-classification heuristics that don't have a wiki citation backing them.
- Net new LLM call sites outside the executive-summary pipeline.
- Vendor entries without a documented source in `notes`.

If you're not sure, open an issue first and we'll talk through it.

## Security disclosure

See [SECURITY.md](SECURITY.md). Don't open public issues for security findings.
