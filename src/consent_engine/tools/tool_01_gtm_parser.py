"""Tool 1 — GTM Container Parser.

Extracts per-tag consent requirements from a captured GTM container JS body.

Key domain rule:
    Advanced Consent Mode (ACM) ONLY applies to Google's own tag types.
    Non-Google tags (Custom HTML, Custom Image, vendor pixels) MUST have
    explicit consent settings configured in GTM. A non-Google tag without
    consent settings fires regardless of user consent state — this is a
    confirmed violation.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from consent_engine.models.audit_result import TagConsentEntry

_log = logging.getLogger(__name__)

# GTM function codes for Google-owned tags.
# These are covered by Advanced Consent Mode (cookieless pings in denied state).
_GOOGLE_TAG_TYPES: frozenset[str] = frozenset(
    {
        "__ua",  # Universal Analytics (deprecated)
        "__ga4",  # GA4 Config
        "__ga4event",  # GA4 Event
        "__flc",  # Floodlight Counter
        "__flsd",  # Floodlight Sales
        "__awct",  # Google Ads Conversion Tracking
        "__gclidw",  # Google Ads Remarketing
        "__googtag",  # Google Tag (gtag.js)
        "__sp",  # Google Surveys
        "__awdc",  # Google Ads Dynamic Conversion
        "__cvt",  # Conversion Linker
        # Without double-underscore prefix (some GTM versions omit it)
        "ua",
        "ga4",
        "ga4event",
        "flc",
        "flsd",
        "awct",
        "gclidw",
        "googtag",
        "sp",
        "awdc",
        "cvt",
    }
)

# Regex to locate the start of the embedded container JSON in gtm.js
_CONTAINER_START_RE = re.compile(r'\(\{"resource":', re.DOTALL)


def _extract_container_json(js_body: str) -> dict[str, Any] | None:
    """Extract and parse the container JSON embedded in a GTM JS body.

    GTM container JS embeds the container data as:
        ({"resource":{...tags, triggers, macros...}})

    Uses a brace-counting approach to extract the balanced JSON object.
    Returns None if the pattern is not found or parsing fails.
    """
    match = _CONTAINER_START_RE.search(js_body)
    if not match:
        return None
    # Skip the opening '(' to get to the start of the JSON object
    start = match.start() + 1
    depth = 0
    for i in range(start, len(js_body)):
        ch = js_body[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    result: dict[str, Any] = json.loads(js_body[start : i + 1])  # noqa: E203
                    return result
                except json.JSONDecodeError:
                    return None
    return None


def _classify_tag(tag: dict[str, Any]) -> TagConsentEntry:
    """Classify a single GTM tag entry into a TagConsentEntry."""
    func = tag.get("function", "")
    tag_id = int(tag.get("tag_id", 0))
    tag_name = tag.get("instance_name", func) or func
    is_google = func in _GOOGLE_TAG_TYPES
    consent_settings = tag.get("consent_settings")

    if consent_settings:
        consent_val = int(consent_settings.get("consent", 0))
        # Extract consent type strings from cm array where type == 0 (string literal)
        consent_types = [
            cm_entry["string"]
            for cm_entry in consent_settings.get("cm", [])
            if isinstance(cm_entry, dict) and cm_entry.get("type") == 0 and cm_entry.get("string")
        ]
        requirement: str = "required" if consent_val >= 2 else "optional"
    else:
        consent_types = []
        requirement = "acm_managed" if is_google else "missing"

    return TagConsentEntry(
        tag_id=tag_id,
        tag_name=tag_name,
        tag_type=func,
        is_google_tag=is_google,
        consent_types=consent_types,
        requirement=requirement,  # type: ignore[arg-type]
    )


def parse_gtm_container(
    gtm_container_js: str,
    page_html: str = "",
) -> list[TagConsentEntry]:
    """Parse a GTM container JS body to extract per-tag consent requirements.

    Args:
        gtm_container_js: Raw gtm.js response body (from ScanResult.gtm_container_js).
        page_html: Page HTML (currently used only to confirm GTM presence).

    Returns:
        List of TagConsentEntry, one per tag. Returns empty list if the JS
        body cannot be parsed — never raises.

    Domain rule:
        Tags with requirement="missing" are non-Google tags with no consent
        configuration. They fire regardless of user consent state.
        This is a confirmed violation — ACM does not protect non-Google tags.
    """
    if not gtm_container_js:
        return []

    try:
        container = _extract_container_json(gtm_container_js)
    except Exception:  # noqa: BLE001
        _log.warning("GTM container JSON extraction failed", exc_info=True)
        return []

    if not container:
        return []

    tags = container.get("resource", {}).get("tags", [])
    if not isinstance(tags, list):
        return []

    result = []
    for tag in tags:
        try:
            result.append(_classify_tag(tag))
        except Exception:  # noqa: BLE001
            _log.debug("Skipping unparseable tag: %s", tag)
    return result
