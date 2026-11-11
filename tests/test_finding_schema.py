"""Tests for evals/finding_schema.py."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

from consent_engine.models.audit_result import ViolationStatus

REPO_ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "finding_schema", REPO_ROOT / "evals" / "finding_schema.py"
)
assert _spec and _spec.loader
fs = importlib.util.module_from_spec(_spec)
sys.modules["finding_schema"] = fs
_spec.loader.exec_module(fs)

# Keywords structured outputs reject.
UNSUPPORTED = {
    "minimum",
    "maximum",
    "multipleOf",
    "minLength",
    "maxLength",
    "minItems",
    "maxItems",
    "pattern",
}


def _walk(node: Any) -> list[dict[str, Any]]:
    if isinstance(node, dict):
        return [node, *(child for value in node.values() for child in _walk(value))]
    if isinstance(node, list):
        return [child for value in node for child in _walk(value)]
    return []


def test_every_object_is_closed_and_fully_required() -> None:
    objects = [n for n in _walk(fs.FINDINGS_SCHEMA) if n.get("type") == "object"]
    assert len(objects) == 2
    for obj in objects:
        assert obj["additionalProperties"] is False
        assert obj["required"] == list(obj["properties"])


def test_schema_uses_no_unsupported_keywords() -> None:
    for node in _walk(fs.FINDINGS_SCHEMA):
        assert not UNSUPPORTED & set(node), node


def test_every_field_has_a_description() -> None:
    for obj in (fs.FINDINGS_SCHEMA, fs.FINDING_SCHEMA):
        for name, spec in obj["properties"].items():
            assert spec.get("description"), name


def test_verdicts_match_the_engine_statuses() -> None:
    verdict = fs.FINDING_SCHEMA["properties"]["verdict"]
    assert verdict["enum"] == [status.value for status in ViolationStatus]
    assert "requires_further_investigation" in verdict["enum"]


def test_finding_has_the_planned_fields() -> None:
    assert list(fs.FINDING_SCHEMA["properties"]) == [
        "finding_id",
        "vendor",
        "verdict",
        "claim",
        "cited_request_ids",
        "cited_cookies",
        "root_cause",
        "fix",
        "confidence",
        "escalate",
        "escalation_reason",
    ]


def test_schema_is_plain_json() -> None:
    assert json.loads(json.dumps(fs.FINDINGS_SCHEMA)) == fs.FINDINGS_SCHEMA
