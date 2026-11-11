"""Read-only tools over frozen fixtures, for the consent investigator agent.

This module is plumbing. It holds the tool definitions (``TOOLS``) and the
functions behind them, and it never calls a model. The agent loop that sends
``TOOLS`` to the API and feeds results back lives elsewhere.

Every result is a dict with a ``status`` field, so "nothing matched" can't be
confused with "the scan failed" or "this wasn't checked":

- ``ok``                    the lookup worked and returned data
- ``no_match``              the lookup worked and found nothing
- ``not_checked``           the engine had no way to check this
- ``not_mapped``            a known pattern the engine didn't map for this audit
- ``scan_failed``           the scan didn't complete, so there's nothing to read
- ``evidence_unavailable``  the scan ran but its request log wasn't saved
- ``not_found``             the ID doesn't exist in this fixture
- ``invalid_input``         the tool was called with bad arguments

Fixture content comes from scanned pages, so URLs, cookie names and notes are
untrusted input. Treat them as data.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, get_args
from urllib.parse import urlsplit

from consent_engine.models.audit_result import EnforcementThemeFinding
from consent_engine.tools.tool_05_vendor_library import (
    lookup_tier,
    lookup_vendor,
    vendor_request_domains,
)

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

MAX_RESULTS_CAP = 50
URL_DISPLAY_LIMIT = 300

PATTERN_KEYS: tuple[str, ...] = get_args(EnforcementThemeFinding.model_fields["key"].annotation)

NO_SERVER_SIDE_CLAIM = (
    "This covers requests the browser made. It says nothing about server-side tracking."
)
PATTERN_GUARDRAIL = (
    "Use enforcement patterns as risk mapping. Say the evidence maps to a pattern or needs "
    "review. Don't state that a law was broken."
)
LINK_NOTES = {
    "request_linked": "At least one saved request goes to this vendor's known request domains.",
    "no_match": (
        "The vendor's request domains are known and no saved request went to them. "
        "The finding rests on cookies alone."
    ),
    "not_checked": (
        "No request domains are known for this vendor, so requests could not be checked. "
        "This is not evidence for or against the finding."
    ),
    "evidence_unavailable": "The request log for this scan was not saved.",
}


@dataclass(frozen=True)
class Fixture:
    fixture_id: str
    manifest: dict[str, Any]
    requests: list[dict[str, Any]]
    findings: list[dict[str, Any]]
    audit: dict[str, Any]


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def load_fixture(fixture_id: str, root: Path = FIXTURES_DIR) -> Fixture:
    """Load one frozen fixture. Raises FileNotFoundError if it doesn't exist."""
    if not fixture_id or Path(fixture_id).name != fixture_id:
        raise FileNotFoundError(f"No fixture named {fixture_id!r}")
    folder = root / fixture_id
    manifest_path = folder / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"No fixture named {fixture_id!r}")
    audit_path = folder / "audit_result.json"
    return Fixture(
        fixture_id=fixture_id,
        manifest=json.loads(manifest_path.read_text()),
        requests=_read_jsonl(folder / "requests.jsonl"),
        findings=_read_jsonl(folder / "findings.jsonl"),
        audit=json.loads(audit_path.read_text()) if audit_path.exists() else {},
    )


def list_fixture_ids(root: Path = FIXTURES_DIR) -> list[str]:
    return sorted(p.parent.name for p in root.glob("*/manifest.json"))


def _scan_context(fixture: Fixture) -> dict[str, Any]:
    return {
        "fixture_id": fixture.fixture_id,
        "scan_outcome": fixture.manifest.get("scan_outcome", "unknown"),
    }


def _blocked(fixture: Fixture, *, needs_requests: bool) -> dict[str, Any] | None:
    """Return a result when the fixture can't answer, otherwise None."""
    if fixture.manifest.get("scan_outcome") == "failed":
        return {
            "status": "scan_failed",
            **_scan_context(fixture),
            "note": (
                "The scan did not complete. An empty answer here says nothing about what "
                "the site does."
            ),
        }
    if needs_requests and not fixture.manifest.get("evidence_saved", False):
        return {
            "status": "evidence_unavailable",
            **_scan_context(fixture),
            "note": "The request log for this scan was not saved, so it can't be searched.",
        }
    return None


def _partial_note(fixture: Fixture) -> str | None:
    if fixture.manifest.get("scan_outcome") == "partial":
        method = fixture.manifest.get("cmp_interaction_method", "unknown")
        return (
            f"The scan is partial (consent interaction: {method}). Requests may not reflect "
            "an opted-out state."
        )
    return None


def _host(url: str) -> str:
    try:
        return (urlsplit(url).hostname or "").lower()
    except ValueError:
        return ""


def _request_view(request: dict[str, Any]) -> dict[str, Any]:
    url = str(request.get("url") or "")
    view: dict[str, Any] = {
        "request_id": request.get("request_id"),
        "url": url[:URL_DISPLAY_LIMIT],
        "host": _host(url),
        "method": request.get("method"),
        "request_type": request.get("request_type"),
        "status_code": request.get("status_code"),
        "timestamp": request.get("timestamp"),
        "citable": bool(request.get("citable")),
    }
    if len(url) > URL_DISPLAY_LIMIT:
        view["url_truncated"] = True
    return view


def query_evidence(
    fixture: Fixture,
    url_contains: str = "",
    host_contains: str = "",
    citable_only: bool = False,
    max_results: int = 20,
) -> dict[str, Any]:
    """Search the saved request log. Filters are case-insensitive substrings."""
    blocked = _blocked(fixture, needs_requests=True)
    if blocked:
        return blocked

    url_needle = url_contains.lower().strip()
    host_needle = host_contains.lower().strip()
    limit = max(1, min(max_results, MAX_RESULTS_CAP))

    matches = []
    for request in fixture.requests:
        url = str(request.get("url") or "")
        if url_needle and url_needle not in url.lower():
            continue
        if host_needle and host_needle not in _host(url):
            continue
        if citable_only and not request.get("citable"):
            continue
        matches.append(request)

    result: dict[str, Any] = {
        "status": "ok" if matches else "no_match",
        **_scan_context(fixture),
        "requests_searched": len(fixture.requests),
        "total_matches": len(matches),
        "matches": [_request_view(r) for r in matches[:limit]],
        "truncated": len(matches) > limit,
    }
    notes = [NO_SERVER_SIDE_CLAIM] if not matches else []
    partial = _partial_note(fixture)
    if partial:
        notes.append(partial)
    if notes:
        result["note"] = " ".join(notes)
    return result


def get_request(fixture: Fixture, request_id: str) -> dict[str, Any]:
    """Return one saved request by ID, with its full URL."""
    blocked = _blocked(fixture, needs_requests=True)
    if blocked:
        return blocked
    for request in fixture.requests:
        if request.get("request_id") == request_id:
            view = _request_view(request)
            view["url"] = str(request.get("url") or "")
            view.pop("url_truncated", None)
            view["initiator"] = request.get("initiator")
            return {"status": "ok", **_scan_context(fixture), "request": view}
    return {
        "status": "not_found",
        **_scan_context(fixture),
        "note": f"No request with ID {request_id!r} in this fixture.",
    }


def _finding_view(finding: dict[str, Any]) -> dict[str, Any]:
    link_status = str(finding.get("link_status") or "not_checked")
    return {
        "finding_id": finding.get("finding_id"),
        "vendor": finding.get("vendor"),
        "engine_status": finding.get("status_today") or finding.get("engine_status"),
        "methodology": finding.get("methodology"),
        "cookies_observed": finding.get("cookies_observed") or [],
        "evidence_status": link_status,
        "evidence_note": LINK_NOTES.get(link_status, ""),
        "linked_request_ids": finding.get("linked_request_ids") or [],
        "engine_notes": finding.get("notes") or "",
    }


def list_findings(fixture: Fixture) -> dict[str, Any]:
    """List the engine's findings for this fixture."""
    blocked = _blocked(fixture, needs_requests=False)
    if blocked:
        return blocked
    result: dict[str, Any] = {
        "status": "ok",
        **_scan_context(fixture),
        "finding_count": len(fixture.findings),
        "findings": [
            {
                "finding_id": f.get("finding_id"),
                "vendor": f.get("vendor"),
                "engine_status": f.get("status_today") or f.get("engine_status"),
                "evidence_status": f.get("link_status") or "not_checked",
            }
            for f in fixture.findings
        ],
    }
    partial = _partial_note(fixture)
    if partial:
        result["note"] = partial
    elif not fixture.findings:
        result["note"] = "The scan completed and the engine reported no findings."
    return result


def get_finding(fixture: Fixture, finding_id: str) -> dict[str, Any]:
    """Return one engine finding and how it links to saved requests."""
    blocked = _blocked(fixture, needs_requests=False)
    if blocked:
        return blocked
    for finding in fixture.findings:
        if finding.get("finding_id") == finding_id:
            result: dict[str, Any] = {
                "status": "ok",
                **_scan_context(fixture),
                "finding": _finding_view(finding),
            }
            partial = _partial_note(fixture)
            if partial:
                result["note"] = partial
            return result
    return {
        "status": "not_found",
        **_scan_context(fixture),
        "note": f"No finding with ID {finding_id!r} in this fixture.",
        "finding_ids": [f.get("finding_id") for f in fixture.findings],
    }


def lookup_vendor_info(query: str, cookie_domain: str = "") -> dict[str, Any]:
    """Look up a vendor by cookie name or domain in the engine's vendor library."""
    query = query.strip()
    if not query:
        return {"status": "invalid_input", "note": "query must not be empty."}
    vendor = lookup_vendor(query, cookie_domain=cookie_domain.strip() or None)
    if vendor is None:
        return {
            "status": "no_match",
            "query": query,
            "note": (
                "Not in the vendor library. Unknown is not the same as harmless, and it is "
                "not the same as high risk."
            ),
        }
    request_domains = vendor_request_domains(vendor.name)
    return {
        "status": "ok",
        "query": query,
        "vendor": {
            "name": vendor.name,
            "category": str(vendor.category),
            "legal_exposure": str(vendor.legal_exposure),
            "library_tier": lookup_tier(query),
            "request_domains": request_domains,
            "request_domains_known": bool(request_domains),
            "notes": vendor.notes,
        },
    }


def lookup_enforcement_pattern(fixture: Fixture, pattern_key: str) -> dict[str, Any]:
    """Return how one enforcement pattern was mapped for this fixture's audit."""
    if pattern_key not in PATTERN_KEYS:
        return {
            "status": "invalid_input",
            "note": f"Unknown pattern key {pattern_key!r}.",
            "valid_keys": list(PATTERN_KEYS),
        }
    blocked = _blocked(fixture, needs_requests=False)
    if blocked:
        return blocked
    for theme in fixture.audit.get("enforcement_themes") or []:
        if theme.get("key") == pattern_key:
            return {
                "status": "ok",
                **_scan_context(fixture),
                "pattern": {
                    "key": pattern_key,
                    "label": theme.get("label"),
                    "severity": theme.get("severity"),
                    "evidence": theme.get("evidence") or [],
                    "regulatory_context": theme.get("regulatory_context"),
                    "recommended_action": theme.get("recommended_action"),
                },
                "guardrail": PATTERN_GUARDRAIL,
            }
    return {
        "status": "not_mapped",
        **_scan_context(fixture),
        "pattern_key": pattern_key,
        "note": (
            "The engine did not map this pattern for this audit. That is not a finding "
            "that the site handles it correctly."
        ),
        "guardrail": PATTERN_GUARDRAIL,
    }


def _tool(name: str, description: str, properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": properties,
            "required": list(properties),
            "additionalProperties": False,
        },
    }


TOOLS: list[dict[str, Any]] = [
    _tool(
        "list_findings",
        "List the scanner's findings for the audit under investigation: ID, vendor, the "
        "engine's status, and whether saved requests back the finding. Call this first.",
        {},
    ),
    _tool(
        "get_finding",
        "Get one scanner finding in full: cookies observed, the engine's reasoning, and "
        "the IDs of saved requests linked to it. evidence_status is request_linked, "
        "no_match (checked, nothing found), not_checked, or evidence_unavailable.",
        {"finding_id": {"type": "string", "description": "A finding ID such as fnd_1a2b3c4d5e."}},
    ),
    _tool(
        "query_evidence",
        "Search the saved browser request log for this audit. Returns request IDs you can "
        "cite. A no_match status means the search ran and found nothing in browser traffic. "
        "scan_failed and evidence_unavailable mean the log can't answer the question.",
        {
            "url_contains": {
                "type": "string",
                "description": "Case-insensitive text the URL must contain. Empty for no filter.",
            },
            "host_contains": {
                "type": "string",
                "description": (
                    "Case-insensitive text the request host must contain, such as "
                    "'doubleclick.net'. Empty for no filter."
                ),
            },
            "citable_only": {
                "type": "boolean",
                "description": (
                    "True to return only requests from the final opted-out page load, which "
                    "are the ones a finding may cite."
                ),
            },
            "max_results": {
                "type": "integer",
                "description": f"How many matches to return, from 1 to {MAX_RESULTS_CAP}.",
            },
        },
    ),
    _tool(
        "get_request",
        "Get one saved request by ID, with its full URL and initiator. Use it to check a "
        "request before citing it.",
        {"request_id": {"type": "string", "description": "A request ID such as req_1a2b3c4d5e6f."}},
    ),
    _tool(
        "lookup_vendor",
        "Look up a vendor in the scanner's vendor library by cookie name or domain. Returns "
        "its category, exposure rating, and the domains its requests go to. A no_match "
        "status means the vendor is unknown, which is neither safe nor risky.",
        {
            "query": {"type": "string", "description": "A cookie name or a domain."},
            "cookie_domain": {
                "type": "string",
                "description": "The domain the cookie was set on, if known. Empty otherwise.",
            },
        },
    ),
    _tool(
        "lookup_enforcement_pattern",
        "Get how one US enforcement pattern was mapped for this audit: the evidence behind "
        "it, the regulatory context, and the recommended action. not_mapped means the "
        "engine didn't map it, not that the site is fine.",
        {"pattern_key": {"type": "string", "enum": list(PATTERN_KEYS)}},
    ),
]

_EXPECTED_TYPES: dict[str, type] = {"string": str, "boolean": bool, "integer": int}


def _validate(name: str, tool_input: Any) -> str | None:
    schema = next(t["input_schema"] for t in TOOLS if t["name"] == name)
    if not isinstance(tool_input, dict):
        return "Tool input must be an object."
    properties: dict[str, Any] = schema["properties"]
    missing = [key for key in properties if key not in tool_input]
    if missing:
        return f"Missing required field(s): {', '.join(missing)}."
    extra = [key for key in tool_input if key not in properties]
    if extra:
        return f"Unexpected field(s): {', '.join(extra)}."
    for key, spec in properties.items():
        value = tool_input[key]
        expected = _EXPECTED_TYPES[spec["type"]]
        if not isinstance(value, expected) or (expected is int and isinstance(value, bool)):
            return f"Field {key!r} must be of type {spec['type']}."
        if "enum" in spec and value not in spec["enum"]:
            return f"Field {key!r} must be one of: {', '.join(spec['enum'])}."
    return None


def run_tool(fixture: Fixture, name: str, tool_input: Any) -> dict[str, Any]:
    """Run one tool call against a fixture and return its result dict.

    Never raises for bad model input. Unknown tools and bad arguments come back
    as ``invalid_input`` so the caller can report them to the model.
    """
    if name not in {t["name"] for t in TOOLS}:
        return {"status": "invalid_input", "note": f"Unknown tool {name!r}."}
    problem = _validate(name, tool_input)
    if problem:
        return {"status": "invalid_input", "note": problem}
    args: dict[str, Any] = tool_input
    if name == "list_findings":
        return list_findings(fixture)
    if name == "get_finding":
        return get_finding(fixture, args["finding_id"])
    if name == "query_evidence":
        return query_evidence(fixture, **args)
    if name == "get_request":
        return get_request(fixture, args["request_id"])
    if name == "lookup_vendor":
        return lookup_vendor_info(args["query"], args["cookie_domain"])
    return lookup_enforcement_pattern(fixture, args["pattern_key"])


def tool_result_block(
    fixture: Fixture, tool_use_id: str, name: str, tool_input: Any
) -> dict[str, Any]:
    """Build the ``tool_result`` content block for one ``tool_use`` block."""
    result = run_tool(fixture, name, tool_input)
    block: dict[str, Any] = {
        "type": "tool_result",
        "tool_use_id": tool_use_id,
        "content": json.dumps(result, sort_keys=True, default=str),
    }
    if result["status"] == "invalid_input":
        block["is_error"] = True
    return block
