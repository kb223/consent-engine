"""Tool 6 — Server-Side GTM Detector.

Detects SSGTM by fetching first-party JavaScript response bodies and scanning
for GTM fingerprints. URL pattern matching alone is unreliable — Stape's custom
loader and similar solutions use fully obfuscated script names and paths.

If SSGTM detected: client-side consent enforcement may be bypassed.
GPC Sec-GPC:1 header cannot be forwarded to server-side containers.
"""

from __future__ import annotations

import re

import httpx
import tldextract
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_GTM_ID_RE = re.compile(r"GTM-[A-Z0-9]+")
_BODY_LIMIT_CHARS = 20_480  # 20 KB — sufficient to catch fingerprints in loader preamble (applied to str, not bytes)

# Known third-party GTM/analytics domains — never flagged as SSGTM
_THIRD_PARTY_DOMAINS = frozenset(
    [
        "googletagmanager.com",
        "google-analytics.com",
        "analytics.google.com",
        "googleadservices.com",
        "doubleclick.net",
        "googlesyndication.com",
        "google.com",
        "facebook.com",
        "facebook.net",
    ]
)

# Reserved for a future low-confidence scoring pass — URL patterns alone are not
# sufficient for detection (Stape and similar tools use fully arbitrary paths).
_PATH_HINT_RE = re.compile(r"/(gtg|metrics|tagging|google-tag|gtm)/", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------


class SSGTMResult(BaseModel):
    detected: bool
    confidence: str | None = None  # "high" | "medium" | "low" | None
    domain: str | None = None
    loader_url: str | None = None
    container_id: str | None = None
    evidence: list[str] = []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _registered_domain(url: str) -> str:
    """Return the registrable domain (e.g. 'kennethjbuchanan.com') for a URL."""
    ext = tldextract.extract(url)
    return f"{ext.domain}.{ext.suffix}" if ext.suffix else ext.domain


def _is_first_party(url: str, target_url: str) -> bool:
    """Return True if url is served from the same registrable domain as target_url."""
    url_domain = _registered_domain(url)
    target_domain = _registered_domain(target_url)
    if not url_domain or not target_domain:
        return False
    # Also reject known third-party tracking domains regardless of registered domain
    ext = tldextract.extract(url)
    full_domain = f"{ext.domain}.{ext.suffix}"
    if full_domain in _THIRD_PARTY_DOMAINS:
        return False
    return url_domain == target_domain


def _looks_like_js(url: str) -> bool:
    """Return True if the URL likely points to a JavaScript file."""
    path = url.split("?")[0].lower()
    if path.endswith(".js") or "/js/" in path or "script" in path:
        return True
    # Extensionless paths may be obfuscated JS loaders (e.g. Stape custom loader)
    # Skip known non-JS extensions; treat anything else as a candidate
    last_segment = path.rsplit("/", 1)[-1]
    has_extension = "." in last_segment
    non_js_extensions = {
        ".css",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".svg",
        ".woff",
        ".woff2",
        ".ttf",
        ".ico",
        ".json",
        ".xml",
        ".html",
        ".htm",
        ".php",
        ".txt",
    }
    if not has_extension:
        return True
    ext = "." + last_segment.rsplit(".", 1)[-1]
    return ext not in non_js_extensions


def _fingerprint_body(body: str) -> tuple[str | None, str | None, list[str]]:
    """Scan a JS response body for GTM fingerprints.

    Returns:
        (confidence, container_id, evidence_list)
        confidence: "high" | "medium" | None
    """
    evidence: list[str] = []
    container_id: str | None = None

    if "google_tag_manager" in body:
        evidence.append("google_tag_manager")

    match = _GTM_ID_RE.search(body)
    if match:
        container_id = match.group(0)
        evidence.append(f"container_id:{container_id}")

    if "googletagmanager.com" in body:
        evidence.append("googletagmanager.com")

    if evidence:
        # HIGH if we have the object name or a container ID directly in body
        is_high = "google_tag_manager" in evidence or container_id is not None
        confidence = "high" if is_high else "medium"
        return confidence, container_id, evidence

    return None, None, []


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def detect_ssgtm(network_requests: list[str], target_url: str) -> SSGTMResult:
    """Detect server-side GTM by inspecting first-party JavaScript response bodies.

    Also detects Stape custom loader by identifying first-party /g/collect endpoints
    and custom loader paths (e.g. /sky/) that proxy GA4 requests through the site domain.

    Args:
        network_requests: All request URLs captured during the scan (from ScanResult).
        target_url: The page URL being audited (used to identify first-party domain).

    Returns:
        SSGTMResult with detection status, confidence, and evidence.
    """
    # --- Pass 1: Detect first-party /g/collect (Stape custom loader signature) ---
    _collect_re = re.compile(r"/g/collect\b")
    for url in network_requests:
        if _is_first_party(url, target_url) and _collect_re.search(url) and "gcs=" in url:
            ext = tldextract.extract(url)
            domain = f"{ext.subdomain}.{ext.domain}.{ext.suffix}".lstrip(".")
            # Extract GTM container ID from the gtm= parameter if present
            gtm_match = re.search(r"[?&]gtm=([^&]+)", url)
            return SSGTMResult(
                detected=True,
                confidence="high",
                domain=domain,
                loader_url=url.split("?")[0],  # strip query for cleaner display
                container_id=None,
                evidence=[
                    "first_party_collect_endpoint",
                    f"gtm_param:{gtm_match.group(1)}" if gtm_match else "ga4_collect",
                ],
            )

    # --- Pass 2: Fingerprint first-party JS responses (existing logic) ---
    candidates = [
        url for url in network_requests if _is_first_party(url, target_url) and _looks_like_js(url)
    ]

    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        for url in candidates:
            try:
                resp = await client.get(url, headers={"Accept": "application/javascript"})
                if resp.status_code != 200:
                    continue

                body = resp.text[:_BODY_LIMIT_CHARS]
                confidence, container_id, evidence = _fingerprint_body(body)

                if confidence in ("high", "medium"):
                    ext = tldextract.extract(url)
                    domain = f"{ext.subdomain}.{ext.domain}.{ext.suffix}".lstrip(".")
                    return SSGTMResult(
                        detected=True,
                        confidence=confidence,
                        domain=domain,
                        loader_url=url,
                        container_id=container_id,
                        evidence=evidence,
                    )

            except (httpx.RequestError, httpx.TimeoutException):
                continue  # Network error — skip this candidate

    return SSGTMResult(detected=False)
