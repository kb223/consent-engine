"""CMP Banner-Click Module — auto-detect and click through opt-out flows.

Used as a fallback inside _scan_s3() when OneTrust cookie injection does not
suppress the consent banner (i.e., the site uses a different CMP provider).
"""

from __future__ import annotations

import asyncio
import re

from patchright.async_api import Frame, Page

from consent_engine.tools.cmp_detector import CMPProfile

# ---------------------------------------------------------------------------
# Vocabulary
# ---------------------------------------------------------------------------

REJECT_VOCAB: frozenset[str] = frozenset(
    {
        "reject",
        "decline",
        "deny",
        "opt out",
        "refuse",
        "disagree",
        "no thanks",
        "only necessary",
        "only essential",
        "save preferences",
        "confirm my choices",
        "do not sell",
        "do not sell my personal information",
        "your privacy choices",
        "opt-out of targeted advertising",
        "opt-out of targeted ads",
    }
)

# Vocabulary for navigation buttons that open a preferences/settings panel.
# These are clicked as a fallback step when no REJECT_VOCAB button is visible,
# to progress multi-step flows toward a save/confirm button.
PREF_NAV_VOCAB: frozenset[str] = frozenset(
    {
        "manage preferences",
        "manage cookies",
        "cookie settings",
        "privacy settings",
        "customize",
        "customise",
        "more options",
        "preferences",
        "settings",
    }
)

# Selector list tried when accessibility tree yields no scored nodes
_FALLBACK_SELECTORS: list[str] = [
    # Generic
    "[data-testid*='reject']",
    "[id*='reject']",
    "[class*='reject-all']",
    "button:has-text('Reject')",
    "button:has-text('Decline')",
    "button:has-text('Opt out')",
    # OneTrust
    "#onetrust-reject-all-handler",
    # Cookiebot
    "#CybotCookiebotDialogBodyButtonDecline",
    # CookieYes
    ".cky-btn-reject",
    # Didomi
    "#didomi-notice-disagree-button",
    # Quantcast
    ".qc-cmp2-summary-buttons button:first-child",
    # iubenda
    "#iubenda-cs-reject-btn",
    ".iubenda-cs-reject-btn",
    # Civic Cookie Control
    ".ccc-button-slides__button--deny",
    # Consentmanager
    ".cmpboxbtnno",
    "a[onclick*='denyAll']",
    # Borlabs
    ".borlabs-cookie-btn-deny",
    "[id*='BorlabsCookie'] .borlabs-cookie-btn-deny",
    # Termly
    "[data-tid='banner-decline']",
    # Complianz
    ".cmplz-btn.cmplz-deny",
    # CookieScript
    "#cookiescript_reject",
    # CookieHub
    ".ch2-btn.ch2-deny-all-btn",
    # TrustArc (iframe — also tried inside frame context)
    "#truste-consent-required",
    "#truste-consent-reject",
    "#truste-consent-button-reject",
    "a.call[onclick*='rejectAll']",
    "a[onclick*='declineAll']",
    # Shopify first-party consent banner
    "[data-shopify-consent='decline']",
    "button[data-tracking-optout]",
]

# Banner container selectors used to detect if a banner is present
_BANNER_SELECTORS = (
    "[role='dialog'], [id*='cookie'], [id*='consent'], "
    "[class*='banner'], [class*='cookie'], [class*='consent']"
)


# ---------------------------------------------------------------------------
# Pure helpers (no Playwright — unit-testable)
# ---------------------------------------------------------------------------


def _score_node(name: str) -> int:
    """Score an accessibility node name against REJECT_VOCAB.

    Returns:
        2 — exact word-boundary match found in name
        1 — substring match found (but not whole-word)
        0 — no match
    """
    lower = name.lower()
    best = 0
    for term in REJECT_VOCAB:
        if re.search(rf"\b{re.escape(term)}\b", lower):
            best = max(best, 2)
        elif term in lower:
            best = max(best, 1)
        if best == 2:
            break  # Can't do better
    return best


def _score_nav_node(name: str) -> int:
    """Score a node against PREF_NAV_VOCAB (navigation buttons for multi-step flows).

    Returns:
        2 — exact word-boundary match
        1 — substring match
        0 — no match
    """
    lower = name.lower()
    best = 0
    for term in PREF_NAV_VOCAB:
        if re.search(rf"\b{re.escape(term)}\b", lower):
            best = max(best, 2)
        elif term in lower:
            best = max(best, 1)
        if best == 2:
            break
    return best


def _is_gcs_denied(network_requests: list[str]) -> bool:
    """Return True if any URL in network_requests shows a GCS denied state.

    Uses parse_gcs_value from tool_03 for consistency — denied = both
    ad_storage and analytics_storage are "denied".
    """
    from consent_engine.tools.tool_03_browser_scanner import (
        extract_gcs_from_url,
        parse_gcs_value,
    )

    for url in network_requests:
        raw = extract_gcs_from_url(url)
        if raw is None:
            continue
        parsed = parse_gcs_value(raw)
        if parsed.ad_storage == "denied" and parsed.analytics_storage == "denied":
            return True
    return False


# ---------------------------------------------------------------------------
# Playwright helpers
# ---------------------------------------------------------------------------


async def _banner_present(page: Page) -> bool:
    """Return True if a consent banner element is visible on the page."""
    selectors = [s.strip() for s in _BANNER_SELECTORS.split(",")]
    try:
        for sel in selectors:
            locs = await page.locator(sel).all()
            for loc in locs:
                if await loc.is_visible(timeout=100):
                    return True
        return False
    except Exception:  # noqa: BLE001
        return False


async def attempt_cmp_decline(
    page: Page,
    network_requests: list[str],
    cmp_profile: CMPProfile | None = None,
    max_rounds: int = 4,
) -> str:
    """Click through a consent banner opt-out flow.

    Tries accessibility-tree scoring first; falls back to CSS selectors.
    Loops up to max_rounds to handle multi-step banners.

    Returns:
        "api_click"                 — JS API successfully triggered deny-all
        "banner_click"              — GCS denied signal confirmed in network requests
        "banner_click_inconclusive" — banner dismissed but no GCS confirmation
        "banner_click_failed"       — max rounds exhausted, banner still present
    """
    # --- 1. JS API Strategy ---

    # OneTrust — covers both GDPR and US CCPA flows
    if cmp_profile and cmp_profile.name == "OneTrust":
        try:
            result = await page.evaluate("""
                () => {
                    if (!window.OneTrust) return null;
                    if (typeof window.OneTrust.RejectAll === 'function') {
                        window.OneTrust.RejectAll();
                        return 'reject_all';
                    }
                    if (typeof window.OneTrust.UpdateConsent === 'function') {
                        window.OneTrust.UpdateConsent('Category', 'C0002:0,C0003:0,C0004:0');
                        return 'update_consent';
                    }
                    return null;
                }
            """)
            if result:
                await asyncio.sleep(1.5)
                if _is_gcs_denied(network_requests):
                    return "api_click"
        except Exception:
            pass

    # Didomi — setUserDisagreeToAll() is the authoritative deny-all API
    if cmp_profile and cmp_profile.js_api and cmp_profile.name == "Didomi":
        try:
            success = await page.evaluate(
                "() => { if (window.Didomi && typeof window.Didomi.setUserDisagreeToAll === 'function') { return window.Didomi.setUserDisagreeToAll(); } return false; }"
            )
            if success:
                await asyncio.sleep(1.5)
                if _is_gcs_denied(network_requests):
                    return "api_click"
        except Exception:
            pass

    # Sourcepoint — _sp_.rejectAll(campaignType) — confirmed in official docs
    # campaignType 'gdpr' for EU, 'ccpa' for US (try both)
    if cmp_profile and cmp_profile.name == "Sourcepoint":
        try:
            result = await page.evaluate("""
                () => {
                    if (!window._sp_) return null;
                    if (typeof window._sp_.rejectAll === 'function') {
                        // Try CCPA first (US ICP target), then GDPR
                        try { window._sp_.rejectAll('ccpa'); } catch(e) {}
                        try { window._sp_.rejectAll('gdpr'); } catch(e) {}
                        return 'sp_reject_all';
                    }
                    return null;
                }
            """)
            if result:
                await asyncio.sleep(2.0)
                if _is_gcs_denied(network_requests):
                    return "api_click"
        except Exception:
            pass

    # CookieYes — rejectAll() documented in Consent Banner Action API
    if cmp_profile and cmp_profile.name == "CookieYes":
        try:
            result = await page.evaluate("""
                () => {
                    if (typeof window.CookieYes !== 'undefined' && typeof window.CookieYes.rejectAll === 'function') {
                        window.CookieYes.rejectAll();
                        return 'cookieyes_reject';
                    }
                    // Fallback: dispatch custom CookieYes reject event
                    if (typeof window.getCkyConsent === 'function') {
                        document.dispatchEvent(new CustomEvent('cky-banner-reject-all'));
                        return 'cookieyes_event';
                    }
                    return null;
                }
            """)
            if result:
                await asyncio.sleep(1.5)
                if _is_gcs_denied(network_requests):
                    return "api_click"
        except Exception:
            pass

    # Usercentrics — UC_UI.denyAllConsents() confirmed in official docs
    # Runs inside shadow DOM (#usercentrics-root) so normal clicks fail
    if cmp_profile and cmp_profile.name == "Usercentrics":
        try:
            result = await page.evaluate("""
                () => {
                    if (typeof window.UC_UI !== 'undefined' && typeof window.UC_UI.denyAllConsents === 'function') {
                        window.UC_UI.denyAllConsents();
                        return 'uc_deny_all';
                    }
                    return null;
                }
            """)
            if result:
                await asyncio.sleep(1.5)
                if _is_gcs_denied(network_requests):
                    return "api_click"
        except Exception:
            pass

    # CookieHub — cookiehub.denyAll() confirmed in official docs
    if cmp_profile and cmp_profile.name == "CookieHub":
        try:
            result = await page.evaluate("""
                () => {
                    if (typeof window.cookiehub !== 'undefined' && typeof window.cookiehub.denyAll === 'function') {
                        window.cookiehub.denyAll();
                        return 'cookiehub_deny';
                    }
                    return null;
                }
            """)
            if result:
                await asyncio.sleep(1.5)
                if _is_gcs_denied(network_requests):
                    return "api_click"
        except Exception:
            pass

    # CookieScript — CookieScript.instance.reject() confirmed in official docs
    if cmp_profile and cmp_profile.name == "CookieScript":
        try:
            result = await page.evaluate("""
                () => {
                    if (window.CookieScript && window.CookieScript.instance &&
                        typeof window.CookieScript.instance.reject === 'function') {
                        window.CookieScript.instance.reject();
                        return 'cookiescript_reject';
                    }
                    return null;
                }
            """)
            if result:
                await asyncio.sleep(1.5)
                if _is_gcs_denied(network_requests):
                    return "api_click"
        except Exception:
            pass

    # Ketch — window.ketch('setConsent', {...}) via semaphore queue
    # localStorage key is site-specific so injection is not possible; use JS API only
    if cmp_profile and cmp_profile.name == "Ketch":
        try:
            result = await page.evaluate("""
                () => {
                    const deniedPurposes = {
                        analytics: {allowed: false},
                        marketing: {allowed: false},
                        advertising: {allowed: false},
                        personalization: {allowed: false},
                        functional: {allowed: false},
                    };
                    if (typeof window.ketch === 'function') {
                        window.ketch('setConsent', {purposes: deniedPurposes});
                        return 'ketch_set_consent';
                    }
                    if (Array.isArray(window.semaphore)) {
                        window.semaphore.push(['setConsent', {purposes: deniedPurposes}]);
                        return 'ketch_semaphore';
                    }
                    return null;
                }
            """)
            if result:
                await asyncio.sleep(2.0)
                if _is_gcs_denied(network_requests):
                    return "api_click"
        except Exception:
            pass

    # Piwik PRO — ppms.cm.api('setComplianceSettings', {...})
    if cmp_profile and cmp_profile.name == "PiwikPRO":
        try:
            result = await page.evaluate("""
                () => {
                    if (typeof window.ppms !== 'undefined' && window.ppms.cm && typeof window.ppms.cm.api === 'function') {
                        window.ppms.cm.api('setComplianceSettings', {
                            consents: {
                                analytics: {status: 0},
                                remarketing: {status: 0},
                                ab_testing: {status: 0},
                                user_feedback: {status: 0}
                            }
                        }, function(){}, function(){});
                        return 'piwikpro_deny';
                    }
                    return null;
                }
            """)
            if result:
                await asyncio.sleep(1.5)
                if _is_gcs_denied(network_requests):
                    return "api_click"
        except Exception:
            pass

    # Shopify Customer Privacy API — setTrackingConsent (server-side, async)
    if cmp_profile and cmp_profile.name in ("Shopify", "Pandectes"):
        try:
            result = await page.evaluate("""
                () => {
                    if (window.Shopify && window.Shopify.customerPrivacy &&
                        typeof window.Shopify.customerPrivacy.setTrackingConsent === 'function') {
                        window.Shopify.customerPrivacy.setTrackingConsent(
                            {analytics: false, marketing: false, preferences: false, sale_of_data: false},
                            function(err) {}
                        );
                        return 'shopify_tracking_consent_denied';
                    }
                    return null;
                }
            """)
            if result:
                await asyncio.sleep(2.0)
                if _is_gcs_denied(network_requests):
                    return "api_click"
        except Exception:
            pass

    # Consentmanager.net — __cmp('setConsent', 0, callback)
    if cmp_profile and cmp_profile.name == "Consentmanager":
        try:
            result = await page.evaluate("""
                () => {
                    if (typeof window.__cmp === 'function') {
                        window.__cmp('setConsent', 0, function() {});
                        return 'cmp_set_consent_deny';
                    }
                    return null;
                }
            """)
            if result:
                await asyncio.sleep(1.5)
                if _is_gcs_denied(network_requests):
                    return "api_click"
        except Exception:
            pass

    # Cookiebot — submitCustomConsent(preferences, statistics, marketing)
    # All false = deny all optional categories
    if cmp_profile and cmp_profile.name == "Cookiebot":
        try:
            result = await page.evaluate("""
                () => {
                    if (window.Cookiebot && typeof window.Cookiebot.submitCustomConsent === 'function') {
                        window.Cookiebot.submitCustomConsent(false, false, false);
                        return 'cookiebot_deny';
                    }
                    // Fallback: trigger decline via CookieConsent object
                    if (window.CookieConsent && typeof window.CookieConsent.decline === 'function') {
                        window.CookieConsent.decline();
                        return 'cookieconsent_decline';
                    }
                    return null;
                }
            """)
            if result:
                await asyncio.sleep(1.5)
                if _is_gcs_denied(network_requests):
                    return "api_click"
        except Exception:
            pass

    # TrustArc — truste.cma.callApi('setConsentDecision', '0') + PrivacyManagerAPI
    # TrustArc runs inside an iframe but exposes a parent-window JS API on window.truste.
    # Also try window.PrivacyManagerAPI.callApi for newer deployments.
    if cmp_profile and cmp_profile.name == "TrustArc":
        try:
            result = await page.evaluate("""
                () => {
                    let hit = null;
                    try {
                        if (window.truste && window.truste.cma && typeof window.truste.cma.callApi === 'function') {
                            // setConsentDecision accepts '0' = deny all, '1' = allow all, category-coded string otherwise
                            window.truste.cma.callApi('setConsentDecision', window.truste.cma.callApi('getDomain') || '*', '0');
                            hit = 'trustarc_cma_deny';
                        }
                    } catch(e) {}
                    try {
                        if (window.PrivacyManagerAPI && typeof window.PrivacyManagerAPI.callApi === 'function') {
                            window.PrivacyManagerAPI.callApi('setConsentDecision', window.location.hostname, {consent: {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}});
                            hit = hit || 'trustarc_pmapi_deny';
                        }
                    } catch(e) {}
                    try {
                        if (window.truste && window.truste.eu && window.truste.eu.clickPathAPI && typeof window.truste.eu.clickPathAPI === 'function') {
                            window.truste.eu.clickPathAPI('decline');
                            hit = hit || 'trustarc_clickpath_decline';
                        }
                    } catch(e) {}
                    // PostMessage fallback — TrustArc banners listen for a "submit_preferences" message
                    try {
                        window.postMessage(JSON.stringify({
                            source: 'preference_manager',
                            message: 'submit_preferences',
                            consent: {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}
                        }), '*');
                        hit = hit || 'trustarc_postmessage';
                    } catch(e) {}
                    return hit;
                }
            """)
            if result:
                await asyncio.sleep(2.0)
                if _is_gcs_denied(network_requests):
                    return "api_click"
        except Exception:
            pass

    # Osano (common on US DTC brands)
    try:
        result = await page.evaluate("""
            () => {
                if (window.Osano && window.Osano.cm && typeof window.Osano.cm.deny === 'function') {
                    window.Osano.cm.deny();
                    return 'osano_deny';
                }
                // Fallback: denyAll() alias
                if (window.Osano && window.Osano.cm && typeof window.Osano.cm.denyAll === 'function') {
                    window.Osano.cm.denyAll();
                    return 'osano_deny_all';
                }
                return false;
            }
        """)
        if result:
            await asyncio.sleep(1.5)
            if _is_gcs_denied(network_requests):
                return "api_click"
    except Exception:
        pass

    for _round in range(max_rounds):
        clicked = await _try_click_decline(page, cmp_profile)

        if not clicked:
            # Check toggles before giving up (if we previously clicked "Manage Preferences")
            toggled = await _uncheck_toggles(page, cmp_profile)
            if toggled:
                # Need to loop again to click the "Save" button
                await asyncio.sleep(0.5)
                continue

            # Nothing scored — wait briefly in case a secondary panel is still rendering
            await asyncio.sleep(0.8)
            if not await _banner_present(page):
                break  # No banner and nothing to click — we're done
            # Banner still present but nothing scored — give up
            break

        await asyncio.sleep(1.5)

        if _is_gcs_denied(network_requests):
            return "banner_click"

        if not await _banner_present(page):
            # Banner gone — wait briefly for secondary panel to render, then loop again
            await asyncio.sleep(0.5)
            continue

    # Loop exhausted
    if _is_gcs_denied(network_requests):
        return "banner_click"

    if not await _banner_present(page):
        return "banner_click_inconclusive"

    return "banner_click_failed"


async def _uncheck_toggles(page: Page, cmp_profile: CMPProfile | None) -> bool:
    """Find and uncheck any enabled toggles for Marketing/Analytics/Sales before saving.

    Handles both GDPR category toggles and US CCPA sales/advertising opt-out toggles.
    """
    context: Page | Frame = page
    if cmp_profile and cmp_profile.dom_type == "iframe":
        for frame in page.frames:
            if "truste" in frame.name or "truste" in frame.url:
                context = frame
                break

    found = False

    # GDPR: checkboxes inside labels with consent category names
    _gdpr_labels = (
        "label:has-text('Analytics') input[type='checkbox'], "
        "label:has-text('Marketing') input[type='checkbox'], "
        "label:has-text('Advertising') input[type='checkbox'], "
        "label:has-text('Functional') input[type='checkbox']"
    )
    try:
        locators = await context.locator(_gdpr_labels).all()
        for loc in locators:
            if await loc.is_checked():
                await loc.uncheck()
                found = True
    except Exception:
        pass

    # US CCPA: OneTrust sales/sharing/targeted advertising toggles
    # These are ON by default — we need to switch them to OFF before confirming
    _ccpa_toggle_selectors = [
        "input[id*='sale']:checked",
        "input[id*='Sale']:checked",
        "input[id*='sharing']:checked",
        "input[id*='targeted']:checked",
        "input.category-switch-handler:checked",
        "label:has-text('Sale') input:checked",
        "label:has-text('Sharing') input:checked",
        "label:has-text('Targeted Advertising') input:checked",
        "label:has-text('Cookie-Based Sales') input:checked",
        "label:has-text('Opt Out') input:not(:checked)",  # some use inverse logic
    ]
    for sel in _ccpa_toggle_selectors:
        try:
            locators = await context.locator(sel).all()
            for loc in locators:
                try:
                    if await loc.is_visible():
                        await loc.click()
                        found = True
                        await asyncio.sleep(0.3)
                except Exception:
                    pass
        except Exception:
            pass

    # OneTrust CCPA toggle: look for enabled switches inside the CCPA preference center
    # These are often rendered as <div class="ot-switch"> with an <input> inside
    try:
        switches = await context.locator(".ot-switch input[type='checkbox']:checked").all()
        for sw in switches:
            try:
                label_text = await context.locator(
                    f"label[for='{await sw.get_attribute('id')}']"
                ).inner_text(timeout=500)
                # Only uncheck non-essential categories
                if any(
                    kw in label_text.lower()
                    for kw in ("sale", "advertis", "target", "analytic", "market", "sharing")
                ):
                    await sw.click()
                    found = True
                    await asyncio.sleep(0.3)
            except Exception:
                pass
    except Exception:
        pass

    return found


async def _try_click_decline(page: Page, cmp_profile: CMPProfile | None = None) -> bool:
    """Find and click the best decline/reject element. Returns True if clicked."""
    context: Page | Frame = page

    # --- LAYER 3: Specialized CMP Handling ---

    # Axeptio: shadow DOM — normal CSS selectors can't reach buttons.
    # Cookie injection handles opt-out pre-load. If we reach the clicker it means
    # cookies didn't suppress it; try JS API via axeptio events.
    if cmp_profile and cmp_profile.name == "Axeptio":
        try:
            result = await page.evaluate("""
                () => {
                    // Axeptio exposes a global event system
                    if (window._axeptio_) {
                        // Mark all choices as denied in their internal store
                        if (typeof window._axeptio_.on === 'function') {
                            window.axeptio_deny_all = true;
                        }
                    }
                    // Try direct cookie set as last resort
                    document.cookie = 'axeptio_cookies=' + encodeURIComponent(
                        JSON.stringify({$$completed: true, $$invalidate: false})
                    ) + '; path=/';
                    document.cookie = 'axeptio_authorized_vendors=; path=/';
                    return 'axeptio_cookie_reset';
                }
            """)
            if result:
                await asyncio.sleep(1.0)
        except Exception:
            pass

    # Usercentrics: shadow DOM — UC_UI JS API is authoritative (handled above in JS API section).
    # If we reach here the API failed; try to pierce shadow DOM via evaluate.
    if cmp_profile and cmp_profile.name == "Usercentrics":
        try:
            clicked = await page.evaluate("""
                () => {
                    const root = document.querySelector('#usercentrics-root');
                    if (!root || !root.shadowRoot) return false;
                    const buttons = root.shadowRoot.querySelectorAll('button');
                    for (const btn of buttons) {
                        const text = (btn.innerText || btn.textContent || '').toLowerCase();
                        if (text.includes('deny') || text.includes('reject') || text.includes('decline')) {
                            btn.click();
                            return true;
                        }
                    }
                    return false;
                }
            """)
            if clicked:
                await asyncio.sleep(1.5)
                return True
        except Exception:
            pass

    # TrueVault: multi-step CCPA footer flow
    if cmp_profile and cmp_profile.name == "TrueVault":
        # In CCPA mode, the "banner" is often not a banner but a footer link.
        # Step 1: Look for "Your Privacy Choices" or "Do Not Sell"
        selectors = [
            ".truevault-polaris-optout",
            "a[class*='truevault-polaris-optout']",
            "a:has-text('Your Privacy Choices')",
            "a:has-text('Do Not Sell My Personal Information')",
            "span:has-text('Your Privacy Choices')",
            "a:has-text('Privacy Choices')",
        ]

        clicked = False
        for sel in selectors:
            try:
                locator = page.locator(sel)
                if await locator.count() > 0 and await locator.first.is_visible():
                    await locator.first.click()
                    await asyncio.sleep(3)
                    clicked = True
                    break
            except Exception:
                continue

        if not clicked:
            # Maybe it's buried in "More Info"
            try:
                more_info = page.locator(".BannerAction_actionText__xVcTc:has-text('More Info')")
                if await more_info.count() > 0:
                    await more_info.first.click()
                    await asyncio.sleep(3)
            except Exception:
                pass

        # Step 2: Handle the form (check opt-out and submit)
        for frame in page.frames:
            try:
                checkbox = frame.locator(
                    "label:has-text('Browser Opt-Out'), input[type='checkbox']"
                )
                if await checkbox.count() > 0:
                    await checkbox.first.click()
                    await asyncio.sleep(0.5)

                submit = frame.locator(
                    "button:has-text('SUBMIT REQUEST'), button:has-text('Confirm'), .truevault-polaris-optout-submit"
                )
                if await submit.count() > 0:
                    await submit.first.click()
                    await asyncio.sleep(3)
                    return True
            except Exception:
                continue

    # --- LAYER 4: Standard button-click strategy ---
    # 0. Context selection based on dom_type
    if cmp_profile and cmp_profile.dom_type == "iframe":
        for frame in page.frames:
            if "truste" in frame.name or "truste" in frame.url:
                context = frame
                break

    # Primary: collect interactive element names via JS
    nodes: list[dict[str, object]] = await context.evaluate(
        """() => {
            const tags = ['button', 'a', '[role="button"]', '[role="link"]'];
            const results = [];
            for (const sel of tags) {
                document.querySelectorAll(sel).forEach(el => {
                    // Skip hidden elements (display:none or inside a hidden ancestor)
                    if (el.offsetParent === null && el.tagName.toLowerCase() !== 'body') return;
                    const name = (el.innerText || el.getAttribute('aria-label') || '').trim();
                    const role = el.getAttribute('role') || el.tagName.toLowerCase();
                    if (name) results.push({ name, role });
                });
            }
            return results;
        }"""
    )

    best_node, best_score = _find_best_node(nodes)

    if best_score > 0 and best_node:
        try:
            name = str(best_node.get("name", ""))
            role_raw = str(best_node.get("role", "button")).lower()
            # Normalise tag-name roles to ARIA roles Playwright understands
            aria_role = "link" if role_raw == "a" else "button"
            if aria_role == "link":
                await context.get_by_role("link", name=name).first.click(timeout=3_000)
            else:
                await context.get_by_role("button", name=name).first.click(timeout=3_000)
            return True
        except Exception:  # noqa: BLE001
            pass

    # Layer 4: Standard button-click strategy
    # 1. Look for an immediate "Reject All" button (Tier 1)
    if best_score == 0 and nodes:
        nav_best: dict[str, object] | None = None
        nav_score = 0
        for node in nodes if isinstance(nodes, list) else []:
            s = _score_nav_node(str(node.get("name", "") or ""))
            if s > nav_score:
                nav_score = s
                nav_best = node
        if nav_score > 0 and nav_best:
            try:
                name = str(nav_best.get("name", ""))
                role_raw = str(nav_best.get("role", "button")).lower()
                aria_role = "link" if role_raw == "a" else "button"
                if aria_role == "link":
                    await context.get_by_role("link", name=name).first.click(timeout=3_000)
                else:
                    await context.get_by_role("button", name=name).first.click(timeout=3_000)
                return True
            except Exception:  # noqa: BLE001
                pass

    # Fallback: CSS selector list
    for selector in _FALLBACK_SELECTORS:
        try:
            locator = context.locator(selector).first
            if await locator.count() > 0:
                await locator.click(timeout=3_000)
                return True
        except Exception:  # noqa: BLE001
            continue

    return False


def _find_best_node(
    nodes: list[dict[str, object]] | dict[str, object] | None,
    _best: tuple[dict[str, object] | None, int] = (None, 0),
) -> tuple[dict[str, object] | None, int]:
    """Walk a flat list (or recursive dict) of nodes, return highest-scoring one.

    Accepts either:
    - a flat list of {"name": str, "role": str} dicts (JS DOM collection), or
    - a recursive accessibility-snapshot dict with optional "children" key.

    The tuple default ``(None, 0)`` is immutable, so there is no
    mutable-default-argument hazard.
    """
    if nodes is None:
        return _best

    # Flat list branch (JS DOM collection)
    if isinstance(nodes, list):
        for node in nodes:
            name = str(node.get("name", "") or "")
            score = _score_node(name)
            if score > _best[1]:
                _best = (node, score)
        return _best

    # Recursive dict branch (accessibility snapshot — kept for forward-compat)
    name = str(nodes.get("name", "") or "")
    score = _score_node(name)
    if score > _best[1]:
        _best = (nodes, score)

    children = nodes.get("children") or []
    for child in children if isinstance(children, list) else []:
        _best = _find_best_node(child, _best)

    return _best
