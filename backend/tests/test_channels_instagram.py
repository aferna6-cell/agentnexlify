"""Tests for the Instagram Business connect flow (channels_instagram router).

Contracts covered:
  - GET /auth returns 503 when the Meta app isn't configured
  - GET /auth returns an auth_url with Instagram scopes when configured
  - GET /{tenant_id}/status reports not-connected when no integrations row
  - GET /{tenant_id}/status reports connected with metadata when row exists
  - GET /{tenant_id}/status rejects cross-tenant access (403)
  - GET /callback rejects missing/invalid state (400)
  - DELETE /{tenant_id}/disconnect returns 404 when nothing is connected

The OAuth token-exchange happy path talks to the Meta Graph API and is
covered manually — these tests pin the auth/validation surface only.
"""

from unittest.mock import MagicMock

from backend.config import settings

TENANT_ID = "00000000-0000-0000-0000-000000000001"


def _configure_meta_app(monkeypatch):
    monkeypatch.setattr(settings, "facebook_app_id", "test-app-id", raising=False)
    monkeypatch.setattr(
        settings, "facebook_app_secret", "test-app-secret", raising=False
    )


def _unconfigure_meta_app(monkeypatch):
    monkeypatch.setattr(settings, "facebook_app_id", "", raising=False)
    monkeypatch.setattr(settings, "facebook_app_secret", "", raising=False)


class TestInstagramAuth:
    def test_auth_503_when_platform_unconfigured(
        self, client, auth_headers, monkeypatch
    ):
        _unconfigure_meta_app(monkeypatch)
        resp = client.get("/api/v1/channels/instagram/auth", headers=auth_headers)
        assert resp.status_code == 503
        detail = resp.json()["detail"]
        assert detail["error"] == "instagram_not_configured"

    def test_auth_returns_url_with_instagram_scopes(
        self, client, auth_headers, mock_supabase, monkeypatch
    ):
        _configure_meta_app(monkeypatch)
        resp = client.get("/api/v1/channels/instagram/auth", headers=auth_headers)
        assert resp.status_code == 200
        auth_url = resp.json()["auth_url"]
        assert "client_id=test-app-id" in auth_url
        assert "instagram_basic" in auth_url
        assert "instagram_content_publish" in auth_url
        # nonce must be persisted under provider='instagram'
        insert_call = mock_supabase.table.return_value.insert.call_args
        assert insert_call is not None
        assert insert_call.args[0]["provider"] == "instagram"
        assert insert_call.args[0]["tenant_id"] == TENANT_ID

    def test_auth_requires_jwt(self, client):
        resp = client.get("/api/v1/channels/instagram/auth")
        assert resp.status_code in (401, 422)


class TestInstagramStatus:
    def test_status_not_connected(self, client, auth_headers, mock_supabase):
        chain = (
            mock_supabase.table.return_value.select.return_value.eq.return_value
            .eq.return_value.limit.return_value.execute
        )
        chain.return_value = MagicMock(data=[])
        resp = client.get(
            f"/api/v1/channels/instagram/{TENANT_ID}/status", headers=auth_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["connected"] is False

    def test_status_connected_with_metadata(
        self, client, auth_headers, mock_supabase, monkeypatch
    ):
        _configure_meta_app(monkeypatch)
        chain = (
            mock_supabase.table.return_value.select.return_value.eq.return_value
            .eq.return_value.limit.return_value.execute
        )
        chain.return_value = MagicMock(
            data=[
                {
                    "id": "int-1",
                    "metadata": {
                        "instagram_username": "mtoptions",
                        "instagram_business_account_id": "1789",
                        "page_id": "page-1",
                        "page_name": "MT Options",
                    },
                }
            ]
        )
        resp = client.get(
            f"/api/v1/channels/instagram/{TENANT_ID}/status", headers=auth_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["connected"] is True
        assert body["instagram_username"] == "mtoptions"
        assert body["instagram_business_account_id"] == "1789"
        assert body["page_name"] == "MT Options"
        assert body["platform_configured"] is True

    def test_status_cross_tenant_forbidden(self, client, auth_headers):
        other = "00000000-0000-0000-0000-000000000099"
        resp = client.get(
            f"/api/v1/channels/instagram/{other}/status", headers=auth_headers
        )
        assert resp.status_code == 403


class TestInstagramCallback:
    def test_callback_missing_params_400(self, client):
        resp = client.get("/api/v1/channels/instagram/callback")
        assert resp.status_code == 400

    def test_callback_invalid_state_400(self, client):
        resp = client.get(
            "/api/v1/channels/instagram/callback",
            params={"code": "abc", "state": "not-a-valid-jwt"},
        )
        assert resp.status_code == 400

    def test_callback_user_denied_redirects(self, client):
        resp = client.get(
            "/api/v1/channels/instagram/callback",
            params={"error": "access_denied"},
        )
        # RedirectResponse back to frontend with error param
        assert resp.status_code in (302, 307)
        assert "instagram_error=access_denied" in resp.headers["location"]


class TestInstagramDisconnect:
    def test_disconnect_404_when_not_connected(
        self, client, auth_headers, mock_supabase
    ):
        chain = (
            mock_supabase.table.return_value.select.return_value.eq.return_value
            .eq.return_value.limit.return_value.execute
        )
        chain.return_value = MagicMock(data=[])
        resp = client.delete(
            f"/api/v1/channels/instagram/{TENANT_ID}/disconnect",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_disconnect_removes_integration(
        self, client, auth_headers, mock_supabase
    ):
        chain = (
            mock_supabase.table.return_value.select.return_value.eq.return_value
            .eq.return_value.limit.return_value.execute
        )
        chain.return_value = MagicMock(data=[{"id": "int-1"}])
        resp = client.delete(
            f"/api/v1/channels/instagram/{TENANT_ID}/disconnect",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        delete_eq = mock_supabase.table.return_value.delete.return_value.eq
        delete_eq.assert_called_with("id", "int-1")
