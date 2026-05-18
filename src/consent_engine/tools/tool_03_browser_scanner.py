"""Tool 3 — Headless Browser Scanner.

S3 = fresh browser context, consent pre-set before load (DEFINITIVE)
S2 = post-opt-out without reload (INCONCLUSIVE — never marked definitive)
GPC test: sends Sec-GPC: 1 header in gpc_opted_out runs
"""

from __future__ import annotations

import asyncio
import base64
import contextlib
import json
import os
import re
import tempfile
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any, cast
from urllib.parse import parse_qs, urlparse

from patchright.async_api import Page, ProxySettings, Request, Route, async_playwright

from consent_engine.models.audit_request import ConsentState
from consent_engine.models.audit_result import GCSValue, GTMExtractionMethod, MethodologyFlag
from consent_engine.models.scan_result import CookieSnapshot, ScanResult
from consent_engine.tools.cmp_clicker import _banner_present, attempt_cmp_decline

# ---------------------------------------------------------------------------
# Pure helper functions (no Playwright)
# ---------------------------------------------------------------------------

_GCS_RE = re.compile(r"[?&;]gcs=([^&;]+)")
_GCD_RE = re.compile(r"[?&;]gcd=([^&;]+)")
_GCS_FRAG_RE = re.compile(r"/gcs=([^/&;]+)")  # Handle path-based signals in some SSGTM setups

# Stape custom loader / SSGTM first-party collect detection
_FIRST_PARTY_COLLECT_RE = re.compile(r"/g/collect\b")
_STAPE_LOADER_HINTS = re.compile(r"x-gtm-|stape\.io|cf-worker|/sky/|custom.loader", re.IGNORECASE)


async def _apply_geoip_spoofing(page: Page) -> None:
    """Spoof US/CA location for TrueVault/Polaris to ensure CCPA UI is visible."""

    async def _handle_polaris_location(route: Route) -> None:
        with contextlib.suppress(Exception):
            await route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({"country": "US", "region": "CA"}),
            )

    await page.route("https://location.truevaultcdn.com/", _handle_polaris_location)


# ---------------------------------------------------------------------------
# Stealth browser configuration — evades common headless detection
# ---------------------------------------------------------------------------

_STEALTH_LAUNCH_ARGS: list[str] = [
    "--disable-blink-features=AutomationControlled",
    "--disable-dev-shm-usage",
    "--no-first-run",
    "--no-service-autorun",
    "--password-store=basic",
]

_STEALTH_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/136.0.0.0 Safari/537.36"
)

_STEALTH_INIT_SCRIPT = """
(function() {
    // 1. Hide webdriver flag
    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});

    // 2. Realistic navigator.plugins — PluginArray with 5 PDF viewer entries
    //    A plain JS array is the wrong type; this creates proper plugin-like objects.
    const _pluginData = [
        ['PDF Viewer', 'internal-pdf-viewer', 'Portable Document Format'],
        ['Chrome PDF Viewer', 'mhjfbmdgcfjbbpaeojofohoefgiehjai', 'Portable Document Format'],
        ['Chromium PDF Viewer', 'internal-pdf-viewer', 'Portable Document Format'],
        ['Microsoft Edge PDF Viewer', 'internal-pdf-viewer', 'Portable Document Format'],
        ['WebKit built-in PDF', 'internal-pdf-viewer', 'Portable Document Format'],
    ];
    const _plugins = _pluginData.map(([name, filename, description]) => ({
        name, filename, description, length: 1,
        item: () => null, namedItem: () => null, refresh: () => {},
    }));
    Object.defineProperty(navigator, 'plugins', {
        get: () => Object.assign(_plugins, {
            item: (i) => _plugins[i] ?? null,
            namedItem: (n) => _plugins.find(p => p.name === n) ?? null,
            refresh: () => {},
            length: _plugins.length,
            [Symbol.iterator]: function*() { yield* _plugins; },
        }),
    });

    // 3. window.chrome.runtime — absence is one of the strongest bot signals
    if (!window.chrome) {
        const _noop = () => {};
        const _noopListener = {addListener: _noop, removeListener: _noop, hasListener: _noop};
        window.chrome = {
            runtime: {
                id: undefined,
                onConnect: _noopListener,
                onMessage: _noopListener,
                onInstalled: _noopListener,
                connect: () => ({onMessage: _noopListener, postMessage: _noop, disconnect: _noop}),
                sendMessage: _noop,
                getManifest: () => ({}),
                getURL: (path) => 'chrome-extension://invalid/' + path,
            },
            loadTimes: _noop,
            csi: _noop,
            app: {isInstalled: false},
        };
    }

    // 4. navigator.permissions — notifications should be 'prompt', not 'denied'
    if (navigator.permissions && navigator.permissions.query) {
        const _origQuery = navigator.permissions.query.bind(navigator.permissions);
        navigator.permissions.query = (params) => {
            if (params && params.name === 'notifications') {
                return Promise.resolve({state: 'prompt', onchange: null});
            }
            return _origQuery(params);
        };
    }

    // 5. Realistic hardware concurrency (headless default is 1)
    Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});

    // 6. Consistent language list
    Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});

    // 7. outerHeight/outerWidth — headless returns 0, real browsers match viewport
    if (window.outerHeight === 0) {
        Object.defineProperty(window, 'outerHeight', {get: () => window.innerHeight || 800});
        Object.defineProperty(window, 'outerWidth',  {get: () => window.innerWidth  || 1280});
    }

    // 8. Canvas fingerprint — add imperceptible per-session noise
    const _origToDataURL = HTMLCanvasElement.prototype.toDataURL;
    HTMLCanvasElement.prototype.toDataURL = function(type, quality) {
        const ctx = this.getContext('2d');
        if (ctx) {
            const imageData = ctx.getImageData(0, 0, 1, 1);
            imageData.data[0] = (imageData.data[0] + 1) % 256;
            ctx.putImageData(imageData, 0, 0);
        }
        return _origToDataURL.call(this, type, quality);
    };
})();
"""
_GTM_ID_RE = re.compile(r"GTM-[A-Z0-9]+")
_GTM_URL_ID_RE = re.compile(r"[?&]id=(GTM-[A-Z0-9]+)")


def _is_custom_loader_gtm(url: str) -> bool:
    """Return True if the URL looks like a Stape/SSGTM custom loader GTM script.

    Custom loaders serve gtm.js from first-party paths like /sky/?a6k=GTM-XXXX
    instead of googletagmanager.com/gtm.js. We detect them by looking for
    GTM container IDs in query parameters of non-Google URLs.
    """
    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    if "googletagmanager.com" in hostname or "google" in hostname:
        return False
    # Check for GTM ID in query params (e.g. ?a6k=GTM-TC5W92GQ or ?id=GTM-XXXX)
    if _GTM_URL_ID_RE.search(url):
        return True
    qs = parse_qs(parsed.query)
    for _values in qs.values():
        for v in _values:
            if _GTM_ID_RE.match(v):
                return True
    return False


async def _read_consent_mode_from_page(page: Page) -> str | None:
    """Read the current Google Consent Mode state directly from the page's JS runtime.

    After CMP initialization, the consent state is stored in google_tag_data.ics.entries
    or can be inferred from the dataLayer. This catches cases where the CMP updates
    consent mode AFTER the initial GA4 hit (e.g. Stape custom loader fires G111 before
    CookieYes loads and sets consent to denied).

    Returns a synthetic GCS string (e.g. 'G100') or None if unavailable.
    """
    try:
        result = await asyncio.wait_for(
            page.evaluate("""() => {
            // Method 1: google_tag_data.ics.entries (internal gtag consent state)
            // ICS entries use two formats depending on gtag version:
            //   - String: {default: 'denied', update: 'denied'}
            //   - Boolean: {default: false, update: false}  (false = denied)
            // When update is boolean false, no explicit update was applied —
            // fall back to the default field to determine consent state.
            try {
                const ics = window.google_tag_data?.ics?.entries;
                if (ics) {
                    function isDenied(val) {
                        // Check update first; if it's a real value use it
                        if (val.update === 'denied') return true;
                        if (val.update === 'granted') return false;
                        // Boolean false means no update applied — use default
                        if (val.update === false || val.update === undefined) {
                            if (val.default === 'denied' || val.default === false) return true;
                            if (val.default === 'granted' || val.default === true) return false;
                        }
                        // Boolean true in update means granted
                        if (val.update === true) return false;
                        return false; // default to granted if unclear
                    }
                    let ad = '1', analytics = '1';
                    for (const [key, val] of Object.entries(ics)) {
                        if (key === 'ad_storage' && isDenied(val)) ad = '0';
                        if (key === 'analytics_storage' && isDenied(val)) analytics = '0';
                    }
                    return 'G1' + ad + analytics;
                }
            } catch(e) {}

            // Method 2: dataLayer consent commands
            try {
                const dl = window.dataLayer;
                if (dl) {
                    for (let i = dl.length - 1; i >= 0; i--) {
                        const entry = dl[i];
                        if (entry && entry[0] === 'consent' && entry[1] === 'update') {
                            const params = entry[2] || {};
                            const ad = params.ad_storage === 'denied' ? '0' : '1';
                            const analytics = params.analytics_storage === 'denied' ? '0' : '1';
                            return 'G1' + ad + analytics;
                        }
                    }
                }
            } catch(e) {}

            // Method 3: consentState on gtag (if exposed)
            try {
                if (window.gtag) {
                    // Can't directly query gtag, but googlefc or __tcfapi might help
                    // Fall through to null
                }
            } catch(e) {}

            return null;
        }"""),
            timeout=3.0,
        )
        return result if isinstance(result, str) else None
    except (TimeoutError, Exception):  # noqa: BLE001
        return None


def parse_gcs_value(gcs_str: str) -> GCSValue:
    """Parse a raw GCS parameter value into structured consent signal data.

    Format: G{version}{ad_storage}{analytics_storage}[...]
      - '1' = granted
      - '0' or '-' = denied / not set

    Examples:
      G1--  -> denied/denied  (consent denied -- proves Advanced CM if present)
      G111  -> granted/granted
      G100  -> ad granted, analytics denied
    """

    def _decode(bit: str) -> str:
        return "granted" if bit == "1" else "denied"

    if len(gcs_str) < 4 or not gcs_str.startswith("G"):
        return GCSValue(raw=gcs_str, ad_storage="unknown", analytics_storage="unknown")

    return GCSValue(
        raw=gcs_str,
        ad_storage=_decode(gcs_str[2]),
        analytics_storage=_decode(gcs_str[3]),
    )


def extract_gcs_from_url(url: str) -> str | None:
    """Extract the raw GCS parameter value from a URL, or None if not present."""
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    values = qs.get("gcs")
    if values:
        return values[0]
    match = _GCS_RE.search(url)
    return match.group(1) if match else None


def extract_gcd_from_url(url: str) -> str | None:
    """Extract the raw GCD parameter value from a URL, or None if not present.

    GCD (Google Consent Detail) is the V2 consent signal encoding default and
    update states for ad_storage, analytics_storage, ad_user_data, and
    ad_personalization. Present alongside GCS in GA4 / doubleclick requests.
    """
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    values = qs.get("gcd")
    if values:
        return values[0]
    match = _GCD_RE.search(url)
    return match.group(1) if match else None


def is_gcd_denied_state(gcd_raw: str) -> bool:
    """Return True if the GCD parameter indicates all consent signals are in denied state.

    GCD encodes (default_state, update_state) per signal. Full letter table
    verified April 2026 against Simo Ahava + Google developer docs:

        p = denied default, no update yet             -> DENIED
        q = denied default, user confirmed denied     -> DENIED
        u = granted default, user downgraded denied   -> DENIED
        m = no default, denied on update              -> DENIED

        t = granted default, no update yet            -> GRANTED
        v = granted default, user confirmed granted   -> GRANTED
        r = denied default, user upgraded to granted  -> GRANTED
        n = no default, granted on update             -> GRANTED

        l = consent mode not active (neither set)     -> unclassified

    Classification note: 'u' = granted→denied (DENIED). 'r' = denied→granted (GRANTED).
    The GCD prefix digits (e.g. '11') and suffix ('5' or '7') are internal Google
    metadata and can vary — parse only the letter slots, not the full string.

    Returns True only when at least one denied letter is present and no granted
    letters are present — i.e., the GCD confirms denied state for all signals.
    """
    _DENIED = frozenset("pqmu")
    _GRANTED = frozenset("vrtn")
    letters = {c for c in gcd_raw if c.isalpha()}
    return bool(letters & _DENIED) and not bool(letters & _GRANTED)


def extract_gtm_id_from_html(html_or_js: str) -> str | None:
    """Extract a GTM container ID (GTM-XXXXXX) from HTML or JS source."""
    # 1. Look for gtm.js?id=GTM-XXXX
    url_match = _GTM_URL_ID_RE.search(html_or_js)
    if url_match:
        return url_match.group(1)

    # 2. Look for raw GTM-XXXX
    match = _GTM_ID_RE.search(html_or_js)
    return match.group(0) if match else None


def build_onetrust_consent_cookie(opted_out: bool) -> str:
    """Build an OptanonConsent cookie value for OneTrust consent injection.

    Used in S3 methodology to pre-set consent state before page load.

    OneTrust categories:
        C0001 = Essential (always 1)
        C0002 = Analytics / Performance
        C0003 = Functional
        C0004 = Targeting / Advertising
    """
    from datetime import datetime

    groups = "C0001:1,C0002:0,C0003:0,C0004:0" if opted_out else "C0001:1,C0002:1,C0003:1,C0004:1"
    ts = int(datetime.now(UTC).timestamp() * 1000)

    return f"isGpcEnabled=1&datestamp={ts}&version=202401.1.0&groups={groups}&hosts=&genVendors=&consentId=123"


async def _extract_gtm_from_page(
    page: Page,
    page_html: str,
    gtm_js_body: str | None = None,
) -> tuple[str | None, str | None, GTMExtractionMethod]:
    """Extract GTM container ID using available methods (priority order).

    1. If gtm_js_body was already intercepted from network: parse it for GTM ID.
    2. Evaluate window.google_tag_manager in the live page.
    3. Regex scan page HTML for GTM-XXXXXX pattern.

    Returns:
        (container_id, container_js_or_None, extraction_method)
        extraction_method is LIVE if the ID came from a live JS source,
        NONE if it came from HTML regex only (no container JS available).
    """
    # Method 1: Already-intercepted gtm.js body
    if gtm_js_body:
        gtm_id = extract_gtm_id_from_html(gtm_js_body)
        if gtm_id:
            return gtm_id, gtm_js_body, GTMExtractionMethod.LIVE

    # Method 2: Evaluate window.google_tag_manager — keys only, then JSON for smallest container.
    # SSGTM sites expose huge google_tag_manager objects with circular DOM refs;
    # JSON.parse(JSON.stringify(window.google_tag_manager)) can hang indefinitely on them.
    try:
        gtm_ids: list[str] = await asyncio.wait_for(
            page.evaluate(
                "() => { const g = window.google_tag_manager; "
                "return g ? Object.keys(g).filter(k => k.startsWith('GTM-')) : []; }"
            ),
            timeout=3.0,
        )
        if gtm_ids:
            try:
                gtm_js = await asyncio.wait_for(
                    page.evaluate(
                        "(id) => { "
                        "try { return JSON.stringify(window.google_tag_manager[id]); } "
                        "catch (e) { return null; } }",
                        gtm_ids[0],
                    ),
                    timeout=5.0,
                )
                if gtm_js:
                    return gtm_ids[0], gtm_js, GTMExtractionMethod.LIVE
            except (TimeoutError, Exception):  # noqa: BLE001
                # Container serialization timed out; still return the ID we found.
                return gtm_ids[0], None, GTMExtractionMethod.LIVE
    except (TimeoutError, Exception):  # noqa: BLE001
        pass  # Page may have JS errors or stringify may hang — don't crash the scan

    # Method 3: Regex scan page HTML (last resort — no container JS available)
    gtm_id = extract_gtm_id_from_html(page_html)
    if gtm_id:
        return gtm_id, None, GTMExtractionMethod.NONE

    return None, None, GTMExtractionMethod.NONE


async def _block_shopify_cart_routes(page: Any) -> None:
    """Abort background polling requests that prevent networkidle from resolving.

    Covers Shopify cart-sync XHRs, fraud-detection beacons, analytics polling,
    and performance-monitoring endpoints. None of these are relevant to consent
    or tracking analysis. Blocking them stabilises networkidle timing.

    The handler swallows TargetClosedError so that browser cleanup (on timeout
    cancellation) does not propagate exceptions from in-flight route callbacks.
    """
    _BLOCKED_PATTERNS = (
        # Shopify cart sync
        "/cart/update.js",
        "/cart/add.js",
        "/cart/change.js",
        # Shopify platform telemetry + GraphQL store API (polls continuously)
        "monorail-edge.shopifysvc.com",
        "/api/2025-07/graphql.json",
        "/api/2024-10/graphql.json",
        "/api/graphql.json",
        # Forter fraud detection (fires repeatedly)
        "forter.com",
        # Optimizely analytics polling
        "logx.optimizely.com",
        # Yottaa performance monitoring
        "yottaa.net",
        # Klaviyo beacon polling
        "a.klaviyo.com",
    )

    async def _safe_abort(route: Any) -> None:
        with contextlib.suppress(Exception):
            await route.abort()

    await page.route(
        lambda url: any(pat in url for pat in _BLOCKED_PATTERNS),
        _safe_abort,
    )


async def _scan_s1(url: str, proxy_url: str | None = None) -> ScanResult:
    """S1 baseline scan — fresh browser context, no consent injection.

    Represents a first-time visitor arriving before any consent interaction.
    All cookies that fire here fired without any consent signal.
    """
    proxy: ProxySettings | None = ProxySettings(server=proxy_url) if proxy_url else None

    har_fd, har_path = tempfile.mkstemp(suffix=".har")
    os.close(har_fd)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=_STEALTH_LAUNCH_ARGS)
        context = await browser.new_context(
            proxy=proxy,
            record_har_path=har_path,
            user_agent=_STEALTH_UA,
            viewport={"width": 1280, "height": 800},
            locale="en-US",
            timezone_id="America/Los_Angeles",
            geolocation={"latitude": 34.0522, "longitude": -118.2437},
            permissions=["geolocation"],
        )
        await context.add_init_script(_STEALTH_INIT_SCRIPT)
        page = await context.new_page()
        await _block_shopify_cart_routes(page)

        # --- GEOIP Spoofing for CCPA Awareness ---
        await _apply_geoip_spoofing(page)

        network_requests: list[str] = []
        page.on("request", lambda req: network_requests.append(req.url))

        _js_responses: list[Any] = []
        page.on(
            "response",
            lambda r: (
                _js_responses.append(r)
                if "javascript" in r.headers.get("content-type", "").lower()
                else None
            ),
        )

        gtm_js_body: str | None = None

        try:
            async with page.expect_response(
                lambda r: "gtm.js" in r.url,
                timeout=5_000,
            ) as response_info:
                await page.goto(url, wait_until="networkidle", timeout=30_000)
            gtm_response = await response_info.value
            gtm_js_body = await gtm_response.text()
        except Exception:  # noqa: BLE001
            gtm_js_body = None

        # Track 2: fingerprint-check JS responses if Track 1 (URL match) missed
        if gtm_js_body is None:
            for _resp in _js_responses[:25]:
                try:
                    _body = await asyncio.wait_for(_resp.text(), timeout=2.0)
                    if "google_tag_manager" in _body:
                        gtm_js_body = _body
                        break
                except Exception:  # noqa: BLE001
                    continue

        raw_cookies = await context.cookies()
        page_html = await page.content()
        gtm_id, gtm_js, gtm_method = await _extract_gtm_from_page(page, page_html, gtm_js_body)

        await context.close()  # ensures HAR is written before browser closes
        await browser.close()

    cookies = [
        CookieSnapshot(
            name=c["name"],
            value=c["value"],
            domain=c["domain"],
            path=c["path"],
            secure=c["secure"],
            http_only=c["httpOnly"],
            same_site=c.get("sameSite", "Lax"),
            expires=c.get("expires"),
        )
        for c in raw_cookies
    ]

    # Extract GCS and GCD values from all network requests
    # Priority: find the first non-G111 signal if multiple exist, or just the first valid one.
    gcs_value: GCSValue | None = None
    gcd_raw: str | None = None
    gcs_records: list[GCSValue] = []
    gcd_records: list[str] = []

    for req_url in network_requests:
        raw_gcs = extract_gcs_from_url(req_url)
        if raw_gcs:
            gcs_records.append(parse_gcs_value(raw_gcs))
        raw_gcd = extract_gcd_from_url(req_url)
        if raw_gcd:
            gcd_records.append(raw_gcd)

    # Decision logic:
    # 1. Prefer denied signals if they exist
    # 2. Prefer most recent signals? (for now, just prefer the first one found that isn't 'unknown')
    if gcs_records:
        denied = [
            g for g in gcs_records if g.ad_storage == "denied" or g.analytics_storage == "denied"
        ]
        gcs_value = denied[0] if denied else gcs_records[0]

    if gcd_records:
        gcd_raw = gcd_records[0]

    return ScanResult(
        url=url,
        methodology=MethodologyFlag.S1,
        consent_state=ConsentState.OPTED_IN,
        timestamp=datetime.now(tz=UTC),
        cookies=cookies,
        network_requests=network_requests,
        gcs_value=gcs_value,
        gcd_raw=gcd_raw,
        gtm_container_id=gtm_id,
        gtm_extraction_method=gtm_method,
        gtm_container_js=gtm_js,
        page_html=page_html,
        har_path=har_path,
    )


def _domain_from_url(url: str) -> str:
    """Extract the hostname from a URL, returning an empty string if not found."""
    if url and not url.startswith(("http://", "https://")):
        url = "https://" + url
    return urlparse(url).hostname or ""


async def _try_ccpa_optout(page: Page, network_requests: list[str]) -> bool:
    """US CCPA opt-out fallback for sites where OneTrust cookie injection alone
    doesn't update Consent Mode signals.

    Covers the common US opt-out mechanisms in priority order:
      1. OneTrust JS API (RejectAll / UpdateConsent)
      2. Osano JS API
      3. "Your Privacy Choices" / "Do Not Sell" footer link → modal interaction
      4. GPC JS flag injection as last resort

    Returns True if any mechanism was successfully triggered.
    """
    # --- Strategy 1: OneTrust JS API ---
    try:
        result = await page.evaluate("""
            () => {
                if (window.OneTrust) {
                    if (typeof window.OneTrust.RejectAll === 'function') {
                        window.OneTrust.RejectAll();
                        return 'onetrust_reject_all';
                    }
                    if (typeof window.OneTrust.UpdateConsent === 'function') {
                        window.OneTrust.UpdateConsent('Category', 'C0002:0,C0003:0,C0004:0');
                        return 'onetrust_update_consent';
                    }
                }
                if (window.OneTrustStub && typeof window.OneTrustStub.RejectAll === 'function') {
                    window.OneTrustStub.RejectAll();
                    return 'onetrust_stub';
                }
                return null;
            }
        """)
        if result:
            await asyncio.sleep(1.5)
            return True
    except Exception:
        pass

    # --- Strategy 2: Osano JS API ---
    try:
        result = await page.evaluate("""
            () => {
                if (window.Osano && window.Osano.cm && typeof window.Osano.cm.denyAll === 'function') {
                    window.Osano.cm.denyAll();
                    return true;
                }
                return false;
            }
        """)
        if result:
            await asyncio.sleep(1.5)
            return True
    except Exception:
        pass

    # --- Strategy 3: CookieYes / CookieLaw JS API ---
    try:
        result = await page.evaluate("""
            () => {
                if (window.CookieYes && typeof window.CookieYes.reject === 'function') {
                    window.CookieYes.reject();
                    return true;
                }
                if (typeof window.ckyAllowConsent === 'function') {
                    return false;  // Don't accidentally accept
                }
                return false;
            }
        """)
        if result:
            await asyncio.sleep(1.5)
            return True
    except Exception:
        pass

    # --- Strategy 4: Footer "Your Privacy Choices" / "Do Not Sell" link ---
    _ccpa_link_selectors = [
        "a.ot-sdk-show-settings",
        "button.ot-sdk-show-settings",
        "a:has-text('Your Privacy Choices')",
        "button:has-text('Your Privacy Choices')",
        "a:has-text('Do Not Sell My Personal Information')",
        "a:has-text('Do Not Sell or Share My Personal Information')",
        "a:has-text('Do Not Sell')",
        "a:has-text('Privacy Choices')",
        "button:has-text('Privacy Choices')",
        "a:has-text('Privacy Preferences')",
        "button:has-text('Privacy Preferences')",
        "[class*='privacy-choices']",
        "[id*='privacy-choices']",
        "[class*='do-not-sell']",
        "[id*='do-not-sell']",
    ]

    clicked_link = False
    for sel in _ccpa_link_selectors:
        try:
            locator = page.locator(sel).first
            if await locator.is_visible(timeout=800):
                await locator.scroll_into_view_if_needed()
                await locator.click()
                await asyncio.sleep(2.0)
                clicked_link = True
                break
        except Exception:
            continue

    if not clicked_link:
        return False

    # After opening CCPA modal, try JS API first (now that OneTrust is fully loaded)
    try:
        result = await page.evaluate("""
            () => {
                if (window.OneTrust && typeof window.OneTrust.RejectAll === 'function') {
                    window.OneTrust.RejectAll();
                    return true;
                }
                return false;
            }
        """)
        if result:
            await asyncio.sleep(1.0)
            return True
    except Exception:
        pass

    # Fall through to UI interaction on the now-open modal
    from consent_engine.tools.cmp_clicker import attempt_cmp_decline

    method = await attempt_cmp_decline(page, network_requests, max_rounds=3)
    return method in ("banner_click", "api_click", "banner_click_inconclusive")


async def _scan_s3(url: str, opted_out: bool = True, proxy_url: str | None = None) -> ScanResult:
    """S3 definitive scan — injects OptanonConsent cookie before page load.

    Pre-sets consent state on the domain prior to navigation, so the page
    receives the consent signal on first load. This is the legally defensible
    methodology for determining whether a site respects opted-out consent.

    If the OneTrust cookie injection does not suppress the banner (i.e., the
    site uses a different CMP), the scan falls back to banner-click opt-out
    in a clean browser context (no injected cookies).
    """
    domain = _domain_from_url(url)
    consent_state = ConsentState.OPTED_OUT if opted_out else ConsentState.OPTED_IN
    proxy: ProxySettings | None = ProxySettings(server=proxy_url) if proxy_url else None

    har_fd, har_path = tempfile.mkstemp(suffix=".har")
    os.close(har_fd)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=_STEALTH_LAUNCH_ARGS)
        context = await browser.new_context(
            proxy=proxy,
            record_har_path=har_path,
            user_agent=_STEALTH_UA,
            viewport={"width": 1280, "height": 800},
            locale="en-US",
            timezone_id="America/Los_Angeles",
            geolocation={"latitude": 34.0522, "longitude": -118.2437},
            permissions=["geolocation"],
        )
        await context.add_init_script(_STEALTH_INIT_SCRIPT)

        # Inject consent cookies BEFORE creating the page or calling goto
        await context.add_cookies(
            [
                {
                    "name": "OptanonConsent",
                    "value": build_onetrust_consent_cookie(opted_out=opted_out),
                    "domain": domain,
                    "path": "/",
                    "secure": False,
                    "httpOnly": False,
                    "sameSite": "Lax",
                },
                {
                    "name": "OptanonAlertBoxClosed",
                    "value": "2026-01-01T00:00:00.000Z",
                    "domain": domain,
                    "path": "/",
                    "secure": False,
                    "httpOnly": False,
                    "sameSite": "Lax",
                },
            ]
        )

        page = await context.new_page()
        await _block_shopify_cart_routes(page)

        # --- GEOIP Spoofing for CCPA Awareness ---
        await _apply_geoip_spoofing(page)

        network_requests: list[str] = []
        page.on("request", lambda req: network_requests.append(req.url))

        _js_responses: list[Any] = []
        _collect_responses: list[Any] = []  # first-party /g/collect (Stape custom loader)

        def _on_s3_response(r: Any) -> None:
            ct = r.headers.get("content-type", "").lower()
            if "javascript" in ct:
                _js_responses.append(r)
            if _FIRST_PARTY_COLLECT_RE.search(r.url):
                _collect_responses.append(r)

        page.on("response", _on_s3_response)

        gtm_js_body: str | None = None

        try:
            async with page.expect_response(
                lambda r: "gtm.js" in r.url or _is_custom_loader_gtm(r.url),
                timeout=5_000,
            ) as response_info:
                await page.goto(url, wait_until="networkidle", timeout=30_000)
            gtm_response = await response_info.value
            gtm_js_body = await gtm_response.text()
        except Exception:  # noqa: BLE001
            gtm_js_body = None

        # Track 2: fingerprint-check JS responses if Track 1 (URL match) missed
        if gtm_js_body is None:
            for _resp in _js_responses[:25]:
                try:
                    _body = await asyncio.wait_for(_resp.text(), timeout=2.0)
                    if "google_tag_manager" in _body:
                        gtm_js_body = _body
                        break
                except Exception:  # noqa: BLE001
                    continue

        # Extract GCS from first-party /g/collect response bodies (Stape custom loader)
        # Stape returns send_pixel directives in SSE responses containing forwarded GCS
        for _cresp in _collect_responses[:10]:
            try:
                _cbody = await asyncio.wait_for(_cresp.text(), timeout=2.0)
                for _gcs_m in _GCS_RE.finditer(_cbody):
                    network_requests.append(f"__stape_collect_response__?gcs={_gcs_m.group(1)}")
                for _gcd_m in _GCD_RE.finditer(_cbody):
                    network_requests.append(f"__stape_collect_response__?gcd={_gcd_m.group(1)}")
            except Exception:  # noqa: BLE001
                continue

        # --- LAYER 1: CMP Detection ---
        from consent_engine.tools.cmp_detector import detect_cmp

        cmp_profile = await detect_cmp(page, network_requests)

        title = await page.title()
        bot_detection_encountered = (
            "Security Check" in title
            or "Cloudflare" in title
            or "Access Denied" in title
            or "Just a moment" in title
            or "Challenge" in title
        )

        # --- LAYER 2: Banner Check ---
        # Enter Context 2 if: (a) banner is still visible despite OneTrust cookie injection,
        # OR (b) TrueVault detected — its consent UI is a footer link, not a visible banner.
        # Skip Context 2 for "unknown" CMPs: we have no injection plan and banner selectors
        # ([class*='banner']) can match promotional banners (false positive → infinite loop).
        #
        # IMPORTANT: Before abandoning Context 1 for Context 2, check if the cookie
        # injection already produced a denied GCS signal. CCPA-style OneTrust banners
        # can remain visible in the DOM even when consent is properly denied (e.g.,
        # a "Do Not Sell" footer notice). If GCS is already denied, the injection
        # worked and we must NOT fall through to a clean Context 2 with no cookies.
        cmp_method: str | None = None
        _cmp_is_known = cmp_profile is not None and cmp_profile.name not in ("unknown",)

        # Check if cookie injection already produced a denied GCS signal
        _injection_gcs_denied = any(
            (raw := extract_gcs_from_url(ru)) is not None
            and len(raw) >= 4
            and "0" in raw[2:]  # any denied bit in the GCS value
            for ru in network_requests
        )
        _need_context2 = not _injection_gcs_denied and (
            (_cmp_is_known and await _banner_present(page))
            or (cmp_profile and cmp_profile.name == "TrueVault")
        )
        if _need_context2:
            # OneTrust cookies were ignored or wrong CMP — we need to inject or click
            # Create a clean browser context (no cookies)
            await context.close()  # ensures HAR is written before browser closes

            har_fd2, har_path2 = tempfile.mkstemp(suffix=".har")
            os.close(har_fd2)

            context2 = await browser.new_context(
                proxy=proxy,
                record_har_path=har_path2,
                user_agent=_STEALTH_UA,
                viewport={"width": 1280, "height": 800},
                locale="en-US",
                timezone_id="America/Los_Angeles",
                geolocation={"latitude": 34.0522, "longitude": -118.2437},
                permissions=["geolocation"],
            )
            await context2.add_init_script(_STEALTH_INIT_SCRIPT)

            # --- LAYER 3: CMP-Specific Injection ---
            from consent_engine.tools.cmp_injector import build_injection_plan

            injection_plan = build_injection_plan(cmp_profile, domain)

            if injection_plan.init_script:
                await context2.add_init_script(injection_plan.init_script)
            if injection_plan.cookies:
                # cast: CMPInjectionPlan.cookies is list[dict[str,Any]] which is
                # runtime-identical to Sequence[SetCookieParam] (a TypedDict).
                await context2.add_cookies(cast(Sequence[Any], injection_plan.cookies))

            page2 = await context2.new_page()
            await _block_shopify_cart_routes(page2)

            # Apply same spoofing to the fresh interaction context
            await _apply_geoip_spoofing(page2)

            network_requests2: list[str] = []

            def _on_request2(req: Request) -> None:
                network_requests2.append(req.url)

            page2.on("request", _on_request2)

            _js_responses2: list[Any] = []
            page2.on(
                "response",
                lambda r: (
                    _js_responses2.append(r)
                    if "javascript" in r.headers.get("content-type", "").lower()
                    else None
                ),
            )

            gtm_js_body2: str | None = None
            try:
                async with page2.expect_response(
                    lambda r: "gtm.js" in r.url or "gtg.js" in r.url,
                    timeout=5_000,
                ) as response_info2:
                    await page2.goto(url, wait_until="networkidle", timeout=30_000)
                gtm_response2 = await response_info2.value
                gtm_js_body2 = await gtm_response2.text()
            except Exception:  # noqa: BLE001
                gtm_js_body2 = None

            if gtm_js_body2 is None:
                for _resp2 in _js_responses2[:25]:
                    try:
                        _body2 = await asyncio.wait_for(_resp2.text(), timeout=2.0)
                        if "google_tag_manager" in _body2:
                            gtm_js_body2 = _body2
                            break
                    except Exception:  # noqa: BLE001
                        continue

            # Recheck banner after layer 3 injection
            if (injection_plan.cookies or injection_plan.init_script) and not await _banner_present(
                page2
            ):
                if cmp_profile and cmp_profile.name == "TrueVault":
                    # For TrueVault, we ALWAYS want to try the UI interaction because the "banner" is the footer link
                    cmp_method = await attempt_cmp_decline(page2, network_requests2, cmp_profile)
                else:
                    cmp_method = f"injection:{cmp_profile.name}"
            else:
                # --- LAYER 4: UI Interaction (cmp_clicker) ---
                cmp_method = await attempt_cmp_decline(page2, network_requests2, cmp_profile)

                # --- LAYER 5: Post-decline Confirmation ---
                if cmp_method in ("banner_click", "api_click"):
                    # Hard reload to verify persistence
                    network_requests2_before_reload = list(network_requests2)
                    network_requests2.clear()
                    with contextlib.suppress(Exception):
                        await page2.reload(wait_until="networkidle", timeout=15000)

                    from consent_engine.tools.cmp_clicker import _is_gcs_denied

                    if not _is_gcs_denied(network_requests2) and await _banner_present(page2):
                        cmp_method = "banner_click_reverted"

                    # Merge network requests back
                    network_requests2.extend(network_requests2_before_reload)

            # --- LAYER 6: Final Network Wait ---
            # Wait for any post-interaction pings (GCS/GCD) to fire
            with contextlib.suppress(Exception):
                await page2.wait_for_load_state("networkidle", timeout=5000)
            await asyncio.sleep(2.0)  # Buffer for async pings

            # --- JS-evaluated consent mode (Context 2) ---
            js_gcs2 = await _read_consent_mode_from_page(page2)
            if js_gcs2:
                network_requests2.append(f"__js_consent_mode__?gcs={js_gcs2}")

            # --- LAYER 7: Force consent denied if CMP geo-targeting left GCS granted ---
            network_requests = network_requests2
            raw_cookies = await asyncio.wait_for(context2.cookies(), timeout=5.0)
            try:
                page_html = await asyncio.wait_for(page2.content(), timeout=10.0)
            except (TimeoutError, Exception):  # noqa: BLE001
                page_html = ""
            # Final container extraction
            gtm_id, gtm_js, gtm_method = await _extract_gtm_from_page(
                page2, page_html, gtm_js_body2
            )

            # LAST RESORT: Scan all network requests for GTM ID if still missing
            if not gtm_id:
                for req_url in network_requests2:
                    gtm_id = extract_gtm_id_from_html(req_url)
                    if gtm_id:
                        gtm_method = GTMExtractionMethod.LIVE
                        break
            # Close context (writes HAR). Timeout guards against Playwright blocking
            # on HAR file writing for high-request-count pages (e.g. Shopify stores).
            with contextlib.suppress(Exception):
                await asyncio.wait_for(context2.close(), timeout=10.0)
            with contextlib.suppress(Exception):
                await browser.close()

            final_har_path = har_path2
        else:
            cmp_method = "cookie_injection"
            # Reload after injection so SPAs and CMPs that read consent state on init
            # get a clean post-denial load (mirrors real returning-visitor behaviour).
            # Clear network_requests first so we only capture post-reload traffic.
            network_requests.clear()
            with contextlib.suppress(Exception):
                await page.reload(wait_until="networkidle", timeout=20_000)
            with contextlib.suppress(Exception):
                await page.wait_for_load_state("networkidle", timeout=5_000)
            await asyncio.sleep(1.5)

            # --- US CCPA FALLBACK ---
            # For US OneTrust sites the Consent Mode update is triggered by the
            # CCPA "Do Not Sell" UI interaction, not the GDPR cookie injection.
            # If GCS is still G111 after reload, try the CCPA opt-out path.
            _gcs_denied_after_reload = any(
                len(raw := extract_gcs_from_url(ru) or "") >= 4 and "0" in raw[2:]
                for ru in network_requests
            )
            if not _gcs_denied_after_reload:
                _ccpa_success = await _try_ccpa_optout(page, network_requests)
                if _ccpa_success:
                    network_requests.clear()
                    # Use domcontentloaded (not networkidle) for the post-CCPA reload.
                    # Sites like Bombas have continuous background polling that prevents
                    # networkidle from resolving after OneTrust.RejectAll() fires a redirect.
                    # domcontentloaded is sufficient: tracking pixels fire before DOMContentLoaded.
                    with contextlib.suppress(Exception):
                        await page.reload(wait_until="domcontentloaded", timeout=15_000)
                    await asyncio.sleep(3.0)  # give async pings 3s to fire post-DOMContentLoaded
                    cmp_method = "ccpa_optout"

            # --- JS-evaluated consent mode (catches post-CMP state) ---
            # Stape custom loader and similar tools fire GA4 with G111 before the
            # CMP initialises consent mode.  After CMP interaction the JS runtime
            # holds the real (denied) state — read it and inject a synthetic URL
            # so the GCS extraction logic below can prefer the denied signal.
            js_gcs = await _read_consent_mode_from_page(page)
            if js_gcs:
                network_requests.append(f"__js_consent_mode__?gcs={js_gcs}")

            raw_cookies = await asyncio.wait_for(context.cookies(), timeout=5.0)
            try:
                page_html = await asyncio.wait_for(page.content(), timeout=10.0)
            except (TimeoutError, Exception):  # noqa: BLE001
                page_html = ""
            gtm_id, gtm_js, gtm_method = await _extract_gtm_from_page(page, page_html, gtm_js_body)
            with contextlib.suppress(Exception):
                await asyncio.wait_for(context.close(), timeout=10.0)
            with contextlib.suppress(Exception):
                await browser.close()
            final_har_path = har_path

    cookies = [
        CookieSnapshot(
            name=c["name"],
            value=c["value"],
            domain=c["domain"],
            path=c["path"],
            secure=c["secure"],
            http_only=c["httpOnly"],
            same_site=c.get("sameSite", "Lax"),
            expires=c.get("expires"),
        )
        for c in raw_cookies
    ]

    # Extract GCS and GCD values from all network requests
    # Priority: find a denied signal if multiple exist, or else use the last one
    gcs_value: GCSValue | None = None
    gcd_raw: str | None = None
    gcs_records: list[GCSValue] = []
    gcd_records: list[str] = []

    for req_url in network_requests:
        raw_gcs = extract_gcs_from_url(req_url)
        if raw_gcs:
            gcs_records.append(parse_gcs_value(raw_gcs))
        raw_gcd = extract_gcd_from_url(req_url)
        if raw_gcd:
            gcd_records.append(raw_gcd)

    if gcs_records:
        denied = [
            g for g in gcs_records if g.ad_storage == "denied" or g.analytics_storage == "denied"
        ]
        gcs_value = denied[0] if denied else gcs_records[-1]

    if gcd_records:
        denied_gcd = [gcd for gcd in gcd_records if is_gcd_denied_state(gcd)]
        gcd_raw = denied_gcd[0] if denied_gcd else gcd_records[-1]

    # --- GCS geo-targeting override ---
    # CMPs like CookieYes geo-target consent defaults: EU=denied, US=granted.
    # When scanning from a US IP (e.g. Cloud Run), the CMP may report GCS G111
    # even though denied cookies are set and the CMP banner was dismissed.
    # If the CMP is known, denied cookies are confirmed, and GCS is all-granted,
    # override to G100 — the value an EU visitor would see after opting out.
    if (
        gcs_value
        and gcs_value.ad_storage == "granted"
        and gcs_value.analytics_storage == "granted"
        and cmp_profile
        and cmp_profile.name not in ("unknown",)
        and cmp_method is not None
    ):
        _denied_cookie_names = {
            "CookieYes": "cookieyes-consent",
            "OneTrust": "OptanonConsent",
            "Cookiebot": "CookieConsent",
            "Complianz": "cmplz_consent",
        }
        _expected_cookie = _denied_cookie_names.get(cmp_profile.name)
        _has_denied_cookie = _expected_cookie is not None and any(
            c.name == _expected_cookie for c in cookies
        )
        if _has_denied_cookie:
            gcs_value = parse_gcs_value("G100")

    # --- Post-injection methodology classification ---
    # Decision tree:
    #   1. Denied GCS observed                               -> S3 (definitive,
    #      consent was respected)
    #   2. CMP detected AND injection plan existed           -> S3_CONSENT_WIRING_BROKEN
    #      (definitive — we recognised the CMP, we injected the right denial
    #      payload, and GCS still never flipped. That's proof the site's tag
    #      wiring fires before or regardless of CMP state. Findings are legally
    #      defensible.)
    #   3. Otherwise (unknown CMP, or no injection plan)     -> INCONCLUSIVE_UNKNOWN_CMP
    #      (we can't say for sure — the injection may simply have been ignored
    #      because we didn't have the right plan)
    from consent_engine.tools.cmp_injector import has_plan_for

    _gcs_denied_observed = gcs_value is not None and (
        gcs_value.ad_storage == "denied" or gcs_value.analytics_storage == "denied"
    )
    _cmp_name = cmp_profile.name if cmp_profile is not None else None
    _cmp_detected = _cmp_name is not None and _cmp_name != "unknown"
    _injection_plan_existed = has_plan_for(_cmp_name)

    if _gcs_denied_observed:
        methodology: MethodologyFlag = MethodologyFlag.S3
    elif _cmp_detected and _injection_plan_existed:
        methodology = MethodologyFlag.S3_CONSENT_WIRING_BROKEN
    else:
        methodology = MethodologyFlag.INCONCLUSIVE_UNKNOWN_CMP

    return ScanResult(
        url=url,
        methodology=methodology,
        consent_state=consent_state,
        timestamp=datetime.now(tz=UTC),
        cookies=cookies,
        network_requests=network_requests,
        gcs_value=gcs_value,
        gcd_raw=gcd_raw,
        gtm_container_id=gtm_id,
        gtm_extraction_method=gtm_method,
        gtm_container_js=gtm_js,
        page_html=page_html,
        gpc_header_sent=False,
        cmp_interaction_method=cmp_method,
        detected_cmp=cmp_profile.name if cmp_profile.name != "unknown" else None,
        cmp_detection_confidence=cmp_profile.confidence if cmp_profile.name != "unknown" else None,
        bot_detection_encountered=bot_detection_encountered,
        har_path=final_har_path,
    )


async def _scan_gpc(url: str, proxy_url: str | None = None) -> ScanResult:
    """GPC scan — S3 opted-out + Sec-GPC: 1 request header.

    Sends the Global Privacy Control signal on every request. Used to test
    whether the site honors GPC as an opt-out mechanism.

    Note: GPC cannot be forwarded to server-side GTM containers. If SSGTM
    is detected, Tool 6 will flag this as an automatic enforcement gap.
    """
    domain = _domain_from_url(url)
    proxy: ProxySettings | None = ProxySettings(server=proxy_url) if proxy_url else None

    har_fd, har_path = tempfile.mkstemp(suffix=".har")
    os.close(har_fd)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=_STEALTH_LAUNCH_ARGS)
        context = await browser.new_context(
            extra_http_headers={"Sec-GPC": "1"},
            proxy=proxy,
            record_har_path=har_path,
            user_agent=_STEALTH_UA,
            viewport={"width": 1280, "height": 800},
            locale="en-US",
            timezone_id="America/Los_Angeles",
            geolocation={"latitude": 34.0522, "longitude": -118.2437},
            permissions=["geolocation"],
        )
        await context.add_init_script(_STEALTH_INIT_SCRIPT)

        # Same consent injection as S3 opted-out
        await context.add_cookies(
            [
                {
                    "name": "OptanonConsent",
                    "value": build_onetrust_consent_cookie(opted_out=True),
                    "domain": domain,
                    "path": "/",
                    "secure": False,
                    "httpOnly": False,
                    "sameSite": "Lax",
                },
                {
                    "name": "OptanonAlertBoxClosed",
                    "value": "2026-01-01T00:00:00.000Z",
                    "domain": domain,
                    "path": "/",
                    "secure": False,
                    "httpOnly": False,
                    "sameSite": "Lax",
                },
            ]
        )

        page = await context.new_page()
        await _block_shopify_cart_routes(page)

        # Add GPC init script (Layer 8)
        await context.add_init_script(
            "Object.defineProperty(navigator, 'globalPrivacyControl', {get: () => true});"
        )

        network_requests: list[str] = []
        page.on("request", lambda req: network_requests.append(req.url))

        _js_responses: list[Any] = []
        page.on(
            "response",
            lambda r: (
                _js_responses.append(r)
                if "javascript" in r.headers.get("content-type", "").lower()
                else None
            ),
        )

        gtm_js_body: str | None = None

        try:
            async with page.expect_response(
                lambda r: "gtm.js" in r.url,
                timeout=5_000,
            ) as response_info:
                await page.goto(url, wait_until="networkidle", timeout=30_000)
            gtm_response = await response_info.value
            gtm_js_body = await gtm_response.text()
        except Exception:  # noqa: BLE001
            gtm_js_body = None

        # Track 2: fingerprint-check JS responses if Track 1 (URL match) missed
        if gtm_js_body is None:
            for _resp in _js_responses[:25]:
                try:
                    _body = await asyncio.wait_for(_resp.text(), timeout=2.0)
                    if "google_tag_manager" in _body:
                        gtm_js_body = _body
                        break
                except Exception:  # noqa: BLE001
                    continue

        raw_cookies = await context.cookies()
        page_html = await page.content()
        gtm_id, gtm_js, gtm_method = await _extract_gtm_from_page(page, page_html, gtm_js_body)

        await context.close()  # ensures HAR is written before browser closes
        await browser.close()

    cookies = [
        CookieSnapshot(
            name=c["name"],
            value=c["value"],
            domain=c["domain"],
            path=c["path"],
            secure=c["secure"],
            http_only=c["httpOnly"],
            same_site=c.get("sameSite", "Lax"),
            expires=c.get("expires"),
        )
        for c in raw_cookies
    ]

    # Extract GCS and GCD values from all network requests
    # Priority: find a denied signal if multiple exist, or else use the last one
    gcs_value: GCSValue | None = None
    gcd_raw: str | None = None
    gcs_records: list[GCSValue] = []
    gcd_records: list[str] = []

    for req_url in network_requests:
        raw_gcs = extract_gcs_from_url(req_url)
        if raw_gcs:
            gcs_records.append(parse_gcs_value(raw_gcs))
        raw_gcd = extract_gcd_from_url(req_url)
        if raw_gcd:
            gcd_records.append(raw_gcd)

    if gcs_records:
        denied = [
            g for g in gcs_records if g.ad_storage == "denied" or g.analytics_storage == "denied"
        ]
        gcs_value = denied[0] if denied else gcs_records[-1]

    if gcd_records:
        denied_gcd = [gcd for gcd in gcd_records if is_gcd_denied_state(gcd)]
        gcd_raw = denied_gcd[0] if denied_gcd else gcd_records[-1]

    return ScanResult(
        url=url,
        methodology=MethodologyFlag.S3,
        consent_state=ConsentState.GPC_OPTED_OUT,
        timestamp=datetime.now(tz=UTC),
        cookies=cookies,
        network_requests=network_requests,
        gcs_value=gcs_value,
        gcd_raw=gcd_raw,
        gtm_container_id=gtm_id,
        gtm_extraction_method=gtm_method,
        gtm_container_js=gtm_js,
        gpc_header_sent=True,
        page_html=page_html,
        har_path=har_path,
    )


def _looks_like_bot_challenge(title: str, html: str) -> bool:
    """Classify whether a primary-scan page response is actually a WAF/bot wall.

    Returns True when either the <title> or the rendered HTML contains the
    hallmark strings of Cloudflare/Akamai/PerimeterX challenges. Used by
    `scan_page_fast` to decide whether to engage the Scrapling stealthy retry.
    """
    challenge_titles = (
        "Security Check",
        "Cloudflare",
        "Access Denied",
        "Just a moment",
        "Challenge",
        "Attention Required",
        "Blocked",
    )
    challenge_bodies = (
        "checking your browser",
        "cf-challenge",
        "px-captcha",
        "_Incapsula_",
        "Request unsuccessful. Incapsula incident",
    )
    if any(t.lower() in title.lower() for t in challenge_titles if t):
        return True
    body_snippet = (html or "")[:20_000].lower()
    return any(b.lower() in body_snippet for b in challenge_bodies)


async def scan_page_fast(
    url: str, opted_out: bool = True, gpc: bool = False
) -> tuple[ScanResult, str | None]:
    """Fast scan for audit-summary grading — optimised for speed over completeness.

    Cuts ~60-70% of scan time by:
    - Blocking images, fonts, media, stylesheets (only JS/HTML needed for tracking)
    - Using domcontentloaded + short settle instead of networkidle
    - Skipping HAR recording, Context 2 banner click, CCPA fallback, GTM JS extraction
    - Single page load only (cookie injection → load → collect)

    Returns the same ScanResult shape but with empty page_html and no GTM JS body.

    When the primary Chromium scan hits a WAF/bot challenge, the scan transparently
    retries via Scrapling's Camoufox-backed `StealthyFetcher` and records
    `scan_mode_used="stealthy"` on the returned ScanResult.
    """
    domain = _domain_from_url(url)
    if gpc:
        consent_state = ConsentState.GPC_OPTED_OUT
    elif opted_out:
        consent_state = ConsentState.OPTED_OUT
    else:
        consent_state = ConsentState.OPTED_IN

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=_STEALTH_LAUNCH_ARGS)
        context = await browser.new_context(
            user_agent=_STEALTH_UA,
            viewport={"width": 1280, "height": 800},
            locale="en-US",
            timezone_id="America/Los_Angeles",
            geolocation={"latitude": 34.0522, "longitude": -118.2437},
            permissions=["geolocation"],
            extra_http_headers={"Sec-GPC": "1"} if gpc else {},
        )
        await context.add_init_script(_STEALTH_INIT_SCRIPT)

        # Inject consent cookies BEFORE page load
        await context.add_cookies(
            [
                {
                    "name": "OptanonConsent",
                    "value": build_onetrust_consent_cookie(opted_out=opted_out),
                    "domain": domain,
                    "path": "/",
                    "secure": False,
                    "httpOnly": False,
                    "sameSite": "Lax",
                },
                {
                    "name": "OptanonAlertBoxClosed",
                    "value": "2026-01-01T00:00:00.000Z",
                    "domain": domain,
                    "path": "/",
                    "secure": False,
                    "httpOnly": False,
                    "sameSite": "Lax",
                },
            ]
        )

        page = await context.new_page()
        await _block_shopify_cart_routes(page)
        await _apply_geoip_spoofing(page)

        # Block heavy resources — fonts and media don't affect tracking detection
        # OR the final screenshot. Images and CSS are kept so banner screenshots
        # render correctly (no broken logos, no layout collapse).
        await page.route(
            "**/*.{woff,woff2,ttf,eot,mp4,webm,mp3,ogg,wav}",
            lambda route: route.abort(),
        )

        network_requests: list[str] = []
        page.on("request", lambda req: network_requests.append(req.url))

        # Load page — use domcontentloaded (fast) then wait for trackers to fire
        with contextlib.suppress(Exception):
            await page.goto(url, wait_until="domcontentloaded", timeout=20_000)

        # Give tracking pixels 5s to fire after DOM ready
        await asyncio.sleep(5.0)

        # Read JS consent mode state
        js_gcs = await _read_consent_mode_from_page(page)
        if js_gcs:
            network_requests.append(f"__js_consent_mode__?gcs={js_gcs}")

        # Detect CMP (OneTrust, CookieYes, Cookiebot, TrustArc, etc.)
        from consent_engine.tools.cmp_detector import detect_cmp

        try:
            cmp_profile = await asyncio.wait_for(detect_cmp(page, network_requests), timeout=5.0)
        except (TimeoutError, Exception):
            cmp_profile = None

        raw_cookies = await context.cookies()

        # Capture page HTML for og:image / favicon / jurisdiction detection
        page_html = ""
        try:
            page_html = await asyncio.wait_for(page.content(), timeout=5.0)
        except (TimeoutError, Exception):
            page_html = ""

        # Detect WAF/bot challenges so the caller (or this function's retry
        # path) can switch to the Camoufox-backed stealthy scan.
        page_title = ""
        with contextlib.suppress(Exception):
            page_title = await asyncio.wait_for(page.title(), timeout=2.0)
        bot_detection_encountered = _looks_like_bot_challenge(page_title, page_html)

        # Capture a lightweight homepage screenshot (640px wide JPEG, ~30-50KB).
        # After the viewport resize, wait briefly so the CMP banner finishes
        # reflowing and images settle — otherwise we capture mid-animation frames
        # with broken image placeholders or overlapping panels.
        screenshot_b64: str | None = None
        with contextlib.suppress(Exception):
            await page.set_viewport_size({"width": 640, "height": 400})
            await page.wait_for_load_state("networkidle", timeout=3000)
            await asyncio.sleep(0.4)
            _shot = await page.screenshot(type="jpeg", quality=60, timeout=5000)
            screenshot_b64 = base64.b64encode(_shot).decode()

        with contextlib.suppress(Exception):
            await browser.close()

    cookies = [
        CookieSnapshot(
            name=c["name"],
            value=c["value"],
            domain=c["domain"],
            path=c["path"],
            secure=c["secure"],
            http_only=c["httpOnly"],
            same_site=c.get("sameSite", "Lax"),
            expires=c.get("expires"),
        )
        for c in raw_cookies
    ]

    # Extract GCS/GCD from network requests
    gcs_value: GCSValue | None = None
    gcd_raw: str | None = None
    gcs_records: list[GCSValue] = []
    gcd_records: list[str] = []

    for req_url in network_requests:
        raw_gcs = extract_gcs_from_url(req_url)
        if raw_gcs:
            gcs_records.append(parse_gcs_value(raw_gcs))
        raw_gcd = extract_gcd_from_url(req_url)
        if raw_gcd:
            gcd_records.append(raw_gcd)

    if gcs_records:
        denied = [
            g for g in gcs_records if g.ad_storage == "denied" or g.analytics_storage == "denied"
        ]
        gcs_value = denied[0] if denied else gcs_records[-1]

    if gcd_records:
        denied_gcd = [gcd for gcd in gcd_records if is_gcd_denied_state(gcd)]
        gcd_raw = denied_gcd[0] if denied_gcd else gcd_records[-1]

    # GCS geo-targeting override — same logic as full scan.
    # US-targeted CMPs report GCS G111 even when denied cookies are set.
    # If we injected opt-out cookies and they're present, override to G100.
    _denied_cookie_names = {
        "OptanonConsent",  # OneTrust
        "cookieyes-consent",  # CookieYes
        "CookieConsent",  # Cookiebot
        "cmplz_consent",  # Complianz
    }
    if (
        opted_out
        and gcs_value
        and gcs_value.ad_storage == "granted"
        and gcs_value.analytics_storage == "granted"
        and any(c.name in _denied_cookie_names for c in cookies)
    ):
        gcs_value = parse_gcs_value("G100")

    _cmp_name = cmp_profile.name if cmp_profile and cmp_profile.name != "unknown" else None
    _cmp_conf = cmp_profile.confidence if cmp_profile and cmp_profile.name != "unknown" else None

    # Extract GTM container ID from gtm.js network request. The full JS body
    # isn't needed for the fast path — the ID alone populates the report card.
    gtm_id: str | None = None
    for _req in network_requests:
        _m = re.search(r"/gtm\.js\?[^ ]*\bid=(GTM-[A-Z0-9]+)", _req)
        if _m:
            gtm_id = _m.group(1)
            break

    primary_result = ScanResult(
        url=url,
        methodology=MethodologyFlag.S3,
        consent_state=consent_state,
        timestamp=datetime.now(tz=UTC),
        cookies=cookies,
        network_requests=network_requests,
        gcs_value=gcs_value,
        gcd_raw=gcd_raw,
        gtm_container_id=gtm_id,
        gtm_extraction_method=(GTMExtractionMethod.LIVE if gtm_id else GTMExtractionMethod.NONE),
        gtm_container_js=None,
        page_html=page_html,
        gpc_header_sent=gpc,
        cmp_interaction_method="cookie_injection",
        detected_cmp=_cmp_name,
        cmp_detection_confidence=_cmp_conf,
        bot_detection_encountered=bot_detection_encountered,
        scan_mode_used="playwright",
        har_path=None,
    )

    # Retry via Scrapling's Camoufox-backed stealthy fetcher when the primary
    # Chromium scan hit a WAF/bot challenge. The retry returns a ScanResult
    # tagged scan_mode_used="stealthy"; if it also fails we fall back to the
    # primary result so the audit still renders something.
    if bot_detection_encountered:
        stealthy = await _scan_page_stealthy(url=url, opted_out=opted_out, gpc=gpc)
        if stealthy is not None:
            return (stealthy, screenshot_b64)

    return (primary_result, screenshot_b64)


async def _scan_page_stealthy(url: str, opted_out: bool, gpc: bool) -> ScanResult | None:
    """Camoufox-backed stealthy retry for WAF-blocked sites.

    Uses Scrapling's `StealthyFetcher.async_fetch` with a Playwright-compatible
    `page_action` callback that replicates the core capture logic of
    `scan_page_fast` — consent-cookie injection, network-request capture,
    GCS/GCD extraction — while delegating fingerprint spoofing to Camoufox
    (Firefox + BrowserForge) which passes Cloudflare/PerimeterX checks that
    standard Chromium cannot.

    Returns None if Scrapling is unavailable or the retry itself fails, in
    which case the caller should keep its primary-scan ScanResult.
    """
    try:
        from scrapling.fetchers import StealthyFetcher
    except ImportError:
        return None

    domain = _domain_from_url(url)
    if gpc:
        consent_state = ConsentState.GPC_OPTED_OUT
    elif opted_out:
        consent_state = ConsentState.OPTED_OUT
    else:
        consent_state = ConsentState.OPTED_IN

    network_requests: list[str] = []
    captured_cookies: list[dict[str, Any]] = []
    captured_html: str = ""
    captured_cmp_name: str | None = None
    captured_cmp_conf: str | None = None

    async def _page_setup(page: Any) -> Any:
        """Runs before Scrapling navigates — install the request listener here
        so we capture requests made during the initial page load."""
        page.on("request", lambda req: network_requests.append(req.url))
        return page

    async def _page_action(page: Any) -> Any:
        """Runs inside Scrapling's Camoufox context after navigation."""
        nonlocal captured_cookies, captured_html, captured_cmp_name, captured_cmp_conf

        # Let trackers settle
        with contextlib.suppress(Exception):
            await asyncio.sleep(5.0)

        # JS-level Consent Mode read (adds __js_consent_mode__ marker entries)
        with contextlib.suppress(Exception):
            js_gcs = await _read_consent_mode_from_page(page)
            if js_gcs:
                network_requests.append(f"__js_consent_mode__?gcs={js_gcs}")

        # CMP detection
        with contextlib.suppress(Exception):
            from consent_engine.tools.cmp_detector import detect_cmp

            profile = await asyncio.wait_for(detect_cmp(page, network_requests), timeout=5.0)
            if profile and profile.name != "unknown":
                captured_cmp_name = profile.name
                captured_cmp_conf = profile.confidence

        with contextlib.suppress(Exception):
            captured_cookies = await page.context.cookies()

        with contextlib.suppress(Exception):
            captured_html = await asyncio.wait_for(page.content(), timeout=5.0)

        return page

    pre_cookies: list[dict[str, Any]] = [
        {
            "name": "OptanonConsent",
            "value": build_onetrust_consent_cookie(opted_out=opted_out),
            "domain": domain,
            "path": "/",
            "secure": False,
            "httpOnly": False,
            "sameSite": "Lax",
        },
        {
            "name": "OptanonAlertBoxClosed",
            "value": "2026-01-01T00:00:00.000Z",
            "domain": domain,
            "path": "/",
            "secure": False,
            "httpOnly": False,
            "sameSite": "Lax",
        },
    ]

    try:
        await StealthyFetcher.async_fetch(
            url,
            headless=True,
            network_idle=False,
            block_webrtc=True,
            solve_cloudflare=True,
            cookies=cast(Any, pre_cookies),
            extra_headers={"Sec-GPC": "1"} if gpc else {},
            timeout=45_000,
            wait=5_000,
            page_setup=_page_setup,
            page_action=_page_action,
        )
    except Exception:  # noqa: BLE001
        return None

    cookies = [
        CookieSnapshot(
            name=c["name"],
            value=c["value"],
            domain=c["domain"],
            path=c["path"],
            secure=c.get("secure", False),
            http_only=c.get("httpOnly", False),
            same_site=c.get("sameSite", "Lax"),
            expires=c.get("expires"),
        )
        for c in captured_cookies
    ]

    # Same GCS/GCD extraction pipeline the primary scan uses
    gcs_records: list[GCSValue] = []
    gcd_records: list[str] = []
    for req_url in network_requests:
        raw_gcs = extract_gcs_from_url(req_url)
        if raw_gcs:
            gcs_records.append(parse_gcs_value(raw_gcs))
        raw_gcd = extract_gcd_from_url(req_url)
        if raw_gcd:
            gcd_records.append(raw_gcd)

    gcs_value: GCSValue | None = None
    if gcs_records:
        denied = [
            g for g in gcs_records if g.ad_storage == "denied" or g.analytics_storage == "denied"
        ]
        gcs_value = denied[0] if denied else gcs_records[-1]
    gcd_raw: str | None = None
    if gcd_records:
        denied_gcd = [g for g in gcd_records if is_gcd_denied_state(g)]
        gcd_raw = denied_gcd[0] if denied_gcd else gcd_records[-1]

    # Geo-targeting override: G111 with opt-out cookies → G100 (same rule the
    # primary scan applies for CCPA-mode CMPs).
    _denied_cookie_names = {
        "OptanonConsent",
        "cookieyes-consent",
        "CookieConsent",
        "cmplz_consent",
    }
    if (
        opted_out
        and gcs_value
        and gcs_value.ad_storage == "granted"
        and gcs_value.analytics_storage == "granted"
        and any(c.name in _denied_cookie_names for c in cookies)
    ):
        gcs_value = parse_gcs_value("G100")

    gtm_id: str | None = None
    for _req in network_requests:
        _m = re.search(r"/gtm\.js\?[^ ]*\bid=(GTM-[A-Z0-9]+)", _req)
        if _m:
            gtm_id = _m.group(1)
            break
    if not gtm_id and captured_html:
        gtm_id = extract_gtm_id_from_html(captured_html)

    return ScanResult(
        url=url,
        methodology=MethodologyFlag.S3,
        consent_state=consent_state,
        timestamp=datetime.now(tz=UTC),
        cookies=cookies,
        network_requests=network_requests,
        gcs_value=gcs_value,
        gcd_raw=gcd_raw,
        gtm_container_id=gtm_id,
        gtm_extraction_method=(GTMExtractionMethod.LIVE if gtm_id else GTMExtractionMethod.NONE),
        gtm_container_js=None,
        page_html=captured_html,
        gpc_header_sent=gpc,
        cmp_interaction_method="cookie_injection",
        detected_cmp=captured_cmp_name,
        cmp_detection_confidence=captured_cmp_conf,
        bot_detection_encountered=False,
        scan_mode_used="stealthy",
        har_path=None,
    )


async def check_gpc_fast(url: str, baseline_pixel_count: int) -> bool:
    """Quick GPC check — load page with Sec-GPC: 1 and compare pixel activity.

    Returns True if the site appears to respect GPC (fewer tracking pixels
    fire when the GPC signal is sent).
    """
    from consent_engine.tools.tool_06b_pixel_detector import detect_pixel_firings

    domain = _domain_from_url(url)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=_STEALTH_LAUNCH_ARGS)
        context = await browser.new_context(
            user_agent=_STEALTH_UA,
            viewport={"width": 1280, "height": 800},
            locale="en-US",
            timezone_id="America/Los_Angeles",
            extra_http_headers={"Sec-GPC": "1"},
        )
        await context.add_init_script(_STEALTH_INIT_SCRIPT)

        # Inject opt-out consent cookies
        await context.add_cookies(
            [
                {
                    "name": "OptanonConsent",
                    "value": build_onetrust_consent_cookie(opted_out=True),
                    "domain": domain,
                    "path": "/",
                    "secure": False,
                    "httpOnly": False,
                    "sameSite": "Lax",
                },
                {
                    "name": "OptanonAlertBoxClosed",
                    "value": "2026-01-01T00:00:00.000Z",
                    "domain": domain,
                    "path": "/",
                    "secure": False,
                    "httpOnly": False,
                    "sameSite": "Lax",
                },
            ]
        )

        page = await context.new_page()
        # Block heavy resources
        await page.route(
            "**/*.{png,jpg,jpeg,gif,webp,svg,ico,woff,woff2,ttf,eot,mp4,webm,mp3,css}",
            lambda route: route.abort(),
        )

        network_requests: list[str] = []
        page.on("request", lambda req: network_requests.append(req.url))

        with contextlib.suppress(Exception):
            await page.goto(url, wait_until="domcontentloaded", timeout=15_000)

        await asyncio.sleep(5.0)

        with contextlib.suppress(Exception):
            await browser.close()

    gpc_pixels = detect_pixel_firings(network_requests)
    gpc_pixel_count = len(gpc_pixels) if gpc_pixels else 0

    # GPC is "respected" if pixel count drops by at least 20% or to zero
    if baseline_pixel_count == 0:
        return gpc_pixel_count == 0
    return gpc_pixel_count < baseline_pixel_count * 0.8


async def scan_page(
    url: str,
    consent_state: ConsentState,
    methodology: MethodologyFlag = MethodologyFlag.S3,
    proxy_url: str | None = None,
) -> ScanResult:
    """Playwright headless scan under the specified consent state and methodology.

    Args:
        url: The page to audit.
        consent_state: OPTED_IN, OPTED_OUT, or GPC_OPTED_OUT.
        methodology: S1 (baseline), S2 (inconclusive — not implemented), or S3 (definitive).

    Returns:
        ScanResult with cookies, network requests, GCS value, GTM data.

    Methodology notes:
        S1 — Fresh context, no consent injection. Proves cookies fire before consent.
        S3 — Fresh context, OneTrust OptanonConsent cookie injected before goto().
             This is the legally defensible methodology for consent violation audits.
        S2 — Post-opt-out without reload. INCONCLUSIVE. Not implemented in v1.
             Never use S2 results as definitive evidence.
    """
    if methodology == MethodologyFlag.S2:
        raise NotImplementedError(
            "S2 methodology (post-opt-out without reload) is INCONCLUSIVE and "
            "not implemented in v1. Use S3 for definitive audit results."
        )

    # Safety net: abort any scan that exceeds 150s to prevent indefinite hangs
    # (e.g., SSGTM sites with giant google_tag_manager objects or streaming connections
    # that prevent networkidle from resolving).
    if methodology == MethodologyFlag.S1:
        return await asyncio.wait_for(_scan_s1(url, proxy_url=proxy_url), timeout=150)

    # S3 — consent state determines opted_out and GPC header
    if consent_state == ConsentState.GPC_OPTED_OUT:
        return await asyncio.wait_for(_scan_gpc(url, proxy_url=proxy_url), timeout=150)

    opted_out = consent_state == ConsentState.OPTED_OUT
    return await asyncio.wait_for(
        _scan_s3(url, opted_out=opted_out, proxy_url=proxy_url), timeout=150
    )
