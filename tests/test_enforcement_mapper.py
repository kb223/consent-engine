from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from consent_engine.models.audit_result import (
    AuditResult,
    EnforcementThemeFinding,
    MethodologyFlag,
    PixelFiring,
    TrackingTechnology,
)
from consent_engine.tools.enforcement_mapper import (
    build_enforcement_themes,
    build_tracking_inventory,
    infer_sensitive_contexts,
)
from consent_engine.tools.tool_08_report_generator import generate_marp_slides, generate_report


def _audit(**kwargs) -> AuditResult:
    defaults = {
        "audit_id": "test-0000-0000-0000-000000000000",
        "url": "https://example.com/health/therapy",
        "timestamp": datetime.now(UTC),
        "methodology": MethodologyFlag.S3,
        "findings": [],
        "detected_jurisdiction": "US",
    }
    defaults.update(kwargs)
    return AuditResult(**defaults)


def _meta_pixel(url: str = "https://www.facebook.com/tr/") -> PixelFiring:
    return PixelFiring(
        vendor_name="Meta Pixel",
        url=url,
        category="advertising",
        legal_exposure="high",
        matched_pattern="facebook.com/tr",
    )


def test_infer_sensitive_contexts_from_url_and_html() -> None:
    contexts = infer_sensitive_contexts(
        "https://example.com/student-health/video-therapy",
        "<main>Video appointment for teen mental health patients.</main>",
    )

    assert "health" in contexts
    assert "minor_or_student" in contexts
    assert "video_or_streaming" in contexts


def test_infer_sensitive_contexts_ignores_unrelated_body_links() -> None:
    contexts = infer_sensitive_contexts(
        "https://www.bbc.co.uk/",
        """
        <html>
          <head><title>BBC Home</title><meta name="description" content="News and sport"></head>
          <body>
            <a href="/health">Health story</a>
            <a href="/education">Student loans</a>
            <a href="/iplayer">Watch video</a>
          </body>
        </html>
        """,
    )

    assert contexts == []


def test_tracking_inventory_groups_pixel_and_gpc_observation() -> None:
    audit = _audit(pixel_firings=[_meta_pixel()])

    rows = build_tracking_inventory(
        audit,
        gpc_pixel_firings=[_meta_pixel("https://www.facebook.com/tr/?gpc=1")],
        sensitive_contexts=["health"],
    )

    assert len(rows) == 1
    row = rows[0]
    assert row.vendor_name == "Meta Pixel"
    assert row.evidence_type == "pixel"
    assert row.request_count == 2
    assert row.observed_after_opt_out is True
    assert row.observed_under_gpc is True
    assert row.sale_or_sharing_risk == "likely"
    assert row.contract_review_needed is True
    assert row.sensitive_contexts == ["health"]
    assert "gpc_uoom_failure" in row.enforcement_theme_keys
    assert "sensitive_data_purpose_limitation" in row.enforcement_theme_keys


def test_baseline_inventory_does_not_claim_post_opt_out() -> None:
    audit = _audit(methodology=MethodologyFlag.S1, pixel_firings=[_meta_pixel()])

    rows = build_tracking_inventory(audit)

    assert rows[0].observed_after_opt_out is False


def test_enforcement_themes_cover_gpc_sensitive_and_consent_asymmetry() -> None:
    audit = _audit(
        pixel_firings=[_meta_pixel()],
        gpc_tested=True,
        gpc_signal_respected=False,
        gpc_vendors_after_signal=1,
        gpc_pixel_count_baseline=1,
        gpc_pixel_count_with_gpc=1,
        cmp_interaction_method="banner_click_failed",
    )
    audit.tracking_inventory = build_tracking_inventory(
        audit,
        gpc_pixel_firings=[_meta_pixel("https://www.facebook.com/tr/?gpc=1")],
        sensitive_contexts=["health"],
    )

    themes = build_enforcement_themes(audit, sensitive_contexts=["health"])
    keys = {theme.key for theme in themes}

    assert "opt_out_mechanism_failure" in keys
    assert "gpc_uoom_failure" in keys
    assert "consent_asymmetry" in keys
    assert "vendor_governance" in keys
    assert "sensitive_data_purpose_limitation" in keys
    assert "tracking_inventory" in keys


def test_report_and_deck_render_enforcement_outputs() -> None:
    audit = _audit()
    audit.enforcement_themes = [
        EnforcementThemeFinding(
            key="gpc_uoom_failure",
            label="GPC / universal opt-out failure",
            severity="critical",
            evidence=["1 pixel endpoint fired under GPC"],
            regulatory_context="Universal opt-out signals require review.",
            recommended_action="Map GPC to the denied state.",
        )
    ]
    audit.tracking_inventory = [
        TrackingTechnology(
            vendor_name="Meta Pixel",
            category="advertising",
            evidence_type="pixel",
            observed_under_gpc=True,
            sale_or_sharing_risk="likely",
            contract_review_needed=True,
        )
    ]

    report_html = asyncio.run(generate_report(audit, wiki_pages=[], executive_summary="Test."))
    deck_md = generate_marp_slides(audit, executive_summary="Test.")

    assert "Enforcement Pattern Map" in report_html
    assert "Tracking Technology Inventory" in report_html
    assert "Meta Pixel" in report_html
    assert "ENFORCEMENT PATTERN MAP" in deck_md
    assert "TRACKING TECHNOLOGY INVENTORY" in deck_md
