"""Request domains are for citations only and must not change vendor attribution."""

from __future__ import annotations

from consent_engine.tools.tool_05_vendor_library import lookup_vendor, vendor_request_domains


def test_known_vendor_has_request_domains():
    assert "google-analytics.com" in vendor_request_domains("Google Analytics")


def test_unknown_vendor_has_no_request_domains():
    assert vendor_request_domains("Acme Ads") == []


def test_request_domains_do_not_reach_vendor_lookup():
    assert lookup_vendor("piano.io") is None
