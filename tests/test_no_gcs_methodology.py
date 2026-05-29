"""No-Google-Consent-Mode methodology (v0.6.4).

When a known CMP is detected and the reject is applied but the site emits ZERO
Google Consent Mode signals (no gcs= in any request), the GCS-based audit is
not applicable. The engine must classify this as S3_NO_GOOGLE_CONSENT_MODE —
NOT the misleading 'inconclusive_unknown_cmp' (CMP is known) or
'consent_wiring_broken' (there is no wiring to be broken). It is non-definitive:
no confirmed violations, no statutory exposure, and the report/deck must render
a neutral verdict (never a false green 'no violations' / 'AI-ready').
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from consent_engine.models.audit_result import (
    AuditResult,
    MethodologyFlag,
    VendorFinding,
    ViolationStatus,
)
from consent_engine.models.vendor import CookieCategory, LegalExposure, Vendor
from consent_engine.tools.tool_03_browser_scanner import classify_s3_methodology
from consent_engine.tools.tool_08_report_generator import (
    _confirmed_violations,
    estimate_exposure_usd,
    generate_marp_slides,
    generate_report,
)

# --- pure classifier ---------------------------------------------------------


def test_classify_no_gcs_when_cmp_detected_and_no_gcs_at_all() -> None:
    # Sourcepoint (no injection plan) — no GCS anywhere -> not applicable.
    assert (
        classify_s3_methodology(
            gcs_denied_observed=False,
            gcs_observed_at_all=False,
            cmp_detected=True,
            injection_plan_existed=False,
        )
        == MethodologyFlag.S3_NO_GOOGLE_CONSENT_MODE
    )
    # OneTrust (has plan) but still zero GCS -> N/A, NOT wiring_broken.
    assert (
        classify_s3_methodology(
            gcs_denied_observed=False,
            gcs_observed_at_all=False,
            cmp_detected=True,
            injection_plan_existed=True,
        )
        == MethodologyFlag.S3_NO_GOOGLE_CONSENT_MODE
    )


def test_classify_wiring_broken_requires_gcs_present() -> None:
    # GCS present, never denied, CMP + plan -> wiring broken (definitive).
    assert (
        classify_s3_methodology(
            gcs_denied_observed=False,
            gcs_observed_at_all=True,
            cmp_detected=True,
            injection_plan_existed=True,
        )
        == MethodologyFlag.S3_CONSENT_WIRING_BROKEN
    )


def test_classify_s3_when_denied_observed() -> None:
    assert (
        classify_s3_methodology(
            gcs_denied_observed=True,
            gcs_observed_at_all=True,
            cmp_detected=True,
            injection_plan_existed=True,
        )
        == MethodologyFlag.S3
    )


def test_classify_inconclusive_when_cmp_unknown() -> None:
    # Unknown CMP, GCS present but not denied -> inconclusive.
    assert (
        classify_s3_methodology(
            gcs_denied_observed=False,
            gcs_observed_at_all=True,
            cmp_detected=False,
            injection_plan_existed=False,
        )
        == MethodologyFlag.INCONCLUSIVE_UNKNOWN_CMP
    )
    # Unknown CMP AND no GCS -> still inconclusive (can't assert N/A for an
    # unidentified setup we never engaged).
    assert (
        classify_s3_methodology(
            gcs_denied_observed=False,
            gcs_observed_at_all=False,
            cmp_detected=False,
            injection_plan_existed=False,
        )
        == MethodologyFlag.INCONCLUSIVE_UNKNOWN_CMP
    )


# --- rendering: non-definitive + neutral verdict -----------------------------


def _audit_no_gcs() -> AuditResult:
    finding = VendorFinding(
        vendor=Vendor(
            name="Meta",
            domains=["facebook.com"],
            category=CookieCategory.TARGETING,
            legal_exposure=LegalExposure.HIGH,
        ),
        status=ViolationStatus.CONFIRMED,
        methodology=MethodologyFlag.S3_NO_GOOGLE_CONSENT_MODE,
        cookies_observed=["_fbp"],
    )
    return AuditResult(
        audit_id="t-0000-0000-0000-000000000000",
        url="https://www.theguardian.com",
        timestamp=datetime.now(UTC),
        methodology=MethodologyFlag.S3_NO_GOOGLE_CONSENT_MODE,
        findings=[finding],
        detected_jurisdiction="US",
        detected_cmp="Sourcepoint",
        gcs_value=None,
    )


def test_no_gcs_yields_no_confirmed_violations() -> None:
    # A CONFIRMED finding must NOT count under a non-definitive methodology.
    assert _confirmed_violations(_audit_no_gcs()) == []


def test_no_gcs_has_no_exposure() -> None:
    e = estimate_exposure_usd(_audit_no_gcs())
    assert e["has_exposure"] is False


def test_report_no_gcs_is_neutral_not_clean() -> None:
    html = asyncio.run(
        generate_report(_audit_no_gcs(), wiki_pages=[], executive_summary="Test.")
    )
    # Must NOT falsely claim a clean site...
    assert "No Consent Violations Detected" not in html
    # ...and must explain the not-applicable state.
    assert "Google Consent Mode" in html


def test_deck_no_gcs_is_neutral_not_clean() -> None:
    deck = generate_marp_slides(_audit_no_gcs(), executive_summary="Test.")
    assert "No Violations Detected" not in deck
    assert "Consent Mode Not Detected" in deck
    # Must not falsely claim compliance anywhere on the deck.
    assert "site is compliant" not in deck
