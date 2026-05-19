# Security audit — v0.5.0

> Internal audit conducted 2026-05-18 by `gsd-security-auditor` agent against the v0.4.2 codebase before v0.5.0 tagging. All HIGH + MED findings closed in v0.5.0.

## Punch list

### HIGH

#### H1. SSRF — `audit <url>` will fetch any URL Playwright accepts (**CLOSED in v0.5.0**)
**File:** `src/consent_engine/audit.py` (`run_audit`), called from `cli.py`, `api.py`, `mcp_server.py`.

No URL allow/blocklist anywhere. `consent-engine audit http://169.254.169.254/latest/meta-data/` would load the AWS IMDS in a real browser; `http://localhost:6379/` would hit local Redis; `file://`/`chrome://` blockable by Playwright but `http(s)://` to RFC1918, link-local, and metadata ranges was wide open. Same surface reachable unauthenticated via `POST /audit` (HIGH when combined with H2).

**Fix shipped in v0.5.0:** New `_validate_audit_url()` in `audit.py` resolves the URL hostname with `socket.getaddrinfo`, then rejects A/AAAA records in `ipaddress.ip_address(...).is_private | is_loopback | is_link_local | is_reserved | is_multicast | is_unspecified`. Explicit metadata-host blocklist (AWS / GCP / Azure / Alibaba). Scheme allowlist `{http, https}` only. `CONSENT_ENGINE_ALLOW_INTERNAL=1` documented opt-in for self-hosters auditing internal staging.

**Verification:** Live-tested rejecting `http://localhost:6379/`, `http://10.0.0.1/`, `http://169.254.169.254/`, `http://metadata.google.internal/`, `file:///etc/passwd` — all return `ValueError` with actionable messages. `https://example.com` still passes through.

#### H2. FastAPI `/audit` was unauthenticated and bound 0.0.0.0 (**CLOSED in v0.5.0**)
**File:** `src/consent_engine/api.py`.

`uvicorn.run(..., host="0.0.0.0", port=8080)` plus zero auth on `POST /audit`. Any caller on the network could spawn Playwright browser jobs + consume API-key credits. Combined with H1 this was full SSRF-as-a-service.

**Fix shipped in v0.5.0:** Binds `127.0.0.1` by default (override with `CONSENT_ENGINE_HOST=0.0.0.0` only after setting the token). `POST /audit` gated behind `_require_token(...)` reading `CONSENT_ENGINE_API_TOKEN`. Returns `503 Service Unavailable` if the env var isn't set. Accepts `Authorization: Bearer <token>` or `X-Consent-Engine-Token: <token>`. Constant-time compare via `secrets.compare_digest`.

### MED

#### M1. Path traversal in `render-deck`, `chat`, and both MCP read tools (**CLOSED in v0.5.0**)
**Files:** `cli.py::_render_deck_command`, `cli.py::_chat_command` (now removed), `mcp_server.py::_read_audit_result`, `mcp_server.py::_query_evidence`.

The `audit` subcommand uses a server-generated `uuid.uuid4()` so the writer path was safe. But the read paths accepted `audit_id` from the user / MCP host with **no validation** — `consent-engine chat ../../../../etc` would resolve `Path("./out") / "../../../../etc"` and `read_text()` whatever sat there. Information disclosure within the process user. Worse over MCP if the host is a chatbot forwarding untrusted text.

**Fix shipped in v0.5.0:** New `_validate_audit_id()` in `cli.py` + `_safe_audit_dir()` in `mcp_server.py` reject any `audit_id` that doesn't match the UUID4 regex (`[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}`). Defense-in-depth via `Path.resolve()` containment check on the MCP side. Broken `consent-engine chat` subcommand removed entirely (it imported a non-existent `chat_with_context` function and would have raised `ImportError` on invocation).

#### M2. `jinja2 >= 3.1.0` floor permitted CVE-2025-27516 versions (**CLOSED in v0.5.0**)
**File:** `pyproject.toml`.

The resolved `uv.lock` pin was 3.1.6 (patched), but the declared lower bound `>=3.1.0` allowed downstream `pip install consent-engine` to resolve to 3.1.0–3.1.5 (sandbox bypass via `|attr` filter). Not exploitable in our codebase (no untrusted Jinja templates are user-supplied), but a published OSS library should not advertise a known-vulnerable lower bound.

**Fix shipped in v0.5.0:** `jinja2>=3.1.6` in `pyproject.toml`.

#### M3. `_render_markdown` returns `Markup(...)` — bypasses autoescape (**DOCUMENTED, deferred to v0.5.1**)
**File:** `tool_08_report_generator.py`, used in template at `audit_report.html.j2`.

The wiki content is bundled inside the wheel (`data/wiki/*.md`) so it's package-trusted, **but** the filter is registered globally on the Jinja env. If a future contributor wires `executive_summary | markdown` or `firm_name | markdown` it silently turns into stored XSS in the report file. Currently safe by construction, not by enforcement.

**Status:** Documented as a code-quality follow-up. v0.5.1 will rename the filter `wiki_markdown`, bleach-sanitize the output, and add a unit test that the only call site in `audit_report.html.j2` is on `page.content | reg_excerpt | markdown`.

### LOW

#### L1. LiteLLM debug logging defaults are quieted, but not removed
**File:** `src/consent_engine/__init__.py` sets `LITELLM_LOG=ERROR` and `LITELLM_DROP_PARAMS=true`. A user with `LITELLM_LOG=DEBUG` in their environment would see request bodies (including completion API keys redacted by LiteLLM, but URL + headers may leak).

**Status:** Defensive follow-up tracked for v0.5.1 — wrap the LiteLLM call in a try/except that re-raises with an exception message scrubbed of `Authorization` headers and `api_key=` query strings. Add a `tests/test_no_secret_logging.py` regression test that monkeypatches `ANTHROPIC_API_KEY="sentinel-1234"`, runs a failing audit, and asserts the sentinel never appears in captured stdout/stderr or evidence.jsonl.

#### L2. `subprocess.run` for `npx`/`open`/`xdg-open` — no shell injection but tight to PATH
**File:** `cli.py`.

All three use list-form arguments (no `shell=True`), `audit_id` doesn't reach them, and the marp invocation only takes `Path` objects derived from the validated audit dir. Safe today; would become unsafe if anyone ever switches to `shell=True` or interpolates `audit_id` into a string. No code change for v0.5.0; tracked in code comments.

#### L3. `out_dir.mkdir(parents=True)` honors user-supplied `--output-dir`
**File:** `cli.py`.

The CLI lets a user create directories anywhere they have write permission, including outside CWD. Expected CLI behavior, not a vulnerability — flagged in docs (`README.md`) so users running consent-engine as a privileged process aren't surprised.

## Categories with no real risk found

- **XSS in HTML templates** — autoescape on (`tool_08_report_generator.py` Jinja env), `firm_name`, `result.url`, `executive_summary` all flow through `{{ ... }}` escape. Only the `| markdown` filter bypasses, and its single call site operates on package-bundled wiki content. See M3 for the maintenance-burden caveat.
- **Secret handling** — no `print`/`logger`/`json.dump` of `*_API_KEY` anywhere in `src/consent_engine/`. Keys live in `Settings` (`config.py`) and propagate to `os.environ` for LiteLLM (`llm/client.py`). Not written to evidence.jsonl, not printed in CLI output.

## Summary

| Severity | Found | Closed in v0.5.0 | Deferred |
|---|---|---|---|
| HIGH | 2 | 2 | 0 |
| MED | 3 | 2 | 1 (M3) |
| LOW | 3 | 0 | 3 (L1, L2, L3 — non-blocking) |

All HIGH and MED-exploitable items closed. The one deferred MED (M3) is a maintenance-burden item, not an exploitable issue today.
