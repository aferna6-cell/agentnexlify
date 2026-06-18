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


def _ip_is_blocked(ip: ipaddress._BaseAddress) -> bool:
    """True for any address that must not be reachable from an outbound fetch."""
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local  # 169.254.0.0/16 — cloud metadata lives here
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
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
        return not _ip_is_blocked(ipaddress.ip_address(hostname))
    except ValueError:
        pass  # hostname is a domain — resolve it below

    try:
        resolved = socket.getaddrinfo(hostname, None)
    except (socket.gaierror, UnicodeError, OSError):
        return False

    if not resolved:
        return False

    for _family, _type, _proto, _canonname, sockaddr in resolved:
        try:
            # Strip IPv6 scope id (e.g. fe80::1%eth0) before parsing.
            ip = ipaddress.ip_address(sockaddr[0].split("%")[0])
        except (ValueError, IndexError):
            return False
        if _ip_is_blocked(ip):
            return False

    return True


def assert_safe_url(url: str) -> None:
    """Raise ValueError if the URL is unsafe. Used at sync entry points."""
    if not is_safe_url(url):
        raise ValueError(f"Refused unsafe outbound URL: {url!r}")
