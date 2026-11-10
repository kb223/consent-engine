"""Tests for evals/fixture_tools.py. All data here is synthetic."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "fixture_tools", REPO_ROOT / "evals" / "fixture_tools.py"
)
assert _spec and _spec.loader
ft = importlib.util.module_from_spec(_spec)
sys.modules["fixture_tools"] = ft
_spec.loader.exec_module(ft)


def _write_fixture(
    root: Path,
    fixture_id: str = "fx-01",
    *,
    scan_outcome: str = "complete",
    evidence_saved: bool = True,
    requests: list[dict[str, Any]] | None = None,
    findings: list[dict[str, Any]] | None = None,
    themes: list[dict[str, Any]] | None = None,
) -> None:
    folder = root / fixture_id
    folder.mkdir(parents=True)
    manifest = {
        "fixture_id": fixture_id,
        "scan_outcome": scan_outcome,
        "evidence_saved": evidence_saved,
        "cmp_interaction_method": "banner_click_failed",
    }
    (folder / "manifest.json").write_text(json.dumps(manifest))
    (folder / "audit_result.json").write_text(json.dumps({"enforcement_themes": themes or []}))
    for name, rows in (("requests.jsonl", requests or []), ("findings.jsonl", findings or [])):
        (folder / name).write_text("".join(json.dumps(r) + "\n" for r in rows))


REQUESTS = [
    {
        "request_id": "req_aaa",
        "url": "https://shop.example/",
        "method": "GET",
        "request_type": "document",
        "status_code": 200,
        "timestamp": "2026-06-01T00:00:00Z",
        "citable": True,
        "initiator": None,
    },
    {
        "request_id": "req_bbb",
        "url": "https://ads.tracker.example/pixel?id=1",
        "method": "GET",
        "request_type": "image",
        "status_code": 200,
        "timestamp": "2026-06-01T00:00:01Z",
        "citable": True,
        "initiator": "https://shop.example/",
    },
    {
        "request_id": "req_ccc",
        "url": "https://ads.tracker.example/early?id=1",
        "method": "GET",
        "request_type": "image",
        "status_code": 200,
        "timestamp": "2026-05-31T23:59:00Z",
        "citable": False,
        "initiator": None,
    },
]
FINDINGS = [
    {
        "finding_id": "fnd_linked",
        "vendor": "Tracker Co",
        "engine_status": "confirmed_violation",
        "status_today": "confirmed_violation",
        "methodology": "s3_fresh_load_optout_preset",
        "cookies_observed": ["_trk"],
        "link_status": "request_linked",
        "linked_request_ids": ["req_bbb"],
        "notes": "",
    },
    {
        "finding_id": "fnd_unchecked",
        "vendor": "Mystery Vendor",
        "engine_status": "requires_further_investigation",
        "status_today": "requires_further_investigation",
        "methodology": "s3_fresh_load_optout_preset",
        "cookies_observed": ["_m"],
        "link_status": "not_checked",
        "linked_request_ids": [],
        "notes": "",
    },
]
THEME = {
    "key": "gpc_uoom_failure",
    "label": "GPC failure",
    "severity": "high",
    "evidence": ["1 vendor after signal"],
    "regulatory_context": "context",
    "recommended_action": "action",
}


@pytest.fixture
def complete(tmp_path: Path) -> Any:
    _write_fixture(tmp_path, requests=REQUESTS, findings=FINDINGS, themes=[THEME])
    return ft.load_fixture("fx-01", tmp_path)


def test_load_fixture_rejects_missing_and_path_like_ids(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    with pytest.raises(FileNotFoundError):
        ft.load_fixture("fx-99", tmp_path)
    with pytest.raises(FileNotFoundError):
        ft.load_fixture("../fx-01", tmp_path)
    assert ft.list_fixture_ids(tmp_path) == ["fx-01"]


def test_query_evidence_filters_by_host_not_whole_url(complete: Any) -> None:
    hit = ft.query_evidence(complete, host_contains="tracker.example")
    assert hit["status"] == "ok"
    assert [m["request_id"] for m in hit["matches"]] == ["req_bbb", "req_ccc"]

    # "pixel" is in a path, so it must not match as a host.
    assert ft.query_evidence(complete, host_contains="pixel")["status"] == "no_match"
    assert ft.query_evidence(complete, url_contains="PIXEL")["total_matches"] == 1


def test_query_evidence_citable_only_and_truncation(complete: Any) -> None:
    citable = ft.query_evidence(complete, host_contains="tracker", citable_only=True)
    assert [m["request_id"] for m in citable["matches"]] == ["req_bbb"]

    capped = ft.query_evidence(complete, max_results=1)
    assert capped["total_matches"] == 3
    assert len(capped["matches"]) == 1
    assert capped["truncated"] is True


def test_no_match_never_claims_absence_of_server_side_tracking(complete: Any) -> None:
    miss = ft.query_evidence(complete, host_contains="nothing.example")
    assert miss["status"] == "no_match"
    assert miss["requests_searched"] == 3
    assert "server-side" in miss["note"]


def test_failed_scan_is_not_reported_as_no_match(tmp_path: Path) -> None:
    _write_fixture(tmp_path, scan_outcome="failed")
    failed = ft.load_fixture("fx-01", tmp_path)
    assert ft.query_evidence(failed, host_contains="x")["status"] == "scan_failed"
    assert ft.list_findings(failed)["status"] == "scan_failed"
    assert ft.get_finding(failed, "fnd_x")["status"] == "scan_failed"
    assert ft.lookup_enforcement_pattern(failed, "gpc_uoom_failure")["status"] == "scan_failed"


def test_unsaved_evidence_is_its_own_status(tmp_path: Path) -> None:
    _write_fixture(tmp_path, evidence_saved=False, findings=FINDINGS)
    fixture = ft.load_fixture("fx-01", tmp_path)
    assert ft.query_evidence(fixture)["status"] == "evidence_unavailable"
    assert ft.get_request(fixture, "req_aaa")["status"] == "evidence_unavailable"
    # Findings don't need the request log.
    assert ft.list_findings(fixture)["status"] == "ok"


def test_partial_scan_carries_a_caveat(tmp_path: Path) -> None:
    _write_fixture(tmp_path, scan_outcome="partial", requests=REQUESTS, findings=FINDINGS)
    partial = ft.load_fixture("fx-01", tmp_path)
    hit = ft.query_evidence(partial, host_contains="tracker")
    assert hit["status"] == "ok"
    assert "partial" in hit["note"]
    assert "partial" in ft.list_findings(partial)["note"]


def test_clean_complete_scan_reports_zero_findings_as_ok(tmp_path: Path) -> None:
    _write_fixture(tmp_path, requests=REQUESTS)
    clean = ft.list_findings(ft.load_fixture("fx-01", tmp_path))
    assert clean["status"] == "ok"
    assert clean["finding_count"] == 0
    assert "no findings" in clean["note"]


def test_get_finding_separates_linked_from_not_checked(complete: Any) -> None:
    linked = ft.get_finding(complete, "fnd_linked")["finding"]
    assert linked["evidence_status"] == "request_linked"
    assert linked["linked_request_ids"] == ["req_bbb"]

    unchecked = ft.get_finding(complete, "fnd_unchecked")["finding"]
    assert unchecked["evidence_status"] == "not_checked"
    assert "not evidence for or against" in unchecked["evidence_note"]

    missing = ft.get_finding(complete, "fnd_nope")
    assert missing["status"] == "not_found"
    assert missing["finding_ids"] == ["fnd_linked", "fnd_unchecked"]


def test_get_request_returns_full_url(tmp_path: Path) -> None:
    long_url = "https://ads.tracker.example/p?" + "a" * 500
    _write_fixture(tmp_path, requests=[{**REQUESTS[1], "url": long_url}])
    fixture = ft.load_fixture("fx-01", tmp_path)
    listed = ft.query_evidence(fixture)["matches"][0]
    assert listed["url_truncated"] is True
    assert len(listed["url"]) == ft.URL_DISPLAY_LIMIT
    assert ft.get_request(fixture, "req_bbb")["request"]["url"] == long_url
    assert ft.get_request(fixture, "req_zzz")["status"] == "not_found"


def test_lookup_vendor_known_and_unknown() -> None:
    known = ft.lookup_vendor_info("_ga")
    assert known["status"] == "ok"
    assert known["vendor"]["name"]
    assert isinstance(known["vendor"]["request_domains_known"], bool)

    unknown = ft.lookup_vendor_info("zz_not_a_real_cookie_zz")
    assert unknown["status"] == "no_match"
    assert "not the same as harmless" in unknown["note"]
    assert ft.lookup_vendor_info("  ")["status"] == "invalid_input"


def test_enforcement_pattern_mapped_not_mapped_and_invalid(complete: Any) -> None:
    mapped = ft.lookup_enforcement_pattern(complete, "gpc_uoom_failure")
    assert mapped["status"] == "ok"
    assert mapped["pattern"]["severity"] == "high"
    assert "Don't state that a law was broken" in mapped["guardrail"]

    unmapped = ft.lookup_enforcement_pattern(complete, "consent_asymmetry")
    assert unmapped["status"] == "not_mapped"

    bad = ft.lookup_enforcement_pattern(complete, "made_up")
    assert bad["status"] == "invalid_input"
    assert "gpc_uoom_failure" in bad["valid_keys"]


def test_tool_definitions_are_strict_and_closed() -> None:
    names = [t["name"] for t in ft.TOOLS]
    assert len(names) == len(set(names))
    for tool in ft.TOOLS:
        schema = tool["input_schema"]
        assert tool["strict"] is True
        assert schema["additionalProperties"] is False
        assert schema["required"] == list(schema["properties"])
        assert tool["description"]


def test_run_tool_dispatches_every_tool(complete: Any) -> None:
    calls: dict[str, dict[str, Any]] = {
        "list_findings": {},
        "get_finding": {"finding_id": "fnd_linked"},
        "query_evidence": {
            "url_contains": "",
            "host_contains": "tracker",
            "citable_only": True,
            "max_results": 5,
        },
        "get_request": {"request_id": "req_bbb"},
        "lookup_vendor": {"query": "_ga", "cookie_domain": ""},
        "lookup_enforcement_pattern": {"pattern_key": "gpc_uoom_failure"},
    }
    assert set(calls) == {t["name"] for t in ft.TOOLS}
    for name, tool_input in calls.items():
        assert ft.run_tool(complete, name, tool_input)["status"] == "ok", name


@pytest.mark.parametrize(
    ("name", "tool_input"),
    [
        ("delete_everything", {}),
        ("get_finding", {}),
        ("get_finding", {"finding_id": 7}),
        ("get_finding", {"finding_id": "fnd_linked", "extra": "x"}),
        ("get_finding", "fnd_linked"),
        (
            "query_evidence",
            {"url_contains": "", "host_contains": "", "citable_only": False, "max_results": True},
        ),
        ("lookup_enforcement_pattern", {"pattern_key": "made_up"}),
    ],
)
def test_run_tool_reports_bad_input_instead_of_raising(
    complete: Any, name: str, tool_input: Any
) -> None:
    assert ft.run_tool(complete, name, tool_input)["status"] == "invalid_input"


def test_tool_result_block_shape(complete: Any) -> None:
    ok = ft.tool_result_block(complete, "toolu_1", "get_request", {"request_id": "req_bbb"})
    assert ok["type"] == "tool_result"
    assert ok["tool_use_id"] == "toolu_1"
    assert json.loads(ok["content"])["status"] == "ok"
    assert "is_error" not in ok

    bad = ft.tool_result_block(complete, "toolu_2", "nope", {})
    assert bad["is_error"] is True
