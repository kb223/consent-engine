"""Regression tests: CMP detection prefers the specific CMP over generic
base-layer globals.

Truyo and CookiePro are built on OneTrust infrastructure and commonly load
OneTrust's cookielaw.org CDN alongside their own. The old first-match logic
(OneTrust is rule 0) mislabeled those sites as OneTrust. Detection must now
demote the generic base-layer match when a specific CMP co-matches.
"""

from __future__ import annotations

from consent_engine.tools.cmp_detector import _match_cmp_urls


def test_truyo_url_beats_onetrust_cdn() -> None:
    reqs = [
        "https://cdn.cookielaw.org/scripttemplates/otSDKStub.js",
        "https://cmp.truyo.com/cmp.js",
    ]
    assert _match_cmp_urls(reqs) == "Truyo"


def test_truyo_url_beats_onetrust_regardless_of_order() -> None:
    reqs = [
        "https://cmp.truyo.com/cmp.js",
        "https://cdn.cookielaw.org/consent/abc/otSDKStub.js",
    ]
    assert _match_cmp_urls(reqs) == "Truyo"


def test_onetrust_alone_still_detected() -> None:
    reqs = ["https://cdn.cookielaw.org/scripttemplates/otSDKStub.js"]
    assert _match_cmp_urls(reqs) == "OneTrust"


def test_no_cmp_urls_returns_none() -> None:
    assert _match_cmp_urls(["https://example.com/app.js", "https://cdn.x/y.js"]) is None
