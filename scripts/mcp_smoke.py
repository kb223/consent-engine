"""Check that an installed consent-engine MCP server starts and lists its tools.

CI's normal jobs install from uv.lock, but `uvx` users get the newest versions
the package metadata allows. This runs the server the way a user would, so a
breaking release of a dependency fails here instead of in someone's MCP host.

Usage: python scripts/mcp_smoke.py <command> [args...]
"""

from __future__ import annotations

import json
import subprocess
import sys
import threading
from typing import Any, cast

EXPECTED_TOOLS = {"audit_url", "read_audit_result", "query_evidence"}
TIMEOUT_SECONDS = 300
INITIALIZE: dict[str, Any] = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "ci-smoke", "version": "1"},
    },
}
INITIALIZED: dict[str, Any] = {"jsonrpc": "2.0", "method": "notifications/initialized"}
LIST_TOOLS: dict[str, Any] = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}


def _read_reply(server: subprocess.Popen[str], request_id: int) -> dict[str, Any]:
    """Read stdout until the reply to `request_id` arrives.

    Stdin stays open while waiting, as a real MCP host keeps it. The server is
    allowed to drop in-flight requests once stdin closes.
    """
    assert server.stdout is not None
    for line in server.stdout:
        try:
            reply = json.loads(line)
        except json.JSONDecodeError:
            continue
        if reply.get("id") == request_id:
            return cast(dict[str, Any], reply)
    raise RuntimeError(f"server exited with no reply to request {request_id}")


def _send(server: subprocess.Popen[str], message: dict[str, Any]) -> None:
    assert server.stdin is not None
    server.stdin.write(json.dumps(message) + "\n")
    server.stdin.flush()


def main() -> int:
    command = sys.argv[1:]
    if not command:
        print(__doc__, file=sys.stderr)
        return 2
    server = subprocess.Popen(
        command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1
    )
    watchdog = threading.Timer(TIMEOUT_SECONDS, server.kill)
    watchdog.start()
    try:
        _send(server, INITIALIZE)
        _read_reply(server, 1)
        _send(server, INITIALIZED)
        _send(server, LIST_TOOLS)
        tools = {tool["name"] for tool in _read_reply(server, 2)["result"]["tools"]}
    except (RuntimeError, OSError) as e:
        print(f"handshake failed: {e}", file=sys.stderr)
        return 1
    finally:
        watchdog.cancel()
        server.kill()
    if tools != EXPECTED_TOOLS:
        print(f"unexpected tools: {sorted(tools)}", file=sys.stderr)
        return 1
    print(f"ok: {sorted(tools)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
