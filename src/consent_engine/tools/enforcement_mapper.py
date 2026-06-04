"""Map forensic scan evidence to current US enforcement patterns.

This module is deliberately deterministic. It does not decide whether a legal
violation occurred; it groups already-captured evidence into regulator-facing
themes that mirror recent US privacy enforcement priorities.
"""

from __future__ import annotations

import re
from collections import defaultdict
from html import unescape
from typing import Literal
from urllib.parse import urlparse

from consent_engine.models.audit_result import (
    AuditResult,
    EnforcementThemeFinding,
    MethodologyFlag,
    PixelFiring,
    TrackingTechnology,
    ViolationStatus,
)

SaleOrSharingRisk = Literal["none", "possible", "likely"]


_HEALTH_TERMS = (
    "health", "medical", "diagnos", "symptom", "treatment", "therapy",
    "cancer", "hiv", "aids", "ms", "multiple sclerosis", "pregnancy",
    "reproductive", "mental health", "condition", "patient",
)
_LOCATION_TERMS = (
    "geolocation", "precise location", "location data", "gps", "onstar",
    "driving", "driver", "vehicle", "telematics", "insurance rate",
)
_MINOR_TERMS = (
    "child", "children", "kid", "kids", "student", "school", "high school",
    "under 13", "under-13", "under 16", "under-16", "teen", "minor",
    "prom", "homecoming",
)
_VIDEO_TERMS = (
    "video", "streaming", "watch", "episode", "movie", "tv", "connected tv",
)
_FINANCIAL_TERMS = (
    "financial", "bank", "credit", "loan", "mortgage", "insurance",
)
_TITLE_RE = re.compile(r"<title[^>]*>(?P<text>.*?)</title>", re.IGNORECASE | re.DOTALL)
_H1_RE = re.compile(r"<h1[^>]*>(?P<text>.*?)</h1>", re.IGNORECASE | re.DOTALL)
_META_RE = re.compile(r"<meta\b[^>]*>", re.IGNORECASE | re.DOTALL)
_CONTENT_RE = re.compile(r"""\bcontent=(?P<quote>["'])(?P<text>.*?)(?P=quote)""", re.IGNORECASE)


def _strip_tags(value: str) -> str:
    return re.sub(r"<[^>]+>", " ", unescape(value))


def _page_context_snippets(page_html: str | None) -> list[str]:
    """Extract page-level context without treating every linked article as context."""
    if not page_html:
        return []
    html = page_html[:120_000]
    snippets: list[str] = []

    for match in _TITLE_RE.finditer(html):
        snippets.append(_strip_tags(match.group("text")))
    for match in _H1_RE.finditer(html):
        snippets.append(_strip_tags(match.group("text")))

    for match in _META_RE.finditer(html):
        tag = match.group(0)
        tag_lower = tag.lower()
        if not any(
            attr in tag_lower
            for attr in (
                'name="description"',
                "name='description'",
                'property="og:title"',
                "property='og:title'",
                'property="og:description"',
                "property='og:description'",
                'name="twitter:title"',
                "name='twitter:title'",
                'name="twitter:description"',
                "name='twitter:description'",
            )
        ):
            continue
        content_match = _CONTENT_RE.search(tag)
        if content_match:
            snippets.append(_strip_tags(content_match.group("text")))

    return snippets[:12]


def infer_sensitive_contexts(url: str, page_html: str | None) -> list[str]:
    """Infer sensitive page context from URL and first-party page text.

    This is a conservative risk signal. It exists to prioritize review when
    tracking technology is observed on pages whose path or text resembles the
    fact patterns in recent enforcement actions: health content, precise
    location or driving data, minors/students, video viewing, and financial data.
    """
    parsed = urlparse(url)
    haystack = " ".join(
        [
            parsed.netloc.lower(),
            parsed.path.lower().replace("-", " ").replace("_", " "),
            parsed.query.lower().replace("-", " ").replace("_", " "),
            *[snippet.lower() for snippet in _page_context_snippets(page_html)],
        ]
    )

    contexts: list[str] = []
    if any(term in haystack for term in _HEALTH_TERMS):
        contexts.append("health")
    if any(term in haystack for term in _LOCATION_TERMS):
        contexts.append("geolocation_or_driving")
    if any(term in haystack for term in _MINOR_TERMS):
        contexts.append("minor_or_student")
    if any(term in haystack for term in _VIDEO_TERMS):
        contexts.append("video_or_streaming")
    if any(term in haystack for term in _FINANCIAL_TERMS):
        contexts.append("financial")
    return contexts


def build_tracking_inventory(
    audit_result: AuditResult,
    *,
    gpc_pixel_firings: list[PixelFiring] | None = None,
    sensitive_contexts: list[str] | None = None,
) -> list[TrackingTechnology]:
    """Normalize cookies, pixel endpoints, and sSGTM into inventory rows."""
    contexts = sensitive_contexts or []
    by_key: dict[tuple[str, str, str], TrackingTechnology] = {}
    observed_after_opt_out = audit_result.methodology != MethodologyFlag.S1

    def _risk_for(category: str, exposure: str = "") -> tuple[SaleOrSharingRisk, bool]:
        cat = category.lower()
        exp = exposure.lower()
        if cat in {"advertising", "marketing", "targeting", "session_recording"}:
            return "likely", True
        if exp == "high":
            return "likely", True
        if cat in {"analytics", "functional"}:
            return "possible", cat == "analytics"
        return "possible", False

    def _upsert_pixel(pixel: PixelFiring, *, under_gpc: bool = False) -> None:
        risk, contract_review = _risk_for(pixel.category, pixel.legal_exposure)
        key = (pixel.vendor_name, pixel.category, "pixel")
        row = by_key.get(key)
        if row is None:
            row = TrackingTechnology(
                vendor_name=pixel.vendor_name,
                category=pixel.category,
                evidence_type="pixel",
                observed_after_opt_out=observed_after_opt_out,
                sale_or_sharing_risk=risk,
                contract_review_needed=contract_review,
                sensitive_contexts=list(contexts),
            )
            by_key[key] = row
        row.request_count += 1
        row.observed_under_gpc = row.observed_under_gpc or under_gpc
        if len(row.sample_urls) < 5 and pixel.url not in row.sample_urls:
            row.sample_urls.append(pixel.url)

    for pixel in audit_result.pixel_firings:
        _upsert_pixel(pixel)
    for pixel in gpc_pixel_firings or []:
        _upsert_pixel(pixel, under_gpc=True)

    for finding in audit_result.findings:
        risk, contract_review = _risk_for(
            finding.vendor.category, finding.vendor.legal_exposure
        )
        key = (finding.vendor.name, finding.vendor.category, "cookie")
        row = by_key.get(key)
        if row is None:
            row = TrackingTechnology(
                vendor_name=finding.vendor.name,
                category=finding.vendor.category,
                evidence_type="cookie",
                observed_after_opt_out=observed_after_opt_out,
                sale_or_sharing_risk=risk,
                contract_review_needed=contract_review,
                sensitive_contexts=list(contexts),
            )
            by_key[key] = row
        for cookie_name in finding.cookies_observed:
            if cookie_name not in row.cookies_observed:
                row.cookies_observed.append(cookie_name)

    if audit_result.ssgtm_detected and audit_result.ssgtm_domain:
        by_key[("Server-side GTM", "tag_management", "server_side")] = TrackingTechnology(
            vendor_name="Server-side GTM",
            category="tag_management",
            evidence_type="server_side",
            observed_after_opt_out=observed_after_opt_out,
            sample_urls=[audit_result.ssgtm_domain],
            sale_or_sharing_risk="possible",
            contract_review_needed=True,
            sensitive_contexts=list(contexts),
        )

    rows = sorted(by_key.values(), key=lambda r: (r.vendor_name.lower(), r.evidence_type))
    themes = _theme_keys_for_inventory(audit_result, rows, contexts)
    for row in rows:
        row.enforcement_theme_keys = sorted(themes.get(row.vendor_name, set()))
    return rows


def build_enforcement_themes(
    audit_result: AuditResult,
    *,
    sensitive_contexts: list[str] | None = None,
) -> list[EnforcementThemeFinding]:
    """Build a concise, de-duplicated set of enforcement themes."""
    contexts = sensitive_contexts or []
    themes: list[EnforcementThemeFinding] = []
    confirmed = [
        f for f in audit_result.findings if f.status == ViolationStatus.CONFIRMED
    ]
    observed_tracking = bool(confirmed or audit_result.pixel_firings)

    if observed_tracking:
        themes.append(
            EnforcementThemeFinding(
                key="opt_out_mechanism_failure",
                label="Opt-out mechanism failure",
                severity="high" if confirmed else "medium",
                evidence=[
                    f"{len(confirmed)} confirmed vendor finding(s)",
                    f"{len(audit_result.pixel_firings)} pixel endpoint firing(s)",
                ],
                regulatory_context=(
                    "Recent CPPA and California Attorney General matters focus on "
                    "whether opt-out choices suppress downstream tracking, not merely "
                    "whether an interface records a preference."
                ),
                recommended_action=(
                    "Re-test reject-all and GPC paths after each tag or CMP change."
                ),
            )
        )

    if (
        audit_result.gpc_tested
        and audit_result.gpc_signal_respected is False
        and audit_result.gpc_vendors_after_signal > 0
    ):
        themes.append(
            EnforcementThemeFinding(
                key="gpc_uoom_failure",
                label="GPC / universal opt-out failure",
                severity="critical",
                evidence=[
                    f"{audit_result.gpc_vendors_after_signal} pixel endpoint(s) fired under GPC",
                    f"baseline={audit_result.gpc_pixel_count_baseline}, gpc={audit_result.gpc_pixel_count_with_gpc}",
                ],
                regulatory_context=(
                    "California, Connecticut, Colorado, Oregon, and other states "
                    "treat opt-out preference signals as enforceable consumer choices."
                ),
                recommended_action=(
                    "Map Sec-GPC: 1 and navigator.globalPrivacyControl to the same "
                    "denied state used by manual opt-out."
                ),
            )
        )

    if audit_result.cmp_interaction_method in {
        "banner_click_failed",
        "banner_click_reverted",
    }:
        themes.append(
            EnforcementThemeFinding(
                key="consent_asymmetry",
                label="Consent asymmetry / opt-out friction",
                severity="high",
                evidence=[f"CMP interaction result: {audit_result.cmp_interaction_method}"],
                regulatory_context=(
                    "Recent California actions and regulations scrutinize whether "
                    "opting out is as easy as accepting and whether service access is "
                    "conditioned on tracking consent."
                ),
                recommended_action=(
                    "Review the banner manually: reject should be visible or require "
                    "no more steps than accept, and closing the banner must not imply consent."
                ),
            )
        )

    likely_sale_rows = [
        r for r in audit_result.tracking_inventory if r.sale_or_sharing_risk == "likely"
    ]
    if likely_sale_rows:
        themes.append(
            EnforcementThemeFinding(
                key="vendor_governance",
                label="Vendor and third-party governance",
                severity="high",
                evidence=[
                    f"{len(likely_sale_rows)} inventory row(s) likely require sale/sharing review"
                ],
                regulatory_context=(
                    "California enforcement has treated missing or overbroad ad-tech "
                    "contract terms as a primary violation, not just a paperwork issue."
                ),
                recommended_action=(
                    "Confirm each ad-tech, analytics, and pixel vendor has purpose-limited "
                    "contract terms and is classified in the tracking inventory."
                ),
            )
        )

    if contexts and likely_sale_rows:
        themes.append(
            EnforcementThemeFinding(
                key="sensitive_data_purpose_limitation",
                label="Sensitive data / purpose limitation",
                severity="critical" if "health" in contexts else "high",
                evidence=[
                    f"Sensitive context(s): {', '.join(contexts)}",
                    f"{len(likely_sale_rows)} likely sale/sharing row(s)",
                ],
                regulatory_context=(
                    "Healthline and GM show that regulators are applying purpose "
                    "limitation to sensitive page context, location, driving, and other "
                    "service data reused for advertising or data-broker purposes."
                ),
                recommended_action=(
                    "Block advertising and behavioral tracking on sensitive-context pages "
                    "unless a specific consent and purpose basis exists."
                ),
            )
        )

    if "minor_or_student" in contexts:
        themes.append(
            EnforcementThemeFinding(
                key="minors_privacy",
                label="Minor / student privacy",
                severity="critical",
                evidence=["Page context suggests children, students, or under-16 users"],
                regulatory_context=(
                    "Recent California, Florida, Kentucky, and Utah actions prioritize "
                    "minor data, student contexts, age gating, and affirmative consent."
                ),
                recommended_action=(
                    "Verify under-16 sale/sharing controls, age-appropriate notice, and "
                    "affirmative consent before targeted advertising."
                ),
            )
        )

    if audit_result.detected_cmp or audit_result.tracking_inventory:
        themes.append(
            EnforcementThemeFinding(
                key="tracking_inventory",
                label="Tracking technology inventory",
                severity="info",
                evidence=[
                    f"{len(audit_result.tracking_inventory)} inventory row(s) generated"
                ],
                regulatory_context=(
                    "Recent orders require current inventories of tracking technologies "
                    "and periodic scanning to catch drift."
                ),
                recommended_action=(
                    "Review and export this inventory quarterly and after every tag release."
                ),
            )
        )

    if audit_result.ssgtm_detected:
        themes.append(
            EnforcementThemeFinding(
                key="server_side_consent_gap",
                label="Server-side consent propagation gap",
                severity="high",
                evidence=[audit_result.ssgtm_domain or "server-side endpoint detected"],
                regulatory_context=(
                    "Server-side tags can continue sharing data after client-side opt-out "
                    "unless consent and GPC signals are explicitly propagated."
                ),
                recommended_action=(
                    "Audit the server-side container and verify GPC plus CMP state are "
                    "read before each outbound server tag fires."
                ),
            )
        )

    return themes


def _theme_keys_for_inventory(
    audit_result: AuditResult,
    rows: list[TrackingTechnology],
    contexts: list[str],
) -> dict[str, set[str]]:
    theme_keys: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        if row.observed_after_opt_out:
            theme_keys[row.vendor_name].add("opt_out_mechanism_failure")
        if row.observed_under_gpc:
            theme_keys[row.vendor_name].add("gpc_uoom_failure")
        if row.contract_review_needed:
            theme_keys[row.vendor_name].add("vendor_governance")
        if contexts and row.sale_or_sharing_risk == "likely":
            theme_keys[row.vendor_name].add("sensitive_data_purpose_limitation")
        if "minor_or_student" in contexts:
            theme_keys[row.vendor_name].add("minors_privacy")
    if audit_result.ssgtm_detected:
        theme_keys["Server-side GTM"].add("server_side_consent_gap")
    return theme_keys
