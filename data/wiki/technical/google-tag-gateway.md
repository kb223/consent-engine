# Google Tag Gateway (GTG) — Privacy Architecture

tags: gtg, ssgtm, first-party, confidential-computing, audit
related: [[concepts/ssgtm-risk]], [[concepts/consent-mode-v2]]

## What It Is

Google Tag Gateway (GTG) is Google's own privacy-preserving infrastructure solution. It routes website measurement data through a publisher-owned domain rather than directly to Google's servers, using confidential computing.

**GTG is NOT the same as custom Server-Side GTM.** This distinction matters for audits.

## How It Works

1. Website owner deploys a CDN/load balancer on their own domain (e.g. `analytics.example.com`)
2. Google tag requests route through this first-party endpoint
3. Endpoint forwards data to Google using confidential computing (hardware-based TEEs)
4. Google receives aggregated, privacy-preserved signals — not raw identifiers

**Confidential computing guarantee:** Google cannot access the raw data. Processing logic is cryptographically verifiable. No Google employee can read individual user signals.

## Privacy Characteristics

**Data Minimization:** Raw IP addresses and user identifiers processed locally, not exposed to Google's ad systems in identifiable form.

**First-Party Context Benefits:**
- Browsers treat requests as first-party (longer cookie lifetime — 400 days server-set vs. 7 days client-side)
- ITP (Safari Intelligent Tracking Prevention) restrictions reduced
- Ad blockers targeting third-party domains less effective

## GTG vs. Non-Compliant Custom SSGTM

This is the critical audit distinction:

| Characteristic | GTG (Compliant) | Custom SSGTM (Risk) |
|---|---|---|
| Consent Mode signals | Always passed through | May not be passed — depends on config |
| `gcs=` in denied-consent scan | Present | Often absent |
| Data minimization | Built in | Depends on implementation |
| Google policy compliance | Built in | Manual — must be configured |
| Audit evidence | `gcs=` present even with denial | Missing `gcs=` = red flag |

## Identifying GTG vs Non-Compliant SSGTM in Audits

**Signals suggesting compliant GTG:**
- Requests route to a first-party subdomain but body contains standard GTM fingerprints
- `gcs=` parameter IS present in denied-consent scans (Advanced Consent Mode active)
- Container ID follows standard `GTM-XXXXXXXX` format
- `gcd=` parameter present with denial state

**Signals suggesting non-compliant SSGTM bypass:**
- No `gcs=` parameter in network requests despite CMP being present
- Advertising conversion events fire after opted-out consent state
- Server-side container does not pass Consent Mode signals downstream
- First-party domain routes to non-Google infrastructure

## Consent Mode Compatibility

GTG is designed to work WITH Consent Mode V2:
- Denied consent: GTG sends cookieless pings (behavioral modeling data only)
- Granted consent: GTG sends full conversion signals
- `gcs=` and `gcd=` parameters are still present in GTG requests

## Google's Policy Position

Google requires all GTG and SSGTM implementations to:
1. Pass Consent Mode signals through to the server-side container
2. Not fire advertising tags for users who denied `ad_storage`
3. Use `gcs=` and `gcd=` parameters on all requests

Failure: suspension of Google Ads and Analytics access.
