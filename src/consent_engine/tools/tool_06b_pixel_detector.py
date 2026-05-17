"""Tool 6b — Pixel Endpoint Detector.

Detects known tracking pixel endpoints in browser network traffic using the
same methodology as plaintiff law firms (Wiebe Law, Bursor & Fisher, etc.)
and privacy research tools (Blacklight, OpenWPM).

Cookie-based detection (tool_05) catches many vendors, but some pixels fire
network requests without setting cookies — especially under Advanced Consent
Mode. This tool catches those cases by matching raw request URLs against a
library of known pixel endpoint patterns.

Evidence value: Network-level pixel firings post-consent-denial are the
primary exhibit in CIPA, CCPA, and VPPA class action complaints.
"""

from __future__ import annotations

import re

from consent_engine.models.audit_result import PixelFiring

# ---------------------------------------------------------------------------
# Pixel endpoint pattern library
# ---------------------------------------------------------------------------
# Each entry: (vendor_name, pattern, category, legal_exposure)
# Pattern matches against the full request URL (lowercased).
# Ordered by legal exposure priority: high-risk first.

_PIXEL_PATTERNS: list[tuple[str, str, str, str]] = [
    # ── High-exposure advertising pixels (pixel-as-sale doctrine applies) ──
    ("Meta Pixel", r"facebook\.com/tr[/?]", "advertising", "high"),
    ("Meta Pixel", r"connect\.facebook\.net/.+/fbevents\.js", "advertising", "high"),
    ("Meta Pixel", r"graph\.facebook\.com/v\d+/\d+/events", "advertising", "high"),
    ("TikTok Pixel", r"analytics\.tiktok\.com/i18n/pixel", "advertising", "high"),
    ("TikTok Pixel", r"analytics\.tiktok\.com/api/v\d+/pixel", "advertising", "high"),
    ("TikTok Pixel", r"business-api\.tiktok\.com", "advertising", "high"),
    ("LinkedIn Insight Tag", r"snap\.licdn\.com/li\.lms-analytics", "advertising", "high"),
    ("LinkedIn Insight Tag", r"px\.ads\.linkedin\.com", "advertising", "high"),
    ("LinkedIn Insight Tag", r"platform\.linkedin\.com/js/analytics", "advertising", "high"),
    ("Twitter/X Pixel", r"static\.ads-twitter\.com/uwt\.js", "advertising", "high"),
    ("Twitter/X Pixel", r"ads-api\.twitter\.com", "advertising", "high"),
    ("Twitter/X Pixel", r"t\.co/\d+", "advertising", "medium"),
    ("Pinterest Tag", r"ct\.pinterest\.com/v3", "advertising", "high"),
    ("Pinterest Tag", r"ct\.pinterest\.com/user", "advertising", "high"),
    ("Snapchat Pixel", r"sc-static\.net/s/p\.js", "advertising", "high"),
    ("Snapchat Pixel", r"tr\.snapchat\.com/p", "advertising", "high"),
    # ── Google Ads (GCS-dependent — ACM determines compliance) ──
    ("Google Ads", r"googleadservices\.com/pagead/conversion", "advertising", "high"),
    ("Google Ads", r"googlesyndication\.com", "advertising", "medium"),
    ("DoubleClick/DV360", r"doubleclick\.net/activityi;", "advertising", "high"),
    ("DoubleClick/DV360", r"ad\.doubleclick\.net", "advertising", "high"),
    ("DoubleClick/DV360", r"fls\.doubleclick\.net", "advertising", "high"),
    # ── Microsoft / Bing ──
    ("Microsoft Clarity", r"clarity\.ms/collect", "session_recording", "high"),
    ("Microsoft Clarity", r"c\.clarity\.ms", "session_recording", "high"),
    ("Bing Ads UET", r"bat\.bing\.com/action", "advertising", "high"),
    ("Bing Ads UET", r"bat\.bing\.com/p/action", "advertising", "high"),
    # ── Session recorders (CIPA wiretap theory) ──
    ("FullStory", r"fullstory\.com/s/fs\.js", "session_recording", "high"),
    ("FullStory", r"rs\.fullstory\.com/rec/bundle", "session_recording", "high"),
    ("Hotjar", r"static\.hotjar\.com/c/hotjar-\d+\.js", "session_recording", "high"),
    ("Hotjar", r"vc\.hotjar\.io", "session_recording", "high"),
    ("LogRocket", r"cdn\.logrocket\.io", "session_recording", "high"),
    # ── Ad tech / DSP / SSP ──
    ("Criteo", r"bidder\.criteo\.com", "advertising", "high"),
    ("Criteo", r"sslwidget\.criteo\.com", "advertising", "high"),
    ("Criteo", r"static\.criteo\.net", "advertising", "high"),
    ("AppNexus/Xandr", r"acdn\.adnxs\.com", "advertising", "medium"),
    ("AppNexus/Xandr", r"secure\.adnxs\.com", "advertising", "medium"),
    ("TradeDesk", r"js\.adsrvr\.org", "advertising", "high"),
    ("TradeDesk", r"match\.adsrvr\.org", "advertising", "high"),
    ("Quantcast", r"cms\.quantserve\.com", "advertising", "medium"),
    ("LiveRamp", r"launchpad\.privacymanager\.io", "advertising", "high"),
    ("LiveRamp", r"idsync\.rlcdn\.com", "advertising", "high"),
    # ── Retargeting / attribution ──
    ("Reddit Pixel", r"alb\.reddit\.com/snoo", "advertising", "high"),
    ("Reddit Pixel", r"rereddit\.com/pixel", "advertising", "high"),
    ("Reddit Pixel", r"events\.reddit\.com", "advertising", "medium"),
    ("Taboola", r"cdn\.taboola\.com", "advertising", "medium"),
    ("Taboola", r"trc\.taboola\.com", "advertising", "medium"),
    ("Outbrain", r"outbrain\.com/outbrain\.js", "advertising", "medium"),
    ("Outbrain", r"tr\.outbrain\.com", "advertising", "medium"),
    ("Amazon Ads", r"s\.amazon-adsystem\.com", "advertising", "high"),
    ("Amazon Ads", r"aax\.amazon-adsystem\.com", "advertising", "high"),
    ("MediaMath", r"pixel\.mathtag\.com", "advertising", "high"),
    ("MediaMath", r"sync\.mathtag\.com", "advertising", "high"),
    ("PubMatic", r"ads\.pubmatic\.com", "advertising", "medium"),
    ("PubMatic", r"image\d+\.pubmatic\.com", "advertising", "medium"),
    ("Magnite/Rubicon", r"pixel\.rubiconproject\.com", "advertising", "medium"),
    ("Magnite/Rubicon", r"fastlane\.rubiconproject\.com", "advertising", "medium"),
    ("Index Exchange", r"casalemedia\.com", "advertising", "medium"),
    ("Bidswitch", r"bidswitch\.net", "advertising", "medium"),
    ("ShareASale", r"shareasale\.com/shareasale\.js", "advertising", "medium"),
    ("Impact", r"d\.impactradius-event\.com", "advertising", "medium"),
    ("CJ Affiliate", r"www\.emjcd\.com", "advertising", "medium"),
    ("Attentive", r"cdn\.attn\.tv", "advertising", "medium"),
    ("Attentive", r"events\.attentivemobile\.com", "advertising", "medium"),
    # ── Session recorders / analytics (CIPA wiretap theory) ──
    ("Mouseflow", r"o2\.mouseflow\.com", "session_recording", "high"),
    ("Lucky Orange", r"d\.luckyorange\.com", "session_recording", "high"),
    ("ContentSquare", r"t\.contentsquare\.net", "session_recording", "high"),
    ("ContentSquare", r"c\.contentsquare\.net", "session_recording", "high"),
    ("Glassbox", r"cdn\.glassboxdigital\.io", "session_recording", "high"),
    # ── Customer data platforms / enrichment ──
    ("Klaviyo", r"static\.klaviyo\.com/onsite/js", "advertising", "medium"),
    ("Klaviyo", r"a\.klaviyo\.com", "advertising", "medium"),
    ("LiveIntent", r"liad\.liadm\.com", "advertising", "high"),
    ("LiveIntent", r"p\.liadm\.com", "advertising", "high"),
    ("Lotame", r"tags\.crwdcntrl\.net", "advertising", "medium"),
    ("Ketch", r"global\.ketchcdn\.com", "functional", "low"),
    ("Yotpo", r"staticw2\.yotpo\.com", "analytics", "medium"),
    ("Trustpilot", r"widget\.trustpilot\.com", "analytics", "low"),
    ("Bazaarvoice", r"display\.ugc\.bazaarvoice\.com", "analytics", "medium"),
    # ── Analytics (lower exposure but still relevant for consent violations) ──
    ("Amplitude", r"api\.amplitude\.com", "analytics", "medium"),
    ("Mixpanel", r"api\.mixpanel\.com", "analytics", "medium"),
    ("Segment", r"api\.segment\.io", "analytics", "medium"),
    ("Heap Analytics", r"heapanalytics\.com", "analytics", "medium"),
    ("PostHog", r"app\.posthog\.com", "analytics", "medium"),
    ("PostHog", r"us\.i\.posthog\.com", "analytics", "medium"),
    ("Pendo", r"pendo-static-\d+\.storage\.googleapis\.com", "analytics", "medium"),
    ("Pendo", r"app\.pendo\.io", "analytics", "medium"),
]

# Compile patterns for performance
_COMPILED: list[tuple[str, re.Pattern[str], str, str]] = [
    (name, re.compile(pattern, re.IGNORECASE), category, exposure)
    for name, pattern, category, exposure in _PIXEL_PATTERNS
]

# Google domains that send ACM cookieless pings when GCS=G100 + npa=1.
# These are correct Advanced Consent Mode behavior, not violations.
_GOOGLE_ACM_DOMAINS = re.compile(
    r"(pagead2\.googlesyndication\.com|googlesyndication\.com|"
    r"google-analytics\.com/g/collect|googletagmanager\.com/gtm\.js|"
    r"googleadservices\.com/pagead/conversion/\d+/\?)",
    re.IGNORECASE,
)


def _is_acm_ping(url: str) -> bool:
    """Return True if this is a Google ACM cookieless ping (G100 + npa=1).

    These are expected behavior under Advanced Consent Mode — Google sends
    anonymous modeling signals without cookie IDs. Not a violation.
    """
    if not _GOOGLE_ACM_DOMAINS.search(url):
        return False
    url_lower = url.lower()
    # Must have gcs=g1 (denial state) and npa=1 (non-personalized ads flag)
    has_gcs_denial = bool(re.search(r"[?&]gcs=g1[0-9-]{2}", url_lower))
    has_npa = "npa=1" in url_lower
    return has_gcs_denial or has_npa  # either signal confirms ACM ping


def detect_pixel_firings(network_urls: list[str]) -> list[PixelFiring]:
    """Scan browser network requests for known tracking pixel endpoints.

    Args:
        network_urls: List of request URLs captured during the scan (from
            ScanResult.network_requests). These are captured post-consent-denial
            in S3 methodology — any match here is direct forensic evidence.

    Returns:
        List of PixelFiring instances, deduplicated by vendor + pattern.
        Sorted by legal_exposure (high first), then vendor name.
    """
    seen: set[tuple[str, str]] = set()  # (vendor_name, matched_pattern)
    firings: list[PixelFiring] = []

    for url in network_urls:
        for vendor_name, compiled, category, exposure in _COMPILED:
            match = compiled.search(url)
            if not match:
                continue
            dedup_key = (vendor_name, match.group())
            if dedup_key in seen:
                continue
            seen.add(dedup_key)
            firings.append(
                PixelFiring(
                    vendor_name=vendor_name,
                    url=url,
                    category=category,
                    legal_exposure=exposure,
                    matched_pattern=match.group(),
                    is_acm_ping=_is_acm_ping(url),
                )
            )

    # Sort: high exposure first, then alphabetically
    return sorted(firings, key=lambda f: (0 if f.legal_exposure == "high" else 1, f.vendor_name))
