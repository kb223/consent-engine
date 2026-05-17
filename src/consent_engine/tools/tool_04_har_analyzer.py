"""Tool 4 — HAR File Analyzer.

GCS/GCD: match ANY URL containing gcs= or gcd= as substring.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from consent_engine.models.audit_result import GCSHit, HarAnalysis
from consent_engine.tools.tool_03_browser_scanner import (
    extract_gcd_from_url,
    extract_gcs_from_url,
    parse_gcs_value,
)

_log = logging.getLogger(__name__)

_CONSENT_URL_PATTERNS = ("consent", "onetrust", "cookielaw", "cookiepro", "usercentrics")


def _iso_to_ms(dt_str: str) -> float:
    """Convert ISO 8601 datetime string to milliseconds epoch."""
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.timestamp() * 1000.0
    except Exception:  # noqa: BLE001
        return 0.0


def analyze_har(har_path: str) -> HarAnalysis:
    """Analyze a Playwright-recorded HAR file for consent signals.

    Extracts:
    - Full GCS/GCD timeline (every hit in chronological order)
    - POST request bodies (beacons, dataLayer pushes)
    - Response bodies from consent API endpoints

    Args:
        har_path: Path to the HAR JSON file written by Playwright.

    Returns:
        HarAnalysis with extracted data. Returns empty HarAnalysis if
        the file is missing, unreadable, or contains no relevant entries.
    """
    try:
        har_data = json.loads(Path(har_path).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        _log.warning("HAR analysis failed — file unreadable: %s", har_path, exc_info=True)
        return HarAnalysis()

    entries = har_data.get("log", {}).get("entries", [])
    if not entries:
        return HarAnalysis()

    base_ms = _iso_to_ms(entries[0].get("startedDateTime", ""))

    gcs_timeline: list[GCSHit] = []
    post_payloads: list[str] = []
    consent_api_responses: list[str] = []

    for entry in entries:
        request = entry.get("request", {})
        response = entry.get("response", {})
        url = request.get("url", "")
        started_ms = max(0.0, _iso_to_ms(entry.get("startedDateTime", "")) - base_ms)

        # GCS/GCD — collect every hit (not just the first)
        raw_gcs = extract_gcs_from_url(url)
        if raw_gcs:
            gcs_timeline.append(
                GCSHit(
                    url=url,
                    gcs_value=parse_gcs_value(raw_gcs),
                    gcd_raw=extract_gcd_from_url(url),
                    timestamp_ms=started_ms,
                )
            )

        # POST payloads
        if request.get("method", "").upper() == "POST":
            body = request.get("postData", {}).get("text", "")
            if body:
                post_payloads.append(body)

        # Consent API response bodies
        if any(pat in url.lower() for pat in _CONSENT_URL_PATTERNS):
            body = response.get("content", {}).get("text", "")
            if body:
                consent_api_responses.append(body)

    return HarAnalysis(
        gcs_timeline=gcs_timeline,
        post_payloads=post_payloads,
        consent_api_responses=consent_api_responses,
    )
