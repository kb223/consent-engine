"""Tests for src/consent_engine/mcp_server.py — the MCP tool surface.

Verifies the v0.5.0 path-traversal guard (_safe_audit_dir) and the tool
schema contract. The actual MCP stdio server is exercised at integration
time by Claude Desktop / Claude Code; here we test the validators + tool
schemas in isolation.

Skipped when the optional `[mcp]` extra is not installed (in which case
importing consent_engine.mcp_server raises SystemExit).
"""

from __future__ import annotations

import pytest

pytest.importorskip("mcp", reason="mcp extra not installed; skipping MCP server tests")

from consent_engine.mcp_server import (  # noqa: E402  - import after skipif
    _AUDIT_ID_PATTERN,
    _safe_audit_dir,
)

# ----------------------------------------------------------------------
# Audit-id validator (closes M1 path-traversal vector from the v0.5.0 audit)
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "good_id",
    [
        "12345678-1234-1234-1234-123456789abc",
        "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "ffffffff-ffff-ffff-ffff-ffffffffffff",
    ],
)
def test_safe_audit_dir_accepts_valid_uuid4(good_id: str, tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "out" / good_id).mkdir(parents=True)
    result = _safe_audit_dir(good_id)
    assert good_id in str(result)
    assert result.is_dir()


@pytest.mark.parametrize(
    "bad_id",
    [
        "../etc/passwd",
        "../../../../etc/passwd",
        "not-a-uuid",
        "../",
        "12345678-1234-1234-1234-123456789abc/../etc",
        "",
        "12345678123412341234123456789abc",  # no hyphens
        "AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAAA",  # uppercase rejected
    ],
)
def test_safe_audit_dir_rejects_path_traversal(bad_id: str) -> None:
    with pytest.raises(ValueError):
        _safe_audit_dir(bad_id)


def test_audit_id_pattern_is_lowercase_uuid4() -> None:
    """Regression: the pattern must reject uppercase to keep the path-resolve check sound."""
    assert _AUDIT_ID_PATTERN.fullmatch("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    assert not _AUDIT_ID_PATTERN.fullmatch("A1B2C3D4-E5F6-7890-ABCD-EF1234567890")


# ----------------------------------------------------------------------
# Tool registration — three tools exposed
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_tools_returns_three_audit_tools() -> None:
    """audit_url + read_audit_result + query_evidence."""
    from consent_engine.mcp_server import list_tools

    tools = await list_tools()
    names = {t.name for t in tools}
    assert names == {"audit_url", "read_audit_result", "query_evidence"}


@pytest.mark.asyncio
async def test_tool_schemas_have_required_fields() -> None:
    from consent_engine.mcp_server import list_tools

    by_name = {t.name: t for t in await list_tools()}

    assert by_name["audit_url"].inputSchema["required"] == ["url"]
    assert by_name["read_audit_result"].inputSchema["required"] == ["audit_id"]
    assert by_name["query_evidence"].inputSchema["required"] == ["audit_id"]


# ----------------------------------------------------------------------
# Read-tools handle bad audit_id without raising (return error TextContent)
# ----------------------------------------------------------------------


def test_read_audit_result_returns_error_text_on_bad_id() -> None:
    from consent_engine.mcp_server import _read_audit_result

    result = _read_audit_result("../../../etc")
    assert len(result) == 1
    assert "error" in result[0].text.lower()


def test_query_evidence_returns_error_text_on_bad_id() -> None:
    from consent_engine.mcp_server import _query_evidence

    result = _query_evidence({"audit_id": "../etc"})
    assert len(result) == 1
    assert "error" in result[0].text.lower()
