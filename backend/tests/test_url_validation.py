"""Tests for the shared SSRF URL guard (backend/services/url_validation.py).

This is the canonical guard used by the website crawler, content repurposer,
webhook dispatcher, instant-KB, and the leadgen enricher.

Contract:
- Only http/https schemes pass.
- localhost, internal-suffix hosts, and literal private/reserved IPs are blocked.
- 169.254.169.254 (cloud metadata) is blocked.
- A hostname that RESOLVES to a private/reserved IP is blocked (DNS-rebind /
  metadata-pivot defense).
- Unresolvable hosts are treated as unsafe.
- assert_safe_url raises on unsafe and is silent on safe.
"""

import ipaddress
import socket
from unittest.mock import patch

import httpcore
import httpx
import pytest

from backend.services.url_validation import (
    ValidatedIPTransport,
    assert_safe_url,
    is_safe_url,
    safe_connect_ips,
)


def _addrinfo(ip):
    # Mirrors socket.getaddrinfo's 5-tuple: (family, type, proto, canon, sockaddr)
    return [(2, 1, 6, "", (ip, 0))]


def test_rejects_non_http_schemes():
    assert is_safe_url("ftp://example.com") is False
    assert is_safe_url("file:///etc/passwd") is False
    assert is_safe_url("gopher://example.com") is False


def test_rejects_localhost_and_loopback_literals():
    assert is_safe_url("http://localhost/admin") is False
    assert is_safe_url("http://127.0.0.1/") is False
    assert is_safe_url("http://0.0.0.0/") is False
    assert is_safe_url("http://[::1]/") is False


def test_rejects_private_literal_ips():
    assert is_safe_url("http://10.0.0.5/") is False
    assert is_safe_url("http://192.168.1.1/") is False
    assert is_safe_url("http://172.16.4.4/") is False


def test_rejects_cloud_metadata_link_local():
    assert is_safe_url("http://169.254.169.254/latest/meta-data/") is False


def test_rejects_ipv6_loopback_link_local_and_mapped_private():
    assert is_safe_url("http://[::1]/") is False
    assert is_safe_url("http://[fe80::1]/") is False
    assert is_safe_url("http://[::ffff:127.0.0.1]/") is False
    assert is_safe_url("http://[::ffff:169.254.169.254]/") is False
    assert is_safe_url("http://[fc00::1]/") is False


def test_rejects_internal_suffixes():
    assert is_safe_url("http://db.internal/") is False
    assert is_safe_url("http://printer.local/") is False
    assert is_safe_url("http://nas.lan/") is False


def test_allows_public_literal_ip():
    # Public literal IP short-circuits before DNS.
    assert is_safe_url("http://8.8.8.8/") is True


def test_resolves_and_allows_public_domain():
    with patch("backend.services.url_validation.socket.getaddrinfo", return_value=_addrinfo("93.184.216.34")):
        assert is_safe_url("https://example.com/") is True


def test_resolves_and_blocks_dns_rebind_to_private_ip():
    # The key case a literal-only guard misses: public-looking host -> internal IP.
    with patch("backend.services.url_validation.socket.getaddrinfo", return_value=_addrinfo("10.0.0.5")):
        assert is_safe_url("https://evil.example.com/") is False


def test_resolves_and_blocks_metadata_pivot():
    with patch("backend.services.url_validation.socket.getaddrinfo", return_value=_addrinfo("169.254.169.254")):
        assert is_safe_url("https://rebind.attacker.com/") is False


def test_unresolvable_host_is_unsafe():
    with patch("backend.services.url_validation.socket.getaddrinfo", side_effect=socket.gaierror):
        assert is_safe_url("https://does-not-resolve.invalid/") is False


def test_assert_safe_url_raises_on_unsafe():
    with pytest.raises(ValueError):
        assert_safe_url("http://169.254.169.254/")


def test_assert_safe_url_silent_on_safe():
    assert assert_safe_url("http://8.8.8.8/") is None


def test_safe_connect_ips_returns_public_literal():
    assert safe_connect_ips("8.8.8.8") == ["8.8.8.8"]


def test_safe_connect_ips_blocks_mapped_loopback():
    assert safe_connect_ips("::ffff:127.0.0.1") is None
    assert safe_connect_ips("::ffff:169.254.169.254") is None


def test_validated_transport_connects_to_check_ip_not_rebound_private(monkeypatch):
    """public-at-check → private-at-connect must not open a private socket."""
    hostname_lookups = []
    connected = []

    def flipping_getaddrinfo(host, port, *args, **kwargs):
        host_s = host.decode() if isinstance(host, bytes) else str(host)
        try:
            ipaddress.ip_address(host_s.split("%")[0])
            family = socket.AF_INET6 if ":" in host_s else socket.AF_INET
            return [(family, socket.SOCK_STREAM, 6, "", (host_s, port or 0))]
        except ValueError:
            pass
        hostname_lookups.append(host_s)
        if len(hostname_lookups) == 1:
            return _addrinfo("93.184.216.34")
        return _addrinfo("127.0.0.1")

    def spy_create_connection(address, *args, **kwargs):
        dest = address[0]
        try:
            ipaddress.ip_address(dest)
            dest_ips = [dest]
        except ValueError:
            infos = flipping_getaddrinfo(dest, address[1] if len(address) > 1 else 0)
            dest_ips = [item[4][0] for item in infos]
        connected.extend(dest_ips)
        raise OSError("test must not complete a real connect")

    monkeypatch.setattr(
        "backend.services.url_validation.socket.getaddrinfo", flipping_getaddrinfo
    )
    monkeypatch.setattr("socket.getaddrinfo", flipping_getaddrinfo)
    monkeypatch.setattr(
        "httpcore._backends.sync.socket.create_connection", spy_create_connection
    )

    assert is_safe_url("https://rebind.attacker.test/") is True
    transport = ValidatedIPTransport()
    with pytest.raises((httpcore.ConnectError, httpx.ConnectError, OSError)):
        transport._pool._network_backend.connect_tcp("rebind.attacker.test", 443)

    assert "127.0.0.1" not in connected
    assert all(not _is_blocked_ip(ip) for ip in connected)


def test_validated_transport_pins_check_time_ips(monkeypatch):
    """Explicit connect_ips must be used even if hostname DNS later goes private."""
    connected = []

    def private_only_getaddrinfo(host, port, *args, **kwargs):
        host_s = host.decode() if isinstance(host, bytes) else str(host)
        try:
            ipaddress.ip_address(host_s.split("%")[0])
            family = socket.AF_INET6 if ":" in host_s else socket.AF_INET
            return [(family, socket.SOCK_STREAM, 6, "", (host_s, port or 0))]
        except ValueError:
            return _addrinfo("127.0.0.1")

    def spy_create_connection(address, *args, **kwargs):
        connected.append(address[0])
        raise OSError("test must not complete a real connect")

    monkeypatch.setattr(
        "backend.services.url_validation.socket.getaddrinfo",
        private_only_getaddrinfo,
    )
    monkeypatch.setattr("socket.getaddrinfo", private_only_getaddrinfo)
    monkeypatch.setattr(
        "httpcore._backends.sync.socket.create_connection", spy_create_connection
    )

    transport = ValidatedIPTransport(connect_ips=["93.184.216.34"])
    with pytest.raises((httpcore.ConnectError, httpx.ConnectError, OSError)):
        transport._pool._network_backend.connect_tcp("rebind.attacker.test", 443)

    assert connected == ["93.184.216.34"]
    assert "127.0.0.1" not in connected


def _is_blocked_ip(raw: str) -> bool:
    ip = ipaddress.ip_address(raw.split("%")[0])
    mapped = getattr(ip, "ipv4_mapped", None)
    ip = mapped if mapped is not None else ip
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )
