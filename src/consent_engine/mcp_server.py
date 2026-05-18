"""MCP server wrapper for consent-engine.

Exposes the audit pipeline as Model Context Protocol tools so Claude Desktop
(and any other MCP host) can run an audit, read the result, and query the
captured evidence from a conversation.

Run standalone:
    uvx consent-engine-mcp

Register in Claude Desktop config:
    {
      "mcpServers": {
        "consent-engine": {
          "command": "uvx",
          "args": ["consent-engine-mcp"]
        }
      }
    }
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

# `mcp` is an optional dependency. If the user installed
# `pip install consent-engine[mcp]` we get it; otherwise we surface a clear
# error rather than failing on import.
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import TextContent, Tool
except ImportError as e:                                          # pragma: no cover
    raise SystemExit(
        "MCP support requires the optional [mcp] extra:\n"
        "  pip install 'consent-engine[mcp]'\n"
    ) from e


server: Server = Server("consent-engine")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="audit_url",
            description=(
                "Run a forensic consent-compliance audit against a URL. "
                "Returns the audit_id, a one-paragraph executive summary, "
                "and a violations count. Use read_audit_result / "
                "query_evidence to drill into specifics."
            ),
            inputSchema={
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"],
            },
        ),
        Tool(
            name="read_audit_result",
            description=(
                "Load the structured audit_result.json for a prior audit. "
                "Returns the full Pydantic model as JSON."
            ),
            inputSchema={
                "type": "object",
                "properties": {"audit_id": {"type": "string"}},
                "required": ["audit_id"],
            },
        ),
        Tool(
            name="query_evidence",
            description=(
                "Filter the captured network evidence for a prior audit. "
                "Use this when the user asks 'why did X fire' or 'what was "
                "happening at time T'. Filter by url substring, "
                "host substring, or time window."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "audit_id": {"type": "string"},
                    "url_contains": {"type": "string"},
                    "host_contains": {"type": "string"},
                    "max_results": {"type": "integer", "default": 20},
                },
                "required": ["audit_id"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    if name == "audit_url":
        return await _audit_url(arguments["url"])
    if name == "read_audit_result":
        return _read_audit_result(arguments["audit_id"])
    if name == "query_evidence":
        return _query_evidence(arguments)
    raise ValueError(f"Unknown tool: {name}")


async def _audit_url(url: str) -> list[TextContent]:
    # Lazy import — avoids pulling Playwright at MCP server start
    from consent_engine.audit import run_audit

    bundle = await run_audit(url=url)
    audit_dir = Path("./out") / bundle.audit_id
    audit_dir.mkdir(parents=True, exist_ok=True)
    (audit_dir / "audit_result.json").write_text(
        json.dumps(bundle.audit_result.model_dump(mode="json"), indent=2, default=str)
    )
    with (audit_dir / "evidence.jsonl").open("w") as f:
        for url in bundle.scan_result.network_requests:
            f.write(json.dumps({"url": url}) + "\n")
    (audit_dir / "report.html").write_text(bundle.report_html)
    (audit_dir / "deck.marp.md").write_text(bundle.deck_marp_md)
    return [TextContent(
        type="text",
        text=(
            f"Audit complete: {bundle.audit_id}\n"
            f"  URL: {url}\n"
            f"  Findings: {len(bundle.audit_result.findings)} vendor finding(s)\n\n"
            f"Summary:\n{bundle.executive_summary}"
        ),
    )]


def _read_audit_result(audit_id: str) -> list[TextContent]:
    path = Path("./out") / audit_id / "audit_result.json"
    if not path.exists():
        return [TextContent(type="text", text=f"No audit bundle at {path}")]
    return [TextContent(type="text", text=path.read_text())]


def _query_evidence(args: dict[str, Any]) -> list[TextContent]:
    audit_id = args["audit_id"]
    max_results = args.get("max_results", 20)
    url_contains = (args.get("url_contains") or "").lower()
    host_contains = (args.get("host_contains") or "").lower()

    path = Path("./out") / audit_id / "evidence.jsonl"
    if not path.exists():
        return [TextContent(type="text", text=f"No evidence at {path}")]

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

    return [TextContent(
        type="text",
        text=f"{len(matches)} match(es):\n" + json.dumps(matches, indent=2, default=str),
    )]


def cli() -> None:
    """Entrypoint registered as `consent-engine-mcp` in pyproject.toml."""
    asyncio.run(_run())


async def _run() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":                                            # pragma: no cover
    cli()
