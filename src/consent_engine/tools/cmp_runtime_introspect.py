"""CMP runtime introspection + consent-event dataLayer capture.

Two related extractors that run inside the page context after the CMP SDK
has had a chance to initialize. Both are best-effort: any failure returns
gracefully so the audit pipeline never breaks because a CMP's API surface
changed shape between SDK versions.

## What this answers

1. **What does the CMP *think* it is doing?**
   `OneTrust.testLog()` exposes the template name (Loi-25v1.1, GDPR,
   CCPA-USA), the geolocation rule (e.g. "Global Audience (loi 25-GDPR)"
   for a Quebec page that gets both Law 25 + GDPR coverage), the consent
   model (opt-in vs opt-out), and the vendor + cookie lists the CMP knows
   about. Compare against what actually fires = forensic evidence of
   CMP misconfiguration.

2. **What consent commands did the page push to dataLayer?**
   Captures the narrow set of consent signals that matter legally:
   - `gtag('consent', 'default', {...})` — initial Consent Mode state
   - `gtag('consent', 'update', {...})` — state transitions
   - `OneTrustGroupsUpdated` — OneTrust category-state change broadcasts
   - `OneTrustLoaded` — OneTrust SDK ready signal
   - Cookiebot / CookieYes / Didomi / Usercentrics native events
   - `__tcfapi` calls (IAB TCF)
   - Anything with "consent" in the event name (custom site events)

## What this does NOT do

- Full dataLayer capture (page_view, click, ecommerce events). Out of
  scope for this audit type. The forensic question is "did the CMP work?"
  not "what did the site track?"
- Modify the page or trigger interactions. Pure read.
- Throw on missing globals. Returns `None` / `[]` if the CMP API or
  dataLayer doesn't exist.

## CMP coverage roadmap

- v0.5.7: OneTrust
- v0.6.0: + Truyo, Cookiebot, CookieYes, Didomi, Usercentrics  (this file)
- v0.6.1: TrustArc, Sourcepoint, CookieInformation, Klaro, Borlabs
"""

from __future__ import annotations

import asyncio
import json
from contextlib import suppress
from typing import TYPE_CHECKING, Any, cast

from consent_engine.models.audit_result import CMPRuntimeConfig, ConsentEvent

if TYPE_CHECKING:
    from playwright.async_api import Page


# Per-CMP introspection JS expressions. Each returns a JSON-serializable
# dict or `null` if the CMP isn't present. Wrapped in a try/catch on the
# Python side, so internal CMP-API exceptions don't break the scan.
_ONETRUST_INTROSPECT_JS = """
(() => {
  try {
    if (typeof window.OneTrust === 'undefined') return null;
    const ot = window.OneTrust;

    // === Step 1: trigger testLog() — Python side captures output ===
    // OneTrust.testLog() prints to the page console via console.log + %c
    // styling, console.group, and console.table. Rather than wrap those
    // here (brittle across SDK versions), we trigger the call and let the
    // Python-side Playwright console-event listener catch every message.
    // The parsed fields land back here via a global the listener writes to.
    if (typeof ot.testLog === 'function') {
      try { ot.testLog(); } catch (e) {}
    }
    // Give buffer one tick for any async console output to flush.
    // (testLog is synchronous in current SDKs but defensive against future.)
    const logBlob = (window.__ce_testlog_blob__ || '');

    // Patterns to extract from the testLog output. OneTrust changes the
    // exact wording across script versions but these patterns are stable
    // back to script-version ~202101.
    function match(re) {
      const m = logBlob.match(re);
      return m ? m[1].trim() : null;
    }
    const scriptVersion = match(/Script Version Published:\\s+([0-9.]+)/i);
    const consentModelLog = match(/consent model is:\\s+(opt-in|opt-out|implicit)/i);
    const geoCountry = match(/\\bGeolocation is\\s+([A-Z]{2,3})\\b/);
    // Geolocation rule may contain spaces + parens; stop at newline OR
    // the next "The " sentence prefix that testLog uses between facts.
    const geoRule = match(/Geolocation rule is\\s+(.+?)(?:\\n|$)/i);
    // TemplateName tokens are word + dashes + dots (e.g. Loi-25v1.1, CCPA-USA).
    const templateName = match(/TemplateName\\s+is\\s+(\\S+)/i);

    // === Step 2: pull structured data from GetDomainData() ===
    // GetDomainData gives us the expected cookies-by-category map and the
    // canonical consent model object — fallbacks if testLog wasn't available.
    const domainData = (typeof ot.GetDomainData === 'function') ? ot.GetDomainData() : null;

    // Consent model from GetDomainData is a dict like {Name: 'opt-in'}
    let consentModelData = null;
    if (domainData && domainData.ConsentModel) {
      if (typeof domainData.ConsentModel === 'string') {
        consentModelData = domainData.ConsentModel.toLowerCase();
      } else if (typeof domainData.ConsentModel === 'object' && domainData.ConsentModel.Name) {
        consentModelData = String(domainData.ConsentModel.Name).toLowerCase();
      }
    }

    // Reconcile consent model: prefer testLog match, fall back to GetDomainData.
    let consentModel = 'unknown';
    const candidate = (consentModelLog || consentModelData || '').toLowerCase();
    if (candidate.includes('opt-in') || candidate === 'optin') consentModel = 'opt-in';
    else if (candidate.includes('opt-out') || candidate === 'optout') consentModel = 'opt-out';
    else if (candidate.includes('implicit')) consentModel = 'implicit';

    // Cookies-by-category map
    const expectedCookies = {};
    if (domainData && Array.isArray(domainData.Groups)) {
      for (const grp of domainData.Groups) {
        const cat = grp.OptanonGroupId || grp.GroupName || 'unknown';
        const cookies = [];
        if (Array.isArray(grp.FirstPartyCookies)) {
          for (const c of grp.FirstPartyCookies) {
            if (c && c.Name) cookies.push(c.Name);
          }
        }
        if (Array.isArray(grp.Hosts)) {
          for (const h of grp.Hosts) {
            if (h && Array.isArray(h.Cookies)) {
              for (const c of h.Cookies) {
                if (c && c.Name) cookies.push(c.Name);
              }
            }
          }
        }
        if (cookies.length > 0) expectedCookies[cat] = cookies;
      }
    }

    // Vendor IDs (IAB TCF mode)
    const vendorIds = [];
    if (domainData && Array.isArray(domainData.GeneralVendorsIds)) {
      for (const v of domainData.GeneralVendorsIds) vendorIds.push(String(v));
    } else if (domainData && Array.isArray(domainData.GeneralVendors)) {
      for (const v of domainData.GeneralVendors) {
        if (v && v.VendorId) vendorIds.push(String(v.VendorId));
      }
    }

    // Domain ID — extractable from the cookielaw.org script URL if not in data
    let domainId = null;
    const otScript = document.querySelector('script[src*="cdn.cookielaw.org"]');
    if (otScript) {
      const m = otScript.src.match(/cookielaw\\.org\\/(?:consent\\/)?([0-9a-f-]{30,})/i);
      if (m) domainId = m[1];
    }

    return {
      cmp_name: 'OneTrust',
      template_name: templateName,
      geolocation_rule: geoRule,
      geolocation_country: geoCountry,
      consent_model: consentModel,
      expected_cookies_by_category: expectedCookies,
      expected_vendor_ids: vendorIds,
      script_version: scriptVersion,
      domain_id: domainId,
      raw_dump: logBlob.slice(0, 4000) || (domainData ? JSON.stringify(domainData).slice(0, 4000) : null),
    };
  } catch (e) {
    return null;
  }
})()
"""


async def extract_onetrust_runtime(page: Page) -> CMPRuntimeConfig | None:
    """Return OneTrust's self-reported runtime config, or None if not OneTrust.

    Safe to call on any page — returns None unless `window.OneTrust` exists
    AND `OneTrust.GetDomainData()` returns a populated object. Five-second
    timeout so a hung introspection never blocks the audit.

    Implementation:
    1. Attach a Playwright console listener that buffers messages.
    2. Trigger `OneTrust.testLog()` to fire console output that exposes
       template_name + geolocation_rule + script_version (fields not
       available on GetDomainData()).
    3. Inject the captured buffer back into the page as `window.__ce_testlog_blob__`.
    4. Run the introspection JS which regex-parses the blob + reads
       GetDomainData() for structured fields.
    5. Detach the listener.
    """
    captured: list[str] = []

    def _on_console(msg: Any) -> None:
        with suppress(Exception):
            captured.append(msg.text)

    page.on("console", _on_console)
    try:
        # First check OneTrust is even present + trigger testLog so the
        # console listener has something to buffer.
        try:
            await asyncio.wait_for(
                page.evaluate(
                    "() => { if (typeof window.OneTrust !== 'undefined' && "
                    "typeof window.OneTrust.testLog === 'function') { "
                    "try { window.OneTrust.testLog(); } catch (e) {} } }"
                ),
                timeout=3.0,
            )
        except (TimeoutError, Exception):  # noqa: BLE001
            return None

        # Brief settle for console messages to flush across the CDP wire.
        await asyncio.sleep(0.3)

        # Push the captured blob into the page so the introspection JS can
        # regex it. `repr()` would mangle quotes; use json.dumps for safety.
        blob = "\n".join(captured)
        await page.evaluate(
            "(b) => { window.__ce_testlog_blob__ = b; }",
            blob,
        )

        # Run the full introspection now that the blob is in place.
        try:
            result = await asyncio.wait_for(
                page.evaluate(_ONETRUST_INTROSPECT_JS), timeout=5.0
            )
        except (TimeoutError, Exception):  # noqa: BLE001
            return None

        if not result or not isinstance(result, dict):
            return None

        try:
            return CMPRuntimeConfig.model_validate(result)
        except Exception:  # noqa: BLE001
            return None
    finally:
        with suppress(Exception):
            page.remove_listener("console", _on_console)


# Narrow set of consent-related events. Anything else (page_view, click,
# ecommerce, etc.) is ignored — this is a CONSENT forensics tool, not a
# generic dataLayer dump.
_CONSENT_EVENT_EXTRACT_JS = """
(() => {
  try {
    const dl = window.dataLayer;
    if (!Array.isArray(dl)) return [];

    const consentEvents = [];

    // Patterns that flag a dataLayer entry as consent-relevant.
    // Order matters here: more specific checks first.
    const ONETRUST_GROUPS_UPDATED = /^OneTrustGroupsUpdated$/i;
    const ONETRUST_LOADED = /^OneTrustLoaded$/i;
    const COOKIEYES = /^cookieyes_consent_update$|^cky_consent$|^ckyConsentEvent$/i;
    const COOKIEBOT = /^Cookiebot|^CookieConsentDeclaration/i;
    const DIDOMI = /^didomi/i;
    const USERCENTRICS = /^uc_(?:consent|ui)|^usercentrics|^UC_/i;
    const TCF_API = /^tcfapi|__tcfapi/i;
    const TRUYO = /^truyo|^Truyo/i;
    const KETCH = /^ketch_consent|^ketch\./i;
    const SHOPIFY_PRIVACY = /^shopify_privacy|^trekkie\.ready|^trekkie\.config/i;
    const TEALIUM_CONSENT = /^utag\.gdpr|^utag_gdpr|^tealium_consent/i;
    const SOURCEPOINT = /^sp_consent|^_sp_consent/i;
    const TRUSTARC = /^TrustArc|^truste_consent/i;
    const COOKIEFIRST = /^CookieFirst|^cookiefirst_consent/i;
    const KLARO = /^klaro_/i;
    const IUBENDA = /^iubenda_consent/i;
    const CONSENT_FALLBACK = /consent/i;

    function classify(eventName, entry) {
      // gtag consent commands — entries shaped like ['consent', 'default'|'update', {...params}]
      // The actual array entries are arguments objects; gtag-stub-loaded dataLayer
      // stores them as numeric-index objects. Handle both.
      if (Array.isArray(entry) && entry.length >= 2 && entry[0] === 'consent') {
        if (entry[1] === 'default') return 'gtag_consent_default';
        if (entry[1] === 'update') return 'gtag_consent_update';
      }
      if (entry && typeof entry === 'object' && entry['0'] === 'consent') {
        if (entry['1'] === 'default') return 'gtag_consent_default';
        if (entry['1'] === 'update') return 'gtag_consent_update';
      }

      if (!eventName) return null;
      if (ONETRUST_GROUPS_UPDATED.test(eventName)) return 'onetrust_groups_updated';
      if (ONETRUST_LOADED.test(eventName)) return 'onetrust_loaded';
      if (COOKIEYES.test(eventName)) return 'cookieyes_consent';
      if (COOKIEBOT.test(eventName)) return 'cookiebot';
      if (DIDOMI.test(eventName)) return 'didomi';
      if (USERCENTRICS.test(eventName)) return 'usercentrics';
      if (TCF_API.test(eventName)) return 'tcfapi';
      if (TRUYO.test(eventName)) return 'custom_consent';     // map to custom_consent
      if (KETCH.test(eventName)) return 'custom_consent';
      if (SHOPIFY_PRIVACY.test(eventName)) return 'custom_consent';
      if (TEALIUM_CONSENT.test(eventName)) return 'custom_consent';
      if (SOURCEPOINT.test(eventName)) return 'custom_consent';
      if (TRUSTARC.test(eventName)) return 'custom_consent';
      if (COOKIEFIRST.test(eventName)) return 'custom_consent';
      if (KLARO.test(eventName)) return 'custom_consent';
      if (IUBENDA.test(eventName)) return 'custom_consent';
      if (CONSENT_FALLBACK.test(eventName)) return 'custom_consent';
      return null;
    }

    function flattenParams(obj) {
      const out = {};
      if (!obj || typeof obj !== 'object') return out;
      for (const [k, v] of Object.entries(obj)) {
        if (k === 'event' || k === 'gtm.uniqueEventId' || k === 'gtm.start') continue;
        if (v === null || v === undefined) continue;
        if (typeof v === 'object') {
          try { out[k] = JSON.stringify(v).slice(0, 200); } catch (e) { out[k] = String(v); }
        } else {
          out[k] = String(v).slice(0, 200);
        }
      }
      return out;
    }

    for (let i = 0; i < dl.length; i++) {
      const entry = dl[i];
      if (!entry) continue;

      const eventName = (typeof entry === 'object' && !Array.isArray(entry)) ? (entry.event || null) : null;
      const source = classify(eventName, entry);
      if (!source) continue;

      let params = {};
      if (source === 'gtag_consent_default' || source === 'gtag_consent_update') {
        // Third arg is the consent params object
        const p = Array.isArray(entry) ? entry[2] : entry['2'];
        params = flattenParams(p);
      } else {
        params = flattenParams(entry);
      }

      consentEvents.push({
        index_in_stream: i,
        source: source,
        event_name: eventName,
        params: params,
      });
    }

    return consentEvents;
  } catch (e) {
    return [];
  }
})()
"""


async def extract_consent_events(page: Page) -> list[ConsentEvent]:
    """Return the consent-related subset of window.dataLayer pushes.

    Empty list when dataLayer is missing, empty, or contains no consent
    events. Five-second timeout. Validation failures on individual rows
    are silently dropped (rather than failing the whole list) so malformed
    pushes don't sink the audit.
    """
    try:
        raw = await asyncio.wait_for(page.evaluate(_CONSENT_EVENT_EXTRACT_JS), timeout=5.0)
    except (TimeoutError, Exception):  # noqa: BLE001
        return []

    if not isinstance(raw, list):
        return []

    events: list[ConsentEvent] = []
    for row in cast(list[dict[str, Any]], raw):
        try:
            events.append(ConsentEvent.model_validate(row))
        except Exception:  # noqa: BLE001
            continue
    return events


# ============================================================================
# Cookiebot
# ============================================================================
#
# Cookiebot exposes `window.Cookiebot` after the SDK initializes. The runtime
# config we want lives on Cookiebot.consent (current state), Cookiebot.consents
# (per-category booleans), Cookiebot.regulations (which legal framework
# Cookiebot decided to apply), and Cookiebot.declaredCookies (the expected
# vendor cookie list, mirrors OneTrust's GetDomainData().Groups).
_COOKIEBOT_INTROSPECT_JS = """
(() => {
  try {
    if (typeof window.Cookiebot === 'undefined') return null;
    const cb = window.Cookiebot;
    const consent = cb.consent || {};
    const regulations = cb.regulations || {};

    // Cookiebot.regulations.gdprApplies | ccpaApplies | lgpdApplies
    let template = null;
    const regs = [];
    if (regulations.gdprApplies) regs.push('GDPR');
    if (regulations.ccpaApplies) regs.push('CCPA');
    if (regulations.lgpdApplies) regs.push('LGPD');
    if (regs.length) template = regs.join('+');

    // Cookiebot is always opt-in under GDPR; opt-out only if pure CCPA
    let consentModel = 'opt-in';
    if (regulations.ccpaApplies && !regulations.gdprApplies) {
      consentModel = 'opt-out';
    }

    // Expected cookies map: Cookiebot.declaredCookies is an array of
    // {Name, Provider, Purpose, Category, Lifetime} objects.
    const expectedCookies = {};
    if (Array.isArray(cb.declaredCookies)) {
      for (const c of cb.declaredCookies) {
        const cat = c.Category || 'unknown';
        if (!expectedCookies[cat]) expectedCookies[cat] = [];
        if (c.Name) expectedCookies[cat].push(c.Name);
      }
    }

    return {
      cmp_name: 'Cookiebot',
      template_name: template,
      geolocation_rule: regulations ? JSON.stringify(regulations).slice(0, 200) : null,
      geolocation_country: cb.country || null,
      consent_model: consentModel,
      expected_cookies_by_category: expectedCookies,
      expected_vendor_ids: [],
      script_version: cb.serial || null,
      domain_id: cb.dbid || null,
      raw_dump: JSON.stringify({
        consent: consent,
        regulations: regulations,
        country: cb.country,
        cbid: cb.cbid,
        dbid: cb.dbid,
      }).slice(0, 4000),
    };
  } catch (e) { return null; }
})()
"""


async def extract_cookiebot_runtime(page: Page) -> CMPRuntimeConfig | None:
    """Return Cookiebot's self-reported runtime config, or None."""
    try:
        result = await asyncio.wait_for(page.evaluate(_COOKIEBOT_INTROSPECT_JS), timeout=5.0)
    except (TimeoutError, Exception):  # noqa: BLE001
        return None
    if not result or not isinstance(result, dict):
        return None
    try:
        return CMPRuntimeConfig.model_validate(result)
    except Exception:  # noqa: BLE001
        return None


# ============================================================================
# CookieYes
# ============================================================================
#
# CookieYes exposes its API via `window.getCkyConsent()` returning the current
# consent decision dict, plus `window.cky_*` configuration globals. The
# `_ckyConsent` cookie carries the persisted state.
_COOKIEYES_INTROSPECT_JS = """
(() => {
  try {
    const has = typeof window.getCkyConsent === 'function'
             || typeof window.CookieYes !== 'undefined'
             || typeof window._cky_config !== 'undefined';
    if (!has) return null;

    let consent = null;
    if (typeof window.getCkyConsent === 'function') {
      try { consent = window.getCkyConsent(); } catch (e) {}
    }

    // CookieYes templates: GDPR (default), CCPA, LGPD. Inferred from config
    // when present, otherwise from the consent.regulation field.
    const cfg = window._cky_config || window.CookieYes || {};
    const regulation = (consent && consent.regulation) || cfg.regulation || null;

    let template = null;
    let consentModel = 'opt-in';
    if (regulation) {
      const r = String(regulation).toUpperCase();
      if (r.includes('CCPA')) { template = 'CCPA'; consentModel = 'opt-out'; }
      else if (r.includes('GDPR')) { template = 'GDPR'; }
      else if (r.includes('LGPD')) { template = 'LGPD'; }
      else { template = r; }
    }

    // Expected cookies by category — CookieYes stores in cfg.categories
    const expectedCookies = {};
    if (cfg.categories && typeof cfg.categories === 'object') {
      for (const [cat, info] of Object.entries(cfg.categories)) {
        if (info && Array.isArray(info.cookies)) {
          expectedCookies[cat] = info.cookies.map(c => c.name || c).filter(Boolean);
        }
      }
    }

    return {
      cmp_name: 'CookieYes',
      template_name: template,
      geolocation_rule: regulation,
      geolocation_country: (consent && consent.country) || null,
      consent_model: consentModel,
      expected_cookies_by_category: expectedCookies,
      expected_vendor_ids: [],
      script_version: cfg.version || null,
      domain_id: cfg.domainId || cfg.siteId || null,
      raw_dump: JSON.stringify({consent: consent, cfg_keys: Object.keys(cfg).slice(0, 40)}).slice(0, 4000),
    };
  } catch (e) { return null; }
})()
"""


async def extract_cookieyes_runtime(page: Page) -> CMPRuntimeConfig | None:
    """Return CookieYes's self-reported runtime config, or None."""
    try:
        result = await asyncio.wait_for(page.evaluate(_COOKIEYES_INTROSPECT_JS), timeout=5.0)
    except (TimeoutError, Exception):  # noqa: BLE001
        return None
    if not result or not isinstance(result, dict):
        return None
    try:
        return CMPRuntimeConfig.model_validate(result)
    except Exception:  # noqa: BLE001
        return None


# ============================================================================
# Didomi
# ============================================================================
#
# Didomi exposes `window.Didomi.getCurrentUserStatus()` (consent decision),
# `Didomi.getVendors()` (vendor list), and `Didomi.getConfig()` (template +
# geolocation). The opt-in/opt-out model depends on the regulation applied.
_DIDOMI_INTROSPECT_JS = """
(() => {
  try {
    if (typeof window.Didomi === 'undefined') return null;
    const d = window.Didomi;

    let userStatus = null;
    let config = null;
    try { userStatus = (typeof d.getCurrentUserStatus === 'function') ? d.getCurrentUserStatus() : null; } catch (e) {}
    try { config = (typeof d.getConfig === 'function') ? d.getConfig() : null; } catch (e) {}

    // Template / regulation
    let template = null;
    const reg = config && config.regulation;
    if (reg) {
      const r = String(reg).toLowerCase();
      if (r.includes('gdpr')) template = 'GDPR';
      else if (r.includes('ccpa')) template = 'CCPA';
      else if (r.includes('lgpd')) template = 'LGPD';
      else if (r.includes('none')) template = 'NONE';
      else template = String(reg);
    }

    let consentModel = 'opt-in';
    if (template === 'CCPA' || template === 'NONE') consentModel = 'opt-out';

    // Geolocation
    let geoCountry = null;
    let geoRule = null;
    try {
      const loc = (typeof d.getUserCountryCode === 'function') ? d.getUserCountryCode() : null;
      if (loc) geoCountry = loc;
    } catch (e) {}
    if (config && config.user && config.user.country) geoCountry = config.user.country;
    if (config && config.app && config.app.name) geoRule = config.app.name;

    // Expected cookies: Didomi maps purposes to vendors → cookies. We surface
    // the purpose list since the cookie list is harder to reach without iterating.
    const expectedCookies = {};
    if (config && config.app && Array.isArray(config.app.vendors)) {
      expectedCookies['enabled_vendors'] = config.app.vendors.slice(0, 50).map(String);
    }

    // Vendor IDs
    const vendorIds = [];
    try {
      const vs = (typeof d.getVendors === 'function') ? d.getVendors() : null;
      if (Array.isArray(vs)) {
        for (const v of vs.slice(0, 50)) {
          if (v && v.id !== undefined) vendorIds.push(String(v.id));
        }
      }
    } catch (e) {}

    return {
      cmp_name: 'Didomi',
      template_name: template,
      geolocation_rule: geoRule,
      geolocation_country: geoCountry,
      consent_model: consentModel,
      expected_cookies_by_category: expectedCookies,
      expected_vendor_ids: vendorIds,
      script_version: (config && config.app && config.app.apiVersion) || null,
      domain_id: (config && config.app && config.app.apiKey) || null,
      raw_dump: JSON.stringify({user_status: userStatus, app_name: config && config.app && config.app.name}).slice(0, 4000),
    };
  } catch (e) { return null; }
})()
"""


async def extract_didomi_runtime(page: Page) -> CMPRuntimeConfig | None:
    """Return Didomi's self-reported runtime config, or None."""
    try:
        result = await asyncio.wait_for(page.evaluate(_DIDOMI_INTROSPECT_JS), timeout=5.0)
    except (TimeoutError, Exception):  # noqa: BLE001
        return None
    if not result or not isinstance(result, dict):
        return None
    try:
        return CMPRuntimeConfig.model_validate(result)
    except Exception:  # noqa: BLE001
        return None


# ============================================================================
# Usercentrics
# ============================================================================
#
# Usercentrics exposes `window.__ucCmp` (Cmp v2) or `window.UC_UI` (legacy v1).
# The v2 API gives us getConsents(), getSettings(), getDocumentLanguage(), etc.
_USERCENTRICS_INTROSPECT_JS = """
(() => {
  try {
    const ucCmp = window.__ucCmp;
    const ucUI = window.UC_UI;
    if (!ucCmp && !ucUI) return null;

    let settings = null;
    let consents = null;
    if (ucCmp) {
      try { settings = (typeof ucCmp.getSettings === 'function') ? ucCmp.getSettings() : null; } catch (e) {}
      try { consents = (typeof ucCmp.getConsents === 'function') ? ucCmp.getConsents() : null; } catch (e) {}
    } else if (ucUI) {
      try { settings = (typeof ucUI.getSettingsId === 'function') ? { settingsId: ucUI.getSettingsId() } : null; } catch (e) {}
      try { consents = (typeof ucUI.getServicesBaseInfo === 'function') ? ucUI.getServicesBaseInfo() : null; } catch (e) {}
    }

    // Template — Usercentrics calls it "regulation" or "settings.consentSection"
    let template = null;
    let consentModel = 'opt-in';
    if (settings && settings.regulation) {
      template = String(settings.regulation).toUpperCase();
      if (template.includes('CCPA') || template === 'US') consentModel = 'opt-out';
    } else if (settings && settings.consent && settings.consent.legalFramework) {
      template = String(settings.consent.legalFramework).toUpperCase();
    }

    // Expected services / vendors
    const vendorIds = [];
    if (Array.isArray(consents)) {
      for (const c of consents.slice(0, 50)) {
        const id = c.id || c.templateId || c.serviceId;
        if (id) vendorIds.push(String(id));
      }
    }

    return {
      cmp_name: 'Usercentrics',
      template_name: template,
      geolocation_rule: (settings && (settings.controllerId || settings.country)) || null,
      geolocation_country: (settings && settings.country) || null,
      consent_model: consentModel,
      expected_cookies_by_category: {},
      expected_vendor_ids: vendorIds,
      script_version: (settings && settings.version) || null,
      domain_id: (settings && (settings.settingsId || settings.settingsID)) || null,
      raw_dump: JSON.stringify({
        settings_keys: settings ? Object.keys(settings).slice(0, 30) : null,
        consent_count: Array.isArray(consents) ? consents.length : 0,
      }).slice(0, 4000),
    };
  } catch (e) { return null; }
})()
"""


async def extract_usercentrics_runtime(page: Page) -> CMPRuntimeConfig | None:
    """Return Usercentrics's self-reported runtime config, or None."""
    try:
        result = await asyncio.wait_for(page.evaluate(_USERCENTRICS_INTROSPECT_JS), timeout=5.0)
    except (TimeoutError, Exception):  # noqa: BLE001
        return None
    if not result or not isinstance(result, dict):
        return None
    try:
        return CMPRuntimeConfig.model_validate(result)
    except Exception:  # noqa: BLE001
        return None


# ============================================================================
# Truyo
# ============================================================================
#
# Truyo (Intertrust) is a US-focused CCPA CMP. Exposes window.Truyo or
# window._truyo, with consent decisions stored on Truyo.consent or
# Truyo.preferences. Less documented than the others — we read what's
# available and surface a minimal config when present.
_TRUYO_INTROSPECT_JS = """
(() => {
  try {
    const t = window.Truyo || window._truyo;
    if (!t) return null;

    const consent = t.consent || t.preferences || t.privacyState || null;
    const config = t.config || t.settings || null;

    // Truyo is fundamentally a CCPA opt-out platform. Some deployments also
    // serve GDPR templates for EU users — that lives on config.regulation.
    let template = 'CCPA';
    let consentModel = 'opt-out';
    if (config && config.regulation) {
      const r = String(config.regulation).toUpperCase();
      template = r;
      if (r.includes('GDPR') || r.includes('LGPD')) consentModel = 'opt-in';
    }

    return {
      cmp_name: 'Truyo',
      template_name: template,
      geolocation_rule: (config && config.geolocation) || null,
      geolocation_country: (config && config.country) || null,
      consent_model: consentModel,
      expected_cookies_by_category: {},
      expected_vendor_ids: [],
      script_version: (config && config.version) || (t.version) || null,
      domain_id: (config && (config.domainId || config.tenantId)) || null,
      raw_dump: JSON.stringify({
        config_keys: config ? Object.keys(config).slice(0, 30) : null,
        consent_keys: consent ? Object.keys(consent).slice(0, 30) : null,
      }).slice(0, 4000),
    };
  } catch (e) { return null; }
})()
"""


async def extract_truyo_runtime(page: Page) -> CMPRuntimeConfig | None:
    """Return Truyo's self-reported runtime config, or None."""
    try:
        result = await asyncio.wait_for(page.evaluate(_TRUYO_INTROSPECT_JS), timeout=5.0)
    except (TimeoutError, Exception):  # noqa: BLE001
        return None
    if not result or not isinstance(result, dict):
        return None
    try:
        return CMPRuntimeConfig.model_validate(result)
    except Exception:  # noqa: BLE001
        return None


# ============================================================================
# Dispatcher
# ============================================================================


async def extract_cmp_runtime(page: Page, detected_cmp: str | None) -> CMPRuntimeConfig | None:
    """Dispatch to the per-CMP extractor based on the detected CMP name.

    Each extractor checks for the relevant JS globals; if the detected CMP
    matches a known extractor we call it directly. Otherwise we fall through
    to OneTrust (the most widely deployed and the one that originally
    motivated the introspect layer).
    """
    if detected_cmp == "OneTrust":
        return await extract_onetrust_runtime(page)
    if detected_cmp == "Cookiebot":
        return await extract_cookiebot_runtime(page)
    if detected_cmp == "CookieYes":
        return await extract_cookieyes_runtime(page)
    if detected_cmp == "Didomi":
        return await extract_didomi_runtime(page)
    if detected_cmp == "Usercentrics":
        return await extract_usercentrics_runtime(page)
    if detected_cmp == "Truyo":
        return await extract_truyo_runtime(page)
    # Unknown / unrecognized CMP — try OneTrust as the legacy default since
    # many sites still ship OneTrust globals even after migrating away.
    return await extract_onetrust_runtime(page)


__all__ = [
    "extract_cmp_runtime",
    "extract_consent_events",
    "extract_cookiebot_runtime",
    "extract_cookieyes_runtime",
    "extract_didomi_runtime",
    "extract_onetrust_runtime",
    "extract_truyo_runtime",
    "extract_usercentrics_runtime",
]


# Optional: a tiny sync helper for unit-testing the JS expressions without
# spinning up a Playwright browser. Not used by the scan pipeline.
def _onetrust_introspect_js_source() -> str:
    """Return the OneTrust JS expression for snapshot testing."""
    return _ONETRUST_INTROSPECT_JS


def _consent_event_extract_js_source() -> str:
    """Return the consent-event extractor JS expression for snapshot testing."""
    return _CONSENT_EVENT_EXTRACT_JS


_ = json  # silence "imported but unused" — kept for future raw_dump parsing
