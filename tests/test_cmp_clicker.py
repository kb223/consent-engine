"""Unit tests for the pure helpers in cmp_clicker (no Playwright).

Locks the per-CMP reject-click reliability fixes (v0.6.4):
- REJECT_VOCAB recognizes Sourcepoint's "No, thank you" reject label.
- _is_cmp_message_frame identifies CMP message iframes (TrustArc, Sourcepoint)
  so the clicker enters them — Sourcepoint reports dom_type "standard" yet
  renders its banner inside an sp_message_iframe, so iframe entry must not be
  gated on dom_type alone.
"""

from __future__ import annotations

from consent_engine.tools.cmp_clicker import (
    _BANNER_SELECTORS,
    _is_cmp_message_frame,
    _score_node,
)


def test_banner_selectors_exclude_bare_banner_class() -> None:
    # A bare [class*='banner'] matches promo/ad/hero/subscription banners and
    # caused _banner_present to report successful Sourcepoint rejects as
    # 'banner_click_failed'. It must stay out of the consent-banner selectors.
    joined = " ".join(_BANNER_SELECTORS)
    assert "[class*='banner'" not in joined
    # Consent-specific coverage must be present.
    assert any("sp_message_iframe" in s for s in _BANNER_SELECTORS)  # Sourcepoint
    assert any("onetrust-banner-sdk" in s for s in _BANNER_SELECTORS)  # OneTrust
    assert any("cookie" in s for s in _BANNER_SELECTORS)


def test_score_node_recognizes_reject_all() -> None:
    assert _score_node("Reject all") == 2


def test_score_node_recognizes_sourcepoint_no_thank_you() -> None:
    # Guardian / many Sourcepoint banners label reject-all as "No, thank you".
    assert _score_node("No, thank you") > 0


def test_score_node_recognizes_do_not_consent() -> None:
    assert _score_node("Do not consent") > 0


def test_score_node_ignores_accept() -> None:
    assert _score_node("Yes, I accept") == 0
    assert _score_node("Manage cookies") == 0


def test_is_cmp_message_frame_matches_trustarc() -> None:
    assert _is_cmp_message_frame("truste-iframe", "https://consent.truste.com/x")


def test_is_cmp_message_frame_matches_sourcepoint_cname() -> None:
    # Sourcepoint message iframe served from a first-party CNAME.
    assert _is_cmp_message_frame("", "https://sourcepoint.theguardian.com/index.html?id=1")


def test_is_cmp_message_frame_matches_privacy_mgmt() -> None:
    assert _is_cmp_message_frame("", "https://cdn.privacy-mgmt.com/index.html")


def test_is_cmp_message_frame_matches_sp_message_iframe_name() -> None:
    assert _is_cmp_message_frame("sp_message_iframe_1482255", "about:blank")


def test_is_cmp_message_frame_rejects_ad_frames() -> None:
    assert not _is_cmp_message_frame("google_ads_iframe_x", "https://googlesyndication.com/x")
    assert not _is_cmp_message_frame("", "")
    assert not _is_cmp_message_frame("", "https://www.theguardian.com/")
