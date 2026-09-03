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

import socket
from unittest.mock import patch

import pytest

from backend.services.url_validation import assert_safe_url, is_safe_url


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
