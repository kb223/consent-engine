"""Jurisdiction-aware financial-exposure rendering (v0.6.3).

A Canadian or EU site must NOT show US statutes (CCPA/CIPA) or US settlement
precedents (Sephora/Disney) on the Financial Exposure slide. The US regime is a
per-consumer multiplier; EU/CA are turnover-percentage caps with their own
statutes and anchors. These tests lock that separation.
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
from consent_engine.tools.jurisdiction_detector import country_to_jurisdiction
from consent_engine.tools.tool_08_report_generator import (
    estimate_exposure_usd,
    generate_marp_slides,
    generate_report,
)


def _audit(juris: str) -> AuditResult:
    finding = VendorFinding(
        vendor=Vendor(
            name="Meta",
            domains=["facebook.com"],
            category=CookieCategory.TARGETING,
            legal_exposure=LegalExposure.HIGH,
        ),
        status=ViolationStatus.CONFIRMED,
        methodology=MethodologyFlag.S3,
        cookies_observed=["_fbp"],
    )
    return AuditResult(
        audit_id="t-0000-0000-0000-000000000000",
        url="https://example.test",
        timestamp=datetime.now(UTC),
        methodology=MethodologyFlag.S3,
        findings=[finding],
        detected_jurisdiction=juris,
        gcs_value=GCSValue(raw="G100", ad_storage="denied", analytics_storage="denied"),
    )


def _deck(juris: str) -> str:
    return generate_marp_slides(_audit(juris), executive_summary="Test summary.")


def test_country_to_jurisdiction_mapping() -> None:
    assert country_to_jurisdiction("CA") == "CA"
    assert country_to_jurisdiction("FR") == "EU"
    assert country_to_jurisdiction("GB") == "UK"  # UK GDPR / PECR is its own regime
    assert country_to_jurisdiction("US") is None  # don't override; let heuristic run
    assert country_to_jurisdiction(None) is None


def test_uk_exposure_uses_uk_gdpr_not_eu_or_us() -> None:
    d = _deck("UK")
    assert "UK GDPR" in d
    assert "£17.5M" in d
    assert "ICO" in d
    # Must NOT borrow EU/US specifics or the per-consumer model.
    assert "CNIL" not in d
    assert "€20M" not in d
    assert "Sephora" not in d
    assert "$7,500" not in d


def test_uk_estimate_exposure_is_turnover_cap() -> None:
    e = estimate_exposure_usd(_audit("UK"))
    assert e["model"] == "turnover_cap"
    assert "£17.5M" in str(e["components"])


def test_us_exposure_uses_ccpa_per_consumer() -> None:
    d = _deck("US")
    assert "$7,500" in d  # CCPA per-consumer rate
    assert "Sephora" in d  # US settlement precedent
    assert "CA opt-outs" in d  # per-consumer volume tiers


def test_canada_exposure_uses_law25_not_us() -> None:
    d = _deck("CA")
    assert "Law 25" in d
    assert "CAD $25M" in d
    assert "Tim Hortons" in d  # the honest Canadian precedent note
    # Must NOT borrow US statutes / precedents / the per-consumer tier model.
    assert "Sephora" not in d
    assert "$7,500" not in d
    assert "CA opt-outs" not in d


def test_eu_exposure_uses_gdpr_not_us() -> None:
    d = _deck("EU")
    assert "GDPR" in d
    assert "€20M" in d
    assert "CNIL" in d  # real EU cookie-fine anchor
    assert "Sephora" not in d
    assert "$7,500" not in d
    assert "CA opt-outs" not in d


# --- report-side: estimate_exposure_usd + rendered HTML ---------------------


def test_estimate_exposure_us_is_per_consumer() -> None:
    e = estimate_exposure_usd(_audit("US"))
    assert e["model"] == "per_consumer"
    assert e["has_exposure"] is True


def test_estimate_exposure_canada_is_turnover_cap() -> None:
    e = estimate_exposure_usd(_audit("CA"))
    assert e["model"] == "turnover_cap"
    assert e["has_exposure"] is True
    assert "CAD $25M" in str(e["components"])
    assert "Tim Hortons" in str(e.get("note"))


def test_estimate_exposure_eu_is_turnover_cap() -> None:
    e = estimate_exposure_usd(_audit("EU"))
    assert e["model"] == "turnover_cap"
    assert "€20M" in str(e["components"])


def _report(juris: str) -> str:
    return asyncio.run(
        generate_report(_audit(juris), wiki_pages=[], executive_summary="Test summary.")
    )


def test_report_html_canada_uses_law25_not_us_exposure() -> None:
    html = _report("CA")
    assert "Quebec Law 25" in html
    assert "CAD $25M" in html
    # The US settlement precedent must not appear in a Canadian report's exposure.
    assert "Sephora" not in html


def test_report_html_eu_uses_gdpr_not_us_exposure() -> None:
    html = _report("EU")
    assert "€20M" in html
    assert "Sephora" not in html
