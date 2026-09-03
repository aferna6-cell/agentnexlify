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
from unittest.mock import patch

import pytest

from backend.services.website_connect import (
    FORBIDDEN_CREDENTIAL_FIELDS,
    PLATFORMS,
    PageFetch,
    detect_platform,
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

    def test_empty_key_never_matches(self):
        assert widget_is_present(_wp_html(KEY_A), "") is False
        assert widget_is_present(_wp_html(KEY_A), None) is False


class TestNormalizeAndSecrets:
    def test_adds_https_and_strips_slash(self):
        assert normalize_website_url("example.com/") == "https://example.com"

    def test_rejects_private_urls(self):
        with pytest.raises(ValueError):
            normalize_website_url("http://127.0.0.1/")

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
