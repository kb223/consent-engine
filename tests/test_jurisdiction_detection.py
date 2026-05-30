"""Jurisdiction detection must be SCANNER-INDEPENDENT (v0.6.5).

The verdict must depend only on signals the SITE declares, never on where the
scan runs from. Two real bugs are locked here:

  1. A scan from a Canadian IP made every CMP-geolocated site report Canadian
     law (Quebec Law 25), because the resolver trusted the CMP's IP-based
     geolocation_country (= the scanner's location). resolve_jurisdiction must
     not consider CMP geo at all.
  2. _canadian_content_signal matched bare city names ("Toronto", "Edmonton")
     and a bare "Canada"/"Canadian" mention, so a global news site (bbc.com)
     with a Canadian city in a headline flipped to CA. Editorial content is not
     site identity.
"""

from __future__ import annotations

from consent_engine.tools.jurisdiction_detector import (
    _canadian_content_signal,
    _french_language_signal,
    detect_jurisdiction,
    resolve_jurisdiction,
)

# --- bug #2: editorial content must not flip jurisdiction to CA --------------


def test_uk_news_site_naming_canadian_cities_is_uk_not_ca() -> None:
    # bbc.com: en-GB site whose homepage mentions Canadian cities in headlines.
    # Must resolve UK (en-GB), and crucially NOT CA from the editorial city names.
    html = (
        '<html lang="en-GB"><head><meta property="og:locale" content="en_GB"></head>'
        "<body>Wildfires near Edmonton and Toronto; updates from Vancouver and Calgary."
        "</body></html>"
    )
    assert detect_jurisdiction(html, "https://www.bbc.com") == "UK"


def test_us_site_with_canada_in_headline_stays_us() -> None:
    html = '<html lang="en-US"><body>Canada wildfires spread; Canadian officials respond.</body></html>'
    assert detect_jurisdiction(html, "https://www.cnn.com") == "US"


def test_canadian_content_signal_ignores_bare_city_and_country() -> None:
    assert not _canadian_content_signal("Breaking news from Toronto, Vancouver and Edmonton")
    assert not _canadian_content_signal("Canada and Canadian officials commented today")


def test_canadian_content_signal_keeps_site_identity_markers() -> None:
    assert _canadian_content_signal("Conforme à la Loi 25 du Québec")
    assert _canadian_content_signal("Hydro-Québec, Montréal")
    assert _canadian_content_signal("We comply with PIPEDA")


def test_canadian_content_signal_ignores_hex_asset_hashes() -> None:
    # THE bbc.com bug: under IGNORECASE the old A1A-1A1 postal-code regex matched
    # hex fragments in CSS/asset hashes (e.g. a5b7a0 inside 537a5b7a0167d5a8),
    # producing 100+ false hits and flipping the site to CA.
    asset_html = (
        '<link rel="stylesheet" href="/_next/static/css/537a5b7a0167d5a8.css">'
        '<script src="/static/f92e6ec078-web-3.7.0.js"></script>'
    )
    assert not _canadian_content_signal(asset_html)


def test_french_gate_blocks_canadian_check_on_english_pages() -> None:
    # An English (en-GB) page mentioning Montréal in editorial copy must NOT be
    # CA — the Canadian-content tiebreaker only runs on French-language pages.
    # (en-GB resolves UK; the point here is that it does not flip to CA.)
    english = '<html lang="en-GB"><body>The Montréal Canadiens won; Québec reacts.</body></html>'
    assert detect_jurisdiction(english, "https://www.bbc.com") == "UK"
    # The same markers on a FRENCH page DO resolve CA (the legitimate case).
    french = '<html lang="fr"><body>Les Canadiens de Montréal. Hydro-Québec.</body></html>'
    assert detect_jurisdiction(french, "https://example.com") == "CA"


def test_french_language_signal() -> None:
    assert _french_language_signal('<html lang="fr">')
    assert _french_language_signal('<html lang="fr-CA">')
    assert _french_language_signal('<meta property="og:locale" content="fr_FR">')
    assert not _french_language_signal('<html lang="en-GB">')
    assert not _french_language_signal('<html lang="en-US">')


# --- preserved behavior: genuine Quebec / CA / EU sites ----------------------


def test_quebec_french_com_site_is_ca() -> None:
    html = '<html lang="fr"><body>Hydro-Québec. Conforme à la Loi 25.</body></html>'
    assert detect_jurisdiction(html, "https://www.hydroquebec.com") == "CA"


def test_ca_tld_is_ca() -> None:
    assert detect_jurisdiction("<html></html>", "https://www.canadiantire.ca") == "CA"


def test_eu_tld_is_eu() -> None:
    assert detect_jurisdiction("<html></html>", "https://www.lemonde.fr") == "EU"


# --- UK is its own regime, not folded into EU --------------------------------


def test_uk_cctld_is_uk() -> None:
    assert detect_jurisdiction("<html></html>", "https://www.tesco.co.uk") == "UK"
    assert detect_jurisdiction("<html></html>", "https://example.uk") == "UK"


def test_uk_dotcom_with_en_gb_is_uk() -> None:
    # bbc.com declares en-GB on a generic TLD -> UK, not EU and not US.
    html = '<html lang="en-GB"><head><meta property="og:locale" content="en_GB"></head><body>News</body></html>'
    assert detect_jurisdiction(html, "https://www.bbc.com") == "UK"


def test_fr_tld_still_eu_not_uk() -> None:
    assert detect_jurisdiction('<html lang="fr"></html>', "https://www.lemonde.fr") == "EU"


def test_declared_en_ca_locale_is_ca() -> None:
    html = '<html lang="en-CA"><body>Shop online</body></html>'
    assert detect_jurisdiction(html, "https://shop.example.com") == "CA"


# --- bug #1: resolve_jurisdiction is scanner-independent ----------------------


def test_resolve_jurisdiction_explicit_override_wins() -> None:
    assert resolve_jurisdiction("EU", "<html lang='en-US'></html>", "https://www.cnn.com") == "EU"


def test_resolve_jurisdiction_us_site_resolves_us_regardless_of_scan_location() -> None:
    # No CMP geolocation parameter exists on resolve_jurisdiction by design — the
    # scanner's location cannot leak in. A US site resolves US even though this
    # very scan runs from a Canadian IP (which the CMP would report as "CA").
    html = '<html lang="en-US"><head><meta property="og:locale" content="en_US"></head><body>News</body></html>'
    assert resolve_jurisdiction(None, html, "https://www.cnn.com") == "US"


def test_resolve_jurisdiction_signature_excludes_cmp_geo() -> None:
    # Structural guarantee: if someone re-adds a CMP-geo argument, this fails.
    import inspect

    params = list(inspect.signature(resolve_jurisdiction).parameters)
    assert params == ["explicit_override", "page_html", "url"]


def test_jurisdiction_lists_stay_in_sync() -> None:
    # Self-anneal: the CLI --jurisdiction choices, the copy helper, and the
    # exposure framework must all cover exactly SUPPORTED_JURISDICTIONS. v0.6.7
    # added "UK" everywhere EXCEPT the CLI choices — this guards that bug class.
    from consent_engine.cli import SUPPORTED_JURISDICTIONS as cli_set
    from consent_engine.tools.jurisdiction_detector import (
        _JURISDICTION_COPY,
        SUPPORTED_JURISDICTIONS,
    )
    from consent_engine.tools.tool_08_report_generator import _JURISDICTION_EXPOSURE

    expected = set(SUPPORTED_JURISDICTIONS)
    assert set(cli_set) == expected  # CLI uses the shared constant
    assert set(_JURISDICTION_COPY) == expected  # every regime has phrasing
    assert expected.issubset(set(_JURISDICTION_EXPOSURE))  # and an exposure entry
