# CMP Technical Profiles — Mid-Market & Enterprise Reference

tags: cmp, detection, injection, javascript-api, shadow-dom, cookie, onetrust, cookiebot, didomi, sourcepoint, usercentrics, ketch, osano, trustarc, quantcast
related: [[concepts/consent-mode-v2]], [[concepts/cmp-failures]], [[technical/scanner-methodology]]

Last verified: April 2026. Sources: official developer docs, GitHub SDK repos, live site testing.

---

## Tier 1 — Enterprise Dominant

### OneTrust

- **JS global:** `window.OneTrust` or `window.OnetrustActiveGroups`
- **CDN:** `cdn.cookielaw.org`, `optanon.blob.core.windows.net`
- **Banner DOM:** `#onetrust-banner-sdk` (regular DOM)
- **Reject button:** `#onetrust-reject-all-handler`
- **Cookie:** `OptanonConsent` (URL-encoded query string)
  - Format: `isGpcEnabled=0&datestamp=...&version=...&groups=C0001:1,C0002:0,C0003:0,C0004:0,C0005:0&AwaitingReconsent=false`
  - C0001:1 = strictly necessary (always 1), all others :0 = denied
  - Companion: `OptanonAlertBoxClosed` = any timestamp (suppresses re-show)
- **JS API:** `OneTrust.RejectAll()` — confirmed in developer.onetrust.com docs
  - Fallback: `OneTrust.UpdateConsent('Category', 'C0002:0,C0003:0,C0004:0')`
- **CCPA vs GDPR:** OneTrust serves different UIs by geo. CCPA "Do Not Sell" uses separate toggle mechanism — `OneTrust.RejectAll()` covers both modes.
- **Consent Mode V2:** Native. Fires `gtag('consent','update')` via GTM template. Google-certified CMP.

### TrustArc

- **JS global:** `window.truste` with `.eu` property
- **CDN:** `consent.trustarc.com`
- **Banner DOM:** `iframe[id*='truste']` or `iframe[src*='trustarc']` — **IFRAME**
- **Cookies:**
  - `notice_preferences=0:` — no categories selected
  - `cmapi_cookie_privacy=permit 1` — necessary only (category 1 = strictly necessary)
  - `notice_gdpr_prefs=0,1,2:` — deny all optional groups
  - ⚠️ WARNING: `cmapi_cookie_privacy=permit 1,2,3` **grants** analytics + marketing. All-denied = `permit 1` only.
- **JS API:** No clean deny-all API. Uses `PrivacyManagerAPI` postMessage protocol inside iframe.
- **Consent Mode V2:** Supported via GTM tag template. Google-certified CMP.

### Sourcepoint

- **JS global:** `window._sp_`
- **CDN:** `cdn.privacy-mgmt.com`, `sourcepoint.mgr.consensu.org`
- **Banner DOM:** `div[id^='sp_message_container']` (regular DOM)
- **Reject button:** `.sp_choice_type_REJECT_ALL`, `[choice-type="REJECT_ALL"]`
- **Storage:** localStorage `_sp_user_consent_{propertyId}`, `_sp_local_state`, `_sp_non_keyed_local_state` — **site-specific keys, cannot inject generically**
- **JS API:** `window._sp_.rejectAll('gdpr')` or `window._sp_.rejectAll('ccpa')` — confirmed in official docs. Choice type ID 13 = Reject All.
- **Consent Mode V2:** Supported.

### Didomi

- **JS global:** `window.Didomi`
- **CDN:** `sdk.privacy-center.org`
- **Banner DOM:** `#didomi-host`, `#didomi-notice` (regular DOM)
- **Reject button:** `#didomi-notice-disagree-button`, `.didomi-notice-banner .didomi-button-secondary`
- **Storage:** `didomi_token` (cookie, proprietary format) + `didomi_dcs` (binary cookie, 2025+)
  - ⚠️ Proprietary encrypted format — cookie injection unreliable. Use JS API.
- **JS API:** `Didomi.setUserDisagreeToAll()` — primary deny-all method
- **Consent Mode V2:** Native. Fires `gtag('consent','update')` automatically.

### Usercentrics

- **JS global:** `window.UC_UI`
- **CDN:** `app.usercentrics.eu`, `privacy-proxy.usercentrics.eu`
- **Banner DOM:** `#usercentrics-root` — **SHADOW DOM** (shadow host; normal CSS selectors fail)
- **Storage:** localStorage `uc_settings` — complex per-service schema keyed by service ID; generic stub unreliable
- **JS API:** `UC_UI.denyAllConsents()` — authoritative deny-all. Fires `UC_UI_CMP_EVENT` with type `DENY_ALL`.
- **Consent Mode V2:** Native. Google-certified CMP.

---

## Tier 2 — Mid-Market / Growing Enterprise

### Cookiebot (Usercentrics subsidiary)

- **JS global:** `window.CookieConsent` with `.stamp` property
- **CDN:** `consent.cookiebot.com`, `consentcdn.cookiebot.com`
- **Banner DOM:** `#CybotCookiebotDialog` (regular DOM)
- **Reject button:** `#CybotCookiebotDialogBodyButtonDecline`
- **Cookie:** `CookieConsent` (URL-encoded JSON)
  - Format: `{stamp:'-1',necessary:true,preferences:false,statistics:false,marketing:false,method:'explicit',ver:2147483647,utc:1700000000000,region:''}`
  - Note: single-quoted keys (not valid JSON) — URL-encode as-is
- **JS API:** `Cookiebot.submitCustomConsent(false, false, false)` — args: (preferences, statistics, marketing)
- **Consent Mode V2:** Native.

### Quantcast Choice

- **JS global:** `window.__tcfapi` (generic TCF; Quantcast also sets `window.Quantcast`)
- **CDN:** `cmp.quantcast.com`
- **Banner DOM:** `.qc-cmp2-container`, `#qcCmpUi` (regular DOM)
- **Cookies:** `euconsent-v2` (IAB TCF v2.2 string), `addtl_consent`
- **Injection:** IAB TCF all-denied string in `euconsent-v2`
- **Known 2025 issue:** Publisher CMP updates broke Quantcast integrations — some banner button selectors shifted. Button text matching is more reliable than fixed selectors.
- **Consent Mode V2:** Native.

### Ketch

- **JS global:** `window.ketch` (function) or `window.semaphore` (array queue)
- **CDN:** `global.ketchcdn.com`
- **Banner DOM:** `#ketch-lanyard` — often **headless** (no visible banner in many deployments)
- **Storage:** localStorage key `_ketch_consent_v1_{orgCode}_{propertyCode}` — **site-specific suffix, cannot inject generically**
- **JS API:** `window.ketch('setConsent', {purposes: {analytics: {allowed: false}, ...}})` via semaphore queue
- **Consent Mode V2:** Native via GTM template.

### Osano

- **JS global:** `window.Osano`
- **CDN:** `cmp.osano.com`
- **Banner DOM:** `.osano-cm-window`, `.osano-cm-dialog` (regular DOM)
- **Reject button:** `.osano-cm-deny`
- **Storage:** localStorage `osano_consentmanager`
  - Format: `{"ANALYTICS":"DENY","MARKETING":"DENY","PERSONALIZATION":"DENY","STORAGE":"DENY"}`
  - Note: all-caps category keys
- **JS API:** `Osano.cm.deny()` — primary. Fallback: `Osano.cm.denyAll()`
- **Consent Mode V2:** Native.

### Crownpeak (Evidon)

- **JS global:** `window.evidon`
- **CDN:** `c.betrad.com`
- **Banner DOM:** regular DOM
- **JS API:** Evidon-specific; JS API available (`evidon.notice.api`)
- **Consent Mode V2:** Supported.

---

## Tier 3 — Regional Enterprise / Specialized

### Axeptio (French enterprise, EU DTC)

- **JS global:** `window.axeptio`
- **CDN:** `static.axept.io`
- **Banner DOM:** `#axeptio_overlay` — **SHADOW DOM** (confirmed: browser-use/browser-use issue #2276)
  - ⚠️ Current codebase had this as `standard` DOM — now corrected to `shadow_dom`
- **Cookies:**
  - `axeptio_cookies` = `{"$$completed":true,"$$invalidate":false}` — marks consent completed
  - `axeptio_authorized_vendors` = `[]` — no authorized vendors
- **Consent Mode V2:** Supported.

### Didomi (see Tier 1 above)

### TrustCommander (Commanders Act / TagCommander)

- **JS global:** `window.tC` AND `window.tc_cmp`
- **CDN:** `cdn.tagcommander.com`
- **Banner DOM:** `.tc-privacy-wrapper`, `#tc_privacy` (regular DOM)
- **Cookie:** `TC_PRIVACY` — JSON `{"categories":[],"vendors":[]}`
- **JS API:** `tC.setCategoryConsent(categoryId, 0)` per-category. Direct cookie manipulation deprecated in favor of onsite API.
- **Consent Mode V2:** Supported via Commanders Act.

### Consentmanager.net

- **JS global:** `window.__cmp` (function) AND `window.cmp_ok`
- **CDN:** `cdn.consentmanager.net`
- **Banner DOM:** `#cmpbox`, `.cmpbox` (regular DOM)
- **Reject button:** `.cmpboxbtnno`, `a[onclick*="denyAll"]`
- **Cookies:** `cmpconsentstring` (IAB TCF v2.2 string), `cmp_c` (vendor consent map)
  - As of 2025: no third-party cookies under consentmanager.net domain — first-party only
- **JS API:** `__cmp('setConsent', 0, callback)` — 0 = deny all
- **Consent Mode V2:** Google-certified.

### iubenda

- **JS global:** `window._iub` with `._iub.cs`
- **CDN:** `cdn.iubenda.com`
- **Banner DOM:** `#iubenda-cs-banner`, `.iubenda-cs-content` (regular DOM)
- **Reject button:** `#iubenda-cs-reject-btn`, `.iubenda-cs-reject-btn`
- **Cookie:** `_iub_cs-{cookiePolicyId}` — **site-specific policy ID suffix, cannot inject generically**
  - CCPA mode: also sets `iubenda_ccpa_opted_out=true`
- **Consent Mode V2:** Native. TCF 2.3 support arrived 2026.

### Borlabs Cookie (WordPress — DTC/mid-market)

- **JS global:** `window.BorlabsCookie` (v2) or `window.borlabs_cookie` (v3)
- **Banner DOM:** `#BorlabsCookieBox` (v2), `#borlabs-cookie-widget` (v3)
- **Reject button:** `.borlabs-cookie-btn-deny`
- **Storage (v2):** localStorage `BorlabsCookie` — JSON `{"consents":{"statistics":false,"marketing":false},"version":"2"}`
- **Storage (v3):** REST API `/wp-json/borlabs-cookie/v1/consent` — localStorage alone insufficient
- **JS API (v2):** `BorlabsCookie.denyAll()`. **v3:** no documented browser JS API — banner click required.
- **Consent Mode V2:** v3 supports Consent Mode V2.

### Civic Cookie Control (UK enterprise)

- **JS global:** `window.CookieControl` with `.load()` method
- **CDN:** `cc.cdn.civiccomputing.com`
- **Banner DOM:** `#ccc`, `#ccc-icon`, `.ccc-module--slideout` (regular DOM)
- **Reject button:** `.ccc-button-slides__button--deny`
- **Cookie:** `CookieControl` (JSON) — contains a signed `encoded` field that makes injection unreliable
- **Consent Mode V2:** Supported.

---

## Cookie/localStorage Injection Reference

| CMP | Type | Name | All-Denied Value |
|---|---|---|---|
| OneTrust | cookie | `OptanonConsent` | `groups=C0001:1,C0002:0,C0003:0,C0004:0` + `OptanonAlertBoxClosed` |
| Cookiebot | cookie | `CookieConsent` | URL-encoded `{stamp:'-1',necessary:true,preferences:false,statistics:false,marketing:false}` |
| CookieYes | cookie | `cookieyes-consent` | `consent:no,action:yes,advertisement:no,analytics:no,functional:no,performance:no` |
| Osano | localStorage | `osano_consentmanager` | `{"ANALYTICS":"DENY","MARKETING":"DENY","PERSONALIZATION":"DENY","STORAGE":"DENY"}` |
| Usercentrics | localStorage | `uc_settings` | JS API preferred — `uc_settings` schema is per-service keyed by service ID |
| Ketch | n/a | site-specific | ❌ Cannot inject — use JS API `ketch('setConsent',{...})` |
| TrustArc | cookie | `notice_preferences`, `cmapi_cookie_privacy` | `0:` and `permit 1` (not `permit 1,2,3` — that grants categories) |
| Termly | cookie | `termly-consent` | `{"analytics":false,"advertising":false,"performance":false,"social_networking":false,"essential":true}` |
| Complianz | cookie | `cmplz_consent`, `cmplz_banner-status` | `0` and `dismissed` |
| Axeptio | cookie | `axeptio_cookies` + `axeptio_authorized_vendors` | `{"$$completed":true,"$$invalidate":false}` and `[]` |
| Quantcast / IAB TCF | cookie | `euconsent-v2` | All-denied TCF v2.2 base64url string |
| CookieScript | cookie | `CookieScriptConsent` | `{"action":"reject","categories":""}` |
| CookieHub | cookie | `cookiehub` + `euconsent-v2` | `{"analytics":false,"marketing":false,"preferences":false}` |
| TrustCommander | cookie | `TC_PRIVACY` | `{"categories":[],"vendors":[]}` |
| Consentmanager | cookie | `cmpconsentstring` + `cmp_c` | all-denied TCF string + empty |
| Borlabs v2 | localStorage | `BorlabsCookie` | `{"consents":{"statistics":false,"marketing":false},"version":"2"}` |
| iubenda | cookie | `_iub_cs-{policyId}` | ❌ Cannot inject — site-specific ID |
| Civic | cookie | `CookieControl` | ❌ Signed encoded field — unreliable |
| Sourcepoint | localStorage | `_sp_user_consent_{propertyId}` | ❌ Cannot inject — use JS API `_sp_.rejectAll()` |
| Didomi | cookie | `didomi_token` / `didomi_dcs` | ❌ Encrypted — use JS API `Didomi.setUserDisagreeToAll()` |

---

## Shadow DOM CMPs (CSS selectors won't work — requires JS API or shadow DOM traversal)

| CMP | Shadow Host | Solution |
|---|---|---|
| Usercentrics | `#usercentrics-root` | `UC_UI.denyAllConsents()` JS API |
| Axeptio | `#axeptio_overlay` | Cookie injection pre-load + JS event |

---

## Known Issues (April 2026)

1. **Axeptio dom_type was `standard`** — corrected to `shadow_dom`. CSS selector clicks were silently failing.
2. **TrustArc `cmapi_cookie_privacy=permit 1,2,3`** — was granting analytics + marketing. Corrected to `permit 1`.
3. **Ketch localStorage key** — `ketch_consent` does not exist. Real key is `_ketch_consent_v1_{org}_{property}`. Removed injection, JS API only.
4. **Usercentrics `uc_settings` stub** — oversimplified schema. JS API is authoritative.
5. **Didomi `didomi_dcs`** — new binary cookie format deployed 2025. `didomi_token` injection alone may not suppress banner. JS API remains correct.
6. **Quantcast 2025** — publisher CMP update broke some integrations; button selectors shifted.

---

## Tier 4 — Platform-Native / Ecosystem-Specific (CMPs #16–35)

### Shopify Customer Privacy API (DTC — Shopify stores)

- **JS global:** `window.Shopify.customerPrivacy` (available after Shopify's privacy script loads)
- **Detection:** `typeof window.Shopify !== 'undefined' && typeof window.Shopify.customerPrivacy !== 'undefined'`
- **CDN:** Served from Shopify's own CDN — no external script URL; injected via theme liquid or Shopify Pixels
- **Banner DOM:** No standard DOM — Shopify's built-in consent UI or third-party CMP UI layered on top
- **Deny-all API:**
  ```js
  window.Shopify.customerPrivacy.setTrackingConsent(
    { analytics: false, marketing: false, preferences: false, sale_of_data: false },
    function(err) { /* callback */ }
  );
  ```
- **Storage:** POSTs to Shopify Storefront API at checkout domain — **no localStorage key to inject**. Consent is server-side.
- **Consent Mode V2:** Shopify Pixels natively map to GCM V2 signals. Third-party CMPs (Pandectes, CookieYes, etc.) call `setTrackingConsent` and separately fire `gtag('consent','update')`.
- **Note:** `setTrackingConsent` returning success with `true` despite `false` values is a known Shopify platform bug in some theme configurations. Banner suppression requires the server-side consent record to be written — JS injection alone is insufficient.

### Pandectes (Shopify-specific CMP)

- **JS global:** `window.Pandectes` (event-based; listen for `PandectesEvent_OnConsent` on document)
- **CDN:** `cdn.pandectes.io` — script injected via Shopify app embed
- **Banner DOM:** Regular DOM; standard Shopify theme injection
- **Cookie:** `_pandectes_gdpr` — base64-encoded JSON
  - Decoded structure: `{"id":"...","preferences":0,"status":"...","timestamp":...,"version":...}`
  - `preferences` is a 3-bit bitwise integer: bit 0 = Functionality, bit 1 = Performance, bit 2 = Targeting
  - All-denied value: `preferences: 0`
- **Deny-all API:** No documented programmatic deny-all API. Must go through `setTrackingConsent` via Shopify Customer Privacy API.
- **Consent Mode V2:** Yes — Google-certified CMP. Fires GCM V2 signals. Also supports IAB TCF v2.3.
- **ICP relevance:** Leading CMP for Shopify Plus DTC brands.

### Piwik PRO Consent Manager (Enterprise analytics / fintech / B2B SaaS)

- **JS global:** `window.ppms` — specifically `window.ppms.cm.api` (command queue)
- **Detection:** `typeof window.ppms !== 'undefined' && typeof window.ppms.cm !== 'undefined'`
- **CDN:** `{account}.piwik.pro` — self-hosted or Piwik PRO cloud. Script URL: `https://{account}.piwik.pro/ppms.js`
- **Banner DOM:** Regular DOM; configurable
- **Deny-all API:**
  ```js
  ppms.cm.api('setComplianceSettings', {consents: {analytics: {status: 0}, remarketing: {status: 0}}}, onSuccess, onError);
  // status: 0 = declined, 1 = approved, -1 = no decision
  ```
- **Storage:** localStorage `stg_traffic_source`, `ppms_privacy_{siteId}` — site-specific suffix
- **Consent Mode V2:** Yes — Piwik PRO natively integrates GCM V2.
- **Note:** Piwik PRO is analytics-first — the CMP component is their built-in consent layer, not a separate product. Common in fintech, public sector, healthcare where Google Analytics is prohibited.

### Transcend (airgap.js — large enterprise SaaS)

- **JS global:** `window.airgap` (primary) + `window.transcend` (consent UI layer)
- **Detection:** `typeof window.airgap !== 'undefined'`
- **CDN:** `https://transcend-cdn.com/cm/{bundle-id}/airgap.js`
- **Banner DOM:** Custom UI via `window.transcend`; often shadow DOM or iframe depending on deployment
- **Deny-all API:**
  ```js
  // Requires a trusted user-initiated click event — cannot be called programmatically without user gesture
  airgap.optOut(); // opts user out of all non-essential purposes
  // OR via setConsent:
  airgap.setConsent(event, {purposes: {Advertising: false, Analytics: false, Functional: false, SaleOfInfo: false}});
  ```
  - ⚠️ `airgap.setConsent` requires a genuine `click` or `submit` event — **cannot be called from arbitrary JS without user interaction**. Transcend deliberately blocks synthetic event injection.
- **Storage:** localStorage `tcmConsent` (JSON, current) — previously `tcm3PConsent` (pre-airgap 8.38.0)
- **Consent Mode V2:** Yes — `SaleOfInfo` maps to `ads_data_redaction`. GCM V2 support via airgap 8.33.0+.
- **ICP relevance:** Used by large enterprise SaaS (Notion, Brex, etc.). Enforcement is network-level (patches `fetch`, `XHR`, `WebSocket`) — strongest enforcement model of any CMP.

### Ensighten Privacy / CHEQ Consent (Enterprise TMS)

- **JS global:** `window.Bootstrapper` — specifically `Bootstrapper.gateway` and `Bootstrapper.privacy`
- **Detection:** `typeof window.Bootstrapper !== 'undefined' && typeof Bootstrapper.privacy !== 'undefined'`
- **CDN:** `nexus.ensighten.com/{accountPath}/Bootstrap.js`
- **Banner DOM:** Regular DOM; configurable per deployment
- **Cookie:** `CONSENTMGR` — format: `c1=1&c2=1&c3=0&ts={timestamp}` where each `cn` is a consent category
  - All-denied (only strictly necessary): e.g. `c1=1&c2=0&c3=0`
  - Category numbers are deployment-specific — cannot be generic
- **JS API:**
  ```js
  Bootstrapper.gateway.getCookie('Marketing'); // returns "0" or "1"
  // No documented deny-all API — category IDs are deployment-specific
  ```
- **Consent Mode V2:** Supported via GTM integration. Ensighten rebranded to CHEQ Control & Compliance.
- **Note:** Category cookie key numbers (`c1`, `c2`, etc.) are configured per-account. Cannot write a generic deny-all cookie without knowing account's category mapping.

### DataGrail Consent (Enterprise privacy platform)

- **JS global:** `window.DG_BANNER_API`
- **Detection:** `typeof window.DG_BANNER_API !== 'undefined'`
- **CDN:** DataGrail-hosted; script injected via GTM or direct embed
- **Banner DOM:** Regular DOM; `.dg-banner` container
- **Deny-all API:** `window.DG_BANNER_API.plugins.scriptControl.unmanagedScripts()` — surfaces unmanaged scripts (debug utility). No documented programmatic deny-all; enforcement is tag-blocking.
- **Storage:** Not publicly documented — cookie/localStorage keys are internal
- **Consent Mode V2:** Supported
- **Note:** DataGrail is primarily a DSR/privacy ops platform. Their CMP (DataGrail Consent) is a secondary product. Detection signal is the `DG_BANNER_API` global. Less common than OneTrust at enterprise scale but growing in US fintech.

### CookiePro (OneTrust mid-market product)

- **JS global:** `window.OneTrust` — **identical to OneTrust enterprise**
- **CDN:** `cdn.cookielaw.org` — same CDN as OneTrust. Script URL pattern: `cdn.cookielaw.org/consent/{uuid}/OtAutoBlock.js`
- **Banner DOM:** `#onetrust-banner-sdk` — identical to OneTrust
- **Cookie:** `OptanonConsent` — identical format to OneTrust
- **JS API:** `OneTrust.RejectAll()` — identical to OneTrust
- **Consent Mode V2:** Yes — same as OneTrust (Google-certified)
- **Detection note:** CookiePro is a branding layer over the same OneTrust SDK. The only reliable distinguisher is the account UUID in the CDN URL, which maps to a CookiePro subscription vs. full OneTrust enterprise. For detection purposes, treat as OneTrust — all selectors, cookies, and API calls are identical.

### Termly (SMB / mid-market — US-focused)

- **JS global:** `window.Termly` (object with API methods)
- **Detection:** `typeof window.Termly !== 'undefined'`
- **CDN:** `app.termly.io/embed.min.js` (script loaded from Termly CDN)
- **Banner DOM:** Regular DOM; `#termly-code-snippet-support` container
- **Cookie:** `termly-consent` — JSON format:
  - `{"analytics":false,"advertising":false,"performance":false,"social_networking":false,"essential":true}`
- **Deny-all JS API:** No documented `denyAll()` method. Read consent state via:
  ```js
  window.Termly.getConsentState();
  // Returns: {essential: true, performance: true, analytics: true, advertising: false, social_networking: true, unclassified: true}
  ```
  No programmatic deny-all — consent changes require banner interaction.
- **Consent Mode V2:** Yes — Termly supports GCM V2 integration.
- **Note:** Termly lacks a JS deny-all API — this is a gap for automated enforcement. Cookie injection is the only bypass path; format above is reliable for standard deployments.

### Klaro (Open-source — used by some enterprise/public sector)

- **JS global:** `window.klaro` (when loaded as UMD bundle)
- **Detection:** `typeof window.klaro !== 'undefined'`
- **CDN:** Self-hosted or `cdn.klaro.app/klaro.js` — open source, no single CDN
- **Banner DOM:** Regular DOM; `#klaro` container with `.cm-modal` or `.cookie-notice`
- **Cookie:** `klaro` (default name, configurable) — JSON format:
  - `{"googleAnalytics":false,"hotjar":false}` — keyed by service names defined in config
- **Deny-all JS API:**
  ```js
  let manager = klaro.getManager();
  manager.declineAll();
  manager.saveAndApplyConsents();
  ```
- **Consent Mode V2:** Yes — via GTM tutorial integration (not built-in; requires config).
- **Note:** Cookie key names are service names set in site config — not generic. `klaro.getManager().declineAll()` is confirmed in source and docs. Cookie name itself can be reconfigured — `klaro` is only the default.

### CCM19 (DACH enterprise — German-hosted)

- **JS global:** `window.CCM` (object bundled as global)
- **Detection:** `typeof window.CCM !== 'undefined'`
- **CDN:** `cloud.ccm19.de/app.js?apiKey={key}&domain={domain}` (SaaS) or self-hosted
- **Banner DOM:** Regular DOM; `#ccm19-widget` or `.ccm19-overlay`
- **Cookie:** Internal storage via cookie/localStorage/sessionStorage (configurable). Cookie name set in admin.
- **JS API:**
  ```js
  CCM.acceptedCookies;     // array of accepted cookie names
  CCM.acceptedEmbeddings;  // array of accepted embedding names
  // No documented deny-all API — consent changes go through banner UI or GTM events
  ```
- **Consent Mode V2:** Yes — TCF v2.3 + GCM V2 ready.
- **Note:** Entirely German-hosted (no AWS, no Google Cloud). Popular with DACH-region enterprise and public sector. No English deny-all API method confirmed in docs — GTM triggers are the integration path.

### Real Cookie Banner (WordPress / WooCommerce DTC)

- **JS global:** No dedicated global — uses WordPress REST API + server-side consent storage
- **Detection:** Check for `#real-cookie-banner` DOM element or `rcb-cookie-banner` CSS class
- **CDN:** Self-hosted WordPress plugin (devowl.io) — `wp-content/plugins/real-cookie-banner/`
- **Banner DOM:** Regular DOM; `#real-cookie-banner`
- **Storage:** Consents stored server-side via WordPress REST API — **no client-side cookie or localStorage** to inject
- **Deny-all API:** No browser JS API. Consent requires user interaction with banner or WP admin action.
- **Consent Mode V2:** Yes (v5.0+).
- **Note:** Consent is recorded server-side in WordPress database. No client-side injection path exists — must click banner. Detection relies on DOM element presence.

---

## Tier 5 — Platform-Native (No-Code Website Builders)

### Wix (Built-in consent policy)

- **JS global:** `window.consentPolicyManager`
- **Detection:** `typeof window.consentPolicyManager !== 'undefined'`
- **API:** `window.consentPolicyManager.getCurrentConsentPolicy()` returns current policy
- **Event:** `document.addEventListener('consentPolicyChanged', handler)` — fires on policy change
- **Storage:** Wix-managed server-side — no public cookie name
- **Consent Mode V2:** Not natively. Wix stores rely on third-party CMPs (CookieYes, Cookiebot, etc.) for GCM V2.
- **Note:** `window.consentPolicyManager` is Wix's own API layer, not a CMP. No deny-all JS method exposed. Third-party CMPs sit on top.

### Squarespace (Built-in banner)

- **JS global:** None — Squarespace's native banner has no JavaScript API
- **Detection:** DOM check for `.sqs-cookie-banner-v2` or `#sqs-cookie-banner`
- **Cookie:** `ss_cv` or `ss_cpv` (Squarespace-internal — not publicly documented)
- **Banner DOM:** Regular DOM; `.sqs-cookie-banner-v2`
- **Consent Mode V2:** No — Squarespace's native banner does not send GCM V2 signals as of 2026. Customers must disable native banner and use a third-party CMP (CCM19, iubenda, etc.) for GCM V2 compliance.
- **Note:** Squarespace's banner is informational only in some configurations — does not block cookies pre-consent. Treat as low-confidence detection target; most compliant Squarespace sites use an injected third-party CMP.

### Webflow (No built-in CMP)

- **JS global:** None — Webflow has no native CMP
- **Detection:** N/A — look for injected third-party CMP globals instead
- **Note:** Webflow sites use injected CMPs (Finsweet Cookie Consent, CookieHub, CookieScript, etc.) added via Site Settings > Custom Code. The Finsweet solution (`fs-cc` attribute pattern) is the most common Webflow-specific implementation.
  - Finsweet detection: `document.querySelector('[fs-cc="banner"]')`

---

## Extended Cookie/localStorage Injection Reference (CMPs #16–35)

| CMP | Type | Name | All-Denied Value |
|---|---|---|---|
| Shopify Customer Privacy | server-side POST | n/a | `setTrackingConsent({analytics:false, marketing:false, preferences:false, sale_of_data:false})` |
| Pandectes | cookie | `_pandectes_gdpr` | base64(`{"preferences":0,"status":"denied"}`) — use `setTrackingConsent` instead |
| Piwik PRO | localStorage | `ppms_privacy_{siteId}` | JS API: `ppms.cm.api('setComplianceSettings', {consents:{analytics:{status:0},remarketing:{status:0}}})` |
| Transcend (airgap) | localStorage | `tcmConsent` | JS API only — requires trusted click event; `airgap.optOut()` |
| Ensighten | cookie | `CONSENTMGR` | `c1=1&cN=0...` — category IDs are deployment-specific |
| DataGrail | internal | not public | ❌ No injection path — use `DG_BANNER_API` debug utils |
| CookiePro | cookie | `OptanonConsent` | Same as OneTrust: `groups=C0001:1,C0002:0,C0003:0,C0004:0` |
| Termly | cookie | `termly-consent` | `{"analytics":false,"advertising":false,"performance":false,"social_networking":false,"essential":true}` |
| Klaro | cookie | `klaro` (default) | `{"serviceName":false,...}` — keys are site-defined service names |
| CCM19 | configurable | admin-defined | ❌ No generic injection — use GTM/banner |
| Real Cookie Banner | server-side | n/a | ❌ No client-side path |
| Wix | server-side | n/a | ❌ No client-side path |
| Squarespace | cookie | `ss_cv` (internal) | ❌ No API; DOM button click only |

---

## Shadow DOM CMPs — Extended

| CMP | Shadow Host | Solution |
|---|---|---|
| Transcend | varies by deployment | JS API `airgap.optOut()` (requires user gesture) |
