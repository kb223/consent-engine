"""MCP server wrapper for consent-engine.

Exposes the audit pipeline as Model Context Protocol tools so Claude Desktop
(and any other MCP host) can run an audit, read the result, and query the
captured evidence from a conversation.

Built on the FastMCP API: tool schemas are generated from the type hints and
docstrings below rather than hand-written JSON.

Run standalone (the [mcp] extra is required):
    uvx --from 'consent-engine[mcp]' consent-engine-mcp

Debug in the MCP Inspector (from a source clone):
    uv run mcp dev src/consent_engine/mcp_server.py --with-editable .

Register in Claude Desktop config:
    {
      "mcpServers": {
        "consent-engine": {
          "command": "/Users/you/.local/bin/uvx",
          "args": ["--from", "consent-engine[mcp]", "consent-engine-mcp"]
        }
      }
    }

Use the absolute path from `which uvx`; macOS GUI apps do not inherit the
shell PATH.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Annotated, Any

_AUDIT_ID_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def _output_base() -> Path:
    """Resolve the audit-output base directory, creating it if needed.

    Under Claude Desktop the host CWD is arbitrary (often read-only), so a
    CWD-relative `./out` is unreliable. Honor `CONSENT_ENGINE_OUT_DIR` if set,
    otherwise fall back to `~/.consent-engine/out`. Both the write path and
    `_safe_audit_dir` (read path) go through here so they stay consistent.
    """
    env = os.environ.get("CONSENT_ENGINE_OUT_DIR")
    base = Path(env) if env else Path.home() / ".consent-engine" / "out"
    base.mkdir(parents=True, exist_ok=True)
    return base.resolve()


def _safe_audit_dir(audit_id: str) -> Path:
    """Resolve `<output base>/<audit_id>` after rejecting non-UUID inputs.

    Closes the MCP-side path-traversal vector — an MCP host could pass an
    untrusted audit_id like `../../../etc` and reach files outside the output
    base. Audit IDs come from `uuid.uuid4()` so we can validate the shape.
    """
    if not _AUDIT_ID_PATTERN.fullmatch(audit_id):
        raise ValueError(f"Invalid audit_id format: {audit_id!r} (expected UUID4)")
    out = _output_base()
    candidate = (out / audit_id).resolve()
    if not str(candidate).startswith(str(out) + "/"):
        raise ValueError(f"audit_id resolves outside output base: {audit_id!r}")
    return candidate

# `mcp` is an optional dependency. If the user installed
# `pip install consent-engine[mcp]` we get it; otherwise we surface a clear
# error rather than failing on import.
try:
    from mcp.server.fastmcp import FastMCP
except ImportError as e:                                          # pragma: no cover
    raise SystemExit(
        "MCP support requires the optional [mcp] extra. Install with one of:\n"
        "  uvx --from 'consent-engine[mcp]' consent-engine-mcp   (recommended, no global install)\n"
        "  pip install 'consent-engine[mcp]'                    (global install)\n"
        "  uv pip install 'consent-engine[mcp]'                 (uv-managed env)\n"
    ) from e

from pydantic import Field  # noqa: E402  - imported after the optional-extra guard

# Named `mcp` because `mcp dev <file>` auto-discovers the server object by
# looking for `mcp`, `server`, then `app`. Importing FastMCP by name (rather
# than `import mcp`) means this assignment does not shadow the package.
mcp = FastMCP("consent-engine")


@mcp.tool()
async def audit_url(
    url: Annotated[str, Field(description="Fully qualified URL to audit, including scheme.")],
) -> str:
    """Run a forensic consent-compliance audit against a URL.

    Returns the audit_id, a one-paragraph executive summary, and a violations
    count. Use read_audit_result / query_evidence to drill into specifics.
    """
    # Lazy import — avoids pulling Playwright at MCP server start
    from consent_engine.audit import run_audit

    bundle = await run_audit(url=url)
    audit_dir = _output_base() / bundle.audit_id
    audit_dir.mkdir(parents=True, exist_ok=True)
    (audit_dir / "audit_result.json").write_text(
        json.dumps(bundle.audit_result.model_dump(mode="json"), indent=2, default=str)
    )
    with (audit_dir / "evidence.jsonl").open("w") as f:
        if bundle.scan_result.request_log:
            for entry in bundle.scan_result.request_log:
                f.write(json.dumps(entry.model_dump(mode="json"), default=str) + "\n")
        else:
            for request_url in bundle.scan_result.network_requests:
                f.write(json.dumps({"url": request_url}) + "\n")
    (audit_dir / "report.html").write_text(bundle.report_html)
    (audit_dir / "deck.marp.md").write_text(bundle.deck_marp_md)
    return (
        f"Audit complete: {bundle.audit_id}\n"
        f"  URL: {url}\n"
        f"  Output: {audit_dir}\n"
        f"  Findings: {len(bundle.audit_result.findings)} vendor finding(s)\n\n"
        f"Summary:\n{bundle.executive_summary}"
    )


@mcp.tool()
def read_audit_result(
    audit_id: Annotated[str, Field(description="UUID4 audit_id returned by audit_url.")],
) -> str:
    """Load the structured audit_result.json for a prior audit.

    Returns the full Pydantic model as JSON.
    """
    try:
        audit_dir = _safe_audit_dir(audit_id)
    except ValueError as e:
        return f"error: {e}"
    path = audit_dir / "audit_result.json"
    if not path.exists():
        return f"No audit bundle at {path}"
    return path.read_text()


@mcp.tool()
def query_evidence(
    audit_id: Annotated[str, Field(description="UUID4 audit_id returned by audit_url.")],
    url_contains: Annotated[
        str, Field(description="Case-insensitive substring to match against the request URL.")
    ] = "",
    host_contains: Annotated[
        str, Field(description="Case-insensitive substring to match against the request host.")
    ] = "",
    max_results: Annotated[
        int, Field(description="Maximum number of matching requests to return.")
    ] = 20,
) -> str:
    """Filter the captured network evidence for a prior audit.

    Use this when the user asks 'why did X fire' or 'what fired on this page'.
    Filter by url substring or host substring.
    """
    url_contains = (url_contains or "").lower()
    host_contains = (host_contains or "").lower()

    try:
        audit_dir = _safe_audit_dir(audit_id)
    except ValueError as e:
        return f"error: {e}"
    path = audit_dir / "evidence.jsonl"
    if not path.exists():
        return f"No evidence at {path}"

    matches: list[dict[str, Any]] = []
    for line in path.read_text().splitlines():
        try:
            evt = json.loads(line)
        except json.JSONDecodeError:
            continue
        u = (evt.get("url") or "").lower()
        if url_contains and url_contains not in u:
            continue
        if host_contains and host_contains not in u:
            continue
        matches.append(evt)
        if len(matches) >= max_results:
            break

    return f"{len(matches)} match(es):\n" + json.dumps(matches, indent=2, default=str)


def cli() -> None:
    """Entrypoint registered as `consent-engine-mcp` in pyproject.toml."""
    mcp.run()


if __name__ == "__main__":                                            # pragma: no cover
    cli()
