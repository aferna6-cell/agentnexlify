"""Router tests for backend/routers/gmail_integration.py — Gmail OAuth
connect / callback / status / disconnect.

Contracts:
  - _jwt_secret prefers jwt_secret_key, falls back to api_secret_key
  - _encode_state / _decode_state round-trip tenant_id (+ optional
    os_thread_id); invalid or tenant_id-less tokens raise HTTPException(400)
  - /connect 503s when the platform Google OAuth app isn't configured,
    otherwise returns an auth_url built from gmail_connector.get_auth_url
  - /callback: code-exchange failure -> 400, save_integration failure -> 500,
    profile-fetch failure is best-effort (connect still succeeds), and the
    redirect target depends on settings.frontend_url (RedirectResponse vs
    HTMLResponse fallback) and os_thread_id (deep link vs #integrations)
  - /status reports connected/not-connected shapes
  - /disconnect removes the integration, failure -> 500
"""

import os
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

os.environ.setdefault("TESTING", "1")

import pytest
from jose import jwt

from backend.dependencies import _get_current_tenant
from backend.main import app
from backend.routers import gmail_integration as router_mod
from backend.tests.conftest import SyncASGITestClient

CLAIMS = {"tenant_id": "22222222-2222-2222-2222-222222222222"}


def _client():
    app.dependency_overrides[_get_current_tenant] = lambda: CLAIMS
    return SyncASGITestClient(app)


def _teardown():
    app.dependency_overrides.pop(_get_current_tenant, None)


def _state_token(tenant_id="tenant-1", os_thread_id=None, secret="s3cr3t"):
    with patch.multiple(router_mod.settings, jwt_secret_key=secret):
        return router_mod._encode_state(tenant_id, os_thread_id)


# ---------------------------------------------------------------------------
# _jwt_secret
# ---------------------------------------------------------------------------


class TestJwtSecret:
    def test_prefers_jwt_secret_key_when_set(self):
        with patch.multiple(router_mod.settings, jwt_secret_key="jwt-secret"):
            assert router_mod._jwt_secret() == "jwt-secret"

    def test_falls_back_to_api_secret_key_when_jwt_secret_key_blank(self):
        with patch.multiple(router_mod.settings, jwt_secret_key=""):
            secret = router_mod._jwt_secret()
        assert secret == router_mod.settings.api_secret_key


# ---------------------------------------------------------------------------
# _encode_state / _decode_state
# ---------------------------------------------------------------------------


class TestEncodeDecodeState:
    def test_round_trips_tenant_id_only(self):
        with patch.multiple(router_mod.settings, jwt_secret_key="s3cr3t"):
            token = router_mod._encode_state("tenant-1")
            tenant_id, os_thread_id = router_mod._decode_state(token)
        assert tenant_id == "tenant-1"
        assert os_thread_id is None

    def test_round_trips_with_os_thread_id(self):
        with patch.multiple(router_mod.settings, jwt_secret_key="s3cr3t"):
            token = router_mod._encode_state("tenant-1", "thread-9")
            tenant_id, os_thread_id = router_mod._decode_state(token)
        assert tenant_id == "tenant-1"
        assert os_thread_id == "thread-9"

    def test_invalid_token_raises_400(self):
        with pytest.raises(Exception) as excinfo:
            router_mod._decode_state("not-a-valid-jwt")
        assert getattr(excinfo.value, "status_code", None) == 400

    def test_missing_tenant_id_raises_400(self):
        with patch.multiple(router_mod.settings, jwt_secret_key="s3cr3t"):
            token = jwt.encode(
                {"exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
                "s3cr3t",
                algorithm="HS256",
            )
            with pytest.raises(Exception) as excinfo:
                router_mod._decode_state(token)
        assert getattr(excinfo.value, "status_code", None) == 400


# ---------------------------------------------------------------------------
# /connect
# ---------------------------------------------------------------------------


class TestConnect:
    def teardown_method(self):
        _teardown()

    def test_not_configured_returns_503(self):
        client = _client()
        with patch.multiple(
            router_mod.settings,
            google_client_id="",
            google_client_secret="",
            gmail_redirect_uri="",
        ):
            resp = client.get("/api/v1/integrations/gmail/connect")
        assert resp.status_code == 503

    def test_configured_returns_auth_url(self):
        client = _client()
        with patch.multiple(
            router_mod.settings,
            google_client_id="cid",
            google_client_secret="secret",
            gmail_redirect_uri="https://api.example.com/cb",
        ), patch.object(
            router_mod.gmail_connector,
            "get_auth_url",
            return_value="https://accounts.google.com/auth?x=1",
        ) as get_auth_url:
            resp = client.get(
                "/api/v1/integrations/gmail/connect", params={"os_thread_id": "thread-1"}
            )
        assert resp.status_code == 200
        assert resp.json()["auth_url"] == "https://accounts.google.com/auth?x=1"
        get_auth_url.assert_called_once()


# ---------------------------------------------------------------------------
# /callback
# ---------------------------------------------------------------------------


class TestCallback:
    def teardown_method(self):
        _teardown()

    def test_exchange_code_failure_returns_400(self):
        client = _client()
        state = _state_token()
        with patch.multiple(
            router_mod.settings,
            jwt_secret_key="s3cr3t",
            gmail_redirect_uri="https://api.example.com/cb",
        ), patch.object(
            router_mod.gmail_connector, "exchange_code", side_effect=RuntimeError("boom")
        ):
            resp = client.get(
                "/api/v1/integrations/gmail/callback",
                params={"code": "abc", "state": state},
            )
        assert resp.status_code == 400

    def test_save_integration_failure_returns_500(self):
        state = _state_token()
        creds = MagicMock(token="tok", refresh_token="rt", expiry=None)
        client = _client()
        with patch.multiple(
            router_mod.settings,
            jwt_secret_key="s3cr3t",
            gmail_redirect_uri="https://api.example.com/cb",
        ), patch.object(
            router_mod.gmail_connector, "exchange_code", return_value=creds
        ), patch.object(
            router_mod.gmail_connector,
            "save_integration",
            side_effect=RuntimeError("db down"),
        ):
            resp = client.get(
                "/api/v1/integrations/gmail/callback",
                params={"code": "abc", "state": state},
            )
        assert resp.status_code == 500

    def test_profile_fetch_failure_is_best_effort_and_still_redirects(self):
        state = _state_token()
        creds = MagicMock(token="tok", refresh_token="rt", expiry=None)
        client = _client()
        with patch.multiple(
            router_mod.settings,
            jwt_secret_key="s3cr3t",
            gmail_redirect_uri="https://api.example.com/cb",
            frontend_url="https://app.example.com",
        ), patch.object(
            router_mod.gmail_connector, "exchange_code", return_value=creds
        ), patch.object(
            router_mod.gmail_connector, "save_integration", return_value={}
        ), patch.object(
            router_mod.gmail_connector, "get_profile", side_effect=RuntimeError("api down")
        ), patch.object(
            router_mod.gmail_connector, "update_metadata"
        ) as update_metadata:
            resp = client.get(
                "/api/v1/integrations/gmail/callback",
                params={"code": "abc", "state": state},
                follow_redirects=False,
            )
        assert resp.status_code in (302, 307)
        update_metadata.assert_not_called()

    def test_profile_success_updates_metadata_and_deep_links_thread(self):
        state = _state_token(os_thread_id="thread-9")
        creds = MagicMock(token="tok", refresh_token="rt", expiry=None)
        client = _client()
        with patch.multiple(
            router_mod.settings,
            jwt_secret_key="s3cr3t",
            gmail_redirect_uri="https://api.example.com/cb",
            frontend_url="https://app.example.com",
        ), patch.object(
            router_mod.gmail_connector, "exchange_code", return_value=creds
        ), patch.object(
            router_mod.gmail_connector, "save_integration", return_value={}
        ), patch.object(
            router_mod.gmail_connector,
            "get_profile",
            return_value={"emailAddress": "a@b.com", "historyId": "1"},
        ), patch.object(
            router_mod.gmail_connector, "update_metadata"
        ) as update_metadata:
            resp = client.get(
                "/api/v1/integrations/gmail/callback",
                params={"code": "abc", "state": state},
                follow_redirects=False,
            )
        assert resp.status_code in (302, 307)
        assert "thread-9" in resp.headers["location"]
        update_metadata.assert_called_once()

    def test_no_frontend_url_returns_html_fallback(self):
        state = _state_token()
        creds = MagicMock(token="tok", refresh_token="rt", expiry=None)
        client = _client()
        with patch.multiple(
            router_mod.settings,
            jwt_secret_key="s3cr3t",
            gmail_redirect_uri="https://api.example.com/cb",
            frontend_url="",
        ), patch.object(
            router_mod.gmail_connector, "exchange_code", return_value=creds
        ), patch.object(
            router_mod.gmail_connector, "save_integration", return_value={}
        ), patch.object(
            router_mod.gmail_connector, "get_profile", return_value={}
        ):
            resp = client.get(
                "/api/v1/integrations/gmail/callback",
                params={"code": "abc", "state": state},
            )
        assert resp.status_code == 200
        assert "Connected" in resp.text


# ---------------------------------------------------------------------------
# /status
# ---------------------------------------------------------------------------


class TestStatus:
    def teardown_method(self):
        _teardown()

    def test_not_connected(self):
        client = _client()
        with patch.object(
            router_mod.gmail_connector, "get_integration", return_value=None
        ), patch.multiple(
            router_mod.settings,
            google_client_id="",
            google_client_secret="",
            gmail_redirect_uri="",
        ):
            resp = client.get("/api/v1/integrations/gmail/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["connected"] is False
        assert data["email"] is None
        assert data["platform_configured"] is False

    def test_connected(self):
        client = _client()
        row = {
            "metadata": {
                "email_address": "a@b.com",
                "history_id": "5",
                "last_poll_at": "2026-01-01T00:00:00Z",
            }
        }
        with patch.object(router_mod.gmail_connector, "get_integration", return_value=row):
            resp = client.get("/api/v1/integrations/gmail/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["connected"] is True
        assert data["email"] == "a@b.com"
        assert data["history_id"] == "5"


# ---------------------------------------------------------------------------
# /disconnect
# ---------------------------------------------------------------------------


class TestDisconnect:
    def teardown_method(self):
        _teardown()

    def test_success(self):
        client = _client()
        with patch.object(
            router_mod.gmail_connector, "delete_integration", return_value=None
        ) as delete_mock:
            resp = client.post("/api/v1/integrations/gmail/disconnect")
        assert resp.status_code == 200
        assert resp.json() == {"status": "disconnected"}
        delete_mock.assert_called_once_with(CLAIMS["tenant_id"])

    def test_failure_returns_500(self):
        client = _client()
        with patch.object(
            router_mod.gmail_connector,
            "delete_integration",
            side_effect=RuntimeError("db down"),
        ):
            resp = client.post("/api/v1/integrations/gmail/disconnect")
        assert resp.status_code == 500
