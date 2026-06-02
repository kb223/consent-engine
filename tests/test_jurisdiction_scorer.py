"""Weighted jurisdiction content-scorer + confidence (v0.6.11).

The scorer replaced the precedence cascade for generic (non-ccTLD) domains.
test_jurisdiction_detection.py pins the behavioral spec the scorer must
preserve; this file pins the NEW capabilities:
  - a confidence flag (high when a strong declared/operator/TLD signal decided
    it, low for a bare US default or a weak-only inference)
  - US-declared locales count as high-confidence US
  - weak signals (currency, regulator mention) only CORROBORATE: no single weak
    signal flips the US baseline on its own.
"""

from __future__ import annotations

from consent_engine.tools.jurisdiction_detector import (
    detect_jurisdiction,
    detect_jurisdiction_with_confidence,
    resolve_jurisdiction_with_confidence,
)

# --- confidence flag ---------------------------------------------------------


def test_country_tld_is_high_confidence() -> None:
    for url, exp in [("https://x.co.uk", "UK"), ("https://x.de", "EU"), ("https://x.ca", "CA")]:
        assert detect_jurisdiction_with_confidence("<html></html>", url) == (exp, "high")


def test_bare_generic_tld_is_us_low_confidence() -> None:
    juris, conf = detect_jurisdiction_with_confidence(
        "<html><body>Hello</body></html>", "https://x.com"
    )
    assert juris == "US"
    assert conf == "low"


def test_declared_us_locale_is_high_confidence() -> None:
    assert detect_jurisdiction_with_confidence(
        '<html lang="en-US"><body>News</body></html>', "https://cnn.com"
    ) == ("US", "high")


def test_non_eu_country_subtag_narrows_ambiguous_language() -> None:
    # Spanish, Portuguese, and French primary-language tags are EU signals only
    # when no non-EU country subtag is present. A generic Latin American or
    # Canadian localized page must not become EU on language alone.
    assert detect_jurisdiction_with_confidence(
        '<html lang="es-MX"><body>Noticias</body></html>', "https://news.com"
    ) == ("US", "low")
    assert detect_jurisdiction_with_confidence(
        '<html><head><meta property="og:locale" content="pt_BR"></head></html>',
        "https://shop.com",
    ) == ("US", "low")
    assert detect_jurisdiction_with_confidence(
        '<html lang="fr-CA"><body>Bonjour</body></html>', "https://brand.com"
    ) == ("CA", "high")


def test_operator_identity_is_high_confidence() -> None:
    assert detect_jurisdiction_with_confidence(
        "<html><body>Acme GmbH</body></html>", "https://acme.com"
    ) == ("EU", "high")


def test_conflicting_strong_signals_lower_confidence() -> None:
    # A US-localized page with an EU operator is a real ambiguity. Keep the
    # deterministic winner, but do not present the jurisdiction as high confidence.
    assert detect_jurisdiction_with_confidence(
        '<html lang="en-US"><body>Acme GmbH, Berlin</body></html>',
        "https://acme.com",
    ) == ("US", "low")


# --- weak signals only corroborate (never flip US alone) ---------------------


def test_currency_alone_does_not_flip_us() -> None:
    # A US store quoting EUR for shipping must not become EU on the symbol alone.
    assert detect_jurisdiction(
        "<html><body>Ships to the EU from EUR 49 (€49)</body></html>", "https://shop.com"
    ) == "US"


def test_single_regulator_mention_does_not_flip_us() -> None:
    # One CNIL mention (e.g. a global privacy policy) ties the US baseline; the
    # tie resolves to US (conservative).
    assert detect_jurisdiction(
        "<html><body>See our CNIL filing for details.</body></html>", "https://x.com"
    ) == "US"


def test_corroborating_weak_signals_flip_to_eu_low_confidence() -> None:
    # Currency + regulator together clear the US baseline -> EU, but low
    # confidence because no strong declared/operator signal fired.
    juris, conf = detect_jurisdiction_with_confidence(
        "<html><body>Prix: €49. Voir la CNIL. Datenschutz-Hinweis.</body></html>",
        "https://x.com",
    )
    assert juris == "EU"
    assert conf == "low"


def test_strong_signal_beats_weak_us_baseline() -> None:
    assert detect_jurisdiction_with_confidence(
        '<html><head><meta property="og:locale" content="de_DE"></head><body>x</body></html>',
        "https://x.com",
    ) == ("EU", "high")


# --- resolve wrapper ---------------------------------------------------------


def test_resolve_with_confidence_override_is_high() -> None:
    assert resolve_jurisdiction_with_confidence(
        "CA", "<html lang='en-US'></html>", "https://x.com"
    ) == ("CA", "high")


def test_resolve_with_confidence_falls_through_to_scorer() -> None:
    assert resolve_jurisdiction_with_confidence(
        None, "<html lang='en-US'></html>", "https://x.com"
    ) == ("US", "high")
