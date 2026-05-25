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

import tldextract

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
        # EEA non-EU but GDPR applies
        "GB",
        "IS",
        "NO",
        "LI",
        "CH",
    }
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
        # UK/EEA
        "uk",
        "is",
        "no",
        "li",
        "ch",
        # Common second-level domains for EU countries
        "co.uk",
        "org.uk",
        "me.uk",
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

# Quebec/Canadian content markers. Used to disambiguate the "lang='fr' on .com"
# case — a French-language site on a generic TLD is otherwise indistinguishable
# from a France site by the lang-signal alone. Hydro-Québec (hydroquebec.com) is
# the canonical case the old "lang='fr' → EU" rule got wrong.
_CANADIAN_CONTENT_RE = re.compile(
    r"(qu[ée]bec|montr[ée]al|hydro[\s-]qu[ée]bec|ottawa|toronto|vancouver|"
    r"calgary|edmonton|winnipeg|halifax|"
    r"commission d.acc[èe]s|loi\s*25|law\s*25|pipeda|"
    r"\bcanad(?:a|ian|ienne?)\b|"
    r"[A-Z]\d[A-Z][\s-]?\d[A-Z]\d)",  # Canadian postal code (A1A 1A1)
    re.IGNORECASE,
)


def _canadian_content_signal(html: str) -> bool:
    """Heuristic: returns True if HTML has Canadian/Quebec content markers.

    Conservative signal — only checked when other signals are ambiguous (e.g.
    lang='fr' without country subtag on a .com domain). A French-language site
    that mentions "Québec", "Montréal", a Canadian postal code, or Loi 25 is
    almost certainly Canadian, not French. Examples this catches that the old
    logic missed: hydroquebec.com, desjardins.com (when on .com), banque-laurentienne.com.
    """
    if not html:
        return False
    return bool(_CANADIAN_CONTENT_RE.search(html))


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
    ext = tldextract.extract(url)
    suffix = ext.suffix.lower()  # e.g. "co.uk", "de", "ca", "com"
    is_eu = suffix in _EU_TLDS
    is_ca = suffix in _CA_TLDS
    return is_eu, is_ca


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
    ext = tldextract.extract(url) if url else None
    suffix = ext.suffix.lower() if ext else ""

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
            # Last-ditch Quebec disambiguation: a French-language signal on a
            # .com is ambiguous (France vs Quebec). Promote to CA if the page
            # body contains Canadian markers (Hydro-Québec, Loi 25, postal
            # codes, named Canadian cities, etc.). Defaults to EU otherwise.
            if _canadian_content_signal(page_html):
                return "CA"
            return "EU"
        return "US"

    # 3. Truly ambiguous TLD — fall back to all content signals (CA before EU,
    # same precedence rule: country subtag wins over primary-lang heuristic).
    any_eu = False
    any_ca = False

    for fn in (_lang_signals, _hreflang_signals, _geo_region_signals, _og_locale_signals):
        is_eu, is_ca = fn(page_html)
        any_eu = any_eu or is_eu
        any_ca = any_ca or is_ca

    if any_ca:
        return "CA"
    if any_eu:
        if _canadian_content_signal(page_html):
            return "CA"
        return "EU"
    return "US"
