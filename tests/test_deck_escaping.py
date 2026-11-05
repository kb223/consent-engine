"""Scan-derived strings must never reach the Marp deck as live HTML.

The deck renders with `marp --html`, so raw HTML in the markdown executes when
someone opens deck.html. Everything in AuditResult traces back to the audited
site (cookie names, request URLs, response bodies), so the whole model is
treated as hostile rather than field by field.
"""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel

from consent_engine.models.audit_result import AuditResult
from consent_engine.tools.tool_03_browser_scanner import _GCS_RE, parse_gcs_value
from consent_engine.tools.tool_08_report_generator import generate_marp_slides

SAMPLE = Path(__file__).parent.parent / "docs" / "sample-audit" / "audit_result.json"
PAYLOAD = '<img src=x onerror=alert(1)>"\'&'


def _poison(value: Any) -> Any:
    """Return `value` with every plain string replaced by the payload."""
    if isinstance(value, Enum):
        return value
    if isinstance(value, str):
        return PAYLOAD
    if isinstance(value, list):
        return [_poison(v) for v in value]
    if isinstance(value, dict):
        return {_poison(k): _poison(v) for k, v in value.items()}
    if isinstance(value, BaseModel):
        return value.model_copy(
            update={name: _poison(getattr(value, name)) for name in type(value).model_fields}
        )
    return value


@pytest.fixture
def audit() -> AuditResult:
    return AuditResult.model_validate(json.loads(SAMPLE.read_text(encoding="utf-8")))


@pytest.mark.parametrize("variant", ["compliance", "recovery"])
def test_no_scan_derived_string_reaches_the_deck_as_html(audit: AuditResult, variant: str) -> None:
    deck = generate_marp_slides(_poison(audit), PAYLOAD, report_variant=variant)
    assert "<img src=x" not in deck


def test_escaping_happens_once_not_twice(audit: AuditResult) -> None:
    audit.url = "https://example.com/?a=1&b=2"
    deck = generate_marp_slides(audit, "Summary.")
    assert "a=1&amp;b=2" in deck
    assert "&amp;amp;" not in deck


def test_escaping_leaves_the_callers_model_alone(audit: AuditResult) -> None:
    audit.url = "https://example.com/?a=1&b=2"
    generate_marp_slides(audit, "Summary.")
    assert audit.url == "https://example.com/?a=1&b=2"


def test_hostile_collect_body_does_not_survive_gcs_parsing() -> None:
    body = '{"next":"https://x/g/collect?v=2&gcs=<img src=x onerror=alert(1)>&en=page_view"}'
    captured = _GCS_RE.search(body)
    assert captured is not None
    parsed = parse_gcs_value(captured.group(1))
    assert "<" not in parsed.raw
    assert parsed.ad_storage == "unknown"
    assert parsed.analytics_storage == "unknown"


@pytest.mark.parametrize(
    ("raw", "ad", "analytics"),
    [
        ("G111", "granted", "granted"),
        ("G100", "denied", "denied"),
        ("G110", "granted", "denied"),
        ("G1--", "denied", "denied"),
    ],
)
def test_valid_gcs_values_still_decode(raw: str, ad: str, analytics: str) -> None:
    parsed = parse_gcs_value(raw)
    assert (parsed.raw, parsed.ad_storage, parsed.analytics_storage) == (raw, ad, analytics)
