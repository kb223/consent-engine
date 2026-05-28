"""Regression tests for the v0.6.2 accuracy + XSS fixes.

Each test guards a bug class that previously shipped:

- fast-scan methodology mislabeled non-OneTrust CMPs as the definitive
  S3_CONSENT_WIRING_BROKEN even though the fast path never injected against them
  (`classify_fast_methodology`)
- the confirmed-violation verdict + statutory-exposure dollars rendered under an
  INCONCLUSIVE methodology (`_confirmed_violations`, `estimate_exposure_usd`,
  `generate_report` verdict band)
- stored XSS in the HTML report via the attacker-controlled audited URL and
  cookie names (Jinja autoescape was silently off because the template is `.j2`)
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from consent_engine.models.audit_result import (
    AuditResult,
    GCSValue,
    MethodologyFlag,
    VendorFinding,
    ViolationStatus,
)
from consent_engine.models.vendor import CookieCategory, LegalExposure, Vendor
from consent_engine.tools.tool_03_browser_scanner import classify_fast_methodology
from consent_engine.tools.tool_08_report_generator import (
    _confirmed_violations,
    estimate_exposure_usd,
    generate_report,
)


def _denied_gcs() -> GCSValue:
    return GCSValue(raw="G100", ad_storage="denied", analytics_storage="denied")


def _granted_gcs() -> GCSValue:
    return GCSValue(raw="G111", ad_storage="granted", analytics_storage="granted")


def _confirmed_finding(cookie: str = "_fbp", vendor_name: str = "Meta") -> VendorFinding:
    return VendorFinding(
        vendor=Vendor(
            name=vendor_name,
            domains=["facebook.com"],
            category=CookieCategory.TARGETING,
            legal_exposure=LegalExposure.HIGH,
        ),
        status=ViolationStatus.CONFIRMED,
        methodology=MethodologyFlag.S3,
        cookies_observed=[cookie],
        gcs_value=_denied_gcs(),
    )


def _audit(
    methodology: MethodologyFlag,
    *,
    url: str = "https://example.com",
    findings: list[VendorFinding] | None = None,
) -> AuditResult:
    return AuditResult(
        audit_id="test-0000-0000-0000-000000000000",
        url=url,
        timestamp=datetime.now(UTC),
        methodology=methodology,
        findings=findings if findings is not None else [],
        detected_jurisdiction="US",
        gcs_value=_denied_gcs(),
    )


# --- classify_fast_methodology (the twice-shipped fast-path bug) -----------


def test_denied_gcs_is_definitive_s3() -> None:
    assert classify_fast_methodology(_denied_gcs(), None) == MethodologyFlag.S3
    assert classify_fast_methodology(_denied_gcs(), "Didomi") == MethodologyFlag.S3


def test_onetrust_granted_is_wiring_broken() -> None:
    assert (
        classify_fast_methodology(_granted_gcs(), "OneTrust")
        == MethodologyFlag.S3_CONSENT_WIRING_BROKEN
    )


def test_non_onetrust_cmp_granted_is_inconclusive() -> None:
    # The bug: a Didomi/Usercentrics/etc. site (the fast path never injected
    # against it) was labeled S3_CONSENT_WIRING_BROKEN "legally defensible". It
    # must be INCONCLUSIVE — we never applied that CMP's denial payload.
    for cmp in ("Didomi", "Usercentrics", "Sourcepoint", "CookieYes", "Cassie"):
        assert (
            classify_fast_methodology(_granted_gcs(), cmp)
            == MethodologyFlag.INCONCLUSIVE_UNKNOWN_CMP
        ), cmp


def test_unknown_cmp_granted_is_inconclusive() -> None:
    assert (
        classify_fast_methodology(_granted_gcs(), None)
        == MethodologyFlag.INCONCLUSIVE_UNKNOWN_CMP
    )


# --- _confirmed_violations (methodology gate) ------------------------------


def test_confirmed_violations_gated_under_inconclusive() -> None:
    a = _audit(MethodologyFlag.INCONCLUSIVE_UNKNOWN_CMP, findings=[_confirmed_finding()])
    assert _confirmed_violations(a) == []


def test_confirmed_violations_pass_under_s3() -> None:
    a = _audit(MethodologyFlag.S3, findings=[_confirmed_finding()])
    assert len(_confirmed_violations(a)) == 1


# --- estimate_exposure_usd (methodology gate) ------------------------------


def test_no_exposure_under_inconclusive() -> None:
    a = _audit(MethodologyFlag.INCONCLUSIVE_UNKNOWN_CMP, findings=[_confirmed_finding()])
    exp = estimate_exposure_usd(a)
    assert exp["has_exposure"] is False
    assert exp["total_exposure_high_usd"] == 0


def test_exposure_present_under_s3() -> None:
    a = _audit(MethodologyFlag.S3, findings=[_confirmed_finding()])
    exp = estimate_exposure_usd(a)
    assert exp["has_exposure"] is True
    assert int(exp["total_exposure_high_usd"]) > 0  # type: ignore[call-overload]


# --- generate_report verdict band + XSS ------------------------------------


def _render(a: AuditResult) -> str:
    return asyncio.run(
        generate_report(a, wiki_pages=[], executive_summary="Test summary.")
    )


def test_inconclusive_report_does_not_claim_violation() -> None:
    a = _audit(MethodologyFlag.INCONCLUSIVE_UNKNOWN_CMP, findings=[_confirmed_finding()])
    html = _render(a)
    assert "Consent Violation Detected" not in html
    assert "Consent Enforcement Not Verified" in html


def test_definitive_report_claims_violation() -> None:
    a = _audit(MethodologyFlag.S3, findings=[_confirmed_finding()])
    html = _render(a)
    assert "Consent Violation Detected" in html


def test_report_escapes_malicious_url_and_cookie() -> None:
    a = _audit(
        MethodologyFlag.S3,
        url='https://x.com/?q="><script>alert(1)</script>',
        findings=[_confirmed_finding(cookie='_fbp"><script>alert(2)</script>')],
    )
    html = _render(a)
    # Raw script tags from attacker-controlled inputs must never reach the report.
    assert "<script>alert(1)</script>" not in html
    assert "<script>alert(2)</script>" not in html
    # Proof the values were rendered AND escaped (not just dropped).
    assert "&lt;script&gt;" in html
