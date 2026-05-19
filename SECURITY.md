# Security policy

> First-class concern. consent-engine drives a real Chromium browser against URLs you give it; the threat model is real.

## Reporting a vulnerability

If you think you've found a security issue:

1. **Don't** open a public GitHub issue.
2. Email Kenneth at `kennethbuchanan23@gmail.com` with the details, ideally with a minimal reproducer.
3. Expect a response within 72 hours. We'll coordinate disclosure timing.

## Threat model (as of v0.5.0)

The audit pipeline launches a real browser against a remote URL, captures every network request, and writes structured forensic evidence to disk. The biggest risks are:

1. **SSRF** — a caller pointing the scanner at internal IPs (cloud metadata services, internal staging hosts, local Redis, etc.) to either probe the internal network or exfiltrate metadata into a viewer's browser.
2. **Path traversal** — a malicious `audit_id` reaching the `render-deck` CLI or the MCP server's `read_audit_result` / `query_evidence` tools could escape `./out/`.
3. **Unauthenticated FastAPI surface** — the `POST /audit` route in `src/consent_engine/api.py` is a remote-code-execution-flavored endpoint by virtue of running Playwright; left open it becomes SSRF-as-a-service.
4. **XSS in rendered HTML report** — user-controlled inputs (audit URL, `--firm-name`, LLM-written executive summary) flow through Jinja2 templates and are rendered as HTML for the buyer to read.

## v0.5.0 mitigations

### SSRF — `_validate_audit_url()` in `src/consent_engine/audit.py`

Every `run_audit()` call resolves the target hostname and rejects:

- non-`http(s)` schemes (no `file://`, no `chrome://`)
- known cloud metadata hosts (`169.254.169.254`, `fd00:ec2::254`, `metadata.google.internal`, `metadata.azure.com`, Alibaba's `100.100.100.200`)
- any A/AAAA record that resolves to a private / loopback / link-local / reserved / multicast / unspecified IP per Python's `ipaddress` module.

Override with `CONSENT_ENGINE_ALLOW_INTERNAL=1` if you're self-hosting and auditing internal staging sites. This bypass is intentional and documented.

### Path traversal — `_validate_audit_id()` + `_safe_audit_dir()`

`src/consent_engine/cli.py` (`render-deck`) and `src/consent_engine/mcp_server.py` (`read_audit_result`, `query_evidence`) validate every `audit_id` against the UUID4 regex before joining it to `./out/`. Defense-in-depth via `Path.resolve()` containment check on the MCP side. Audit IDs are always `uuid.uuid4()` values; non-UUIDs are rejected with `ValueError`.

### Unauthenticated FastAPI — `_require_token()` + 127.0.0.1 default

The `POST /audit` endpoint now requires a bearer token via the `CONSENT_ENGINE_API_TOKEN` env var. If the env var is unset, the route returns `503 Service Unavailable` — the unauthenticated default that shipped in v0.1.x–v0.4.x is **closed** in v0.5.0. The `uvicorn.run()` call binds `127.0.0.1` by default; override with `CONSENT_ENGINE_HOST=0.0.0.0` only after setting the token.

Accepted token headers:
- `Authorization: Bearer <token>`
- `X-Consent-Engine-Token: <token>`

Constant-time compare via `secrets.compare_digest`.

### XSS — Jinja2 `autoescape=select_autoescape(['html'])`

The template environment in `tool_08_report_generator.py` enables HTML autoescape for all `*.html` templates. The only filter that bypasses autoescape is `| markdown` and it's only applied to package-bundled wiki content (`data/wiki/*.md`), which is trusted at build time. User inputs (`firm_name`, `result.url`, `executive_summary`) all flow through `{{ ... }}` escape.

### Dependency hygiene

- `jinja2>=3.1.6` (was `>=3.1.0`) — closes the floor on CVE-2025-27516 (sandbox bypass via `|attr` filter).
- See [docs/release-v0.5.0/cve-scan.md](docs/release-v0.5.0/cve-scan.md) for the full dependency posture.

## Known limitations (v0.5.0)

These ship as documented gaps in v0.5.0 and may be hardened in later releases:

1. **No CAPTCHA / WAF evasion controls.** The Scrapling/Camoufox stealthy fallback exists to *complete* a scan against sites with bot detection, not to bypass *anti-abuse* controls. Don't use this tool to circumvent rate limits on sites you don't own.
2. **Network log retention is local.** `out/<audit_id>/evidence.jsonl` writes to your filesystem with no encryption, no rotation, no purge. If you scan many sites, treat the `out/` directory as sensitive (HAR data + cookie content + headers).
3. **LLM data flow.** If you set an LLM API key, the executive-summary prompt sends a structured summary of findings to that provider. Review their data-handling policy before pointing at production audits.
4. **No rate-limit on the FastAPI route.** Auth gates access but a token-holding caller can spawn arbitrary Playwright jobs. Add reverse-proxy-level limits (nginx, Caddy, Cloudflare) for production deployments.

## Coordinated disclosure log

| Date | Reporter | Severity | Status |
|---|---|---|---|
| 2026-05-18 | Internal v0.5.0 security audit | HIGH x2, MED x3, LOW x3 | All HIGH/MED items fixed in v0.5.0 release |
