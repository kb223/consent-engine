"""Output schema for the consent investigator agent.

Pass ``FINDINGS_SCHEMA`` as ``output_config={"format": {"type": "json_schema",
"schema": FINDINGS_SCHEMA}}``. The final ``end_turn`` message is then valid JSON
in this shape.

The schema only guarantees shape. It can't check that a cited request ID exists
or that a confirmed verdict has a citation. Those are eval checks.

Structured outputs don't support length or numeric limits, so there are none
here. Every object sets ``additionalProperties: false`` and requires all fields.
"""

from __future__ import annotations

from typing import Any

from consent_engine.models.audit_result import ViolationStatus

VERDICTS: list[str] = [status.value for status in ViolationStatus]
CONFIDENCE_LEVELS: list[str] = ["low", "medium", "high"]
AUDIT_STATUSES: list[str] = ["investigated", "scan_failed", "evidence_unavailable"]


def _closed_object(properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


FINDING_SCHEMA: dict[str, Any] = _closed_object(
    {
        "finding_id": {
            "type": "string",
            "description": "The scanner finding this assessment is about, copied exactly.",
        },
        "vendor": {"type": "string", "description": "The vendor name from the scanner finding."},
        "verdict": {
            "type": "string",
            "enum": VERDICTS,
            "description": (
                "Your assessment, in the scanner's own status vocabulary. Use "
                "requires_further_investigation when the evidence can't settle it."
            ),
        },
        "claim": {
            "type": "string",
            "description": (
                "One or two sentences saying what was observed. State observations, "
                "not legal conclusions."
            ),
        },
        "cited_request_ids": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "IDs of saved requests that support the claim, each returned by a tool. "
                "Empty if no request supports it."
            ),
        },
        "cited_cookies": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "Names of observed cookies that support the claim, taken from the "
                "scanner finding. Empty if none."
            ),
        },
        "root_cause": {
            "type": "string",
            "description": (
                "The most likely technical cause, or 'undetermined' when the evidence "
                "doesn't show one."
            ),
        },
        "fix": {
            "type": "string",
            "description": "The change to make, or 'none' when no change is needed.",
        },
        "confidence": {
            "type": "string",
            "enum": CONFIDENCE_LEVELS,
            "description": "How well the cited evidence supports the verdict.",
        },
        "escalate": {
            "type": "boolean",
            "description": "True when a person should review this before anyone acts on it.",
        },
        "escalation_reason": {
            "type": "string",
            "description": "Why a person should review it. Empty when escalate is false.",
        },
    }
)

FINDINGS_SCHEMA: dict[str, Any] = _closed_object(
    {
        "fixture_id": {"type": "string", "description": "The audit that was investigated."},
        "audit_status": {
            "type": "string",
            "enum": AUDIT_STATUSES,
            "description": (
                "investigated when the scan could be assessed. Otherwise the reason it "
                "couldn't, as reported by the tools."
            ),
        },
        "findings": {
            "type": "array",
            "items": FINDING_SCHEMA,
            "description": (
                "One entry per scanner finding. Empty when the scan reported no "
                "findings or couldn't be assessed."
            ),
        },
        "notes": {
            "type": "string",
            "description": (
                "Anything a reviewer needs that doesn't belong to a single finding, "
                "such as a partial scan. Empty if nothing."
            ),
        },
    }
)
