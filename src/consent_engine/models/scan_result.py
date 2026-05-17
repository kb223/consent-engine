"""ScanResult — output model for Tool 3 (Headless Browser Scanner)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from .audit_request import ConsentState
from .audit_result import GCSValue, GTMExtractionMethod, MethodologyFlag

ScanMode = Literal["playwright", "stealthy"]


class CookieSnapshot(BaseModel):
    """A single cookie observed during a browser scan."""

    name: str
    value: str
    domain: str
    path: str
    secure: bool
    http_only: bool
    same_site: str
    expires: float | None = None  # Unix timestamp, None = session cookie


class ScanResult(BaseModel):
    """Output of a single headless browser scan (Tool 3)."""

    url: str
    methodology: MethodologyFlag
    consent_state: ConsentState
    timestamp: datetime
    cookies: list[CookieSnapshot] = []
    network_requests: list[str] = []  # All request URLs observed during scan
    gcs_value: GCSValue | None = None  # First GCS value found in network requests
    gcd_raw: str | None = None  # First GCD (V2 consent detail) value found
    gtm_container_id: str | None = None  # e.g. "GTM-XXXXXX"
    gtm_extraction_method: GTMExtractionMethod = GTMExtractionMethod.NONE
    gtm_container_js: str | None = None  # Raw gtm.js payload (live extraction only)
    gpc_header_sent: bool = False  # True when Sec-GPC: 1 was included in headers
    page_html: str | None = None  # Raw page HTML (for GTM ID regex fallback)
    cmp_interaction_method: str | None = (
        None  # "cookie_injection" | "banner_click" | "banner_click_inconclusive" | "banner_click_failed"
    )
    detected_cmp: str | None = None
    # The CMP identified on the page: "OneTrust" | "CookieYes" | "Cookiebot" | etc.
    cmp_detection_confidence: str | None = None
    # "high" (JS global confirmed) | "medium" (script URL) | "low" (cookie/DOM)
    bot_detection_encountered: bool = False
    # True if WAF/bot protection returned 403/challenge before page loaded
    scan_mode_used: ScanMode = "playwright"
    # "playwright" = primary Chromium scan; "stealthy" = Scrapling/Camoufox fallback
    # engaged after the primary scan hit a WAF/bot challenge
    har_path: str | None = None  # path to auto-captured HAR file (written by Tool 3)
