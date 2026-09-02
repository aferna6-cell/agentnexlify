"""Phase 1b - unified connector registry + in-chat connect.

Covers:
  - connector_registry: status resolution across all backing tables + phone
    column, inference patterns (superset of the legacy 5), OAuth flag
  - GET /api/v1/connectors/status (unregistered router - built standalone
    below, per the task's "do not register in main.py yet" constraint)
  - integrations.py OAuth state JWT round-trip with os_thread_id/return_to
  - integrations.py callback redirect: deep-links back to the Agent OS
    thread when os_thread_id was present in state

connector_awareness.py's own contract (5-connector universe, exact label/
path text) is covered by the pre-existing test_connector_awareness.py,
which this refactor must keep green unmodified.
"""

from unittest.mock import MagicMock

import httpx
import pytest

from backend.services import connector_registry


def _chain(rows):
    result = MagicMock()
    result.data = rows
    c = MagicMock()
    for m in ("select", "eq", "in_", "order", "limit", "insert", "is_"):
        getattr(c, m).return_value = c
    c.execute.return_value = result
    return c


def _status_db(integrations=(), drive_rows=(), tenant_rows=(), api_key_rows=()):
    """Same chain instance returned per table name across repeat calls, so
    a test can inspect ``db.table("x").eq.call_args_list`` after the code
    under test has already run its queries."""
    db = MagicMock()
    chains = {
        "integrations": _chain([{"provider": p} for p in integrations]),
        "tenant_integrations": _chain(list(drive_rows)),
        "tenants": _chain(list(tenant_rows)),
        "tenant_api_keys": _chain(list(api_key_rows)),
    }

    def route(name):
        return chains.get(name) or _chain([])

    db.table.side_effect = route
    return db


# ---------------------------------------------------------------------------
# get_registry / is_oauth_connector
# ---------------------------------------------------------------------------


class TestGetRegistry:
    def test_covers_all_nine_connectors(self):
        keys = [c["key"] for c in connector_registry.get_registry()]
        assert keys == [
            "calendar",
            "hubspot",
            "drive",
            "phone",
            "zapier",
            "gmail",
            "instagram",
            "facebook",
            "twilio_byo",
        ]

    def test_entries_have_label_path_category(self):
        for entry in connector_registry.get_registry():
            assert entry["label"]
            assert entry["connect_path"].startswith("/dashboard/")
            assert entry["category"]
            assert isinstance(entry["oauth"], bool)


class TestIsOauthConnector:
    @pytest.mark.parametrize("key", ["calendar", "hubspot"])
    def test_oauth_connectors(self, key):
        assert connector_registry.is_oauth_connector(key) is True

    @pytest.mark.parametrize(
        "key", ["drive", "phone", "zapier", "gmail", "instagram", "facebook", "twilio_byo"]
    )
    def test_non_oauth_connectors(self, key):
        assert connector_registry.is_oauth_connector(key) is False

    def test_unknown_key_is_false(self):
        assert connector_registry.is_oauth_connector("not-a-real-connector") is False


# ---------------------------------------------------------------------------
# infer_needed_connectors (superset of the legacy 5, ordered)
# ---------------------------------------------------------------------------


class TestInference:
    @pytest.mark.parametrize(
        "text,expected",
        [
            ("Can you sync my Google Calendar?", ["calendar"]),
            ("push this lead to our CRM", ["hubspot"]),
            ("connect my google drive folder", ["drive"]),
            ("I want an AI receptionist to answer my calls", ["phone"]),
            ("set up a zapier automation for new leads", ["zapier"]),
            ("connect gmail so you can monitor my inbox", ["gmail"]),
            ("connect my instagram", ["instagram"]),
            ("connect my facebook page", ["facebook"]),
            ("I want to bring your own twilio number", ["twilio_byo"]),
        ],
    )
    def test_positive(self, text, expected):
        assert connector_registry.infer_needed_connectors(text) == expected

    @pytest.mark.parametrize(
        "text",
        [
            "please call the customer back",
            "draft an email to this customer",
            "the customer drives a truck",
            "",
        ],
    )
    def test_negative(self, text):
        assert connector_registry.infer_needed_connectors(text) == []

    def test_multiple_connectors_preserves_declared_order(self):
        text = "sync my google calendar and push new bookings to hubspot"
        assert connector_registry.infer_needed_connectors(text) == ["calendar", "hubspot"]


# ---------------------------------------------------------------------------
# connection_status - one lookup per table, all nine connectors
# ---------------------------------------------------------------------------


class TestConnectionStatus:
    def test_all_disconnected(self):
        status = connector_registry.connection_status(_status_db(), tenant_id="t1")
        assert status == {
            "calendar": False,
            "hubspot": False,
            "drive": False,
            "phone": False,
            "zapier": False,
            "gmail": False,
            "instagram": False,
            "facebook": False,
            "twilio_byo": False,
        }

    def test_all_connected(self):
        db = _status_db(
            integrations=(
                "google_calendar",
                "hubspot",
                "gmail",
                "instagram",
                "facebook",
                "twilio_byo",
            ),
            drive_rows=[{"provider": "drive", "enabled": True}],
            tenant_rows=[{"twilio_number": "+15550001111"}],
            api_key_rows=[{"id": "k1"}],
        )
        assert all(connector_registry.connection_status(db, tenant_id="t1").values())

    def test_m365_counts_as_calendar(self):
        db = _status_db(integrations=("m365_calendar",))
        assert connector_registry.connection_status(db, tenant_id="t1")["calendar"] is True

    def test_disabled_drive_is_not_connected(self):
        db = _status_db(drive_rows=[{"provider": "drive", "enabled": False}])
        assert connector_registry.connection_status(db, tenant_id="t1")["drive"] is False

    def test_dropbox_row_does_not_count_as_drive(self):
        """tenant_integrations can hold multiple providers - only 'drive' counts."""
        db = _status_db(drive_rows=[{"provider": "dropbox", "enabled": True}])
        assert connector_registry.connection_status(db, tenant_id="t1")["drive"] is False

    def test_client_id_defaults_to_tenant_id(self):
        """No explicit client_id -> same value used for client_id-keyed tables."""
        db = _status_db(api_key_rows=[{"id": "k1"}])
        status = connector_registry.connection_status(db, tenant_id="t1")
        assert status["zapier"] is True

    def test_zapier_uses_client_id_column_not_tenant_id(self):
        """Regression: pre-refactor connector_awareness.py queried
        tenant_api_keys with .eq('tenant_id', ...), but the table's actual
        tenant-scope column is client_id (migrations 110/117). Assert the
        fixed query filters on the right column."""
        db = _status_db(api_key_rows=[{"id": "k1"}])
        connector_registry.connection_status(db, tenant_id="t1", client_id="c1")
        query = db.table("tenant_api_keys")
        eq_calls = [c for c in query.eq.call_args_list if c.args and c.args[0] == "client_id"]
        assert eq_calls, "expected .eq('client_id', ...) on tenant_api_keys"
        tenant_id_calls = [
            c for c in query.eq.call_args_list if c.args and c.args[0] == "tenant_id"
        ]
        assert not tenant_id_calls, "tenant_api_keys has no tenant_id column"

    def test_lookup_failure_fails_closed_for_that_table_only(self):
        broken = _chain([])
        broken.execute.side_effect = RuntimeError("db down")

        def route(name):
            if name == "integrations":
                return broken
            if name == "tenants":
                return _chain([{"twilio_number": "+15550001111"}])
            return _chain([])

        db = MagicMock()
        db.table.side_effect = route
        status = connector_registry.connection_status(db, tenant_id="t1")
        assert status["calendar"] is False
        assert status["gmail"] is False
        assert status["phone"] is True

    def test_tenant_integrations_lookup_failure_fails_closed_for_drive_only(self):
        broken = _chain([])
        broken.execute.side_effect = RuntimeError("db down")

        def route(name):
            if name == "tenant_integrations":
                return broken
            if name == "tenants":
                return _chain([{"twilio_number": "+15550001111"}])
            return _chain([])

        db = MagicMock()
        db.table.side_effect = route
        status = connector_registry.connection_status(db, tenant_id="t1")
        assert status["drive"] is False
        assert status["phone"] is True

    def test_tenants_lookup_failure_fails_closed_for_phone_only(self):
        broken = _chain([])
        broken.execute.side_effect = RuntimeError("db down")

        def route(name):
            if name == "tenants":
                return broken
            if name == "integrations":
                return _chain([{"provider": "hubspot"}])
            return _chain([])

        db = MagicMock()
        db.table.side_effect = route
        status = connector_registry.connection_status(db, tenant_id="t1")
        assert status["phone"] is False
        assert status["hubspot"] is True

    def test_tenant_api_keys_lookup_failure_fails_closed_for_zapier_only(self):
        broken = _chain([])
        broken.execute.side_effect = RuntimeError("db down")

        def route(name):
            if name == "tenant_api_keys":
                return broken
            if name == "tenants":
                return _chain([{"twilio_number": "+15550001111"}])
            return _chain([])

        db = MagicMock()
        db.table.side_effect = route
        status = connector_registry.connection_status(db, tenant_id="t1")
        assert status["zapier"] is False
        assert status["phone"] is True


# ---------------------------------------------------------------------------
# GET /api/v1/connectors/status - standalone app (router not in main.py yet)
# ---------------------------------------------------------------------------


def _connectors_test_client():
    from fastapi import FastAPI

    from backend.routers import connectors as connectors_router

    app = FastAPI()
    app.include_router(connectors_router.router)
    return app, connectors_router


def _auth_headers(tenant_id="00000000-0000-0000-0000-000000000001"):
    from datetime import datetime, timedelta, timezone

    from jose import jwt

    from backend.config import settings

    payload = {
        "tenant_id": tenant_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=24),
    }
    token = jwt.encode(payload, settings.api_secret_key, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_connectors_status_endpoint_returns_full_catalog_with_connected_flags(
    monkeypatch,
):
    app, connectors_router = _connectors_test_client()

    db = _status_db(integrations=("hubspot",))
    monkeypatch.setattr(connectors_router, "get_service_supabase", lambda: db)

    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get("/api/v1/connectors/status", headers=_auth_headers())

    assert resp.status_code == 200
    body = resp.json()
    connectors = {c["key"]: c for c in body["connectors"]}
    assert len(connectors) == 9
    assert connectors["hubspot"]["connected"] is True
    assert connectors["calendar"]["connected"] is False
    assert connectors["hubspot"]["oauth"] is True
    assert connectors["drive"]["connect_path"] == "/dashboard/knowledge"


@pytest.mark.asyncio
async def test_connectors_status_endpoint_requires_auth():
    app, _connectors_router = _connectors_test_client()

    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get("/api/v1/connectors/status")

    # Missing Authorization header -> FastAPI 422 (required Header(...) param
    # unset), same auth-guard shape as every other Depends(_get_current_tenant)
    # endpoint when the header is entirely absent.
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_connectors_status_endpoint_degrades_on_db_error(monkeypatch):
    """Best-effort: a status lookup failure returns the catalog with every
    connector reported disconnected, never a 500."""
    app, connectors_router = _connectors_test_client()

    def _boom():
        raise RuntimeError("db unreachable")

    monkeypatch.setattr(connectors_router, "get_service_supabase", _boom)

    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get("/api/v1/connectors/status", headers=_auth_headers())

    assert resp.status_code == 200
    body = resp.json()
    assert all(c["connected"] is False for c in body["connectors"])


# ---------------------------------------------------------------------------
# integrations.py - OAuth state JWT round-trip (os_thread_id / return_to)
# ---------------------------------------------------------------------------


class TestOAuthStateRoundTrip:
    def test_round_trip_with_thread_and_return_to(self):
        from backend.routers import integrations as integrations_router

        state = integrations_router._encode_state(
            "tenant-9", os_thread_id="th-7", return_to="/dashboard/agent-os"
        )
        claims = integrations_router._decode_state(state)
        assert claims == {
            "tenant_id": "tenant-9",
            "os_thread_id": "th-7",
            "return_to": "/dashboard/agent-os",
        }

    def test_round_trip_without_thread_defaults_to_none(self):
        from backend.routers import integrations as integrations_router

        state = integrations_router._encode_state("tenant-9")
        claims = integrations_router._decode_state(state)
        assert claims == {"tenant_id": "tenant-9", "os_thread_id": None, "return_to": None}

    def test_expired_state_rejected(self):
        from datetime import datetime, timedelta, timezone

        from fastapi import HTTPException
        from jose import jwt

        from backend.routers import integrations as integrations_router

        payload = {
            "tenant_id": "tenant-9",
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        }
        expired = jwt.encode(
            payload, integrations_router._jwt_secret(), algorithm=integrations_router._JWT_ALGORITHM
        )
        with pytest.raises(HTTPException) as exc_info:
            integrations_router._decode_state(expired)
        assert exc_info.value.status_code == 400
        assert "expired" in str(exc_info.value.detail).lower()


    def test_state_token_ttl_covers_interactive_oauth_delays(self):
        """2FA + unverified-app warning routinely exceed a 10-minute state TTL."""
        from backend.routers import integrations as integrations_router
        from backend.routers import gmail_integration as gmail_router

        assert integrations_router._STATE_TOKEN_EXPIRY_MINUTES >= 60
        assert gmail_router._STATE_TOKEN_EXPIRY_MINUTES >= 60

    def test_relative_path_accepted(self):
        from backend.routers import integrations as integrations_router

        assert integrations_router._safe_return_to("/dashboard/agent-os") == "/dashboard/agent-os"

    @pytest.mark.parametrize(
        "value",
        [None, "", "https://evil.example.com", "//evil.example.com", "javascript:alert(1)"],
    )
    def test_unsafe_values_rejected(self, value):
        from backend.routers import integrations as integrations_router

        assert integrations_router._safe_return_to(value) is None


# ---------------------------------------------------------------------------
# integrations.py - callback redirect deep-links back to the OS thread
# ---------------------------------------------------------------------------


class _FakeGoogleCreds:
    token = "access-tok"
    refresh_token = "refresh-tok"
    expiry = None


@pytest.mark.asyncio
async def test_google_callback_redirects_to_thread_when_present(monkeypatch):
    from backend.routers import integrations as integrations_router

    monkeypatch.setattr(
        integrations_router, "exchange_code", lambda code, redirect_uri: _FakeGoogleCreds()
    )
    monkeypatch.setattr(integrations_router, "save_integration", lambda **kwargs: None)

    state = integrations_router._encode_state("tenant-9", os_thread_id="th-42")
    response = await integrations_router.google_callback(code="auth-code", state=state)

    assert response.status_code in (302, 303, 307, 308)
    location = response.headers["location"]
    assert "/dashboard/agent-os" in location
    assert "thread=th-42" in location
    assert "connected=google_calendar" in location


@pytest.mark.asyncio
async def test_google_callback_falls_back_to_hash_redirect_without_thread(monkeypatch):
    from backend.routers import integrations as integrations_router

    monkeypatch.setattr(
        integrations_router, "exchange_code", lambda code, redirect_uri: _FakeGoogleCreds()
    )
    monkeypatch.setattr(integrations_router, "save_integration", lambda **kwargs: None)

    state = integrations_router._encode_state("tenant-9")
    response = await integrations_router.google_callback(code="auth-code", state=state)

    location = response.headers["location"]
    assert location.endswith("/#integrations")
    assert "thread=" not in location


# ---------------------------------------------------------------------------
# integrations.py - auth-URL generation endpoints (state JWT + provider url)
# ---------------------------------------------------------------------------


def test_oauth_success_response_falls_back_to_html_when_no_frontend_url(monkeypatch):
    from fastapi.responses import HTMLResponse

    from backend.routers import integrations as integrations_router

    monkeypatch.setattr(integrations_router.settings, "frontend_url", "")
    response = integrations_router._oauth_success_response(
        provider_key="google_calendar",
        provider_label="Google Calendar",
        os_thread_id=None,
        return_to=None,
        fallback_hash="/#integrations",
    )
    assert isinstance(response, HTMLResponse)
    assert b"Connected!" in response.body


@pytest.mark.asyncio
async def test_google_auth_generates_state_and_returns_auth_url(monkeypatch):
    from backend.routers import integrations as integrations_router

    monkeypatch.setattr(integrations_router.settings, "google_client_id", "gid")
    monkeypatch.setattr(integrations_router.settings, "google_client_secret", "gsecret")
    monkeypatch.setattr(
        integrations_router.settings, "google_redirect_uri", "https://app.test/google/cb"
    )
    monkeypatch.setattr(
        integrations_router,
        "get_auth_url",
        lambda redirect_uri, state: f"https://accounts.google.com/auth?state={state}",
    )

    result = await integrations_router.google_auth(
        claims={"tenant_id": "tenant-1"}, os_thread_id="th-1"
    )
    assert "auth_url" in result
    assert "https://accounts.google.com/auth" in result["auth_url"]


@pytest.mark.asyncio
async def test_m365_auth_generates_state_and_returns_auth_url(monkeypatch):
    from backend.routers import integrations as integrations_router

    monkeypatch.setattr(integrations_router.settings, "m365_client_id", "mid")
    monkeypatch.setattr(integrations_router.settings, "m365_client_secret", "msecret")
    monkeypatch.setattr(
        integrations_router.settings, "m365_redirect_uri", "https://app.test/m365/cb"
    )
    monkeypatch.setattr(
        integrations_router.m365_calendar,
        "build_authorization_url",
        lambda redirect_uri, state: f"https://login.microsoftonline.com/auth?state={state}",
    )

    result = await integrations_router.m365_auth(
        claims={"tenant_id": "tenant-1"}, os_thread_id=None
    )
    assert "auth_url" in result
    assert "https://login.microsoftonline.com/auth" in result["auth_url"]


@pytest.mark.asyncio
async def test_hubspot_auth_generates_state_and_returns_auth_url(monkeypatch):
    from backend.routers import integrations as integrations_router

    monkeypatch.setattr(integrations_router.settings, "hubspot_client_id", "hid")
    monkeypatch.setattr(integrations_router.settings, "hubspot_client_secret", "hsecret")
    monkeypatch.setattr(
        integrations_router.settings, "hubspot_redirect_uri", "https://app.test/hubspot/cb"
    )
    monkeypatch.setattr(
        integrations_router.hubspot_tenant,
        "build_authorization_url",
        lambda redirect_uri, state: f"https://app.hubspot.com/oauth/authorize?state={state}",
    )

    result = await integrations_router.hubspot_auth(
        claims={"tenant_id": "tenant-1"}, os_thread_id="th-9"
    )
    assert "auth_url" in result
    assert "https://app.hubspot.com/oauth/authorize" in result["auth_url"]


# ---------------------------------------------------------------------------
# integrations.py - m365 + hubspot callback deep-link redirects
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_m365_callback_success_redirects_to_thread(monkeypatch):
    from backend.routers import integrations as integrations_router

    monkeypatch.setattr(
        integrations_router.m365_calendar,
        "exchange_code",
        lambda code, redirect_uri: {
            "access_token": "at",
            "refresh_token": "rt",
            "expires_in": 3600,
        },
    )
    monkeypatch.setattr(
        integrations_router,
        "_fetch_m365_profile",
        lambda access_token: {"email": "x@y.com", "calendar_name": "Primary"},
    )
    monkeypatch.setattr(integrations_router.m365_calendar, "save_integration", lambda **kwargs: None)

    state = integrations_router._encode_state("tenant-9", os_thread_id="th-5")
    response = await integrations_router.m365_callback(code="auth-code", state=state)

    assert response.status_code in (302, 303, 307, 308)
    location = response.headers["location"]
    assert "thread=th-5" in location
    assert "connected=m365_calendar" in location


@pytest.mark.asyncio
async def test_hubspot_callback_success_redirects_to_thread(monkeypatch):
    from backend.routers import integrations as integrations_router

    monkeypatch.setattr(
        integrations_router.hubspot_tenant,
        "exchange_code",
        lambda code, redirect_uri: {
            "access_token": "at",
            "refresh_token": "rt",
            "expires_in": 1800,
        },
    )
    monkeypatch.setattr(
        integrations_router.hubspot_tenant,
        "fetch_profile",
        lambda access_token: {"portal_id": "p1"},
    )
    monkeypatch.setattr(
        integrations_router.hubspot_tenant, "save_integration", lambda **kwargs: None
    )

    state = integrations_router._encode_state("tenant-9", os_thread_id="th-8")
    response = await integrations_router.hubspot_callback(code="auth-code", state=state)

    assert response.status_code in (302, 303, 307, 308)
    location = response.headers["location"]
    assert "thread=th-8" in location
    assert "connected=hubspot" in location
