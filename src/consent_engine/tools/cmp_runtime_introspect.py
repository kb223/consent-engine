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

- v0.5.7: OneTrust (this file)
- v0.5.8: Cookiebot, CookieYes
- v0.5.9: Didomi, Usercentrics, TrustArc
- v0.6.0: Sourcepoint, CookieInformation, Klaro
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
    const COOKIEYES = /^cookieyes_consent_update$|^cky_consent$/i;
    const COOKIEBOT = /^Cookiebot/i;
    const DIDOMI = /^didomi/i;
    const USERCENTRICS = /^uc_(?:consent|ui)|^usercentrics/i;
    const TCF_API = /^tcfapi/i;
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


__all__ = [
    "extract_consent_events",
    "extract_onetrust_runtime",
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
