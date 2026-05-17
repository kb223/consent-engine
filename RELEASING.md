# Releasing consent-engine

> Every push of a `v*` tag triggers `.github/workflows/release.yml`, which
> builds + publishes to PyPI via Trusted Publishing and creates a GitHub
> Release. No manual artifact upload, no PyPI API tokens to rotate.

## One-time PyPI setup (do this before the first tag)

PyPI Trusted Publishing connects a GitHub repo to a PyPI project without
shared secrets. GitHub Actions presents an OIDC token; PyPI validates the
repo + workflow + environment name match the registered publisher.

1. Sign in to <https://pypi.org/manage/account/publishing/>.
2. Click **Add a new pending publisher**.
3. Fill in:
   - **PyPI project name**: `consent-engine`
   - **Owner**: `kb223`
   - **Repository name**: `consent-engine`
   - **Workflow name**: `release.yml`
   - **Environment name**: `pypi`
4. Save.

The project is "pending" until first publish, then becomes the real PyPI
project owned by you.

In the GitHub repo also create an **environment** named `pypi`
(Settings → Environments → New environment). Optionally add reviewers so
you have to approve each release. The workflow's `environment: pypi`
clause respects that gate.

## Cutting a release

1. **Bump versions in lockstep**:
   - `src/consent_engine/__init__.py` (`__version__ = "0.1.1"`)
   - `pyproject.toml` (`version = "0.1.1"`)
2. **Update `CHANGELOG.md`** with the changes since the last tag.
3. **Commit + push** the version bump:
   ```sh
   git add -A
   git commit -m "chore(release): v0.1.1"
   git push
   ```
4. **Wait for CI to go green** on `main`.
5. **Tag and push**:
   ```sh
   git tag v0.1.1
   git push --tags
   ```
6. **Watch** <https://github.com/kb223/consent-engine/actions/workflows/release.yml>.
   The pipeline builds, publishes to PyPI, and creates a GitHub Release in
   ~2 minutes.
7. **Verify** the install works from a clean machine:
   ```sh
   uvx consent-engine version
   # → consent-engine 0.1.1
   ```

## What ships

Each release publishes:
- `consent_engine-<version>-py3-none-any.whl` to PyPI
- `consent_engine-<version>.tar.gz` to PyPI
- A GitHub Release with both files attached + release notes from the
  annotated tag (use `git tag -a v0.1.1 -m "release notes here"` if you
  want richer notes)

## Versioning

Semver. Pre-1.0 cadence:
- **patch**: bug fix, doc update, internal refactor
- **minor**: new tool, new CLI subcommand, new wiki page, new eval case
- **major** (1.0): API surface frozen, backward-compat promises begin

## Pre-release flow

For early-access alphas (e.g., before exposing to anyone outside Kenneth):

```sh
git tag v0.2.0a1
git push --tags
```

PyPI publishes to the pre-release channel. Install with:

```sh
uvx --prerelease=allow consent-engine version
```
