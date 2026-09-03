"""Shared URL-safety helpers to prevent SSRF.

Used by outbound-HTTP call sites that accept tenant-supplied URLs
(webhooks, website crawling, content ingestion). Resolves the hostname
to protect against DNS rebinding where a public hostname returns a
private or loopback IP at request time.

Website-connect fetch goes further: it pins the validated IP and connects
to that address with the original Host/SNI so a public-at-check name
cannot rebind to a private address at connect time.
"""

from dataclasses import dataclass
import ipaddress
import logging
import socket
from urllib.parse import urlparse, urlunparse

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


@dataclass(frozen=True)
class PinnedTarget:
    """A URL that has been resolved and validated for a pinned-IP connect.

    ``connect_url`` replaces the hostname with the validated IP so the TCP
    connect cannot re-resolve. Callers must send ``host_header`` and
    ``sni_hostname`` so virtual hosts and TLS still see the original name.
    """

    url: str
    connect_url: str
    hostname: str
    ip: str
    host_header: str
    sni_hostname: str


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


def _parse_http_url(url: str):
    try:
        parsed = urlparse(url)
    except Exception:
        return None
    if parsed.scheme not in ("http", "https"):
        return None
    hostname = (parsed.hostname or "").lower()
    if not hostname or hostname in _BLOCKED_HOSTNAMES:
        return None
    if hostname.endswith(_BLOCKED_TLDS):
        return None
    return parsed


def _resolved_public_ips(hostname: str) -> list[str] | None:
    """Return every resolved IP if all are public. None if unsafe/unresolvable."""
    try:
        literal = ipaddress.ip_address(hostname)
    except ValueError:
        literal = None
    if literal is not None:
        return None if _ip_is_blocked(literal) else [str(literal).split("%")[0]]

    try:
        resolved = socket.getaddrinfo(hostname, None)
    except (socket.gaierror, UnicodeError, OSError):
        return None
    if not resolved:
        return None

    ips: list[str] = []
    for _family, _type, _proto, _canonname, sockaddr in resolved:
        try:
            # Strip IPv6 scope id (e.g. fe80::1%eth0) before parsing.
            ip_text = sockaddr[0].split("%")[0]
            ip = ipaddress.ip_address(ip_text)
        except (ValueError, IndexError):
            return None
        if _ip_is_blocked(ip):
            return None
        ips.append(ip_text)
    return ips or None


def _ip_netloc(ip: str, port: int | None) -> str:
    host = f"[{ip}]" if ":" in ip else ip
    return f"{host}:{port}" if port else host


def _host_header(hostname: str, port: int | None) -> str:
    host = f"[{hostname}]" if ":" in hostname else hostname
    return f"{host}:{port}" if port else host


def pin_safe_url(url: str) -> PinnedTarget | None:
    """Resolve ``url`` once and return a connect-to-IP target if it is public.

    Returns None on any failure. Never raises. The first validated public IP
    is pinned so a later DNS answer cannot steer the TCP connect private.
    """
    parsed = _parse_http_url(url)
    if parsed is None:
        return None
    hostname = (parsed.hostname or "").lower()
    ips = _resolved_public_ips(hostname)
    if not ips:
        return None
    ip = ips[0]
    connect_url = urlunparse((
        parsed.scheme,
        _ip_netloc(ip, parsed.port),
        parsed.path,
        parsed.params,
        parsed.query,
        "",
    ))
    return PinnedTarget(
        url=url,
        connect_url=connect_url,
        hostname=hostname,
        ip=ip,
        host_header=_host_header(hostname, parsed.port),
        sni_hostname=hostname,
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
    return pin_safe_url(url) is not None


def assert_safe_url(url: str) -> None:
    """Raise ValueError if the URL is unsafe. Used at sync entry points."""
    if not is_safe_url(url):
        raise ValueError(f"Refused unsafe outbound URL: {url!r}")
