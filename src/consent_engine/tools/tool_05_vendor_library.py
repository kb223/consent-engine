"""Tool 5 — Vendor Cookie Lookup Library (three-tier)."""

from __future__ import annotations

import csv
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, TypedDict

from consent_engine.models.vendor import CookieCategory, LegalExposure, Vendor

_VENDOR_DATA_PATH = (
    Path(__file__).parent.parent / "data" / "vendor_library" / "vendors.json"
)

_OCD_DATA_PATH = (
    Path(__file__).parent.parent
    / "data"
    / "vendor_library"
    / "open-cookie-database.csv"
)

_OCD_SOURCE_NOTE = "Source: Open Cookie Database"


# ---------------------------------------------------------------------------
# OCD row type
# ---------------------------------------------------------------------------


class OCDRow(TypedDict):
    ID: str
    Platform: str
    Category: str
    cookie_name: str
    Domain: str
    Description: str
    Data_Controller: str
    Wildcard: str


# ---------------------------------------------------------------------------
# OCD index structure
# ---------------------------------------------------------------------------


class OCDIndex(TypedDict):
    exact: dict[str, OCDRow]
    wildcards: list[tuple[str, OCDRow]]
    domain: dict[str, OCDRow]


# ---------------------------------------------------------------------------
# Category / onetrust mapping helpers
# ---------------------------------------------------------------------------

_OCD_CATEGORY_MAP: dict[str, CookieCategory] = {
    "necessary": CookieCategory.ESSENTIAL,
    "functional": CookieCategory.FUNCTIONAL,
    "analytics": CookieCategory.ANALYTICS,
    "marketing": CookieCategory.TARGETING,
    "personalization": CookieCategory.FUNCTIONAL,
    "security": CookieCategory.ESSENTIAL,
}

_CATEGORY_ONETRUST_MAP: dict[CookieCategory, str | None] = {
    CookieCategory.ESSENTIAL: "C0001",
    CookieCategory.ANALYTICS: "C0002",
    CookieCategory.FUNCTIONAL: "C0003",
    CookieCategory.TARGETING: "C0004",
    CookieCategory.UNKNOWN: None,
}


def _map_ocd_category(raw: str) -> CookieCategory:
    return _OCD_CATEGORY_MAP.get(raw.lower().strip(), CookieCategory.UNKNOWN)


def _ocd_row_to_vendor(row: OCDRow) -> Vendor:
    name = row["Platform"] or row["Data_Controller"]
    domain = row["Domain"].strip()
    cookie_name = row["cookie_name"]
    category = _map_ocd_category(row["Category"])
    onetrust = _CATEGORY_ONETRUST_MAP.get(category)
    return Vendor(
        name=name,
        domains=[domain] if domain else [],
        cookie_names=[cookie_name],
        category=category,
        legal_exposure=LegalExposure.UNKNOWN,
        onetrust_category=onetrust,
        notes=_OCD_SOURCE_NOTE,
    )


# ---------------------------------------------------------------------------
# Data loaders (lru_cache on the loaders, NOT on lookup functions)
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _load_vendors() -> tuple[Vendor, ...]:
    try:
        with open(_VENDOR_DATA_PATH) as f:
            raw: list[dict[str, Any]] = json.load(f)
    except FileNotFoundError as e:
        raise FileNotFoundError(
            f"Vendor library not found at {_VENDOR_DATA_PATH}. "
            "Ensure data/vendor_library/vendors.json exists."
        ) from e
    return tuple(Vendor(**v) for v in raw)


@lru_cache(maxsize=1)
def _load_ocd_index() -> OCDIndex:
    exact: dict[str, OCDRow] = {}
    wildcards: list[tuple[str, OCDRow]] = []
    domain: dict[str, OCDRow] = {}

    try:
        with open(_OCD_DATA_PATH, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for raw_row in reader:
                row: OCDRow = {
                    "ID": raw_row.get("ID", ""),
                    "Platform": raw_row.get("Platform", ""),
                    "Category": raw_row.get("Category", ""),
                    "cookie_name": raw_row.get("Cookie / Data Key name", ""),
                    "Domain": raw_row.get("Domain", ""),
                    "Description": raw_row.get("Description", ""),
                    "Data_Controller": raw_row.get("Data Controller", ""),
                    "Wildcard": raw_row.get("Wildcard match", "0"),
                }
                cookie_name = row["cookie_name"]
                if not cookie_name:
                    continue

                if row["Wildcard"] == "1":
                    wildcards.append((cookie_name.lower(), row))
                else:
                    key = cookie_name.lower()
                    if key not in exact:
                        exact[key] = row

                dom = row["Domain"].strip()
                if dom:
                    dom_key = dom.lower()
                    if dom_key not in domain:
                        domain[dom_key] = row
    except FileNotFoundError as e:
        raise FileNotFoundError(
            f"OCD data not found at {_OCD_DATA_PATH}. "
            "Ensure data/vendor_library/open-cookie-database.csv exists."
        ) from e

    return OCDIndex(exact=exact, wildcards=wildcards, domain=domain)


# ---------------------------------------------------------------------------
# Internal tier helpers
# ---------------------------------------------------------------------------


# Short / common cookie names that unrelated FIRST-PARTY sites routinely set.
# A literal first-party cookie named "C" or "uid" must NOT be attributed to a
# tracking vendor on name alone, or it surfaces as a confirmed targeting
# violation with statutory-exposure dollars — a false positive in a
# litigation-facing tool. These are gated on domain below.
_TIER1_GENERIC_NAMES: frozenset[str] = frozenset(
    {"c", "uid", "sp", "tp", "sb", "wd", "mr", "sm", "id", "dpm", "fr", "aid", "pref"}
)


def _is_generic_cookie_name(name: str) -> bool:
    """A cookie name is 'generic' if it is short (<5 chars) or explicitly listed.

    Generic names collide with first-party cookies on unrelated sites, so a
    Tier-1 attribution on such a name is only trusted when the observed cookie
    domain also matches the vendor's domains.
    """
    low = name.lower()
    return len(name) < 5 or low in _TIER1_GENERIC_NAMES


def _tier1_lookup(q: str, cookie_domain: str | None = None) -> Vendor | None:
    """Check custom vendors.json (exact cookie name or domain, case-insensitive).

    For a matched vendor, generic cookie names (short or denylisted — see
    `_is_generic_cookie_name`) are domain-gated when `cookie_domain` is provided:
    the observed cookie domain must match one of the vendor's `domains` (same
    suffix logic Tier-2 uses) or the match is discarded and we fall through.
    This kills false positives where a first-party cookie literally named e.g.
    "C", "uid", "sp", or "fr" gets attributed to Adform/Snowplow/Meta. Longer,
    distinctive names (>=5 chars, not denylisted) are genuinely third-party, so
    exact-name matching for them is kept and loses no true positives.

    The domain-match branch is inherently self-validating and is left untouched,
    so the domain-query fallback in audit.py still resolves vendors by domain.
    """
    for vendor in _load_vendors():
        for name in vendor.cookie_names:
            if q != name.lower():
                continue
            if cookie_domain and _is_generic_cookie_name(name):
                if any(_domain_matches(cookie_domain, dom) for dom in vendor.domains):
                    return vendor
                break  # generic name, domain mismatch — try next vendor
            return vendor
        if any(q == dom.lower() for dom in vendor.domains):
            return vendor
    return None


def _domain_matches(cookie_domain: str, ocd_domain: str) -> bool:
    """Check if a cookie's domain matches the OCD entry's expected domain.

    Handles leading dots (e.g. '.facebook.com' matches 'facebook.com')
    and subdomain matching (e.g. 'ct.pinterest.com' matches '.pinterest.com').
    """
    cd = cookie_domain.lstrip(".").lower()
    od = ocd_domain.lstrip(".").lower()
    return cd == od or cd.endswith("." + od)


def _ocd_domain_ok(name: str, cookie_domain: str | None, ocd_dom: str) -> bool:
    """Whether an OCD row may be attributed to the observed cookie.

    Non-generic names keep prior behavior: accept unless a *present* cookie_domain
    and OCD domain positively mismatch. Generic short names (``C``, ``uid``, ``sp``,
    ``dpm`` ...) are the false-positive magnets — for those we REQUIRE a positive
    domain match, so a generic name on a row with a blank/unknown OCD domain (which
    the old `cookie_domain and ocd_dom and ...` gate let slip through) is refused
    rather than attributed to a tracking vendor.
    """
    if _is_generic_cookie_name(name):
        return bool(cookie_domain and ocd_dom and _domain_matches(cookie_domain, ocd_dom))
    # Non-generic: reject only on a positive domain mismatch; otherwise accept.
    if not (cookie_domain and ocd_dom):
        return True
    return _domain_matches(cookie_domain, ocd_dom)


def _tier2_lookup(q: str, cookie_domain: str | None = None) -> Vendor | None:
    """Check Open Cookie Database: exact cookie, wildcard prefix, then domain.

    When cookie_domain is provided, wildcard matches are only accepted if the
    OCD entry's domain matches the cookie's actual domain. This prevents
    generic prefixes (e.g. '_s', '_ut') from false-matching unrelated vendors.
    Generic short names additionally require a positive domain match (see
    `_ocd_domain_ok`) so blank-domain OCD rows can't produce a false attribution.
    """
    idx = _load_ocd_index()

    # 1. Exact cookie name match
    row = idx["exact"].get(q)
    if row is not None:
        ocd_dom = row["Domain"].strip()
        if _ocd_domain_ok(q, cookie_domain, ocd_dom):
            return _ocd_row_to_vendor(row)
        # else: name matched but domain unvalidated / mismatch — try wildcards/domain

    # 2. Wildcard prefix match (domain-gated when cookie_domain is provided)
    for prefix, wrow in idx["wildcards"]:
        if q.startswith(prefix):
            ocd_dom = wrow["Domain"].strip()
            if not _ocd_domain_ok(q, cookie_domain, ocd_dom):
                continue  # Prefix matched but domain unvalidated / wrong — skip
            return _ocd_row_to_vendor(wrow)

    # 3. Domain match
    dom_row = idx["domain"].get(q)
    if dom_row is not None:
        return _ocd_row_to_vendor(dom_row)

    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def lookup_vendor(query: str, cookie_domain: str | None = None) -> Vendor | None:
    """Look up vendor by cookie name or domain using three-tier priority.

    Tier 1: Custom vendors.json (exact match).
    Tier 2: Open Cookie Database (exact, wildcard prefix, domain).
    Tier 3: Unknown — returns None.

    When cookie_domain is provided, OCD wildcard and exact matches are validated
    against the entry's expected domain to prevent false positives from generic
    cookie names like '_s' or '_ut'.
    """
    q = query.lower().strip()

    result = _tier1_lookup(q, cookie_domain=cookie_domain)
    if result is not None:
        return result

    result = _tier2_lookup(q, cookie_domain=cookie_domain)
    if result is not None:
        return result

    return None


def lookup_tier(query: str) -> int | None:
    """Return which tier matched (1, 2, or None if no match).

    Used for result provenance tracking.
    """
    q = query.lower().strip()

    if _tier1_lookup(q) is not None:
        return 1

    if _tier2_lookup(q) is not None:
        return 2

    return None
