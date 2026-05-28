"""Unit tests for the SSRF guard (consent_engine.security).

Placed at the tests/ root (not tests/tools/) so the tools-conftest autouse
fixture that sets CONSENT_ENGINE_ALLOW_INTERNAL=1 does not apply here. Each
test explicitly clears the override via monkeypatch so the guard is active.
"""

from __future__ import annotations

import pytest

from consent_engine.security import is_blocked_host, validate_audit_url


@pytest.fixture(autouse=True)
def _guard_active(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure the SSRF guard is NOT disabled for these tests."""
    monkeypatch.delenv("CONSENT_ENGINE_ALLOW_INTERNAL", raising=False)


# --- validate_audit_url (initial-URL check) -------------------------------


def test_rejects_cloud_metadata_host() -> None:
    with pytest.raises(ValueError, match="metadata"):
        validate_audit_url("http://169.254.169.254/latest/meta-data/")


def test_rejects_gcp_metadata_hostname() -> None:
    with pytest.raises(ValueError, match="metadata"):
        validate_audit_url("http://metadata.google.internal/")


def test_rejects_loopback() -> None:
    with pytest.raises(ValueError, match="internal/private"):
        validate_audit_url("http://127.0.0.1:8080/")


def test_rejects_non_http_scheme() -> None:
    with pytest.raises(ValueError, match="http"):
        validate_audit_url("file:///etc/passwd")


def test_rejects_missing_hostname() -> None:
    with pytest.raises(ValueError):
        validate_audit_url("http:///no-host")


def test_allows_public_host() -> None:
    # example.com resolves to public IPs — must not raise.
    validate_audit_url("https://example.com/")


# --- is_blocked_host (per-request route-guard check) ----------------------


def test_is_blocked_host_loopback_literal() -> None:
    assert is_blocked_host("127.0.0.1") is not None


def test_is_blocked_host_private_literal() -> None:
    assert is_blocked_host("10.0.0.5") is not None
    assert is_blocked_host("192.168.1.1") is not None
    assert is_blocked_host("172.16.0.1") is not None


def test_is_blocked_host_link_local_metadata() -> None:
    assert is_blocked_host("169.254.169.254") is not None


def test_is_blocked_host_allows_public_ip() -> None:
    assert is_blocked_host("8.8.8.8") is None


def test_is_blocked_host_none_and_empty() -> None:
    assert is_blocked_host(None) is None
    assert is_blocked_host("") is None


def test_override_disables_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONSENT_ENGINE_ALLOW_INTERNAL", "1")
    # With the override on, even loopback is allowed (self-hoster use case).
    assert is_blocked_host("127.0.0.1") is None
    validate_audit_url("http://127.0.0.1:8080/")  # must not raise


# --- obfuscated IPv4 (parser-differential bypass) -------------------------


def test_is_blocked_host_octal_loopback() -> None:
    # ipaddress.ip_address rejects leading-zero octal, but Chromium canonicalizes
    # 0177.0.0.1 -> 127.0.0.1 and connects. The guard must block it.
    assert is_blocked_host("0177.0.0.1") is not None


def test_is_blocked_host_hex_and_dotless_loopback() -> None:
    assert is_blocked_host("0x7f000001") is not None  # hex 127.0.0.1
    assert is_blocked_host("2130706433") is not None  # dotless 127.0.0.1


def test_is_blocked_host_octal_metadata() -> None:
    # 0251.0376.0251.0376 == 169.254.169.254 (link-local / cloud metadata).
    assert is_blocked_host("0251.0376.0251.0376") is not None


def test_validate_rejects_octal_and_dotless() -> None:
    with pytest.raises(ValueError):
        validate_audit_url("http://0177.0.0.1/")
    with pytest.raises(ValueError):
        validate_audit_url("http://2130706433/")


# --- IPv6 ------------------------------------------------------------------


def test_is_blocked_host_ipv6_loopback() -> None:
    assert is_blocked_host("::1") is not None


def test_is_blocked_host_ipv6_ula_and_metadata() -> None:
    assert is_blocked_host("fc00::1") is not None  # unique-local (private)
    assert is_blocked_host("fd00:ec2::254") is not None  # AWS IMDSv2 metadata


def test_is_blocked_host_allows_public_ipv6() -> None:
    assert is_blocked_host("2001:4860:4860::8888") is None  # Google public DNS
