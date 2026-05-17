"""Tool 2 — ACM-Aware Violation Classifier.

Classifies each VendorFinding based on consent state, GCS signal, GCD detail,
and whether the vendor is an Advanced Consent Mode (ACM)-capable Google tag.

Key rules:
    - Google ACM vendors (GA4, DoubleClick/Ads) MAY fire cookieless modeling
      pings when consent is denied (GCS=G100). That is correct behaviour.
    - ALL other tracking vendors must be fully blocked when consent is denied.
      Any cookie or network hit = confirmed violation.
    - GCS=G111 in an opted-out scan means the active CMP overrode our
      injection — requires investigation, not automatically a violation.
    - No GCS at all (no consent mode) + tracking vendor firing = confirmed
      violation regardless of vendor type.
"""

from __future__ import annotations

from consent_engine.models.audit_request import ConsentState
from consent_engine.models.audit_result import GCSValue, ViolationStatus
from consent_engine.models.scan_result import CookieSnapshot
from consent_engine.models.vendor import CookieCategory, Vendor

# Vendor names that are Advanced Consent Mode-capable (Google tags).
# These MAY fire cookieless modeling pings when consent is denied.
_GOOGLE_ACM_VENDOR_NAMES: frozenset[str] = frozenset(
    {
        "Google Analytics",
        "Google / DoubleClick",
    }
)

# Cookie categories that require consent before firing.
_TRACKING_CATEGORIES: frozenset[CookieCategory] = frozenset(
    {CookieCategory.ANALYTICS, CookieCategory.TARGETING}
)

# GA tracking cookie prefixes that indicate full (non-cookieless) measurement.
_GA_COOKIE_PREFIXES: tuple[str, ...] = ("_ga", "_gid")


def is_google_acm_vendor(vendor: Vendor) -> bool:
    """Return True if this vendor is an ACM-capable Google tag.

    Google Analytics and Google/DoubleClick implement Advanced Consent Mode:
    they continue sending anonymised, cookieless modeling pings when consent
    is denied, enabling Google's behavioral modeling (~65% conversion recovery).
    All other vendors must be fully blocked when consent is denied.
    """
    return vendor.name in _GOOGLE_ACM_VENDOR_NAMES


def has_ga_tracking_cookies(cookies: list[CookieSnapshot]) -> bool:
    """Return True if any GA tracking cookies are present in the cookie jar.

    Presence of _ga / _gid / _ga_<property_id> cookies indicates that Google
    Analytics has written full measurement cookies — not a cookieless ping.
    When GCS=G100 but these cookies exist, ACM is misconfigured.
    """
    return any(c.name.startswith(_GA_COOKIE_PREFIXES) for c in cookies)


def classify_finding(
    vendor: Vendor,
    cookies_observed: list[str],
    all_scan_cookies: list[CookieSnapshot],
    gcs_value: GCSValue | None,
    gcd_raw: str | None,
    consent_state: ConsentState,
) -> tuple[ViolationStatus, str]:
    """Classify a single vendor finding using ACM-aware rules.

    Args:
        vendor: The vendor whose cookie/tag was observed.
        cookies_observed: Cookie names attributed to this vendor in this scan.
        all_scan_cookies: All cookies present after the scan (for GA cookie check).
        gcs_value: Parsed GCS consent signal from the scan's network traffic.
        gcd_raw: Raw GCD string from the scan (optional; for evidence notes).
        consent_state: The consent state that was active during the scan.

    Returns:
        (ViolationStatus, notes) where notes is an audit-evidence string.
    """
    is_opted_out = consent_state in (ConsentState.OPTED_OUT, ConsentState.GPC_OPTED_OUT)
    is_tracking = vendor.category in _TRACKING_CATEGORIES

    # Non-tracking vendors (essential, functional) are never violations.
    # Opted-in scans produce no violations.
    if not is_opted_out or not is_tracking:
        return ViolationStatus.NO_EVIDENCE, ""

    # --- Consent was denied (opted-out) and vendor is a tracking category ---

    gcs_denied = (
        gcs_value is not None
        and gcs_value.ad_storage == "denied"
        and gcs_value.analytics_storage == "denied"
    )
    gcs_granted = gcs_value is not None and not gcs_denied

    if is_google_acm_vendor(vendor):
        if gcs_denied:
            # GCS=G100: Google should be sending cookieless modeling pings only.
            if not has_ga_tracking_cookies(all_scan_cookies):
                # No _ga / _gid cookies → pure cookieless ping → ACM compliant.
                gcd_note = f" GCD={gcd_raw}" if gcd_raw else ""
                return (
                    ViolationStatus.ACM_COMPLIANT,
                    f"GCS=G100 — Google firing cookieless modeling ping "
                    f"(Advanced Consent Mode compliant).{gcd_note}",
                )
            else:
                # _ga cookies present despite GCS=G100 → ACM misconfigured.
                return (
                    ViolationStatus.CONFIRMED,
                    "GCS=G100 but _ga cookies were set — "
                    "Advanced Consent Mode misconfigured; full tracking active.",
                )

        elif gcs_granted:
            # GCS=G111 in an opted-out S3 scan.
            # The active CMP (e.g. CookieYes) overrode our consent injection —
            # the tag fired because the CMP granted consent, not our cookie.
            # This requires investigation rather than an automatic violation ruling.
            return (
                ViolationStatus.REQUIRES_INVESTIGATION,
                "GCS=G111 in opted-out scan — active CMP overriding consent injection. "
                "Verify CMP configuration and re-test with banner click methodology.",
            )

        else:
            # No GCS at all → no consent mode configured.
            return (
                ViolationStatus.CONFIRMED,
                f"{vendor.name} firing without any consent mode signal (no GCS detected).",
            )

    else:
        # Non-Google vendor: any firing in opted-out state is a confirmed violation.
        # ACM does not apply — these vendors must be fully blocked when denied.
        gcs_note = f" (GCS={gcs_value.raw})" if gcs_value else " (no consent mode)"
        return (
            ViolationStatus.CONFIRMED,
            f"{vendor.name} fired tracking tag in opted-out consent state{gcs_note}. "
            "Advanced Consent Mode does not cover non-Google vendors.",
        )
