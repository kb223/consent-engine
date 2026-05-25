from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel

from .vendor import Vendor


class GTMExtractionMethod(StrEnum):
    LIVE = "live"  # Intercepted from gtm.js during scan — strongest evidence
    PROVIDED = "provided"  # User-supplied JSON export
    NONE = "none"  # No container data available


class ViolationStatus(StrEnum):
    CONFIRMED = "confirmed_violation"
    LIKELY = "likely_violation"
    REQUIRES_INVESTIGATION = "requires_further_investigation"
    NO_EVIDENCE = "no_evidence_of_violation"
    ACM_COMPLIANT = "acm_cookieless_ping"  # Google tag firing cookieless (correct ACM behaviour)


class MethodologyFlag(StrEnum):
    S1 = "s1_baseline"
    S2 = "s2_post_optout_no_reload"
    S3 = "s3_fresh_load_optout_preset"
    # S3 run completed, but consent injection could not be verified against
    # a denied post-injection Consent Mode signal (e.g. unknown CMP, or
    # injection silently did not suppress tracking). Treat as non-definitive.
    INCONCLUSIVE_UNKNOWN_CMP = "s3_inconclusive_unknown_cmp"
    # S3 run completed with a recognised CMP and a matching injection plan,
    # but Google Consent Mode beacons continued firing with GCS=G111
    # throughout the scan. This is definitive evidence that the site's tag
    # wiring fires before or regardless of the consent state the CMP stores
    # — the CMP is working; the integration is broken. Findings are legally
    # defensible.
    S3_CONSENT_WIRING_BROKEN = "s3_consent_wiring_broken"


class GCSValue(BaseModel):
    raw: str
    ad_storage: str
    analytics_storage: str


class TagConsentEntry(BaseModel):
    """Per-tag GTM consent configuration extracted by Tool 1."""

    tag_id: int
    tag_name: str
    tag_type: str  # GTM function code, e.g. "__html", "__ua", "__ga4"
    is_google_tag: bool
    consent_types: list[str] = []  # e.g. ["ad_storage", "analytics_storage"]
    requirement: Literal[
        "required",  # explicit consent settings present, enforced
        "optional",  # explicit consent settings, default_value=1
        "acm_managed",  # Google tag — ACM handles consent via cookieless ping
        "missing",  # NON-Google tag with no consent settings — VIOLATION
    ]


class GCSHit(BaseModel):
    """A single GCS signal observation from HAR analysis (Tool 4)."""

    url: str
    gcs_value: GCSValue
    gcd_raw: str | None = None
    timestamp_ms: float  # milliseconds from first HAR entry


class HarAnalysis(BaseModel):
    """Output of Tool 4 HAR file analysis."""

    gcs_timeline: list[GCSHit] = []
    post_payloads: list[str] = []  # raw POST bodies (beacons, dataLayer pushes)
    consent_api_responses: list[str] = []  # response bodies from consent endpoints


class PixelFiring(BaseModel):
    """A tracking pixel endpoint observed firing in network traffic post-consent-denial.

    This is the primary evidence method used by plaintiff attorneys — detecting
    known ad/analytics pixel endpoints in HAR/network traffic regardless of cookies.
    """

    vendor_name: str  # e.g. "Meta Pixel", "TikTok Pixel", "LinkedIn Insight Tag"
    url: str  # full request URL observed
    category: str  # "advertising" | "analytics" | "session_recording"
    legal_exposure: str  # "high" | "medium"
    matched_pattern: str  # the pattern that triggered this match
    is_acm_ping: bool = (
        False  # True = Google ACM cookieless ping (G100+npa=1) — expected behavior, not a violation
    )


class VendorFinding(BaseModel):
    vendor: Vendor
    status: ViolationStatus
    methodology: MethodologyFlag
    cookies_observed: list[str] = []
    gcs_value: GCSValue | None = None
    gpc_honored: bool | None = None
    evidence: list[str] = []
    notes: str = ""


class CMPRuntimeConfig(BaseModel):
    """What the CMP's own runtime API reports about itself.

    Populated by `tool_cmp_runtime_introspect` after the page loads and the
    CMP SDK initializes. Lets the audit compare "what the CMP THINKS it is
    doing" (this object) against "what actually happens" (network capture
    + cookies). Mismatches are the most material forensic finding type
    because they prove the CMP is misconfigured, not that the operator is
    making a judgment call about gray-area enforcement.

    Currently OneTrust-only; per-CMP extractors planned for v0.5.8+
    (Cookiebot, CookieYes, Didomi, Usercentrics, TrustArc, Sourcepoint).
    """

    cmp_name: str
    template_name: str | None = None
    geolocation_rule: str | None = None  # e.g. "Global Audience (loi 25-GDPR)"
    geolocation_country: str | None = None  # e.g. "CA"
    consent_model: Literal["opt-in", "opt-out", "implicit", "unknown"] = "unknown"
    expected_cookies_by_category: dict[str, list[str]] = {}
    expected_vendor_ids: list[str] = []
    script_version: str | None = None
    domain_id: str | None = None
    raw_dump: str | None = None  # truncated raw output for forensic record


class ConsentEvent(BaseModel):
    """Single consent-related dataLayer push captured during the scan.

    Filtered narrowly to consent signals (gtag consent commands, CMP-specific
    events like OneTrustGroupsUpdated, custom consent events) — not the full
    dataLayer stream. Order is preserved via `index_in_stream` so race-
    condition forensics (CMP loads after first GA hit, etc.) are possible.
    """

    index_in_stream: int  # position in window.dataLayer
    source: Literal[
        "gtag_consent_default",
        "gtag_consent_update",
        "onetrust_groups_updated",
        "onetrust_loaded",
        "cookieyes_consent",
        "cookiebot",
        "didomi",
        "usercentrics",
        "tcfapi",
        "custom_consent",
    ]
    event_name: str | None = None  # raw 'event' key from the dataLayer entry
    params: dict[str, str] = {}  # flattened key-value pairs


class AuditResult(BaseModel):
    audit_id: str
    url: str
    timestamp: datetime
    methodology: MethodologyFlag
    gtm_extraction_method: GTMExtractionMethod = GTMExtractionMethod.NONE
    gtm_container_id: str | None = None  # e.g. "GTM-XXXXXX"
    ssgtm_detected: bool = False
    ssgtm_domain: str | None = None
    gpc_tested: bool = False
    # GPC signal test — populated when a dedicated GPC scan is run alongside
    # the primary S3 scan. Lets the report show a clear pass/fail on whether
    # the site respected the Global Privacy Control opt-out signal.
    gpc_header_sent: bool = False  # Sec-GPC: 1 HTTP header on all requests
    gpc_navigator_api_set: bool = False  # navigator.globalPrivacyControl = true injected
    gpc_signal_respected: bool | None = None  # True = pixel count dropped; None = not tested
    gpc_vendors_after_signal: int = 0  # vendors still firing after GPC asserted
    gpc_pixel_count_baseline: int = 0  # pixel firings during primary S3 opt-out scan
    gpc_pixel_count_with_gpc: int = 0  # pixel firings during GPC scan
    # Scan-level consent signals from primary scan network traffic
    gcs_value: GCSValue | None = None
    gcd_raw: str | None = None
    cmp_interaction_method: str | None = (
        None  # "cookie_injection" | "banner_click" | "banner_click_inconclusive" | "banner_click_failed" | "banner_click_reverted"
    )
    detected_cmp: str | None = None
    cmp_detection_confidence: str | None = None
    bot_detection_encountered: bool = False
    scan_mode_used: Literal["playwright", "stealthy"] = "playwright"
    # Records whether the primary Chromium scan succeeded ("playwright") or the
    # Scrapling/Camoufox stealthy fallback had to be engaged ("stealthy") — set
    # when the primary scan hit a WAF/bot challenge.
    detected_jurisdiction: str | None = (
        None  # "EU" | "US" | "CA"; str (not Literal) to allow extension without schema migration
    )
    tag_consent_map: list[TagConsentEntry] = []
    gcs_timeline: list[GCSHit] = []
    post_payloads: list[str] = []
    consent_api_responses: list[str] = []
    findings: list[VendorFinding] = []
    pixel_firings: list[
        PixelFiring
    ] = []  # Network-level pixel endpoint detections (plaintiff evidence)
    open_gaps: list[str] = []
    remediation: list[str] = []
    # CMP runtime introspection — what the CMP reports about itself via its
    # JS API. None when the CMP doesn't expose an API we know how to call.
    cmp_runtime_config: CMPRuntimeConfig | None = None
    # Consent-event dataLayer pushes — narrowed to consent signals only.
    consent_events: list[ConsentEvent] = []
