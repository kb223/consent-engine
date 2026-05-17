# Google Consent Mode V2 — Technical Reference

tags: google, consent-mode, gcs, gcd, acm, basic-mode, advanced-mode
related: [[technical/google-tag-gateway]], [[technical/consent-mode-impact]], [[concepts/ssgtm-risk]]

## What It Does

Consent Mode is a signaling system between a CMP and Google tags (GA4, Google Ads). When consent is denied, tags adjust behavior:
- **Basic Mode:** Tags are completely blocked — no data reaches Google
- **Advanced Mode:** Tags fire but send cookieless "pings" for behavioral modeling

Mandatory for EEA/UK advertisers using audience features or remarketing since **March 2024**.

## GCS Parameter (Network Evidence)

The `gcs=` URL parameter in Google Analytics and DoubleClick requests encodes consent state.
Format: `G1AB` where `A` = ad_storage, `B` = analytics_storage. `0` = denied, `1` = granted, `-` = unset.

| GCS Value | ad_storage | analytics_storage | Meaning |
|---|---|---|---|
| `G111` | granted | granted | All consent granted (or Consent Mode not configured) |
| `G100` | denied | denied | Full opt-out — ACM cookieless pings only |
| `G101` | denied | granted | **Partial opt-out** — ad tracking denied, analytics still active |
| `G110` | granted | denied | Partial opt-out — analytics denied, ad tracking still active |
| `G1--` | unset | unset | Consent Mode present but signals not yet set (timing/race condition) |
| No gcs= | n/a | n/a | Basic Consent Mode (tag blocked entirely) or no Consent Mode |

**Key audit signals for S3 opt-out tests:**
- `G100` = ACM correctly implemented — cookieless pings only, correct response to opt-out
- `G101` = **Partial CCPA compliance** — ad_storage denied but analytics_storage still granted. Under CCPA, "Do Not Sell" must cover analytics profiling, not just ad delivery. This is a compliance gap.
- `G110` = Partial compliance (inverse — rare in practice)
- `G111` in S3 test = CMP integration failure — opt-out not propagating to Consent Mode at all

**Key audit signal:** If `gcs=G100` appears in network requests → the tag FIRED despite denied consent. This is Advanced Consent Mode — the tag is not blocked, it sends a cookieless ping.

## GCD Parameter (V2 Detail)

The `gcd=` parameter encodes the default state AND user-update state per consent signal.
Format: `11<ad_storage>1<analytics_storage>1<ad_user_data>1<ad_personalization>5`

Signal order: `ad_storage` → `analytics_storage` → `ad_user_data` → `ad_personalization`.

**⚠️ Prefix `11` and suffix `5` are internal Google metadata digits that can vary — do not hardcode them as the only valid pattern. The separating `1` digits between signal letters are also internal metadata.**

**Full GCD letter table** (verified April 2026 from Simo Ahava + Google docs):

| Letter | Default state | Update state | Result | Classification |
|---|---|---|---|---|
| `l` | not set | not set | Consent Mode not active | unset |
| `p` | denied | none | Denied by default, user hasn't interacted | **DENIED** |
| `q` | denied | denied | Denied default, user confirmed denied | **DENIED** |
| `r` | denied | granted | Denied default, user upgraded to granted | GRANTED |
| `t` | granted | none | Granted by default, user hasn't interacted | GRANTED |
| `u` | granted | denied | Granted default, user downgraded to denied | **DENIED** |
| `v` | granted | granted | Granted default, user confirmed granted | GRANTED |
| `m` | none | denied | No default, denied on update | **DENIED** |
| `n` | none | granted | No default, granted on update | GRANTED |

**Previous wiki had `t` and `u` reversed — confirmed wrong. Correct:** `u` = granted→denied (DENIED), `t` = granted/none (GRANTED).

Examples:
- `11q1q1q1q5` → all four signals denied (default denied, user confirmed)
- `11p1p1p1p5` → all four signals denied (default denied, no user interaction yet)
- `11v1v1v1v5` → all four signals granted (default granted, user confirmed)
- `11u1u1u1u5` → all four signals denied (default granted, user opted out)
- `11r1r1r1r5` → all four signals granted (denied default, user opted in)

**`npa=1` vs `gcs=G100`:** These are parallel systems on different tag types.
- `gcs=G100` appears on GA4/analytics hits — signals `ad_storage` + `analytics_storage` denied
- `npa=1` appears on ad-serving requests (GPT, AdSense) — signals `ad_personalization` denied
- Both can be present simultaneously and are not interchangeable

## V2 New Parameters

Google Consent Mode V2 adds two signals beyond V1:
- **ad_user_data** — consent to send user data to Google for advertising
- **ad_personalization** — consent for personalized remarketing / audience building

All four parameters must default to `denied` on page load before CMP interaction.

**`functionality_storage`, `personalization_storage`, `security_storage`** are accepted by the `gtag('consent', 'default')` API but do NOT appear in GCS or GCD network parameters. They cannot be detected via network traffic inspection.

## Basic vs Advanced Mode Evidence

**Basic Mode:** No `gcs=` in any network request when consent is denied. Zero requests to analytics.google.com or doubleclick.net after opt-out. Tags fully blocked.

- Network evidence: no Google tag hits before CMP interaction. After accept: tags fire with `gcs=G111`. After reject: still no Google tag hits.

**Advanced Mode:** `gcs=G100` present in network requests after opt-out. Requests to `analytics.google.com/g/collect` still fire. Tag NOT blocked — sends cookieless ping.

- Network evidence: GA4 hits to `google-analytics.com/g/collect` pre-consent with `gcs=G100`, GCD with `p` or `q` letters, no cookies set. After consent granted: full payload with `gcs=G111`.

**Mixed mode:** A site can run Basic for some tags (e.g. Google Ads Conversion) and Advanced for others (e.g. GA4) via per-tag consent settings in GTM. Detectable by checking which tag types appear pre-consent.

**Scanner implication:** Absence of pre-consent Google tag hits ≠ Basic Mode compliant. The site may simply have no Consent Mode configured at all (which is also non-compliant for EEA traffic). Timing relative to CMP display matters.

## TCF 2.2 and Consent Mode — Not the Same

IAB TCF (`euconsent-v2` cookie, `__tcfapi` present) and Google Consent Mode are **independent systems**.

- A site can implement TCF without Consent Mode active — `gcs`/`gcd` will show `l` letters (not set).
- Bridge requires: `window['gtag_enable_tcf_support'] = true` OR `TCData.enableAdvertiserConsentMode = true`.
- Without the bridge: `euconsent-v2` present does NOT guarantee Consent Mode signals are correctly set.
- **Audit rule:** Do not use `euconsent-v2` presence as evidence of Consent Mode compliance. Check GCS/GCD in actual network hits.

## The 67% Failure Rate

Empirical data: 67% of Consent Mode V2 implementations fail basic compliance standards.

Primary failure mode: parameters default to `granted` before user interaction. A compliant setup must initialize all four parameters as `denied` on page load. GTM initializing before the CMP loads causes a race condition where tags fire in the `granted` state before consent is captured.

Only 23% of implementations successfully recover the promised 65% data via modeling — due to these implementation errors and insufficient conversion volume (Google requires 1,000+ weekly conversions to model accurately). See [[concepts/cmp-failures]].

## Google's March 2024 Enforcement (EEA/UK)

Non-compliant advertisers face:
- Loss of audience list data for EU/UK traffic
- Inability to use Smart Bidding for EU traffic
- Remarketing campaigns restricted for non-consenting users
- Estimated 15–35% ROAS reduction without CMv2

## Regulatory Gray Area — Advanced Consent Mode

Sending any network request (which exposes IP addresses) before explicit consent may carry legal risk under strict interpretations of GDPR and Quebec Law 25. The transmission of cookieless pings requires a defensible legal basis — typically documented legitimate interest for aggregate modeling.

An audit finding of `gcs=G100` with conversion events = data flowing to Google for modeling. This is not a clean pass — it requires documentation of the legal basis used.
