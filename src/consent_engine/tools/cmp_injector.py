"""CMP Injection — builds per-CMP cookie + localStorage injection plans.

Provides `build_injection_plan()` which returns a `CMPInjectionPlan` containing:
- cookies: list of Playwright cookie dicts to inject into a browser context
- init_script: optional JS string to add via context.add_init_script() that
  mocks localStorage.getItem() for CMPs that store consent in localStorage.

The localStorage mock intercepts storage reads on the FIRST page load, so the
CMP bootstraps in denied state without needing an extra navigation cycle.

Design note on IAB TCF: The __tcfapi() specification does not standardise a
write/setConsent method. We therefore inject the pre-built all-denied
euconsent-v2 cookie string rather than attempting a programmatic write call.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote

from consent_engine.tools.cmp_detector import CMPProfile


@dataclass
class CMPInjectionPlan:
    """Injection artifacts for a single CMP."""

    cookies: list[dict[str, Any]] = field(default_factory=list)
    # Playwright cookie dicts: name, value, domain, path, secure, httpOnly, sameSite

    init_script: str | None = None
    # JS to add via context.add_init_script() — mocks localStorage.getItem for
    # CMPs that store consent in localStorage (Usercentrics, Ketch, Osano).


# ---------------------------------------------------------------------------
# All-denied IAB TCF v2.2 consent string
# This is a pre-built, vendor-reviewed base64url string encoding:
#   - All purposes: consent=false, legitimateInterest=false
#   - All vendors: consent=false, legitimateInterest=false
#   - gdprApplies=true
# It is safe to inject as-is for any IAB TCF v2.x implementation.
# ---------------------------------------------------------------------------
_TCF_ALL_DENIED = (
    "CPwAAAAPwAAAAAAAAAAAAAAAAAAAAQAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAA"
)


def _make_cookie(name: str, value: str, domain: str, *, path: str = "/") -> dict[str, Any]:
    return {
        "name": name,
        "value": value,
        "domain": domain,
        "path": path,
        "secure": False,
        "httpOnly": False,
        "sameSite": "Lax",
    }


def _localStorage_mock(*key_value_pairs: tuple[str, str]) -> str:
    """Generate a JS init_script that intercepts localStorage.getItem for given keys."""
    mapping = {k: v for k, v in key_value_pairs}
    mapping_js = json.dumps(mapping)
    return f"""
(function() {{
    const _denied = {mapping_js};
    const _orig = Storage.prototype.getItem;
    Storage.prototype.getItem = function(key) {{
        if (Object.prototype.hasOwnProperty.call(_denied, key)) {{
            return _denied[key];
        }}
        return _orig.call(this, key);
    }};
}})();
"""


# CMP names that have a concrete injection plan (cookies and/or init_script)
# wired up in build_injection_plan(). Used by Tool 3 to distinguish
# "we know this CMP AND we tried the right injection" from "we have no plan".
# OneTrust is handled upstream in _scan_s3() via build_onetrust_consent_cookie(),
# so it qualifies as a supported plan from the caller's perspective.
_CMPS_WITH_PLAN: frozenset[str] = frozenset(
    {
        "OneTrust",
        "CookieYes",
        "Cookiebot",
        "Termly",
        "Complianz",
        "WP Cookie Notice",
        "CookieScript",
        "CookieHub",
        "TrustArc",
        "Axeptio",
        "TrustCommander",
        "TrueVault",
        "IAB TCF",
        "Quantcast",
        "Usercentrics",
        "Osano",
        "Borlabs",
        "Consentmanager",
        "Shopify",
        "Pandectes",
    }
)


def has_plan_for(cmp_name: str | None) -> bool:
    """Return True if build_injection_plan() has a concrete injection plan
    (cookies or init_script) for this CMP name.

    Used by Tool 3 to distinguish the "broken consent wiring" case (plan
    existed, was injected, but GCS never flipped) from the "unknown/no plan"
    inconclusive case.
    """
    if not cmp_name:
        return False
    return cmp_name in _CMPS_WITH_PLAN


def build_injection_plan(profile: CMPProfile, domain: str) -> CMPInjectionPlan:
    """Return the cookie + init_script injection plan for the detected CMP.

    Args:
        profile: CMPProfile from detect_cmp()
        domain: The site's hostname (e.g. "example.com") — used for cookie domain.

    Returns:
        CMPInjectionPlan with cookies and optional localStorage init_script.
        Returns empty plan for unknown CMPs.
    """
    name = profile.name

    # OneTrust — handled upstream by _scan_s3() before this function is called.
    # Kept here so callers can check membership without special-casing.
    if name == "OneTrust":
        return CMPInjectionPlan()

    if name == "CookieYes":
        return CMPInjectionPlan(
            cookies=[
                _make_cookie(
                    "cookieyes-consent",
                    "consent:no,action:yes,advertisement:no,analytics:no,functional:no,performance:no",
                    domain,
                ),
                _make_cookie("CookieYesSeen1", "1", domain),
            ]
        )

    if name == "Cookiebot":
        value = quote(
            "{stamp:'-1',necessary:true,preferences:false,statistics:false,marketing:false,method:'explicit',ver:2147483647,utc:1700000000000,region:''}",
            safe="",
        )
        return CMPInjectionPlan(cookies=[_make_cookie("CookieConsent", value, domain)])

    if name == "Termly":
        value = json.dumps(
            {
                "analytics": False,
                "advertising": False,
                "performance": False,
                "social_networking": False,
                "essential": True,
            }
        )
        return CMPInjectionPlan(cookies=[_make_cookie("termly-consent", value, domain)])

    if name == "Complianz":
        return CMPInjectionPlan(
            cookies=[
                _make_cookie("cmplz_consent", "0", domain),
                _make_cookie("cmplz_banner-status", "dismissed", domain),
            ]
        )

    if name == "WP Cookie Notice":
        return CMPInjectionPlan(cookies=[_make_cookie("cookie_notice_accepted", "0", domain)])

    if name == "CookieScript":
        value = json.dumps({"action": "reject", "categories": ""})
        return CMPInjectionPlan(cookies=[_make_cookie("CookieScriptConsent", value, domain)])

    if name == "CookieHub":
        value = json.dumps({"analytics": False, "marketing": False, "preferences": False})
        return CMPInjectionPlan(cookies=[_make_cookie("cookiehub", value, domain)])

    if name == "TrustArc":
        # TrustArc deny-all state, multiple cookie shapes observed across deployments:
        #
        # notice_preferences — primary consent state
        #   "0:" = no categories selected (most common)
        #   "2:" = "required only" mode
        # notice_gdpr_prefs — GDPR category denial (0=required, 1=functional, 2=advertising)
        #   "0,1,2:" = all advertising/functional/analytics denied (required only)
        # cmapi_cookie_privacy — TrustArc Consent Manager API cookie
        #   "permit 1" = strictly necessary only (category 1)
        #   JSON form "{\"f\":true,\"a\":false}" used by newer deployments
        # notice_behavior — controls banner re-display; "expressed,eu" suppresses banner
        #
        # Both cookie shapes are set to maximize compatibility across TrustArc versions.
        # JS API (truste.cma.callApi setConsentDecision=0) and iframe DOM click
        # handled in cmp_clicker.py as layers 2 + 3.
        cmapi_json = json.dumps({"f": True, "a": False})
        return CMPInjectionPlan(
            cookies=[
                _make_cookie("notice_preferences", "0:", domain),
                _make_cookie("notice_gdpr_prefs", "0,1,2:", domain),
                _make_cookie("cmapi_cookie_privacy", "permit 1", domain),
                _make_cookie("cmapi_cookie_privacy", cmapi_json, domain, path="/legal"),
                _make_cookie("notice_behavior", "expressed,eu", domain),
                # TrustArc also respects consentUUID presence as "user has acted"
                _make_cookie("consentUUID", "00000000-0000-0000-0000-000000000000", domain),
            ]
        )

    if name == "Axeptio":
        return CMPInjectionPlan(
            cookies=[
                _make_cookie(
                    "axeptio_cookies",
                    json.dumps({"$$completed": True, "$$invalidate": False}),
                    domain,
                ),
                _make_cookie("axeptio_authorized_vendors", "[]", domain),
            ]
        )

    if name == "TrustCommander":
        value = json.dumps({"categories": [], "vendors": []})
        return CMPInjectionPlan(cookies=[_make_cookie("TC_PRIVACY", value, domain)])

    if name == "TrueVault":
        value = json.dumps(
            {
                "implicit": True,
                "analyticsPermitted": False,
                "personalizationPermitted": False,
                "adsPermitted": False,
                "notOptedOut": False,
                "essentialPermitted": True,
            }
        )
        return CMPInjectionPlan(cookies=[_make_cookie("polaris_consent_settings", value, domain)])

    if name in ("IAB TCF", "Quantcast", "CookieHub"):
        return CMPInjectionPlan(cookies=[_make_cookie("euconsent-v2", _TCF_ALL_DENIED, domain)])

    # --- localStorage-based CMPs ---

    if name == "Usercentrics":
        uc_denied = json.dumps(
            {
                "controllerId": "__denied__",
                "services": {},
                "dps": {"consent": False, "legitimate_interest": False},
            }
        )
        return CMPInjectionPlan(
            init_script=_localStorage_mock(("uc_settings", uc_denied)),
        )

    if name == "Ketch":
        # Ketch localStorage key is site-specific: _ketch_consent_v1_{orgCode}_{propertyCode}
        # Cannot be generically injected. Return empty plan — JS API handles opt-out:
        #   window.ketch('setConsent', {purposes: {analytics: {allowed: false}, ...}})
        # via the semaphore queue in cmp_clicker.py
        return CMPInjectionPlan()

    if name == "Osano":
        osano_denied = json.dumps(
            {
                "ANALYTICS": "DENY",
                "MARKETING": "DENY",
                "PERSONALIZATION": "DENY",
                "STORAGE": "DENY",
            }
        )
        return CMPInjectionPlan(
            init_script=_localStorage_mock(("osano_consentmanager", osano_denied)),
        )

    if name == "Borlabs":
        # v2: localStorage injection works. v3: REST API-based (server-side storage),
        # localStorage alone insufficient — cmp_clicker banner click handles v3.
        # We try v2 localStorage injection; if the banner still shows, clicker handles it.
        borlab_v2 = json.dumps(
            {"consents": {"statistics": False, "marketing": False}, "version": "2"}
        )
        return CMPInjectionPlan(
            init_script=_localStorage_mock(("BorlabsCookie", borlab_v2)),
        )

    if name == "Consentmanager":
        # Uses IAB TCF consent string + proprietary consent cookie
        return CMPInjectionPlan(
            cookies=[
                _make_cookie("euconsent-v2", _TCF_ALL_DENIED, domain),
                _make_cookie("cmpconsentstring", _TCF_ALL_DENIED, domain),
                # cmp_c stores custom vendor consent; empty = deny all
                _make_cookie("cmp_c", "", domain),
            ]
        )

    # iubenda: cookie name is _iub_cs-{cookiePolicyId} — site-specific, cannot inject generically.
    # Civic: CookieControl cookie has a signed/encoded field — injection unreliable.
    # Both fall through to banner click in cmp_clicker.py.
    if name in ("iubenda", "Civic"):
        return CMPInjectionPlan()

    if name in ("Shopify", "Pandectes"):
        # Shopify Customer Privacy API (used by Casper, Rhone, most Shopify Plus DTC).
        # Primary path: setTrackingConsent() via first-party JS API — works once
        # Shopify.loadFeatures finishes. We queue it via a pre-page-load init_script
        # so the call fires the moment the API becomes available, before any
        # analytics/marketing pixels load.
        #
        # Also write the first-party cookies Shopify stores for the decision
        # (_tracking_consent, _shopify_tm) so a returning-visitor pattern is
        # observable even before the JS API resolves. Cookie values mirror what
        # Shopify writes client-side after a "deny all" click in the first-party
        # consent banner.
        shopify_consent_cookie = quote(
            json.dumps(
                {
                    "v": "2.1",
                    "con": {
                        "CMP": {
                            "a": "",
                            "m": "",
                            "p": "",
                            "s": "",
                        }
                    },
                    "region": "US-CA",
                    "reg": "CCPA",
                    "purposes": {
                        "a": False,  # analytics
                        "p": False,  # preferences
                        "m": False,  # marketing
                        "sd": True,  # sale_of_data opt-out (CCPA)
                    },
                    "display_banner": False,
                    "sale_of_data_region": True,
                }
            ),
            safe="",
        )
        init_script = """
(function() {
    // Queue setTrackingConsent for as soon as Shopify.customerPrivacy is ready.
    // Shopify fires a 'trackingConsentAccepted' event after the consent write
    // completes; we just need to call the API with all purposes=false.
    function applyDenial() {
        try {
            if (window.Shopify && window.Shopify.customerPrivacy &&
                typeof window.Shopify.customerPrivacy.setTrackingConsent === 'function') {
                window.Shopify.customerPrivacy.setTrackingConsent(
                    {analytics: false, marketing: false, preferences: false, sale_of_data: true},
                    function() {}
                );
                return true;
            }
        } catch(e) {}
        return false;
    }
    if (applyDenial()) return;
    // Poll briefly for the API to become available (Shopify loads async).
    let tries = 0;
    const iv = setInterval(function() {
        if (applyDenial() || ++tries > 40) clearInterval(iv);
    }, 100);
    // Also hook Shopify.loadFeatures so we fire the moment the feature loads.
    Object.defineProperty(window, 'Shopify', {
        configurable: true,
        set: function(v) {
            Object.defineProperty(window, 'Shopify', {value: v, writable: true, configurable: true});
            applyDenial();
        },
        get: function() { return undefined; }
    });
})();
"""
        return CMPInjectionPlan(
            cookies=[
                _make_cookie("_tracking_consent", shopify_consent_cookie, domain),
                _make_cookie("_shopify_tm", "", domain),
                _make_cookie("_shopify_tw", "", domain),
            ],
            init_script=init_script,
        )

    # Transcend: airgap.setConsent requires genuine click event; blocks synthetic injection.
    # Ensighten: category IDs are deployment-specific — cannot write generic deny cookie.
    # DataGrail: no documented injection path.
    # CCM19: admin-defined cookie names — no generic path.
    # Wix: server-side managed.
    if name in ("Transcend", "Ensighten", "DataGrail", "CCM19", "Wix"):
        return CMPInjectionPlan()

    if name == "PiwikPRO":
        # Piwik PRO stores consent in localStorage ppms_privacy_{siteId} — site-specific suffix.
        # Cannot inject generically. JS API is the only reliable path.
        return CMPInjectionPlan()

    # Didomi and Sourcepoint: cookie injection unreliable (proprietary encrypted format).
    # Didomi 2025+: also uses binary didomi_dcs cookie.
    # Caller should fall through to JS API (Didomi.setUserDisagreeToAll, _sp_.rejectAll).
    if name in ("Didomi", "Sourcepoint"):
        return CMPInjectionPlan()

    # Unknown or unsupported CMP
    return CMPInjectionPlan()
