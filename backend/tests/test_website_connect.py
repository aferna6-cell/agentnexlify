"""Website / chatbot connect v1.

Covers the smallest safe vertical slice:
- URL + platform detection / selection
- tenant-scoped connection status
- automatic widget-presence verification
- platform next-actions
- no fake connected state
- no CMS password storage
- no secret leakage in logs

Service tests import only backend.services.website_connect.
Router tests use SyncASGITestClient + JWT isolation.
"""

from __future__ import annotations

import io
import logging
import uuid
import zipfile
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlparse

import pytest

from backend.services.url_validation import (
    PinnedTarget,
    pin_safe_url as real_pin_safe_url,
)
from backend.services.website_connect import (
    FORBIDDEN_CREDENTIAL_FIELDS,
    PLATFORMS,
    PageFetch,
    detect_platform,
    fetch_public_page,
    next_action,
    normalize_website_url,
    redact_secret,
    reject_credential_fields,
    upsert_connection,
    verify_connection,
    widget_is_present,
)


TENANT_A = "00000000-0000-0000-0000-000000000001"
TENANT_B = "00000000-0000-0000-0000-000000000002"
KEY_A = "wk_tenant_a_public_key_aaa"
KEY_B = "wk_tenant_b_public_key_bbb"


class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, store, table, op="select"):
        self.store = store
        self.table = table
        self.op = op
        self._filters = {}
        self._payload = None
        self._limit = None

    def select(self, *_a, **_k):
        self.op = "select"
        return self

    def eq(self, col, val):
        self._filters[col] = val
        return self

    def limit(self, n):
        self._limit = n
        return self

    def insert(self, payload):
        self.op = "insert"
        self._payload = dict(payload)
        return self

    def update(self, payload):
        self.op = "update"
        self._payload = dict(payload)
        return self

    def execute(self):
        rows = self.store.setdefault(self.table, [])
        if self.op == "insert":
            row = dict(self._payload)
            row.setdefault("id", str(uuid.uuid4()))
            rows.append(row)
            return _Result([row])
        matched = [
            r
            for r in rows
            if all(r.get(k) == v for k, v in self._filters.items())
        ]
        if self.op == "update":
            for r in matched:
                r.update(self._payload)
            return _Result([dict(r) for r in matched])
        if self._limit is not None:
            matched = matched[: self._limit]
        return _Result([dict(r) for r in matched])


class FakeDB:
    def __init__(self, tables=None):
        self.tables = tables or {
            "website_connections": [],
            "widget_configs": [],
            "tenants": [],
        }

    def table(self, name):
        return _Query(self.tables, name)


def _page(html: str, headers=None, url="https://example.com") -> PageFetch:
    return PageFetch(
        url=url,
        html=html,
        headers=headers or {},
        ok=True,
        error=None,
    )


def _wp_html(key=None):
    script = ""
    if key:
        script = (
            f'<script async src="https://app.agentnexlify.com/widget/'
            f'agentnexlify-widget.js" data-api-key="{key}"></script>'
        )
    return (
        "<html><head><meta name=\"generator\" content=\"WordPress 6.6\" />"
        "</head><body><link href=\"/wp-content/themes/x/style.css\" />"
        f"{script}</body></html>"
    )


# ---------------------------------------------------------------------------
# Detection + verification primitives
# ---------------------------------------------------------------------------


class TestDetectPlatform:
    def test_wordpress_generator_and_wp_content(self):
        assert detect_platform("https://example.com", _wp_html(), {}) == "wordpress"

    def test_wix_static_host_and_header(self):
        html = '<script src="https://static.wixstatic.com/js/foo.js"></script>'
        assert detect_platform("https://example.com", html, {"x-wix-request-id": "1"}) == "wix"

    def test_squarespace_cdn(self):
        html = '<link href="https://static1.squarespace.com/static/css.css" />'
        assert detect_platform("https://example.com", html, {"server": "squarespace"}) == "squarespace"

    def test_godaddy_builder_markers(self):
        html = '<html data-website="godaddysites.com"><script src="https://img1.wsimg.com/x.js"></script>'
        assert detect_platform("https://biz.godaddysites.com", html, {}) == "godaddy"

    def test_unknown_html_falls_back_to_custom(self):
        assert detect_platform("https://example.com", "<html><body>Hello</body></html>", {}) == "custom"

    def test_fetch_failure_falls_back_to_unknown(self):
        assert detect_platform("https://example.com", "", {}, fetched=False) == "unknown"


class TestWidgetPresence:
    def test_requires_script_and_this_tenant_key(self):
        html = _wp_html(KEY_A)
        assert widget_is_present(html, KEY_A) is True

    def test_other_tenant_key_is_not_connected(self):
        html = _wp_html(KEY_B)
        assert widget_is_present(html, KEY_A) is False

    def test_brand_mention_without_script_is_false_positive(self):
        html = "<html><body>We use AgentNexLiFy for chat.</body></html>"
        assert widget_is_present(html, KEY_A) is False

    def test_script_without_key_is_not_connected(self):
        html = (
            '<script src="https://app.agentnexlify.com/widget/'
            'agentnexlify-widget.js"></script>'
        )
        assert widget_is_present(html, KEY_A) is False

    def test_key_plaintext_without_data_api_key_is_not_connected(self):
        html = (
            '<script src="https://app.agentnexlify.com/widget/'
            f'agentnexlify-widget.js"></script> key={KEY_A}'
        )
        assert widget_is_present(html, KEY_A) is False

    def test_key_on_a_different_tag_is_not_connected(self):
        html = (
            f'<div data-api-key="{KEY_A}"></div>'
            '<script src="https://app.agentnexlify.com/widget/'
            'agentnexlify-widget.js"></script>'
        )
        assert widget_is_present(html, KEY_A) is False

    def test_other_script_key_does_not_count_for_widget(self):
        html = (
            f'<script src="https://cdn.example/other.js" data-api-key="{KEY_A}"></script>'
            '<script src="https://app.agentnexlify.com/widget/'
            'agentnexlify-widget.js"></script>'
        )
        assert widget_is_present(html, KEY_A) is False

    def test_empty_key_never_matches(self):
        assert widget_is_present(_wp_html(KEY_A), "") is False
        assert widget_is_present(_wp_html(KEY_A), None) is False

    def test_comment_with_loader_and_key_is_not_connected(self):
        html = (
            f'<!-- <script src="https://app.agentnexlify.com/widget/'
            f'agentnexlify-widget.js" data-api-key="{KEY_A}"></script> -->'
        )
        assert "agentnexlify-widget.js" in html
        assert KEY_A in html
        assert widget_is_present(html, KEY_A) is False

    def test_substrings_in_text_are_not_connected(self):
        html = (
            f"<p>agentnexlify-widget.js</p>"
            f'<p>data-api-key="{KEY_A}"</p>'
        )
        assert widget_is_present(html, KEY_A) is False

    def test_single_quoted_script_attributes_still_match(self):
        html = (
            "<script async src='https://app.agentnexlify.com/widget/"
            f"agentnexlify-widget.js' data-api-key='{KEY_A}'></script>"
        )
        assert widget_is_present(html, KEY_A) is True


class TestNormalizeAndSecrets:
    def test_adds_https_and_strips_slash(self):
        assert normalize_website_url("example.com/") == "https://example.com"

    def test_rejects_private_urls(self):
        with pytest.raises(ValueError):
            normalize_website_url("http://127.0.0.1/")

    def test_rejects_loopback_link_local_and_ipv6_literals(self):
        blocked = (
            "http://localhost/",
            "http://0.0.0.0/",
            "http://[::1]/",
            "http://[fe80::1]/",
            "http://169.254.169.254/",
            "http://10.0.0.5/",
            "http://192.168.1.1/",
            "http://[::ffff:127.0.0.1]/",
            "http://[::ffff:169.254.169.254]/",
        )
        for raw in blocked:
            with pytest.raises(ValueError):
                normalize_website_url(raw)

    def test_strips_userinfo_so_credentials_are_not_stored(self):
        assert (
            normalize_website_url("https://admin:cms-password@example.com/shop/")
            == "https://example.com/shop"
        )

    def test_keeps_explicit_port_and_rejects_empty_host(self):
        assert (
            normalize_website_url("https://example.com:8443/shop/")
            == "https://example.com:8443/shop"
        )
        with pytest.raises(ValueError):
            normalize_website_url("https://")
        with pytest.raises(ValueError):
            normalize_website_url("   ")

    def test_rejects_credential_fields(self):
        with pytest.raises(ValueError, match="not accepted"):
            reject_credential_fields({"website_url": "https://x.com", "password": "secret"})

    def test_forbidden_set_covers_cms_passwords(self):
        assert "password" in FORBIDDEN_CREDENTIAL_FIELDS
        assert "cms_password" in FORBIDDEN_CREDENTIAL_FIELDS
        assert "application_password" in FORBIDDEN_CREDENTIAL_FIELDS

    def test_redact_secret_never_returns_full_key(self):
        redacted = redact_secret(KEY_A)
        assert KEY_A not in redacted
        assert redacted.startswith("wk_t")
        assert "…" in redacted


# ---------------------------------------------------------------------------
# Live fetch SSRF (redirects / DNS rebind / private / loopback / IPv6)
# ---------------------------------------------------------------------------


class _FakeHTTPResponse:
    def __init__(self, url, status=200, headers=None, content=b"<html></html>"):
        self.url = url
        self.status_code = status
        self.headers = headers or {}
        self.content = content
        self.encoding = "utf-8"
        self.is_redirect = 300 <= status < 400
        self.is_success = 200 <= status < 300


class _FakeHTTPClient:
    def __init__(self, routes, seen, connects=None):
        self._routes = routes
        self.seen = seen
        self.connects = connects if connects is not None else []

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    def get(self, url, headers=None, extensions=None):
        headers = headers or {}
        host = headers.get("Host") or headers.get("host")
        parsed = urlparse(url)
        if host:
            logical = f"{parsed.scheme}://{host}{parsed.path or ''}"
            if parsed.query:
                logical += f"?{parsed.query}"
        else:
            logical = url
        self.seen.append(logical)
        self.connects.append(
            {"url": url, "headers": headers, "extensions": extensions or {}}
        )
        if logical not in self._routes and url not in self._routes:
            raise AssertionError(
                f"fetch_public_page requested blocked URL {url} (logical {logical})"
            )
        return self._routes.get(logical) or self._routes[url]


def _addrinfo(ip):
    return [(2, 1, 6, "", (ip, 0))]


PUBLIC_PIN_IP = "8.8.8.8"


def _pin_public_hosts(url: str) -> PinnedTarget | None:
    host = (urlparse(url).hostname or "").lower()
    if host in {"example.com", "example.org", "safe.example"}:
        parsed = urlparse(url)
        ip_netloc = f"{PUBLIC_PIN_IP}:{parsed.port}" if parsed.port else PUBLIC_PIN_IP
        connect = f"{parsed.scheme}://{ip_netloc}{parsed.path or ''}"
        if parsed.query:
            connect += f"?{parsed.query}"
        host_header = f"{host}:{parsed.port}" if parsed.port else host
        return PinnedTarget(
            url=url,
            connect_url=connect,
            hostname=host,
            ip=PUBLIC_PIN_IP,
            host_header=host_header,
            sni_hostname=host,
        )
    return real_pin_safe_url(url)


class TestFetchPublicPageSSRF:
    def test_does_not_request_loopback_private_link_local_or_ipv6(self, monkeypatch):
        seen = []
        monkeypatch.setattr(
            "backend.services.website_connect.httpx.Client",
            lambda *a, **k: _FakeHTTPClient({}, seen),
        )
        blocked = (
            "http://127.0.0.1/",
            "http://10.1.2.3/",
            "http://169.254.169.254/latest/meta-data/",
            "http://[::1]/",
            "http://[fe80::1]/",
            "http://[::ffff:127.0.0.1]/",
        )
        for url in blocked:
            page = fetch_public_page(url)
            assert page.ok is False
            assert page.error == "unsafe_url"
        assert seen == []

    def test_redirect_to_loopback_is_not_followed(self, monkeypatch):
        seen = []
        start = "https://example.com"
        routes = {
            start: _FakeHTTPResponse(
                start, status=302, headers={"location": "http://127.0.0.1/admin"}
            )
        }
        monkeypatch.setattr(
            "backend.services.website_connect.httpx.Client",
            lambda *a, **k: _FakeHTTPClient(routes, seen),
        )
        monkeypatch.setattr(
            "backend.services.website_connect.pin_safe_url", _pin_public_hosts
        )
        page = fetch_public_page(start)
        assert page.ok is False
        assert page.error == "unsafe_url"
        assert seen == [start]
        assert all("127.0.0.1" not in u for u in seen)

    def test_redirect_to_metadata_and_ipv6_loopback_is_not_followed(self, monkeypatch):
        seen = []
        start = "https://example.com"
        hops = [
            "http://169.254.169.254/latest/meta-data/",
            "http://[::1]/",
            "http://[fe80::1]/",
            "//169.254.169.254/",
        ]
        monkeypatch.setattr(
            "backend.services.website_connect.pin_safe_url", _pin_public_hosts
        )
        for location in hops:
            seen.clear()
            routes = {
                start: _FakeHTTPResponse(
                    start, status=302, headers={"location": location}
                )
            }
            monkeypatch.setattr(
                "backend.services.website_connect.httpx.Client",
                lambda *a, **k: _FakeHTTPClient(routes, seen),
            )
            page = fetch_public_page(start)
            assert page.ok is False
            assert seen == [start]
            joined = " ".join(seen)
            assert "169.254" not in joined
            assert "::1" not in joined
            assert "fe80" not in joined

    def test_dns_rebind_to_private_ip_is_not_requested(self, monkeypatch):
        seen = []
        monkeypatch.setattr(
            "backend.services.website_connect.httpx.Client",
            lambda *a, **k: _FakeHTTPClient({}, seen),
        )
        with patch(
            "backend.services.url_validation.socket.getaddrinfo",
            return_value=_addrinfo("10.0.0.5"),
        ):
            page = fetch_public_page("https://rebind.attacker.test/")
        assert page.ok is False
        assert page.error == "unsafe_url"
        assert seen == []

    def test_dns_rebind_to_ipv6_loopback_is_not_requested(self, monkeypatch):
        seen = []
        monkeypatch.setattr(
            "backend.services.website_connect.httpx.Client",
            lambda *a, **k: _FakeHTTPClient({}, seen),
        )
        with patch(
            "backend.services.url_validation.socket.getaddrinfo",
            return_value=[(10, 1, 6, "", ("::1", 0, 0, 0))],
        ):
            page = fetch_public_page("https://rebind6.attacker.test/")
        assert page.ok is False
        assert page.error == "unsafe_url"
        assert seen == []

    def test_public_at_check_private_at_connect_uses_pinned_ip(self, monkeypatch):
        """Hostname is public on the first resolve, private if re-resolved.

        Connect must use the first validated IP with Host/SNI, never the
        hostname (which would rebind) and never the later private answer.
        """
        seen = []
        connects = []
        lookups = {"n": 0}

        def flipping_getaddrinfo(host, *a, **k):
            if host != "rebind.attacker.test":
                raise OSError("unexpected host")
            lookups["n"] += 1
            if lookups["n"] == 1:
                return _addrinfo("8.8.8.8")
            return _addrinfo("10.0.0.5")

        start = "https://rebind.attacker.test/page"
        routes = {
            start: _FakeHTTPResponse(start, status=200, content=b"<html>ok</html>"),
            "https://8.8.8.8/page": _FakeHTTPResponse(
                "https://8.8.8.8/page", status=200, content=b"<html>ok</html>"
            ),
        }
        monkeypatch.setattr(
            "backend.services.url_validation.socket.getaddrinfo",
            flipping_getaddrinfo,
        )
        monkeypatch.setattr(
            "backend.services.website_connect.httpx.Client",
            lambda *a, **k: _FakeHTTPClient(routes, seen, connects),
        )
        page = fetch_public_page(start)
        assert page.ok is True
        assert "ok" in page.html
        assert connects, "expected a pinned-IP connect"
        assert [c["url"] for c in connects] == ["https://8.8.8.8/page"]
        assert connects[0]["headers"].get("Host") == "rebind.attacker.test"
        assert connects[0]["extensions"].get("sni_hostname") == "rebind.attacker.test"
        assert all("10.0.0.5" not in c["url"] for c in connects)
        assert all(urlparse(c["url"]).hostname == "8.8.8.8" for c in connects)

    def test_redirect_is_repinned_with_host_and_sni(self, monkeypatch):
        seen = []
        connects = []
        start = "https://example.com"
        dest = "https://example.com/page?x=1"
        routes = {
            start: _FakeHTTPResponse(
                start, status=302, headers={"location": "/page?x=1"}
            ),
            dest: _FakeHTTPResponse(dest, status=200, content=b"<html>q</html>"),
        }
        monkeypatch.setattr(
            "backend.services.website_connect.httpx.Client",
            lambda *a, **k: _FakeHTTPClient(routes, seen, connects),
        )
        monkeypatch.setattr(
            "backend.services.website_connect.pin_safe_url", _pin_public_hosts
        )
        page = fetch_public_page(start)
        assert page.ok is True
        assert [c["url"] for c in connects] == [
            f"https://{PUBLIC_PIN_IP}",
            f"https://{PUBLIC_PIN_IP}/page?x=1",
        ]
        assert [c["headers"].get("Host") for c in connects] == [
            "example.com",
            "example.com",
        ]
        assert [c["extensions"].get("sni_hostname") for c in connects] == [
            "example.com",
            "example.com",
        ]

    def test_empty_redirect_location_is_not_success(self, monkeypatch):
        seen = []
        start = "https://example.com"
        routes = {start: _FakeHTTPResponse(start, status=302, headers={"location": ""})}
        monkeypatch.setattr(
            "backend.services.website_connect.httpx.Client",
            lambda *a, **k: _FakeHTTPClient(routes, seen),
        )
        monkeypatch.setattr(
            "backend.services.website_connect.pin_safe_url", _pin_public_hosts
        )
        page = fetch_public_page(start)
        assert page.ok is False
        assert page.error == "redirect"
        assert seen == [start]

    def test_redirect_query_on_public_host_is_followed(self, monkeypatch):
        seen = []
        start = "https://example.com"
        dest = "https://example.com/page?x=1"
        routes = {
            start: _FakeHTTPResponse(
                start, status=302, headers={"location": "/page?x=1"}
            ),
            dest: _FakeHTTPResponse(dest, status=200, content=b"<html>q</html>"),
        }
        monkeypatch.setattr(
            "backend.services.website_connect.httpx.Client",
            lambda *a, **k: _FakeHTTPClient(routes, seen),
        )
        monkeypatch.setattr(
            "backend.services.website_connect.pin_safe_url", _pin_public_hosts
        )
        page = fetch_public_page(start)
        assert page.ok is True
        assert "q" in page.html
        assert seen == [start, dest]

    def test_safe_host_html_is_returned(self, monkeypatch):
        seen = []
        start = "https://example.com"
        html = b"<html><body>ok</body></html>"
        routes = {start: _FakeHTTPResponse(start, status=200, content=html)}
        monkeypatch.setattr(
            "backend.services.website_connect.httpx.Client",
            lambda *a, **k: _FakeHTTPClient(routes, seen),
        )
        monkeypatch.setattr(
            "backend.services.website_connect.pin_safe_url", _pin_public_hosts
        )
        page = fetch_public_page(start)
        assert page.ok is True
        assert "ok" in page.html
        assert seen == [start]

    def test_too_many_redirects_never_marks_success(self, monkeypatch):
        seen = []
        start = "https://example.com"
        routes = {
            start: _FakeHTTPResponse(
                start, status=302, headers={"location": "/next"}
            ),
            "https://example.com/next": _FakeHTTPResponse(
                "https://example.com/next",
                status=302,
                headers={"location": "/next"},
            ),
        }
        monkeypatch.setattr(
            "backend.services.website_connect.httpx.Client",
            lambda *a, **k: _FakeHTTPClient(routes, seen),
        )
        monkeypatch.setattr(
            "backend.services.website_connect.pin_safe_url", _pin_public_hosts
        )
        page = fetch_public_page(start)
        assert page.ok is False
        assert page.error == "too_many_redirects"


class TestMigration201Shape:
    def test_tenant_fk_rls_and_service_role_policy(self):
        sql = (
            Path(__file__).resolve().parents[2]
            / "migrations"
            / "201_website_connections.sql"
        ).read_text()
        assert "REFERENCES tenants(id) ON DELETE CASCADE" in sql
        assert "ENABLE ROW LEVEL SECURITY" in sql
        assert "TO public" in sql
        assert "USING (false)" in sql
        assert "TO service_role" in sql
        assert "USING (true)" in sql
        from backend.services.account_deletion import TENANT_DATA_TABLES

        assert "website_connections" in TENANT_DATA_TABLES


# ---------------------------------------------------------------------------
# Persist + verify (FakeDB)
# ---------------------------------------------------------------------------


class TestUpsertAndVerify:
    def test_upsert_is_idempotent_for_same_tenant_url(self):
        db = FakeDB()
        fetch = lambda url: _page(_wp_html(), url=url)
        first = upsert_connection(
            db, TENANT_A, "https://example.com", fetch_page=fetch
        )
        second = upsert_connection(
            db, TENANT_A, "https://example.com", fetch_page=fetch
        )
        assert first["id"] == second["id"]
        assert len(db.tables["website_connections"]) == 1
        assert second["status"] != "connected"

    def test_does_not_mark_connected_without_this_tenant_widget(self):
        db = FakeDB(
            {
                "website_connections": [],
                "widget_configs": [{"tenant_id": TENANT_A, "api_key": KEY_A}],
                "tenants": [],
            }
        )
        row = upsert_connection(
            db,
            TENANT_A,
            "https://example.com",
            fetch_page=lambda url: _page(_wp_html(KEY_B), url=url),
        )
        assert row["status"] == "needs_action"
        assert row["platform"] == "wordpress"

    def test_auto_connects_when_this_tenant_widget_already_present(self):
        db = FakeDB(
            {
                "website_connections": [],
                "widget_configs": [{"tenant_id": TENANT_A, "api_key": KEY_A}],
                "tenants": [],
            }
        )
        row = upsert_connection(
            db,
            TENANT_A,
            "https://example.com",
            fetch_page=lambda url: _page(_wp_html(KEY_A), url=url),
        )
        assert row["status"] == "connected"
        assert row["verification_method"] == "html_presence"

    def test_verify_reconnect_is_idempotent(self):
        db = FakeDB(
            {
                "website_connections": [],
                "widget_configs": [{"tenant_id": TENANT_A, "api_key": KEY_A}],
                "tenants": [],
            }
        )
        upsert_connection(
            db,
            TENANT_A,
            "https://example.com",
            fetch_page=lambda url: _page(_wp_html(KEY_A), url=url),
        )
        again = verify_connection(
            db,
            TENANT_A,
            fetch_page=lambda url: _page(_wp_html(KEY_A), url=url),
        )
        assert again["status"] == "connected"
        assert len(db.tables["website_connections"]) == 1

    def test_reconnect_upsert_same_url_stays_connected(self):
        db = FakeDB(
            {
                "website_connections": [],
                "widget_configs": [{"tenant_id": TENANT_A, "api_key": KEY_A}],
                "tenants": [],
            }
        )
        first = upsert_connection(
            db,
            TENANT_A,
            "https://example.com",
            fetch_page=lambda url: _page(_wp_html(KEY_A), url=url),
        )
        second = upsert_connection(
            db,
            TENANT_A,
            "https://example.com",
            fetch_page=lambda url: _page(_wp_html(KEY_A), url=url),
        )
        assert first["id"] == second["id"]
        assert second["status"] == "connected"
        assert len(db.tables["website_connections"]) == 1

    def test_url_change_resets_connected_until_reverified(self):
        db = FakeDB(
            {
                "website_connections": [],
                "widget_configs": [{"tenant_id": TENANT_A, "api_key": KEY_A}],
                "tenants": [],
            }
        )
        upsert_connection(
            db,
            TENANT_A,
            "https://example.com",
            fetch_page=lambda url: _page(_wp_html(KEY_A), url=url),
        )
        changed = upsert_connection(
            db,
            TENANT_A,
            "https://example.org",
            fetch_page=lambda url: _page(_wp_html(), url=url),
        )
        assert changed["status"] == "needs_action"
        assert changed["website_url"] == "https://example.org"
        assert len(db.tables["website_connections"]) == 1

    def test_tenant_rows_do_not_leak_across_tenants(self):
        db = FakeDB(
            {
                "website_connections": [],
                "widget_configs": [
                    {"tenant_id": TENANT_A, "api_key": KEY_A},
                    {"tenant_id": TENANT_B, "api_key": KEY_B},
                ],
                "tenants": [],
            }
        )
        upsert_connection(
            db,
            TENANT_A,
            "https://example.com",
            fetch_page=lambda url: _page(_wp_html(KEY_A), url=url),
        )
        row_b = upsert_connection(
            db,
            TENANT_B,
            "https://example.org",
            fetch_page=lambda url: _page("<html>custom</html>", url=url),
        )
        assert row_b["status"] != "connected"
        assert row_b["tenant_id"] == TENANT_B
        a_rows = [
            r for r in db.tables["website_connections"] if r["tenant_id"] == TENANT_A
        ]
        b_rows = [
            r for r in db.tables["website_connections"] if r["tenant_id"] == TENANT_B
        ]
        assert len(a_rows) == 1 and a_rows[0]["status"] == "connected"
        assert len(b_rows) == 1 and b_rows[0]["website_url"] == "https://example.org"

    def test_platform_override_is_honored(self):
        db = FakeDB()
        row = upsert_connection(
            db,
            TENANT_A,
            "https://example.net",
            platform="wix",
            fetch_page=lambda url: _page("<html>no signals</html>", url=url),
        )
        assert row["platform"] == "wix"
        assert row["platform_override"] is True
        assert row["detected_platform"] == "custom"

    def test_wordpress_next_action_is_plugin_not_password(self):
        action = next_action("wordpress", connected=False)
        assert action["code"] == "wordpress_plugin"
        blob = " ".join(str(v) for v in action.values()).lower()
        assert "password" not in blob
        assert "plugin" in blob

    def test_logs_never_include_full_widget_key(self, caplog):
        db = FakeDB(
            {
                "website_connections": [],
                "widget_configs": [{"tenant_id": TENANT_A, "api_key": KEY_A}],
                "tenants": [],
            }
        )
        with caplog.at_level(logging.DEBUG):
            upsert_connection(
                db,
                TENANT_A,
                "https://example.com",
                fetch_page=lambda url: _page(_wp_html(KEY_A), url=url),
            )
            verify_connection(
                db,
                TENANT_A,
                fetch_page=lambda url: _page(_wp_html(KEY_A), url=url),
            )
        joined = " ".join(r.getMessage() for r in caplog.records)
        assert KEY_A not in joined
        assert "password" not in joined.lower()


# ---------------------------------------------------------------------------
# Router isolation
# ---------------------------------------------------------------------------


class TestWebsiteConnectRouter:
    def test_tenant_b_cannot_read_tenant_a_connection(
        self, client, auth_headers_for
    ):
        db = FakeDB(
            {
                "website_connections": [
                    {
                        "id": "row-a",
                        "tenant_id": TENANT_A,
                        "website_url": "https://example.com",
                        "platform": "wordpress",
                        "status": "connected",
                    }
                ],
                "widget_configs": [],
                "tenants": [],
            }
        )
        with patch(
            "backend.routers.website_connect.get_service_supabase",
            return_value=db,
        ):
            resp = client.get(
                "/api/v1/website-connect",
                headers=auth_headers_for(TENANT_B),
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body.get("connection") is None
        assert body.get("status") != "connected"

    def test_password_field_is_rejected(self, client, auth_headers_for):
        resp = client.post(
            "/api/v1/website-connect",
            headers=auth_headers_for(TENANT_A),
            json={
                "website_url": "https://example.com",
                "password": "super-secret-cms",
            },
        )
        assert resp.status_code in (400, 422)
        assert "super-secret-cms" not in resp.text

    def test_verify_does_not_connect_on_other_tenant_key(
        self, client, auth_headers_for
    ):
        db = FakeDB(
            {
                "website_connections": [
                    {
                        "id": "row-a",
                        "tenant_id": TENANT_A,
                        "website_url": "https://example.com",
                        "platform": "wordpress",
                        "detected_platform": "wordpress",
                        "platform_override": False,
                        "status": "needs_action",
                    }
                ],
                "widget_configs": [{"tenant_id": TENANT_A, "api_key": KEY_A}],
                "tenants": [],
            }
        )

        def fake_fetch(url):
            return _page(_wp_html(KEY_B), url=url)

        with patch(
            "backend.routers.website_connect.get_service_supabase",
            return_value=db,
        ), patch(
            "backend.services.website_connect.fetch_public_page",
            side_effect=fake_fetch,
        ):
            resp = client.post(
                "/api/v1/website-connect/verify",
                headers=auth_headers_for(TENANT_A),
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] != "connected"
        assert body["status"] in ("needs_action", "failed")

    def test_connect_upsert_is_idempotent(self, client, auth_headers_for):
        db = FakeDB(
            {
                "website_connections": [],
                "widget_configs": [{"tenant_id": TENANT_A, "api_key": KEY_A}],
                "tenants": [],
            }
        )

        def fake_fetch(url):
            return _page("<html>custom shop</html>", url=url)

        with patch(
            "backend.routers.website_connect.get_service_supabase",
            return_value=db,
        ), patch(
            "backend.services.website_connect.fetch_public_page",
            side_effect=fake_fetch,
        ):
            first = client.post(
                "/api/v1/website-connect",
                headers=auth_headers_for(TENANT_A),
                json={"website_url": "https://example.com"},
            )
            second = client.post(
                "/api/v1/website-connect",
                headers=auth_headers_for(TENANT_A),
                json={"website_url": "https://example.com"},
            )
        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["id"] == second.json()["id"]
        assert len(db.tables["website_connections"]) == 1
        assert second.json()["status"] != "connected"

    def test_plugin_zip_contains_wordpress_plugin_not_secrets(
        self, client, auth_headers_for
    ):
        resp = client.get(
            "/api/v1/website-connect/wordpress-plugin",
            headers=auth_headers_for(TENANT_A),
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("application/zip")
        zf = zipfile.ZipFile(io.BytesIO(resp.content))
        names = zf.namelist()
        assert any(n.endswith("agentnexlify.php") for n in names)
        blob = b"".join(zf.read(n) for n in names)
        assert KEY_A.encode() not in blob
        assert b"super-secret" not in blob
