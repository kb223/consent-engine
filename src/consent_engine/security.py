"""SSRF guard — shared host/URL validation for the audit pipeline.

Two layers of protection:

1. `validate_audit_url(url)` — validates the user-supplied URL *before* the
   browser launches. Rejects non-http(s) schemes and hosts that resolve to
   private / loopback / link-local / reserved / multicast / metadata IPs.

2. `is_blocked_host(host)` — the per-request check the Playwright route guard
   uses for *every* request and redirect the browser makes during the scan.
   The initial-URL check alone is insufficient: a public URL can 30x-redirect
   to an internal IP, or pull a subresource from one. The route guard closes
   that gap by resolving + checking each request host and aborting blocked
   ones.

Set `CONSENT_ENGINE_ALLOW_INTERNAL=1` to bypass both (intended for
self-hosters auditing their own internal staging sites).
"""

from __future__ import annotations

import ipaddress
import os
import socket
from urllib.parse import urlparse

# Cloud metadata endpoints — never legitimate audit targets.
METADATA_HOSTS: frozenset[str] = frozenset(
    {
        "169.254.169.254",  # AWS / GCP / Oracle Cloud IMDSv1
        "fd00:ec2::254",  # AWS IMDSv2 IPv6
        "metadata.google.internal",
        "metadata.azure.com",
        "100.100.100.200",  # Alibaba Cloud
    }
)


def _internal_override() -> bool:
    """True when the operator has opted into scanning internal hosts."""
    return os.environ.get("CONSENT_ENGINE_ALLOW_INTERNAL") == "1"


def _ip_is_blocked(addr: str) -> bool:
    """True if the literal IP address falls in a non-routable / dangerous range."""
    try:
        ip = ipaddress.ip_address(addr)
    except ValueError:
        return False
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def _canonical_ipv4(host: str) -> str | None:
    """Canonical dotted-quad for an IPv4 host given in any legacy/obfuscated form
    a browser URL parser accepts — octal ``0177.0.0.1``, hex ``0x7f000001``,
    dotless ``2130706433`` — or None when `host` is not numeric IPv4 (a real DNS
    name).

    Closes a parser-differential SSRF: ``ipaddress.ip_address("0177.0.0.1")``
    raises (Python rejects leading-zero octal) so the guard's literal-IP branch
    skipped it and DNS resolution didn't canonicalize it either, yet Chromium's
    URL parser turns ``0177.0.0.1`` into ``127.0.0.1`` and connects to loopback.
    We mirror the C/4.3BSD parser (``inet_aton``), which the browser's behavior
    descends from, and only attempt it for plausibly-numeric hosts so DNS names
    are left untouched.
    """
    h = host.lower()
    if not h or any(c not in "0123456789abcdefx." for c in h):
        return None
    try:
        return socket.inet_ntoa(socket.inet_aton(h))
    except OSError:
        return None


def is_blocked_host(host: str | None) -> str | None:
    """Return a human-readable block reason for `host`, or None if allowed.

    Used by the Playwright route guard on every request + redirect. Resolves
    the hostname and checks each resolved address. Designed to fail safe: a
    host that cannot be resolved is allowed through (the browser will fail the
    request itself), but a host that resolves to ANY blocked IP is rejected.
    """
    if _internal_override():
        return None
    if not host:
        return None
    h = host.lower()
    if h in METADATA_HOSTS:
        return f"cloud-metadata host {host}"
    # Obfuscated IPv4 (octal / hex / dotless) — canonicalize the way the browser
    # does before classifying, so 0177.0.0.1 etc. can't slip past as a "hostname".
    canon = _canonical_ipv4(h)
    if canon is not None:
        if _ip_is_blocked(canon):
            return f"internal/private IP {canon} (from {host})"
        return None
    # Literal IP in the host position — check directly without DNS.
    try:
        ipaddress.ip_address(h)
        if _ip_is_blocked(h):
            return f"internal/private IP {host}"
        return None
    except ValueError:
        pass  # not a literal IP; resolve below
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return None  # unresolvable — let the browser handle it
    for info in infos:
        addr = str(info[4][0])
        if _ip_is_blocked(addr):
            return f"internal/private IP {addr} (for host {host})"
    return None


def validate_audit_url(url: str) -> None:
    """Validate the user-supplied audit URL. Raises ValueError if unsafe.

    Closes the high-severity SSRF surface from the v0.5.0 security audit:
    without this, `consent-engine audit http://169.254.169.254/` would hit
    cloud metadata in a real Chromium browser, and the same surface is
    reachable via the FastAPI `POST /audit` route.
    """
    if _internal_override():
        return
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(
            f"Only http/https URLs allowed; got scheme {parsed.scheme!r}. "
            "file:// / chrome:// / etc are rejected to prevent local file disclosure."
        )
    host = parsed.hostname
    if host is None:
        raise ValueError(f"URL is missing a hostname: {url!r}")
    if host.lower() in METADATA_HOSTS:
        raise ValueError(
            f"Refusing to scan known cloud-metadata host: {host}. "
            "Set CONSENT_ENGINE_ALLOW_INTERNAL=1 to override."
        )
    # Obfuscated IPv4 (octal / hex / dotless) — canonicalize like the browser
    # before DNS, so http://0177.0.0.1/ (= 127.0.0.1) can't bypass the guard.
    canon = _canonical_ipv4(host.lower())
    if canon is not None and _ip_is_blocked(canon):
        raise ValueError(
            f"Refusing to scan internal/private IP {canon} (from host {host!r}). "
            "Set CONSENT_ENGINE_ALLOW_INTERNAL=1 to override."
        )
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as e:
        raise ValueError(f"Cannot resolve hostname {host!r}: {e}") from e
    for info in infos:
        addr = str(info[4][0])
        if _ip_is_blocked(addr):
            raise ValueError(
                f"Refusing to scan internal/private IP {addr} (for host {host!r}). "
                "Set CONSENT_ENGINE_ALLOW_INTERNAL=1 to override."
            )


__all__ = ["METADATA_HOSTS", "is_blocked_host", "validate_audit_url"]
