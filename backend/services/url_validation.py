"""Shared URL-safety helpers to prevent SSRF.

Used by outbound-HTTP call sites that accept tenant-supplied URLs
(webhooks, website crawling, content ingestion). Resolves the hostname
to protect against DNS rebinding where a public hostname returns a
private or loopback IP at request time.
"""

import ipaddress
import logging
import socket
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

_BLOCKED_HOSTNAMES = frozenset({
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "::1",
    "",
})

_BLOCKED_TLDS = (
    ".local",
    ".internal",
    ".lan",
    ".localhost",
)


def is_safe_url(url: str) -> bool:
    """Return True if ``url`` is safe for outbound HTTP from a backend service.

    - Scheme must be http or https
    - Hostname must not be in a known blocklist
    - Hostname must resolve to at least one public IP (DNS resolution)
    - No resolved IP may be private, loopback, link-local, or reserved
    - TLD must not be in the internal-only blocklist

    Returns False on any failure. Never raises.
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return False

    if parsed.scheme not in ("http", "https"):
        return False

    hostname = (parsed.hostname or "").lower()
    if hostname in _BLOCKED_HOSTNAMES:
        return False
    if hostname.endswith(_BLOCKED_TLDS):
        return False

    # Direct IP literals: check without DNS.
    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            return False
        return True
    except ValueError:
        pass  # hostname is a domain — resolve it below

    try:
        resolved = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return False

    for _family, _type, _proto, _canonname, sockaddr in resolved:
        try:
            ip = ipaddress.ip_address(sockaddr[0])
        except (ValueError, IndexError):
            return False
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            return False

    return True


def assert_safe_url(url: str) -> None:
    """Raise ValueError if the URL is unsafe. Used at sync entry points."""
    if not is_safe_url(url):
        raise ValueError(f"Refused unsafe outbound URL: {url!r}")
