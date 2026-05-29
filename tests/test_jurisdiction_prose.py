"""Jurisdiction-aware prose + RAG retrieval (v0.6.6).

A non-US report must not be flooded with US (CCPA/CIPA/plaintiff) framing. Two
layers are locked here:
  1. RAG wiki selection — an EU/CA site must NOT pull ccpa.md / cipa-vppa.md /
     us-class-actions.md; it pulls its own regime's pages.
  2. jurisdiction_copy — the single source of regime-specific phrasing (GPC
     legal status, statute, regulator, vantage) used across report + deck.
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
from consent_engine.tools.jurisdiction_detector import jurisdiction_copy
from consent_engine.tools.tool_07_rag_retriever import retrieve_context


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
        gpc_tested=True,
        gcs_value=GCSValue(raw="G111", ad_storage="granted", analytics_storage="granted"),
    )


def _paths(juris: str) -> list[str]:
    return [p.path for p in asyncio.run(retrieve_context(_audit(juris)))]


def test_rag_eu_excludes_us_pages() -> None:
    paths = _paths("EU")
    assert not any(("ccpa" in p or "cipa" in p or "us-class-actions" in p) for p in paths)
    assert any("gdpr" in p for p in paths)


def test_rag_ca_excludes_us_pages() -> None:
    paths = _paths("CA")
    assert not any(("ccpa" in p or "cipa" in p or "us-class-actions" in p) for p in paths)
    assert any(("quebec" in p or "pipeda" in p) for p in paths)


def test_rag_us_keeps_us_pages() -> None:
    # The US path must still load its own enforcement context.
    paths = _paths("US")
    assert any("ccpa" in p for p in paths)


def test_jurisdiction_copy_gpc_legal_per_regime() -> None:
    assert "CCPA" in jurisdiction_copy("US").gpc_legal
    # Non-US regimes must NOT claim GPC is a binding CCPA opt-out.
    assert "CCPA" not in jurisdiction_copy("EU").gpc_legal
    assert "opt-in" in jurisdiction_copy("EU").gpc_legal
    assert "CCPA" not in jurisdiction_copy("CA").gpc_legal
    assert "Law 25" in jurisdiction_copy("CA").gpc_legal


def test_jurisdiction_copy_fields() -> None:
    assert jurisdiction_copy("US").vpn_label == "California"
    assert jurisdiction_copy("EU").vpn_label == "European"
    assert jurisdiction_copy("UK").statute == "UK GDPR / PECR"
    assert jurisdiction_copy(None).vpn_label == "California"  # safe default
