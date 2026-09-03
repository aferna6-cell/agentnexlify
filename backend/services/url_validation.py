"""Shared URL-safety helpers to prevent SSRF.

Used by outbound-HTTP call sites that accept tenant-supplied URLs
(webhooks, website crawling, content ingestion). Resolves the hostname
to protect against DNS rebinding where a public hostname returns a
private or loopback IP at request time.

``is_safe_url`` is a pre-check only. A later ``httpx``/OS DNS lookup can
still flip to a private address (TOCTOU). Callers that open a socket must
use ``ValidatedIPTransport`` so the TCP connect uses only IPs validated
in that same resolve step — never a hostname that will be resolved again.
"""

import ipaddress
import logging
import socket
from urllib.parse import urlparse

import httpcore
import httpx

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


def _unwrap_ip(ip: ipaddress._BaseAddress) -> ipaddress._BaseAddress:
    """Treat IPv4-mapped IPv6 (:ffff:x.x.x.x) as the inner IPv4 address."""
    mapped = getattr(ip, "ipv4_mapped", None)
    return mapped if mapped is not None else ip


def _ip_is_blocked(ip: ipaddress._BaseAddress) -> bool:
    """True for any address that must not be reachable from an outbound fetch."""
    ip = _unwrap_ip(ip)
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local  # 169.254.0.0/16 — cloud metadata lives here
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def safe_connect_ips(hostname: str):
    """Resolve ``hostname`` to public IP strings, or None if it is unsafe.

    Any blocked address in the resolution (including mixed public+private)
    is treated as a rebind and refused. IP literals are validated without DNS.
    """
    hostname = (hostname or "").lower()
    if hostname in _BLOCKED_HOSTNAMES:
        return None
    if hostname.endswith(_BLOCKED_TLDS):
        return None

    try:
        literal = ipaddress.ip_address(hostname)
    except ValueError:
        literal = None
    if literal is not None:
        return None if _ip_is_blocked(literal) else [hostname]

    try:
        resolved = socket.getaddrinfo(hostname, None)
    except (socket.gaierror, UnicodeError, OSError):
        return None

    if not resolved:
        return None

    ips = []
    seen = set()
    for _family, _type, _proto, _canonname, sockaddr in resolved:
        try:
            raw = sockaddr[0].split("%")[0]
            ip = ipaddress.ip_address(raw)
        except (ValueError, IndexError):
            return None
        if _ip_is_blocked(ip):
            return None
        if raw not in seen:
            seen.add(raw)
            ips.append(raw)
    return ips or None


def is_safe_url(url: str) -> bool:
    """Return True if ``url`` is safe for outbound HTTP from a backend service.

    - Scheme must be http or https
    - Hostname must not be in a known blocklist
    - Hostname must resolve to at least one public IP (DNS resolution)
    - No resolved IP may be private, loopback, link-local, or reserved
    - TLD must not be in the internal-only blocklist

    Returns False on any failure. Never raises.

    This does not pin the later TCP connect. Use ``ValidatedIPTransport``
    for any real request so a public-at-check / private-at-connect rebind
    cannot be used as the socket destination.
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return False

    if parsed.scheme not in ("http", "https"):
        return False

    return safe_connect_ips(parsed.hostname or "") is not None


def assert_safe_url(url: str) -> None:
    """Raise ValueError if the URL is unsafe. Used at sync entry points."""
    if not is_safe_url(url):
        raise ValueError(f"Refused unsafe outbound URL: {url!r}")


class ValidatedIPTransport(httpx.HTTPTransport):
    """httpx transport that opens sockets only to SSRF-validated IPs.

    ``connect_ips`` pins destinations from a prior ``safe_connect_ips``
    call (no second hostname lookup). Without it, each TCP connect
    resolves the request host, refuses any blocked address, and connects
    to a remaining public IP. Either way ``socket.create_connection``
    receives an IP literal, not a hostname.
    """

    def __init__(self, connect_ips=None, **kwargs):
        super().__init__(**kwargs)
        pinned = list(connect_ips) if connect_ips else None
        if pinned is not None and not pinned:
            raise ValueError("connect_ips must contain at least one validated IP")
        self._pool._network_backend = _ValidatedIPBackend(pinned)


class _ValidatedIPBackend:
    """httpcore network backend that never connects to an unvalidated host."""

    def __init__(self, connect_ips):
        from httpcore._backends.sync import SyncBackend

        self._inner = SyncBackend()
        self._connect_ips = connect_ips

    def connect_tcp(
        self,
        host,
        port,
        timeout=None,
        local_address=None,
        socket_options=None,
    ):
        ips = self._connect_ips
        if ips is None:
            ips = safe_connect_ips(host if isinstance(host, str) else host.decode())
        if not ips:
            raise httpcore.ConnectError(f"Refused unsafe outbound host: {host!r}")
        last_exc = None
        for ip in ips:
            try:
                return self._inner.connect_tcp(
                    ip,
                    port,
                    timeout=timeout,
                    local_address=local_address,
                    socket_options=socket_options,
                )
            except OSError as exc:
                last_exc = exc
        if last_exc is not None:
            raise last_exc
        raise httpcore.ConnectError(f"Refused unsafe outbound host: {host!r}")

    def __getattr__(self, name):
        return getattr(self._inner, name)
