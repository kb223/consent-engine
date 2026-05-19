"""CMP Detection — identifies which Consent Management Platform is loaded.

Runs after networkidle. CMP scripts are often deferred or GTM-injected, so
checking before networkidle produces false negatives. We use a single
comprehensive JS evaluation across all known CMP globals rather than
per-CMP wait_for_function calls (faster, no timeout stacking).

Returns a CMPProfile describing the detected CMP and its characteristics.
"""

from __future__ import annotations

from dataclasses import dataclass

from playwright.async_api import Page


@dataclass
class CMPProfile:
    """Detected CMP characteristics used by cmp_injector and cmp_clicker."""

    name: str
    # "OneTrust" | "CookieYes" | "Cookiebot" | "Usercentrics" | "Didomi" |
    # "TrustArc" | "Quantcast" | "Osano" | "Ketch" | "Truyo" | "Sourcepoint" |
    # "TrustCommander" | "Termly" | "Complianz" | "Axeptio" | "Klaro" |
    # "CookieScript" | "CookieHub" | "Crownpeak" | "WP Cookie Notice" |
    # "TrueVault" | "IAB TCF" | "unknown"

    confidence: str
    # "high"   — JS global confirmed
    # "medium" — script URL or cookie matched only
    # "low"    — DOM selector matched only

    dom_type: str
    # "standard"     — regular DOM, click buttons normally
    # "shadow_dom"   — banner inside shadow root (Usercentrics, Axeptio)
    # "iframe"       — consent UI inside <iframe> (TrustArc)
    # "headless_api" — no visible banner; JS API or cookie injection only (Ketch)

    js_api: bool
    # True if a proprietary deny-all JS API is known for this CMP


# ---------------------------------------------------------------------------
# Detection rules — ordered by JS global specificity (most specific first).
# Each rule: (js_global_expr, name, confidence, dom_type, js_api)
# js_global_expr is evaluated as JS in the page context.
# ---------------------------------------------------------------------------

_JS_GLOBAL_RULES: list[tuple[str, str, str, str, bool]] = [
    # (js_expression_that_returns_truthy, name, confidence, dom_type, js_api)
    (
        "typeof window.OneTrust !== 'undefined' || typeof window.OnetrustActiveGroups !== 'undefined'",
        "OneTrust",
        "high",
        "standard",
        True,  # RejectAll() + UpdateConsent() JS APIs confirmed in official docs
    ),
    (
        "typeof window.getCkyConsent === 'function' || typeof window.CookieYes !== 'undefined'",
        "CookieYes",
        "high",
        "standard",
        True,  # CookieYes.rejectAll() documented in Consent Banner Action API
    ),
    (
        "typeof window.CookieConsent !== 'undefined' && typeof window.CookieConsent.stamp !== 'undefined'",
        "Cookiebot",
        "high",
        "standard",
        True,  # Cookiebot.submitCustomConsent(true, false, false, false)
    ),
    ("typeof window.UC_UI !== 'undefined'", "Usercentrics", "high", "shadow_dom", True),
    ("typeof window.Didomi !== 'undefined'", "Didomi", "high", "standard", True),
    (
        # Legacy .eu check was too narrow — modern TrustArc Consent Manager
        # exposes window.truste (base object) or window.PrivacyManagerAPI
        # without setting .eu on US deployments.
        "typeof window.truste !== 'undefined' "
        "|| typeof window.PrivacyManagerAPI !== 'undefined' "
        "|| typeof window.trustarc !== 'undefined'",
        "TrustArc",
        "high",
        "iframe",
        False,  # No clean deny-all JS API; uses PrivacyManagerAPI postMessage protocol
    ),
    ("typeof window.Osano !== 'undefined'", "Osano", "high", "standard", True),
    (
        "typeof window.ketch === 'function' || typeof window.semaphore !== 'undefined'",
        "Ketch",
        "high",
        "headless_api",
        True,  # window.ketch('setConsent', {...}) via semaphore queue
    ),
    ("typeof window.Truyo !== 'undefined'", "Truyo", "high", "standard", False),
    (
        "typeof window._sp_ !== 'undefined'",
        "Sourcepoint",
        "high",
        "standard",
        True,
    ),  # _sp_.rejectAll()
    (
        "(typeof window.tC !== 'undefined' && typeof window.tc_cmp !== 'undefined')",
        "TrustCommander",
        "high",
        "standard",
        False,
    ),
    ("typeof window.Termly !== 'undefined'", "Termly", "high", "standard", False),
    ("typeof window.complianz !== 'undefined'", "Complianz", "high", "standard", False),
    (
        "typeof window.axeptio !== 'undefined'",
        "Axeptio",
        "high",
        "shadow_dom",  # CONFIRMED shadow DOM: axeptio overlay runs inside shadow root (browser-use #2276)
        True,  # cookie injection covers; shadow DOM blocks CSS selectors
    ),
    ("typeof window.klaro !== 'undefined'", "Klaro", "high", "standard", True),
    (
        "typeof window.CookieScript !== 'undefined' && typeof window.CookieScript.instance !== 'undefined'",
        "CookieScript",
        "high",
        "standard",
        True,  # CookieScript.instance.reject()
    ),
    (
        "typeof window.cookiehub !== 'undefined'",
        "CookieHub",
        "high",
        "standard",
        True,  # cookiehub.denyAll()
    ),
    ("typeof window.evidon !== 'undefined'", "Crownpeak", "high", "standard", True),
    ("typeof window.polaris !== 'undefined'", "TrueVault", "high", "standard", False),
    # iubenda — JS global is _iub (object) or _iub.cs
    (
        "typeof window._iub !== 'undefined' && typeof window._iub.cs !== 'undefined'",
        "iubenda",
        "high",
        "standard",
        False,  # No documented denyAll() browser API; cookie injection not possible (site-specific policy ID)
    ),
    # Borlabs Cookie — v2 uses BorlabsCookie global, v3 uses borlabs_cookie
    (
        "typeof window.BorlabsCookie !== 'undefined' || typeof window.borlabs_cookie !== 'undefined'",
        "Borlabs",
        "high",
        "standard",
        True,  # v2: BorlabsCookie.denyAll(); v3: banner click required
    ),
    # Civic Cookie Control (UK/enterprise)
    (
        "typeof window.CookieControl !== 'undefined' && typeof window.CookieControl.load === 'function'",
        "Civic",
        "high",
        "standard",
        False,  # No clean deny-all JS API; cookie has signed encoded field (unreliable injection)
    ),
    # Consentmanager.net — uses __cmp but also sets window.cmp_ok (differentiates from generic TCF)
    (
        "typeof window.__cmp === 'function' && typeof window.cmp_ok !== 'undefined'",
        "Consentmanager",
        "high",
        "standard",
        True,  # __cmp('setConsent', 0, callback)
    ),
    # Shopify Customer Privacy API — used by Shopify/Shopify Plus DTC stores
    (
        "typeof window.Shopify !== 'undefined' && typeof window.Shopify.customerPrivacy !== 'undefined'",
        "Shopify",
        "high",
        "headless_api",  # consent written server-side via Storefront API
        True,  # setTrackingConsent({analytics:false, marketing:false, ...})
    ),
    # Pandectes — Shopify-specific CMP (leading for Shopify Plus brands)
    (
        "typeof window.Pandectes !== 'undefined'",
        "Pandectes",
        "high",
        "standard",
        False,  # no documented deny-all JS API; uses Shopify setTrackingConsent
    ),
    # Piwik PRO — enterprise analytics with built-in CMP (fintech, B2B SaaS)
    (
        "typeof window.ppms !== 'undefined' && typeof window.ppms.cm !== 'undefined'",
        "PiwikPRO",
        "high",
        "standard",
        True,  # ppms.cm.api('setComplianceSettings', {consents: {analytics: {status: 0}, ...}})
    ),
    # Transcend (airgap.js) — enterprise SaaS, network-level enforcement
    (
        "typeof window.airgap !== 'undefined'",
        "Transcend",
        "high",
        "standard",
        False,  # airgap.setConsent requires genuine user click event — blocks synthetic injection
    ),
    # Ensighten / CHEQ Consent — enterprise TMS with consent module
    (
        "typeof window.Bootstrapper !== 'undefined' && typeof window.Bootstrapper.privacy !== 'undefined'",
        "Ensighten",
        "high",
        "standard",
        False,  # category IDs are deployment-specific; no generic deny-all
    ),
    # DataGrail Consent — enterprise privacy platform CMP
    (
        "typeof window.DG_BANNER_API !== 'undefined'",
        "DataGrail",
        "high",
        "standard",
        False,  # no documented programmatic deny-all
    ),
    # Klaro — open source CMP (some enterprise/public sector)
    # Already in list above; keeping alias check
    # CCM19 — German enterprise CMP (DACH region)
    (
        "typeof window.CCM !== 'undefined'",
        "CCM19",
        "high",
        "standard",
        False,  # no English deny-all API; banner UI required
    ),
    # Wix built-in consent (platform-native, no opt-out JS path)
    (
        "typeof window.consentPolicyManager !== 'undefined'",
        "Wix",
        "high",
        "headless_api",
        False,  # no deny-all JS method; server-side managed
    ),
    # IAB TCF generic — must come after all CMP-specific globals to avoid masking them.
    # Quantcast, CookieHub etc. all expose __tcfapi but also have specific globals above.
    ("typeof window.__tcfapi === 'function'", "IAB TCF", "high", "standard", False),
    # GPC/GPP generic
    (
        "navigator.globalPrivacyControl === true || typeof window.__gpp === 'function'",
        "GPC/GPP",
        "medium",
        "standard",
        False,
    ),
]

# Script URL patterns as fallback when no JS global is present
_SCRIPT_URL_RULES: list[tuple[str, str]] = [
    ("cdn.cookielaw.org", "OneTrust"),
    ("optanon.blob.core.windows.net", "OneTrust"),  # alternate OneTrust CDN
    ("cdn-cookieyes.com", "CookieYes"),
    ("consent.cookiebot.com", "Cookiebot"),
    ("consentcdn.cookiebot.com", "Cookiebot"),  # alternate Cookiebot CDN
    ("app.usercentrics.eu", "Usercentrics"),
    ("privacy-proxy.usercentrics.eu", "Usercentrics"),  # Usercentrics self-hosted proxy
    ("sdk.privacy-center.org", "Didomi"),
    ("consent.trustarc.com", "TrustArc"),
    ("consent-pref.trustarc.com", "TrustArc"),
    ("preferences-mgr.truste.com", "TrustArc"),
    ("privacy-policy.truste.com", "TrustArc"),
    ("consent-manager.trustarc.com", "TrustArc"),
    (".trustarc.com/", "TrustArc"),  # generic subdomain catch
    (".truste.com/", "TrustArc"),
    ("cmp.quantcast.com", "Quantcast"),
    ("cmp.osano.com", "Osano"),
    ("global.ketchcdn.com", "Ketch"),
    ("cmp.truyo.com", "Truyo"),
    (".truyo.com/", "Truyo"),  # generic Truyo CDN catch (truyoproductionuscdn.truyo.com, etc.)
    ("cdn.privacy-mgmt.com", "Sourcepoint"),
    ("sourcepoint.mgr.consensu.org", "Sourcepoint"),
    ("cdn.tagcommander.com", "TrustCommander"),
    ("app.termly.io", "Termly"),
    ("cdn.complianz.io", "Complianz"),
    ("static.axept.io", "Axeptio"),
    ("cdn.cookie-script.com", "CookieScript"),
    ("cookiehub.com", "CookieHub"),
    ("c.betrad.com", "Crownpeak"),
    ("polaris.truevaultcdn.com", "TrueVault"),
    ("cdn.iubenda.com", "iubenda"),
    ("cc.cdn.civiccomputing.com", "Civic"),
    ("cdn.consentmanager.net", "Consentmanager"),
    ("cdn.pandectes.io", "Pandectes"),
    ("transcend-cdn.com", "Transcend"),
    ("nexus.ensighten.com", "Ensighten"),
    ("cloud.ccm19.de", "CCM19"),
    # Additional CDN patterns + commonly-missed CMPs (added v0.5.4)
    ("cdn.cookiehub.eu", "CookieHub"),
    ("widget.cookieinformation.com", "CookieInformation"),
    ("cookieinformation.com", "CookieInformation"),
    ("cdn.cookielaw.org", "OneTrust"),  # duplicate-safe; already present above as primary
    ("policy.cookiereports.com", "CookieReports"),
    ("klaro.kiprotect.com", "Klaro"),
    ("cdn.cookiebot.eu", "Cookiebot"),  # EU CDN endpoint (in addition to .com)
    ("borlabs.io", "Borlabs"),  # Borlabs Cookie WordPress plugin CDN
    ("cdn.real-cookie-banner.com", "RealCookieBanner"),
    ("cookieyes.com", "CookieYes"),  # broader pattern beyond -cdn-cookieyes
    ("cmp.cookieinformation.com", "CookieInformation"),
    ("policy.app.cookieinformation.com", "CookieInformation"),
    ("static.policy.app.cookieinformation.com", "CookieInformation"),
    ("cdn.privacymanagement.com", "Sourcepoint"),  # Sourcepoint legacy
    ("api.privacy-mgmt.com", "Sourcepoint"),
    (".sp-prod.net/", "Sourcepoint"),
    ("sdks.shopifycdn.com/consent", "Shopify"),  # Shopify Customer Privacy
]

# DOM selector fallbacks
_DOM_SELECTOR_RULES: list[tuple[str, str]] = [
    ("[id^='cky-']", "CookieYes"),
    ("#cky-consent-container", "CookieYes"),
    ("#usercentrics-root", "Usercentrics"),
    ("iframe[id*='truste']", "TrustArc"),
    ("#truste-consent-track", "TrustArc"),
    ("#truste-consent-button", "TrustArc"),
    ("#consent_blackbar", "TrustArc"),
    ("div[id^='trustarc-']", "TrustArc"),
    ("#CybotCookiebotDialog", "Cookiebot"),
    ("#onetrust-banner-sdk", "OneTrust"),
    ("#didomi-host", "Didomi"),
    ("#didomi-notice", "Didomi"),
    ("#klaro", "Klaro"),
    (".qc-cmp2-container", "Quantcast"),
    ("#iubenda-cs-banner", "iubenda"),
    (".osano-cm-window", "Osano"),
    ("#ccc", "Civic"),
    ("#cmpbox", "Consentmanager"),
    ("#cookie-notice", "WP Cookie Notice"),
    ("#BorlabsCookieBox", "Borlabs"),
]

# Profile metadata by name (for rules matched via URL or DOM)
_CMP_META: dict[str, tuple[str, str, bool]] = {
    # name: (confidence, dom_type, js_api)
    "OneTrust": ("medium", "standard", True),
    "CookieYes": ("medium", "standard", True),
    "Cookiebot": ("medium", "standard", True),
    "Usercentrics": ("medium", "shadow_dom", True),
    "Didomi": ("medium", "standard", True),
    "TrustArc": ("medium", "iframe", False),
    "Quantcast": ("medium", "standard", False),
    "Osano": ("medium", "standard", True),
    "Ketch": ("medium", "headless_api", True),
    "Truyo": ("medium", "standard", False),
    "Sourcepoint": ("medium", "standard", True),
    "TrustCommander": ("medium", "standard", False),
    "Termly": ("medium", "standard", False),
    "Complianz": ("medium", "standard", False),
    "Axeptio": ("medium", "shadow_dom", True),  # shadow DOM confirmed
    "Klaro": ("low", "standard", True),
    "CookieScript": ("medium", "standard", True),
    "CookieHub": ("medium", "standard", True),
    "Crownpeak": ("medium", "standard", True),
    "WP Cookie Notice": ("low", "standard", False),
    "TrueVault": ("medium", "standard", False),
    "iubenda": ("medium", "standard", False),
    "Borlabs": ("medium", "standard", True),
    "Civic": ("medium", "standard", False),
    "Consentmanager": ("medium", "standard", True),
    "Shopify": ("medium", "headless_api", True),
    "Pandectes": ("medium", "standard", False),
    "PiwikPRO": ("medium", "standard", True),
    "Transcend": ("medium", "standard", False),
    "Ensighten": ("medium", "standard", False),
    "DataGrail": ("medium", "standard", False),
    "CCM19": ("medium", "standard", False),
    "Wix": ("medium", "headless_api", False),
    "IAB TCF": ("high", "standard", False),
    "GPC/GPP": ("medium", "standard", False),
    # Added in v0.5.4 — caught by URL pattern only (no JS-global yet).
    "CookieInformation": ("medium", "standard", False),
    "CookieReports": ("medium", "standard", False),
    "RealCookieBanner": ("medium", "standard", False),
}


async def detect_cmp(page: Page, network_requests: list[str]) -> CMPProfile:
    """Detect the CMP loaded on the page.

    Priority:
    1. JS global check (high confidence) — single multi-expression JS eval
    2. Script URL pattern match in network_requests (medium confidence)
    3. DOM selector check (low confidence)
    4. Falls back to "unknown"

    IMPORTANT: Call this after page.goto(wait_until="networkidle") so that
    deferred and GTM-injected CMP scripts have had time to execute.
    """
    # --- 1. JS globals: single evaluate with all rules concatenated ---
    # Build a JS expression that returns the matching CMP name or null.
    js_checks = " || ".join(
        f"(({expr}) ? {repr(name)} : null)" for expr, name, *_ in _JS_GLOBAL_RULES
    )
    js_expr = f"(() => {{ return {js_checks}; }})()"

    try:
        matched_name: str | None = await page.evaluate(js_expr)
    except Exception:  # noqa: BLE001
        matched_name = None

    if matched_name:
        for _expr, name, confidence, dom_type, js_api in _JS_GLOBAL_RULES:
            if name == matched_name:
                return CMPProfile(
                    name=name,
                    confidence=confidence,
                    dom_type=dom_type,
                    js_api=js_api,
                )

    # --- 2. Script URL pattern match ---
    for url in network_requests:
        for pattern, name in _SCRIPT_URL_RULES:
            if pattern in url:
                confidence, dom_type, js_api = _CMP_META.get(name, ("medium", "standard", False))
                return CMPProfile(
                    name=name,
                    confidence="medium",
                    dom_type=dom_type,
                    js_api=js_api,
                )

    # --- 3. DOM selector fallback ---
    for selector, name in _DOM_SELECTOR_RULES:
        try:
            count = await page.locator(selector).count()
            if count > 0:
                confidence, dom_type, js_api = _CMP_META.get(name, ("low", "standard", False))
                return CMPProfile(
                    name=name,
                    confidence="low",
                    dom_type=dom_type,
                    js_api=js_api,
                )
        except Exception:  # noqa: BLE001
            continue

    return CMPProfile(name="unknown", confidence="low", dom_type="standard", js_api=False)


def detect_cmp_from_network_only(network_requests: list[str]) -> CMPProfile | None:
    """Network-URL-only CMP detection for post-scan refinement.

    Mirrors the URL fallback path of `detect_cmp` but takes only the URL list
    (no Playwright Page), so it can be invoked from `audit.py` after the scan
    completes when the full network_requests list is available. Catches CMPs
    that load past the in-scan `networkidle` window (Truyo's late-loaded CDN
    on O'Reilly is the canonical example).

    Returns None when no CMP URL pattern matches.
    """
    for url in network_requests:
        for pattern, name in _SCRIPT_URL_RULES:
            if pattern in url:
                confidence, dom_type, js_api = _CMP_META.get(name, ("medium", "standard", False))
                return CMPProfile(
                    name=name,
                    confidence="medium",
                    dom_type=dom_type,
                    js_api=js_api,
                )
    return None
