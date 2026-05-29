"""Jurisdiction Detector — infers regulatory jurisdiction from page HTML and URL.

Signals checked in order (strictest-wins: EU > CA > US):
  1. <html lang="..."> attribute
  2. <link rel="alternate" hreflang="..."> tags
  3. <meta name="geo.region" content="...">
  4. <meta property="og:locale" content="...">
  5. URL TLD heuristic (via tldextract)

Returns "EU" | "CA" | "US". Defaults to "US" when no signals found.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import tldextract

# Single module-level TLDExtract instance using the packaged public-suffix
# snapshot. An empty ``suffix_list_urls`` suppresses the lazy network fetch of
# the Mozilla list on first use, keeping this forensic tool offline-deterministic.
_TLD_EXTRACT = tldextract.TLDExtract(suffix_list_urls=())

# ---------------------------------------------------------------------------
# Signal sets
# ---------------------------------------------------------------------------

# ISO 639-1 language codes associated with EU member states.
# Note: some codes (es, pt, fr, nl) are also used outside EU (e.g., es-MX, pt-BR).
# Country subtag check in _lang_signals / _hreflang_signals narrows this when present.
# Without a country subtag, lang="es" conservatively triggers EU — by design for a
# litigation tool where GDPR over-coverage is preferable to CCPA under-coverage.
_EU_LANG_CODES: frozenset[str] = frozenset(
    {
        "de",
        "fr",
        "es",
        "it",
        "nl",
        "pl",
        "pt",
        "sv",
        "da",
        "fi",
        "cs",
        "ro",
        "hu",
        "sk",
        "hr",
        "bg",
        "lt",
        "lv",
        "et",
        "sl",
        "mt",
        "ga",
        "el",
        "cy",
        "lb",
    }
)

# ISO 3166-1 alpha-2 country codes for EU member states + EEA
_EU_COUNTRY_CODES: frozenset[str] = frozenset(
    {
        "DE",
        "FR",
        "ES",
        "IT",
        "NL",
        "PL",
        "PT",
        "SE",
        "DK",
        "FI",
        "BE",
        "AT",
        "IE",
        "CZ",
        "RO",
        "HU",
        "SK",
        "HR",
        "BG",
        "LT",
        "LV",
        "EE",
        "SI",
        "MT",
        "GR",
        "CY",
        "LU",
        "EU",
        # EEA non-EU but GDPR applies (the UK is split into its own UK GDPR regime)
        "IS",
        "NO",
        "LI",
        "CH",
    }
)

# United Kingdom — UK GDPR + PECR (post-Brexit), enforced by the ICO. Kept
# distinct from the EU framework: different statute names, regulator, and a
# GBP turnover cap (£17.5M / 4%) rather than the EU's €20M.
_UK_COUNTRY_CODES: frozenset[str] = frozenset({"GB", "UK"})
_UK_TLDS: frozenset[str] = frozenset(
    {"uk", "co.uk", "org.uk", "me.uk", "gov.uk", "ac.uk", "ltd.uk", "plc.uk"}
)

# ccTLDs for EU/EEA countries
_EU_TLDS: frozenset[str] = frozenset(
    {
        "eu",
        "de",
        "fr",
        "es",
        "it",
        "nl",
        "pl",
        "pt",
        "se",
        "dk",
        "fi",
        "be",
        "at",
        "ie",
        "cz",
        "ro",
        "hu",
        "sk",
        "hr",
        "bg",
        "lt",
        "lv",
        "ee",
        "si",
        "mt",
        "gr",
        "cy",
        "lu",
        # EEA (UK ccTLDs are handled separately by _UK_TLDS)
        "is",
        "no",
        "li",
        "ch",
    }
)

_CA_TLDS: frozenset[str] = frozenset({"ca"})

# Generic commercial TLDs. These indicate "global site" — hreflang tags on
# these pages are typically international shipping markets, not a declaration
# that the site operates under EU jurisdiction. When a test is run from a US
# geolocation (our default: Los Angeles), a .com/.io/.shop site tested against
# CCPA should return "US", not "EU" just because it ships to Germany.
_US_DEFAULT_TLDS: frozenset[str] = frozenset(
    {"com", "net", "org", "io", "co", "us", "store", "shop", "xyz", "app", "ai"}
)

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

_HTML_LANG_RE = re.compile(r"<html[^>]*\slang=[\"']([^\"']+)[\"']", re.IGNORECASE)
_HREFLANG_RE = re.compile(r'hreflang=["\']([^"\']+)["\']', re.IGNORECASE)
_GEO_REGION_RE = re.compile(
    r'<meta[^>]*name=["\']geo\.region["\'][^>]*content=["\']([^"\']+)["\']',
    re.IGNORECASE,
)
_GEO_REGION_ALT_RE = re.compile(
    r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*name=["\']geo\.region["\']',
    re.IGNORECASE,
)
_OG_LOCALE_RE = re.compile(
    r'<meta[^>]*property=["\']og:locale["\'][^>]*content=["\']([^"\']+)["\']',
    re.IGNORECASE,
)
_OG_LOCALE_ALT_RE = re.compile(
    r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*property=["\']og:locale["\']',
    re.IGNORECASE,
)

# Canadian site-IDENTITY markers — used ONLY as a France-vs-Quebec tiebreaker,
# and ONLY on a page whose declared language is French (see the gate in
# detect_jurisdiction). Hydro-Québec (hydroquebec.com) is the canonical case the
# old "lang='fr' → EU" rule got wrong.
#
# Deliberately EXCLUDES:
#  - bare English city names ("Toronto", "Edmonton", ...) and bare
#    "Canada"/"Canadian" — editorial content on global news sites, not site
#    identity (was flipping UK/US news sites to CA).
#  - a Canadian postal-code regex — under IGNORECASE the A1A-1A1 shape matched
#    hex fragments in CSS/asset hashes (e.g. ".../537a5b7a0167d5a8.css"),
#    producing 100+ false hits on a single news page. It is also redundant: a
#    real Quebec address is accompanied by "Québec"/"Montréal".
# Kept signals are proper-noun / legal-text identity markers that appear in a
# site's own chrome and privacy policy, not its news copy.
_CANADIAN_CONTENT_RE = re.compile(
    r"(qu[ée]bec|montr[ée]al|hydro[\s-]qu[ée]bec|"
    r"commission d.acc[èe]s|\bloi\s*25\b|\blaw\s*25\b|\bpipeda\b)",
    re.IGNORECASE,
)


def _canadian_content_signal(html: str) -> bool:
    """Returns True if HTML has Canadian/Quebec site-identity markers.

    Caller MUST gate this behind `_french_language_signal`: it exists only to
    separate a French-Quebec site (CA) from a French-France site (EU). On an
    English page there is no such ambiguity, so running it there only invites
    false positives from editorial mentions of Canada.
    """
    if not html:
        return False
    return bool(_CANADIAN_CONTENT_RE.search(html))


def _french_language_signal(html: str) -> bool:
    """True if the page's DECLARED primary language is French (html lang /
    og:locale). Intentionally ignores hreflang: an international news site links
    French editions via hreflang without being a French-language site itself.

    Gates the France-vs-Quebec content tiebreaker so it runs only where the
    ambiguity actually exists. An en-GB / en-US site (bbc.com, cnn.com) is never
    subject to the Canadian-content check.
    """
    if not html:
        return False
    m = _HTML_LANG_RE.search(html)
    if m and m.group(1).lower().split("-")[0] == "fr":
        return True
    m = _OG_LOCALE_RE.search(html) or _OG_LOCALE_ALT_RE.search(html)
    return bool(m and m.group(1).lower().replace("-", "_").split("_")[0] == "fr")


# ---------------------------------------------------------------------------
# Signal extractors
# ---------------------------------------------------------------------------


def _lang_signals(html: str) -> tuple[bool, bool]:
    """Return (is_eu, is_ca) from <html lang="..."> attribute."""
    match = _HTML_LANG_RE.search(html)
    if not match:
        return False, False
    lang = match.group(1).lower()
    parts = lang.split("-")
    primary = parts[0]
    # BCP 47: script subtag is 4 chars (e.g. "Hant"), region is 2 chars — take last 2-char subtag
    country = ""
    for part in parts[1:]:
        if len(part) == 2:
            country = part.upper()
    is_eu = primary in _EU_LANG_CODES or country in _EU_COUNTRY_CODES
    is_ca = country == "CA"
    return is_eu, is_ca


def _hreflang_signals(html: str) -> tuple[bool, bool]:
    """Return (is_eu, is_ca) from hreflang link tags."""
    is_eu = False
    is_ca = False
    for match in _HREFLANG_RE.finditer(html):
        val = match.group(1).lower()
        if val == "x-default":
            continue
        parts = val.split("-")
        primary = parts[0]
        # BCP 47: take last 2-char subtag as region
        country = ""
        for part in parts[1:]:
            if len(part) == 2:
                country = part.upper()
        if primary in _EU_LANG_CODES or country in _EU_COUNTRY_CODES:
            is_eu = True
        if country == "CA":
            is_ca = True
    return is_eu, is_ca


def _geo_region_signals(html: str) -> tuple[bool, bool]:
    """Return (is_eu, is_ca) from geo.region meta tag."""
    match = _GEO_REGION_RE.search(html) or _GEO_REGION_ALT_RE.search(html)
    if not match:
        return False, False
    region = match.group(1).upper()
    # Format: "US", "US-CA", "DE", "GB"
    country = region.split("-")[0]
    is_eu = country in _EU_COUNTRY_CODES
    is_ca = country == "CA"
    return is_eu, is_ca


def _og_locale_signals(html: str) -> tuple[bool, bool]:
    """Return (is_eu, is_ca) from og:locale meta tag."""
    match = _OG_LOCALE_RE.search(html) or _OG_LOCALE_ALT_RE.search(html)
    if not match:
        return False, False
    locale = match.group(1)  # e.g. "fr_FR", "en_US", "en_CA"
    parts = locale.replace("-", "_").split("_")
    country = parts[1].upper() if len(parts) > 1 else ""
    lang = parts[0].lower()
    is_eu = lang in _EU_LANG_CODES or country in _EU_COUNTRY_CODES
    is_ca = country == "CA"
    return is_eu, is_ca


def _tld_signals(url: str) -> tuple[bool, bool]:
    """Return (is_eu, is_ca) from URL TLD via tldextract."""
    if not url:
        return False, False
    ext = _TLD_EXTRACT(url)
    suffix = ext.suffix.lower()  # e.g. "co.uk", "de", "ca", "com"
    is_eu = suffix in _EU_TLDS
    is_ca = suffix in _CA_TLDS
    return is_eu, is_ca


def _uk_signals(page_html: str, url: str) -> bool:
    """Return True if the site declares a UK identity (.uk TLD or a GB region).

    Site-intrinsic only (TLD, html-lang country subtag, og:locale, geo.region) —
    never the scanner's IP. Routes GB sites to the UK GDPR / PECR regime instead
    of folding them into the EU framework.
    """
    if url and _TLD_EXTRACT(url).suffix.lower() in _UK_TLDS:
        return True
    m = _HTML_LANG_RE.search(page_html)
    if m and any(p.upper() == "GB" for p in m.group(1).lower().split("-")[1:]):
        return True
    m = _OG_LOCALE_RE.search(page_html) or _OG_LOCALE_ALT_RE.search(page_html)
    if m:
        parts = m.group(1).replace("-", "_").split("_")
        if len(parts) > 1 and parts[1].upper() == "GB":
            return True
    m = _GEO_REGION_RE.search(page_html) or _GEO_REGION_ALT_RE.search(page_html)
    return bool(m and m.group(1).upper().split("-")[0] == "GB")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def detect_jurisdiction(page_html: str, url: str) -> str:
    """Detect regulatory jurisdiction from page HTML and URL.

    TLD wins first: a clearly EU ccTLD (.de, .fr, .eu, .co.uk) returns EU,
    .ca returns CA, and a generic US-default commercial TLD (.com, .io, etc.)
    returns US directly. Content signals (hreflang, lang, geo.region) are used
    only when the TLD is ambiguous — this prevents international shipping
    hreflang tags on a .com site from flipping the verdict to EU when the
    site is actually being tested under CCPA.

    Args:
        page_html: Raw HTML of the audited page (may be empty string).
        url: The audited URL (used for TLD heuristic).

    Returns:
        "EU" | "CA" | "US"
    """
    # 1. TLD takes precedence when it is an unambiguous regional signal.
    ext = _TLD_EXTRACT(url) if url else None
    suffix = ext.suffix.lower() if ext else ""

    if suffix in _UK_TLDS:
        return "UK"
    if suffix in _EU_TLDS:
        return "EU"
    if suffix in _CA_TLDS:
        return "CA"

    # 2. Generic TLD (.com / .io / .net / …). Don't default to US blindly —
    #    honor explicit developer-set signals first. og:locale, html-lang with
    #    country subtag, and geo.region are intentionally declared markers
    #    (set by the developer, not by a CDN shipping list), so they're
    #    treated as STRONG signals. hreflang tags are weaker (often
    #    international-shipping noise on a US-primary .com) and skipped here.
    #    Tesco.com (UK retailer on .com) is the canonical case the old
    #    "return US immediately on generic TLD" rule got wrong.
    if suffix in _US_DEFAULT_TLDS:
        # A .com site that declares a GB region (og:locale en_GB, lang="en-GB",
        # geo.region GB) is a UK site on a generic TLD (e.g. bbc.com) -> UK GDPR.
        if _uk_signals(page_html, url):
            return "UK"
        # Check CA before EU when both signals fire: a Quebec French page
        # (lang="fr-CA") trips is_eu=True via the "fr" primary lang code AND
        # is_ca=True via the country subtag. The country tag is more specific,
        # so CA wins.
        any_eu = False
        for fn in (_og_locale_signals, _lang_signals, _geo_region_signals):
            is_eu, is_ca = fn(page_html)
            if is_ca:
                return "CA"
            any_eu = any_eu or is_eu
        if any_eu:
            # France-vs-Quebec disambiguation — ONLY when the page's declared
            # language is French. An en-GB / en-US site has no such ambiguity,
            # so it must never be subjected to the Canadian-content check (that
            # is what flipped bbc.com to CA). A French .com page carrying
            # Hydro-Québec / Loi 25 / etc. is Quebec, not France.
            if _french_language_signal(page_html) and _canadian_content_signal(page_html):
                return "CA"
            return "EU"
        return "US"

    # 3. Truly ambiguous TLD — fall back to all content signals (UK and CA
    # before EU; country subtag wins over the primary-lang heuristic).
    if _uk_signals(page_html, url):
        return "UK"
    any_eu = False
    any_ca = False

    for fn in (_lang_signals, _hreflang_signals, _geo_region_signals, _og_locale_signals):
        is_eu, is_ca = fn(page_html)
        any_eu = any_eu or is_eu
        any_ca = any_ca or is_ca

    if any_ca:
        return "CA"
    if any_eu:
        if _french_language_signal(page_html) and _canadian_content_signal(page_html):
            return "CA"
        return "EU"
    return "US"


def country_to_jurisdiction(country_code: str | None) -> str | None:
    """Map a CMP-reported ISO-3166 alpha-2 country code to our jurisdiction enum.

    The CMP's own geolocation (from runtime introspection, e.g. OneTrust's
    GetDomainData geolocation rule) is GROUND TRUTH for which regime the operator
    configured — far more reliable than guessing from page HTML/TLD. Callers should
    prefer this over `detect_jurisdiction` when a CMP geolocation is available.

    Returns "CA" or "EU" for a positive non-US signal, else None. We deliberately
    do NOT return "US": the scan runs from a US IP, so a CMP that geolocates by IP
    may report US even for a site that also operates under EU/CA law — returning
    None lets the HTML/TLD heuristic still surface a non-US regime in that case.
    """
    if not country_code:
        return None
    cc = country_code.strip().upper()
    if cc == "CA":
        return "CA"
    if cc in _UK_COUNTRY_CODES:  # GB/UK -> UK GDPR + PECR (ICO)
        return "UK"
    if cc in _EU_COUNTRY_CODES:  # EU members + EEA
        return "EU"
    return None


def resolve_jurisdiction(explicit_override: str | None, page_html: str, url: str) -> str:
    """Resolve the audit's jurisdiction from SCANNER-INDEPENDENT site signals.

    Precedence: explicit operator override > site-intrinsic detection
    (`detect_jurisdiction`: TLD > declared locale/lang/geo.region > content
    tiebreaker > US default).

    This intentionally does NOT consider the CMP's IP-based geolocation
    (`cmp_runtime_config.geolocation_country`). That value reflects where the
    SCAN is executed from (the visitor), not the audited site's market — so a
    scan run from a Canadian IP was stamping Canadian law (Quebec Law 25) onto
    US and UK sites. CMP geolocation is kept as captured evidence, but the
    jurisdiction verdict must be reproducible regardless of scan location, so it
    is derived only from signals the SITE itself declares. `country_to_jurisdiction`
    remains available for callers that have a trustworthy, site-scoped country.
    """
    if explicit_override:
        return explicit_override
    return detect_jurisdiction(page_html or "", url)


# ---------------------------------------------------------------------------
# Jurisdiction-aware copy (single source of truth for regime-specific prose)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class JurisdictionCopy:
    """Regime-specific phrasing reused across the report, deck, and action items.

    Centralising this keeps GPC's legal status, the regulator name, the manual-
    repro vantage, and pixel-evidence framing correct per jurisdiction in ONE
    place, instead of scattering hardcoded "Under CCPA/CPRA..." sentences (which
    rendered on EU/UK/CA reports).
    """

    statute: str  # short regime label for inline prose
    regulator: str  # enforcement body
    vpn_label: str  # geolocation vantage for manual reproduction
    gpc_legal: str  # GPC legal-status sentence
    pixel_evidence: str  # framing for "pixels fired post-denial"


_US_COPY = JurisdictionCopy(
    statute="CCPA/CPRA",
    regulator="California's CPPA",
    vpn_label="California",
    gpc_legal=(
        "Under CCPA/CPRA, GPC is a legally binding opt-out signal. California's CPPA has "
        "stated GPC non-compliance is enforceable without prior notice."
    ),
    pixel_evidence=(
        "Each request is independent forensic evidence, the same pattern plaintiff law firms "
        "source for CIPA/CCPA claims."
    ),
)
_EU_COPY = JurisdictionCopy(
    statute="GDPR / ePrivacy",
    regulator="the relevant EU data-protection authority",
    vpn_label="European",
    gpc_legal=(
        "Under the GDPR consent must be opt-in, so GPC is not itself a binding opt-out signal. "
        "Tracking that continues after a privacy signal is asserted still shows the consent "
        "banner is not enforcing the user's choice."
    ),
    pixel_evidence=(
        "Each request is personal data disclosed without a valid legal basis, the kind of "
        "transfer a GDPR / ePrivacy assessment would examine."
    ),
)
_UK_COPY = JurisdictionCopy(
    statute="UK GDPR / PECR",
    regulator="the ICO",
    vpn_label="UK",
    gpc_legal=(
        "Under UK GDPR and PECR consent must be opt-in, so GPC is not itself a binding opt-out "
        "signal. Tracking that continues after a privacy signal is asserted still shows the "
        "consent banner is not enforcing the user's choice."
    ),
    pixel_evidence=(
        "Each request is personal data disclosed without a valid legal basis, the kind of "
        "transfer an ICO assessment under UK GDPR / PECR would examine."
    ),
)
_CA_COPY = JurisdictionCopy(
    statute="Quebec Law 25 / PIPEDA",
    regulator="the Commission d'accès à l'information / OPC",
    vpn_label="Canadian",
    gpc_legal=(
        "GPC is not yet a binding opt-out signal under Quebec Law 25 or PIPEDA, but tracking "
        "that continues after a privacy signal is asserted shows the consent banner is not "
        "enforcing the user's choice."
    ),
    pixel_evidence=(
        "Each request is a disclosure a Quebec Law 25 / PIPEDA assessment would examine as "
        "data shared without valid consent."
    ),
)
_JURISDICTION_COPY: dict[str, JurisdictionCopy] = {
    "US": _US_COPY,
    "EU": _EU_COPY,
    "UK": _UK_COPY,
    "CA": _CA_COPY,
}


def jurisdiction_copy(jurisdiction: str | None) -> JurisdictionCopy:
    """Return regime-specific phrasing; defaults to US when unknown."""
    return _JURISDICTION_COPY.get((jurisdiction or "US").upper(), _US_COPY)
