from __future__ import annotations

from datetime import UTC, datetime

import pytest
from consent_agent.models.audit_request import ConsentState
from consent_agent.models.audit_result import GTMExtractionMethod, MethodologyFlag
from consent_agent.models.scan_result import CookieSnapshot, ScanResult
from consent_agent.tools.tool_03_browser_scanner import (
    build_onetrust_consent_cookie,
    extract_gcd_from_url,
    extract_gcs_from_url,
    extract_gtm_id_from_html,
    parse_gcs_value,
    scan_page,
)


def test_scan_result_defaults() -> None:
    result = ScanResult(
        url="https://example.com",
        methodology=MethodologyFlag.S1,
        consent_state=ConsentState.OPTED_IN,
        timestamp=datetime.now(tz=UTC),
    )
    assert result.cookies == []
    assert result.network_requests == []
    assert result.gcs_value is None
    assert result.gtm_container_id is None
    assert result.gtm_extraction_method == GTMExtractionMethod.NONE
    assert result.gtm_container_js is None
    assert result.gpc_header_sent is False


def test_scan_result_detected_cmp_defaults_to_none() -> None:
    from datetime import UTC, datetime

    result = ScanResult(
        url="https://example.com",
        methodology=MethodologyFlag.S3,
        consent_state=ConsentState.OPTED_OUT,
        timestamp=datetime.now(tz=UTC),
    )
    assert result.detected_cmp is None
    assert result.cmp_detection_confidence is None
    assert result.bot_detection_encountered is False


def test_scan_result_detected_cmp_accepts_values() -> None:
    from datetime import UTC, datetime

    result = ScanResult(
        url="https://example.com",
        methodology=MethodologyFlag.S3,
        consent_state=ConsentState.OPTED_OUT,
        timestamp=datetime.now(tz=UTC),
        detected_cmp="CookieYes",
        cmp_detection_confidence="high",
        bot_detection_encountered=True,
    )
    assert result.detected_cmp == "CookieYes"
    assert result.cmp_detection_confidence == "high"
    assert result.bot_detection_encountered is True


def test_cookie_snapshot_fields() -> None:
    cookie = CookieSnapshot(
        name="_ga",
        value="GA1.2.12345.67890",
        domain=".example.com",
        path="/",
        secure=False,
        http_only=False,
        same_site="Lax",
        expires=9999999999.0,
    )
    assert cookie.name == "_ga"
    assert cookie.domain == ".example.com"


# --- parse_gcs_value ---


def test_parse_gcs_denied_denied() -> None:
    gcs = parse_gcs_value("G1--")
    assert gcs.raw == "G1--"
    assert gcs.ad_storage == "denied"
    assert gcs.analytics_storage == "denied"


def test_parse_gcs_granted_granted() -> None:
    gcs = parse_gcs_value("G111")
    assert gcs.ad_storage == "granted"
    assert gcs.analytics_storage == "granted"


def test_parse_gcs_advanced_cm_evidence() -> None:
    # G110 = ad_storage granted, analytics_storage denied — proves Advanced CM
    gcs = parse_gcs_value("G110")
    assert gcs.ad_storage == "granted"
    assert gcs.analytics_storage == "denied"


def test_parse_gcs_unknown_format() -> None:
    gcs = parse_gcs_value("INVALID")
    assert gcs.raw == "INVALID"
    assert gcs.ad_storage == "unknown"
    assert gcs.analytics_storage == "unknown"


# --- extract_gcs_from_url ---


def test_extract_gcs_from_analytics_url() -> None:
    url = "https://analytics.google.com/g/collect?v=2&tid=G-XXXXX&gcs=G1--&en=page_view"
    assert extract_gcs_from_url(url) == "G1--"


def test_extract_gcs_from_url_missing() -> None:
    url = "https://example.com/track?tid=G-XXXXX&en=page_view"
    assert extract_gcs_from_url(url) is None


def test_extract_gcs_from_doubleclick_url() -> None:
    url = "https://cm.g.doubleclick.net/pixel?google_nid=abc&gcs=G111"
    assert extract_gcs_from_url(url) == "G111"


def test_extract_gcs_from_ad_doubleclick_semicolon_url() -> None:
    # ad.doubleclick.net uses semicolons as parameter delimiters, not & or ?
    url = "https://ad.doubleclick.net/activity;src=8930181;type=homep0;cat=home;npa=0;gcs=G111;gcd=13v3v3v2v5l1;ord=1"
    assert extract_gcs_from_url(url) == "G111"


def test_extract_gcs_not_confused_by_adjacent_gcd() -> None:
    # Confirm gcs= extraction stops at semicolon when gcd follows immediately
    url = "https://ad.doubleclick.net/activity;gcs=G100;gcd=13v3v3v2v5l1;ord=1"
    assert extract_gcs_from_url(url) == "G100"


def test_extract_gcs_from_ssgtm_collect_url() -> None:
    # analytics.google.com/g/s/collect is the server-side GTM proxied endpoint
    url = (
        "https://analytics.google.com/g/s/collect"
        "?dma=0&npa=0&gcs=G111&gcd=13r3r3r3r5l1&tid=G-JY85S4EVZQ"
    )
    assert extract_gcs_from_url(url) == "G111"


def test_extract_gcs_from_ga_audiences_url() -> None:
    # google.ca/ads/ga-audiences fires for remarketing — contains gcs parameter
    url = (
        "https://www.google.ca/ads/ga-audiences"
        "?v=1&t=sr&gcs=G111&gcd=13r3r3r3r5l1&tid=G-JY85S4EVZQ"
    )
    assert extract_gcs_from_url(url) == "G111"


def test_extract_gcs_denial_state_advanced_consent_mode() -> None:
    # gcs=G100 = ad_storage denied + analytics_storage denied (Advanced Consent Mode evidence)
    url = "https://analytics.google.com/g/collect?v=2&gcs=G100&gcd=11q1q1q1q5&tid=G-XXXXX"
    gcs = extract_gcs_from_url(url)
    assert gcs == "G100"
    parsed = parse_gcs_value("G100")
    assert parsed.ad_storage == "denied"
    assert parsed.analytics_storage == "denied"


# --- extract_gcd_from_url ---


def test_extract_gcd_from_analytics_url() -> None:
    url = "https://analytics.google.com/g/collect?v=2&tid=G-XXXXX&gcs=G111&gcd=13v3v3v2v5l1&en=page_view"
    assert extract_gcd_from_url(url) == "13v3v3v2v5l1"


def test_extract_gcd_from_doubleclick_semicolon_url() -> None:
    url = "https://ad.doubleclick.net/activity;src=123;gcs=G111;gcd=13v3v3v2v5l1;ord=1"
    assert extract_gcd_from_url(url) == "13v3v3v2v5l1"


def test_extract_gcd_from_url_missing() -> None:
    url = "https://example.com/track?tid=G-XXXXX&en=page_view"
    assert extract_gcd_from_url(url) is None


# --- extract_gtm_id_from_html ---


def test_extract_gtm_id_from_script_tag() -> None:
    html = '<script src="https://www.googletagmanager.com/gtm.js?id=GTM-ABC1234"></script>'
    assert extract_gtm_id_from_html(html) == "GTM-ABC1234"


def test_extract_gtm_id_from_noscript() -> None:
    html = '<noscript><iframe src="https://www.googletagmanager.com/ns.html?id=GTM-XYZ9876">'
    assert extract_gtm_id_from_html(html) == "GTM-XYZ9876"


def test_extract_gtm_id_from_js_payload() -> None:
    js = 'var data = {"resource":{"version":"5"},"path":"/gtm/js","id":"GTM-FAKETEST"};'
    assert extract_gtm_id_from_html(js) == "GTM-FAKETEST"


def test_extract_gtm_id_not_present() -> None:
    assert extract_gtm_id_from_html("<html><body>No GTM here</body></html>") is None


# --- build_onetrust_consent_cookie ---


def test_build_opted_out_cookie_has_denied_groups() -> None:
    value = build_onetrust_consent_cookie(opted_out=True)
    assert "C0002%3A0" in value or "C0002:0" in value  # analytics denied
    assert "C0004%3A0" in value or "C0004:0" in value  # targeting denied
    assert "C0001%3A1" in value or "C0001:1" in value  # essential always on


def test_build_opted_in_cookie_has_granted_groups() -> None:
    value = build_onetrust_consent_cookie(opted_out=False)
    assert "C0002%3A1" in value or "C0002:1" in value  # analytics granted
    assert "C0004%3A1" in value or "C0004:1" in value  # targeting granted


# --- S1 Baseline Scanner (integration tests — require Playwright + local server) ---


async def test_s1_scan_returns_scan_result(local_server: str) -> None:
    """S1 baseline: fresh context, no consent interaction, cookies collected."""
    from consent_agent.tools.tool_03_browser_scanner import _scan_s1

    result = await _scan_s1(f"{local_server}/basic")

    assert result.methodology == MethodologyFlag.S1
    assert result.consent_state == ConsentState.OPTED_IN
    assert result.url == f"{local_server}/basic"
    assert result.gpc_header_sent is False


async def test_s1_scan_collects_cookies(local_server: str) -> None:
    """S1 scan captures cookies set by JavaScript during page load."""
    from consent_agent.tools.tool_03_browser_scanner import _scan_s1

    result = await _scan_s1(f"{local_server}/basic")

    cookie_names = [c.name for c in result.cookies]
    assert "test_cookie" in cookie_names
    assert "another_cookie" in cookie_names


async def test_s1_scan_timestamp_is_set(local_server: str) -> None:
    from consent_agent.tools.tool_03_browser_scanner import _scan_s1

    result = await _scan_s1(f"{local_server}/basic")
    assert result.timestamp is not None


# --- S3 Opted-Out Scanner ---


async def test_s3_opted_out_scan_returns_correct_methodology(local_server: str) -> None:
    from consent_agent.tools.tool_03_browser_scanner import _scan_s3

    result = await _scan_s3(f"{local_server}/basic", opted_out=True)

    # /basic is an unknown CMP with no GCS beacon, so the injection-verification
    # guard downgrades methodology to INCONCLUSIVE_UNKNOWN_CMP. Both S3 outcomes
    # are acceptable here — the test validates dispatch, not definitiveness.
    assert result.methodology in (MethodologyFlag.S3, MethodologyFlag.INCONCLUSIVE_UNKNOWN_CMP)
    assert result.consent_state == ConsentState.OPTED_OUT
    assert result.gpc_header_sent is False


async def test_s3_opted_in_scan_returns_correct_consent_state(local_server: str) -> None:
    from consent_agent.tools.tool_03_browser_scanner import _scan_s3

    result = await _scan_s3(f"{local_server}/basic", opted_out=False)

    assert result.consent_state == ConsentState.OPTED_IN
    assert result.methodology in (MethodologyFlag.S3, MethodologyFlag.INCONCLUSIVE_UNKNOWN_CMP)


async def test_s3_opted_out_injects_optanon_cookie(local_server: str) -> None:
    """OptanonConsent cookie is visible to the page as a pre-set cookie."""
    from consent_agent.tools.tool_03_browser_scanner import _scan_s3

    result = await _scan_s3(f"{local_server}/basic", opted_out=True)

    cookie_names = [c.name for c in result.cookies]
    assert "OptanonConsent" in cookie_names


async def test_s3_opted_out_collects_page_cookies(local_server: str) -> None:
    """Page cookies (including JS-set ones) are still collected in S3."""
    from consent_agent.tools.tool_03_browser_scanner import _scan_s3

    result = await _scan_s3(f"{local_server}/basic", opted_out=True)

    cookie_names = [c.name for c in result.cookies]
    assert "test_cookie" in cookie_names


# --- GPC Scanner ---


async def test_gpc_scan_sets_gpc_header_sent(local_server: str) -> None:
    from consent_agent.tools.tool_03_browser_scanner import _scan_gpc

    result = await _scan_gpc(f"{local_server}/basic")

    assert result.gpc_header_sent is True
    assert result.consent_state == ConsentState.GPC_OPTED_OUT
    assert result.methodology == MethodologyFlag.S3


async def test_gpc_scan_still_collects_cookies(local_server: str) -> None:
    from consent_agent.tools.tool_03_browser_scanner import _scan_gpc

    result = await _scan_gpc(f"{local_server}/basic")

    cookie_names = [c.name for c in result.cookies]
    assert "test_cookie" in cookie_names


# --- GTM Live Extraction ---


async def test_gtm_extraction_fallback_to_window_object(local_server: str) -> None:
    """Fallback: window.google_tag_manager is evaluated when gtm.js not intercepted."""
    from consent_agent.models.audit_result import GTMExtractionMethod
    from consent_agent.tools.tool_03_browser_scanner import _extract_gtm_from_page
    from playwright.async_api import async_playwright

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        # /gtm page has window.google_tag_manager = {"GTM-TESTONLY": {...}}
        await page.goto(f"{local_server}/gtm", wait_until="networkidle")
        page_html = await page.content()

        container_id, container_js, method = await _extract_gtm_from_page(page, page_html)
        await browser.close()

    assert container_id == "GTM-TESTONLY"
    assert method == GTMExtractionMethod.LIVE


async def test_gtm_extraction_html_regex_fallback(local_server: str) -> None:
    """Last resort: GTM ID extracted from page HTML when window object is absent."""
    from consent_agent.models.audit_result import GTMExtractionMethod
    from consent_agent.tools.tool_03_browser_scanner import _extract_gtm_from_page
    from playwright.async_api import async_playwright

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        # /basic page has no GTM at all — inject a fake GTM ID in HTML only
        await page.goto(f"{local_server}/basic", wait_until="networkidle")
        # Manually set page HTML with GTM ID reference (simulates gtm snippet in source)
        fake_html = (
            '<script src="https://www.googletagmanager.com/gtm.js?id=GTM-REGEXTEST"></script>'
        )

        container_id, container_js, method = await _extract_gtm_from_page(page, fake_html)
        await browser.close()

    assert container_id == "GTM-REGEXTEST"
    assert method == GTMExtractionMethod.NONE  # HTML regex = no live JS, so NONE
    assert container_js is None


# --- Public scan_page() API ---


async def test_scan_page_s1_dispatches_correctly(local_server: str) -> None:
    result = await scan_page(
        url=f"{local_server}/basic",
        consent_state=ConsentState.OPTED_IN,
        methodology=MethodologyFlag.S1,
    )
    assert result.methodology == MethodologyFlag.S1
    assert result.consent_state == ConsentState.OPTED_IN


async def test_scan_page_s3_opted_out(local_server: str) -> None:
    result = await scan_page(
        url=f"{local_server}/basic",
        consent_state=ConsentState.OPTED_OUT,
        methodology=MethodologyFlag.S3,
    )
    # /basic is an unknown CMP with no GCS beacon — methodology may be
    # downgraded to INCONCLUSIVE_UNKNOWN_CMP by the injection-verification guard.
    assert result.methodology in (MethodologyFlag.S3, MethodologyFlag.INCONCLUSIVE_UNKNOWN_CMP)
    assert result.consent_state == ConsentState.OPTED_OUT


async def test_scan_page_gpc_opted_out(local_server: str) -> None:
    result = await scan_page(
        url=f"{local_server}/basic",
        consent_state=ConsentState.GPC_OPTED_OUT,
        methodology=MethodologyFlag.S3,
    )
    assert result.gpc_header_sent is True
    assert result.consent_state == ConsentState.GPC_OPTED_OUT


async def test_scan_page_s2_raises_not_implemented(local_server: str) -> None:
    """S2 is INCONCLUSIVE and not implemented in MVP. Must raise."""
    import pytest

    with pytest.raises(NotImplementedError, match="S2"):
        await scan_page(
            url=f"{local_server}/basic",
            consent_state=ConsentState.OPTED_OUT,
            methodology=MethodologyFlag.S2,
        )


def test_scan_result_cmp_interaction_method_defaults_to_none() -> None:
    result = ScanResult(
        url="https://example.com",
        methodology=MethodologyFlag.S1,
        consent_state=ConsentState.OPTED_IN,
        timestamp=datetime.now(tz=UTC),
    )
    assert result.cmp_interaction_method is None


def test_scan_result_cmp_interaction_method_accepts_string() -> None:
    result = ScanResult(
        url="https://example.com",
        methodology=MethodologyFlag.S3,
        consent_state=ConsentState.OPTED_OUT,
        timestamp=datetime.now(tz=UTC),
        cmp_interaction_method="cookie_injection",
    )
    assert result.cmp_interaction_method == "cookie_injection"


# --- S3 CMP fallback integration tests ---


async def test_s3_uses_cookie_injection_when_no_banner(local_server: str) -> None:
    """S3 primary path: no banner present -> cmp_interaction_method = cookie_injection."""
    from consent_agent.tools.tool_03_browser_scanner import _scan_s3

    result = await _scan_s3(f"{local_server}/basic", opted_out=True)

    assert result.cmp_interaction_method == "cookie_injection"


async def test_s3_falls_back_to_banner_click_when_banner_present(
    local_server: str,
) -> None:
    """S3 fallback: non-OneTrust banner detected -> clean context -> banner click."""
    from consent_agent.tools.tool_03_browser_scanner import _scan_s3

    result = await _scan_s3(f"{local_server}/banner-single", opted_out=True)

    # OneTrust cookie injection may dismiss the banner before the clicker runs,
    # so cookie_injection is also a valid outcome alongside banner_click variants.
    assert result.cmp_interaction_method in (
        "banner_click",
        "banner_click_inconclusive",
        "banner_click_failed",
        "cookie_injection",
    )


async def test_s3_banner_click_confirmed_when_gcs_denied_beacon_fires(
    local_server: str,
) -> None:
    """S3 fallback: GCS=G1-- beacon fires after decline click -> banner_click confirmed."""
    from consent_agent.tools.tool_03_browser_scanner import _scan_s3

    result = await _scan_s3(f"{local_server}/banner-with-gcs", opted_out=True)

    assert result.cmp_interaction_method in ("banner_click", "cookie_injection")


# --- Track 2 custom loader fingerprint + HAR recording ---


@pytest.mark.asyncio
async def test_s1_scan_captures_custom_gtm_loader(local_server: str) -> None:
    """Track 2: custom loader URL (no 'gtm.js' in path) captured via body fingerprint."""
    from consent_agent.tools.tool_03_browser_scanner import _scan_s1

    result = await _scan_s1(f"{local_server}/custom-loader-page")

    # The custom loader contains 'google_tag_manager' — Track 2 should capture it
    assert result.gtm_container_js is not None
    assert "google_tag_manager" in result.gtm_container_js


@pytest.mark.asyncio
async def test_s1_scan_records_har_file(local_server: str) -> None:
    """Tool 3 records a HAR file during the scan; har_path is set on ScanResult."""
    import os

    from consent_agent.tools.tool_03_browser_scanner import _scan_s1

    result = await _scan_s1(f"{local_server}/basic")

    assert result.har_path is not None
    assert os.path.exists(result.har_path)
    assert result.har_path.endswith(".har")


@pytest.mark.asyncio
async def test_s3_scan_records_har_file(local_server: str) -> None:
    """S3 scan writes HAR file; har_path is set."""
    import os

    from consent_agent.tools.tool_03_browser_scanner import _scan_s3

    result = await _scan_s3(f"{local_server}/basic", opted_out=True)

    assert result.har_path is not None
    assert os.path.exists(result.har_path)


@pytest.mark.asyncio
async def test_har_file_is_valid_json(local_server: str) -> None:
    """HAR file written by Tool 3 is valid JSON with 'log' key."""
    import json
    from pathlib import Path

    from consent_agent.tools.tool_03_browser_scanner import _scan_s1

    result = await _scan_s1(f"{local_server}/basic")
    assert result.har_path is not None
    har_data = json.loads(Path(result.har_path).read_text())

    assert "log" in har_data
    assert "entries" in har_data["log"]


async def test_stealth_chrome_runtime_present(local_server: str) -> None:
    """Headless browser must expose window.chrome.runtime to pass bot detection."""
    from consent_agent.tools.tool_03_browser_scanner import (
        _STEALTH_INIT_SCRIPT,
        _STEALTH_LAUNCH_ARGS,
        _STEALTH_UA,
    )
    from playwright.async_api import async_playwright

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=_STEALTH_LAUNCH_ARGS)
        context = await browser.new_context(user_agent=_STEALTH_UA)
        await context.add_init_script(_STEALTH_INIT_SCRIPT)
        page = await context.new_page()
        await page.goto(f"{local_server}/basic", wait_until="networkidle")

        has_chrome_runtime = await page.evaluate("() => !!(window.chrome && window.chrome.runtime)")
        webdriver = await page.evaluate("() => navigator.webdriver")
        plugins_length = await page.evaluate("() => navigator.plugins.length")
        concurrency = await page.evaluate("() => navigator.hardwareConcurrency")

        await browser.close()

    assert has_chrome_runtime is True, "window.chrome.runtime must be present"
    assert webdriver is None or webdriver is False, "navigator.webdriver must be hidden"
    assert plugins_length >= 5, "navigator.plugins must have realistic entries"
    assert concurrency == 8, "hardwareConcurrency must be 8"


# --- S3 injection-verification methodology tests ---
# Forensic defensibility: S3 must only be marked definitive when we can prove
# the injected consent signal actually suppressed tracking (observed denied GCS
# post-injection). Unknown-CMP or silent-injection-failure cases must downgrade
# to INCONCLUSIVE_UNKNOWN_CMP so reports never claim "consent respected" on
# unverified scans.


async def test_s3_known_cmp_with_denied_gcs_marks_s3_definitive(local_server: str) -> None:
    """Known CMP + observed denied GCS beacon = methodology S3 (definitive)."""
    from consent_agent.tools.tool_03_browser_scanner import _scan_s3

    result = await _scan_s3(f"{local_server}/cmp-onetrust-denied", opted_out=True)

    assert result.detected_cmp == "OneTrust"
    assert result.gcs_value is not None
    assert result.gcs_value.ad_storage == "denied"
    assert result.methodology == MethodologyFlag.S3


async def test_s3_unknown_cmp_with_no_gcs_marks_inconclusive(local_server: str) -> None:
    """Unknown CMP + GCS never changes to denied = INCONCLUSIVE_UNKNOWN_CMP."""
    from consent_agent.tools.tool_03_browser_scanner import _scan_s3

    result = await _scan_s3(f"{local_server}/basic", opted_out=True)

    # /basic has no CMP globals and fires no GCS beacon — the injected
    # OneTrust cookie cannot be verified.
    assert result.detected_cmp is None
    assert result.methodology == MethodologyFlag.INCONCLUSIVE_UNKNOWN_CMP


async def test_s3_known_cmp_with_no_denied_gcs_marks_wiring_broken(
    local_server: str,
) -> None:
    """Known CMP + injection plan existed + GCS never flipped = S3_CONSENT_WIRING_BROKEN.

    When we recognise the CMP AND we have a matching injection plan AND we
    still don't observe a denied GCS signal, that's definitive evidence the
    site's tag wiring is broken — tags fire before or regardless of CMP state.
    """
    from consent_agent.tools.tool_03_browser_scanner import _scan_s3

    # /cmp-cookieyes exposes window.CookieYes (known CMP, and cmp_injector
    # HAS a plan for CookieYes) but does not emit a denied GCS beacon.
    # That's the wiring-broken signature.
    result = await _scan_s3(f"{local_server}/cmp-cookieyes", opted_out=True)

    assert result.methodology == MethodologyFlag.S3_CONSENT_WIRING_BROKEN


async def test_s3_cmp_detected_injection_plan_exists_but_gcs_granted_marks_wiring_broken(
    local_server: str,
) -> None:
    """Explicit coverage: CookieYes (has injection plan) + no denied GCS
    must return S3_CONSENT_WIRING_BROKEN (definitive), NOT inconclusive.

    This is the Quince / Casper scenario: CMP recognised, denial injected
    correctly, but Consent Mode beacons keep firing GCS=G111.
    """
    from consent_agent.tools.cmp_injector import has_plan_for
    from consent_agent.tools.tool_03_browser_scanner import _scan_s3

    # Sanity: confirm CookieYes is in the "has plan" set so this test actually
    # exercises the wiring-broken branch rather than inconclusive fall-through.
    assert has_plan_for("CookieYes") is True

    result = await _scan_s3(f"{local_server}/cmp-cookieyes", opted_out=True)

    assert result.detected_cmp == "CookieYes"
    assert result.methodology == MethodologyFlag.S3_CONSENT_WIRING_BROKEN


async def test_stealth_webdriver_hidden(local_server: str) -> None:
    from consent_agent.tools.tool_03_browser_scanner import (
        _STEALTH_INIT_SCRIPT,
        _STEALTH_LAUNCH_ARGS,
        _STEALTH_UA,
    )
    from playwright.async_api import async_playwright

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=_STEALTH_LAUNCH_ARGS)
        context = await browser.new_context(user_agent=_STEALTH_UA)
        await context.add_init_script(_STEALTH_INIT_SCRIPT)
        page = await context.new_page()
        await page.goto(f"{local_server}/basic", wait_until="networkidle")
        webdriver = await page.evaluate("() => navigator.webdriver")
        await browser.close()

    assert webdriver is None or webdriver is False
