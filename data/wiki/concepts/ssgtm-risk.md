# Server-Side GTM — Consent Bypass Risk

tags: ssgtm, server-side, consent-bypass, gpc, audit
related: [[technical/google-tag-gateway]], [[concepts/consent-mode-v2]], [[enforcement/emerging-trends]]

## The Core Risk

Server-side GTM (SSGTM) containers process tracking calls on a server rather than in the browser. This creates a consent bypass risk:

**Client-side JavaScript cannot block a server-to-server call.**

If a SSGTM container is configured to forward advertising tags regardless of consent state:
- The user's consent denial in the browser is irrelevant
- The `Sec-GPC: 1` header is stripped at the server and not forwarded
- Advertising data reaches platforms regardless of user choice
- The mechanism of transmission (server vs. client) is legally irrelevant to liability

## How to Identify SSGTM in an Audit

**Signals suggesting SSGTM is present:**
- Tags route through a first-party subdomain (e.g., `analytics.example.com`, `metrics.example.com`)
- The domain is not a Google-owned endpoint but the request body has GTM fingerprints
- A GTM container ID (format: `GTM-XXXXXXXX`) present in server-routed requests
- Conversion events appear in network traffic but from a first-party domain

## Distinguishing Compliant vs Non-Compliant SSGTM

| Signal | Implication |
|---|---|
| `gcs=` parameter present in first-party requests during denied-consent scan | SSGTM is passing Consent Mode signals — likely compliant |
| No `gcs=` parameter despite CMP being present | SSGTM may not be passing consent signals — high risk |
| Conversion events fire from first-party domain after opt-out | Non-compliant SSGTM bypass |
| Container follows Google Tag Gateway pattern (see [[technical/google-tag-gateway]]) | May be compliant GTG, not rogue SSGTM |

## GPC and SSGTM

The `Sec-GPC: 1` header is an HTTP request header. When a browser sends this to a first-party server endpoint (SSGTM), the server receives it — but many SSGTM configurations do not:
1. Read the GPC header
2. Map it to consent state
3. Block downstream advertising calls accordingly

This is a systemic implementation gap. Even a site with a fully compliant client-side CMP may be violating GPC via SSGTM.

## Legal Liability

Regulators are beginning to examine SSGTM specifically as a consent bypass mechanism. The 2024–2026 enforcement trend confirms:
- Server-side container that fires advertising tags regardless of consent = same legal liability as client-side pixel
- The mechanism of transmission is irrelevant to the violation

See [[enforcement/emerging-trends]] for the server-side bypass enforcement trend.

## Google's Policy

Google requires all SSGTM implementations to:
1. Pass Consent Mode signals through to the server-side container
2. Not fire advertising tags for users who have denied `ad_storage`
3. Use `gcs=` and `gcd=` parameters to signal consent state on all requests

Failure violates Google Advertising Policies — can result in suspension of Google Ads and Analytics access.
