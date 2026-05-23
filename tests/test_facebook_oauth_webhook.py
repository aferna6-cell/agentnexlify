"""Unit + integration tests for facebook_oauth service + facebook_webhook service
+ channels_facebook router OAuth/disconnect paths.

Covers the changed-lines coverage gap identified during the channels_facebook.py
god-class split (PR #180):
  - backend/services/facebook_oauth.py
  - backend/services/facebook_webhook.py
  - backend/routers/channels_facebook.py OAuth callback + auth-url + disconnect

NOTE: pytest.ini sets asyncio_mode = auto, so async tests run without an
explicit @pytest.mark.asyncio decorator.
"""

import hashlib
import hmac
import json
import os

os.environ["TESTING"] = "1"

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.main import app
from backend.services import facebook_oauth, facebook_webhook

client = TestClient(app)

_TEST_SECRET = "test-secret-key-for-jwt"


def _make_token(tenant_id: str = "tenant-001", role: str = "owner") -> str:
    from jose import jwt

    payload = {
        "tenant_id": tenant_id,
        "sub": tenant_id,
        "email": "test@example.com",
        "plan": "professional",
        "business_name": "Test Biz",
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(days=1),
    }
    return jwt.encode(payload, _TEST_SECRET, algorithm="HS256")


def _auth(tenant_id: str = "tenant-001", role: str = "owner") -> dict:
    return {"Authorization": f"Bearer {_make_token(tenant_id, role)}"}


def _mock_db():
    return MagicMock()


# ---------------------------------------------------------------------------
# facebook_oauth — pure helpers
# ---------------------------------------------------------------------------


class TestFacebookOAuthJwtSecret:
    def test_uses_jwt_secret_key_when_present(self):
        with patch("backend.services.facebook_oauth.settings") as mock_settings:
            mock_settings.jwt_secret_key = "real-secret"
            mock_settings.api_secret_key = "fallback"
            assert facebook_oauth.jwt_secret() == "real-secret"

    def test_falls_back_to_api_secret_key(self):
        with patch("backend.services.facebook_oauth.settings") as mock_settings:
            mock_settings.jwt_secret_key = ""
            mock_settings.api_secret_key = "fallback-secret"
            assert facebook_oauth.jwt_secret() == "fallback-secret"

    def test_returns_empty_when_neither_set(self):
        with patch("backend.services.facebook_oauth.settings") as mock_settings:
            mock_settings.jwt_secret_key = ""
            mock_settings.api_secret_key = ""
            assert facebook_oauth.jwt_secret() == ""


class TestFacebookOAuthStateTokens:
    def test_encode_decode_round_trip(self):
        with patch("backend.services.facebook_oauth.settings") as mock_settings:
            mock_settings.jwt_secret_key = "test-state-secret"
            mock_settings.api_secret_key = "test-state-secret"
            token = facebook_oauth.encode_state("tenant-A", "nonce-xyz")
            tenant_id, nonce = facebook_oauth.decode_state(token)
            assert tenant_id == "tenant-A"
            assert nonce == "nonce-xyz"

    def test_decode_rejects_garbage(self):
        with patch("backend.services.facebook_oauth.settings") as mock_settings:
            mock_settings.jwt_secret_key = "test-state-secret"
            mock_settings.api_secret_key = "test-state-secret"
            with pytest.raises(HTTPException) as exc:
                facebook_oauth.decode_state("not-a-jwt")
            assert exc.value.status_code == 400

    def test_decode_rejects_wrong_provider(self):
        from jose import jwt

        with patch("backend.services.facebook_oauth.settings") as mock_settings:
            mock_settings.jwt_secret_key = "test-state-secret"
            mock_settings.api_secret_key = "test-state-secret"
            bad = jwt.encode(
                {
                    "tenant_id": "t",
                    "nonce": "n",
                    "provider": "google",
                    "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
                },
                "test-state-secret",
                algorithm="HS256",
            )
            with pytest.raises(HTTPException) as exc:
                facebook_oauth.decode_state(bad)
            assert exc.value.status_code == 400

    def test_decode_rejects_missing_tenant_id(self):
        from jose import jwt

        with patch("backend.services.facebook_oauth.settings") as mock_settings:
            mock_settings.jwt_secret_key = "test-state-secret"
            mock_settings.api_secret_key = "test-state-secret"
            bad = jwt.encode(
                {
                    "nonce": "n",
                    "provider": "facebook",
                    "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
                },
                "test-state-secret",
                algorithm="HS256",
            )
            with pytest.raises(HTTPException) as exc:
                facebook_oauth.decode_state(bad)
            assert exc.value.status_code == 400

    def test_decode_rejects_missing_nonce(self):
        from jose import jwt

        with patch("backend.services.facebook_oauth.settings") as mock_settings:
            mock_settings.jwt_secret_key = "test-state-secret"
            mock_settings.api_secret_key = "test-state-secret"
            bad = jwt.encode(
                {
                    "tenant_id": "t",
                    "provider": "facebook",
                    "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
                },
                "test-state-secret",
                algorithm="HS256",
            )
            with pytest.raises(HTTPException) as exc:
                facebook_oauth.decode_state(bad)
            assert exc.value.status_code == 400


class TestFacebookOAuthAuthUrl:
    def test_build_auth_url_has_required_scopes_and_params(self):
        url = facebook_oauth.build_auth_url(
            app_id="123",
            redirect_uri="https://example.com/cb",
            state="abc",
        )
        assert "client_id=123" in url
        assert "redirect_uri=https://example.com/cb" in url
        assert "state=abc" in url
        assert "pages_messaging" in url
        assert "pages_manage_metadata" in url
        assert "response_type=code" in url


# ---------------------------------------------------------------------------
# facebook_oauth — async Graph API wrappers (httpx mocked)
# ---------------------------------------------------------------------------


class _FakeResponse:
    def __init__(self, json_data=None, status_code=200, text=""):
        self._json = json_data or {}
        self.status_code = status_code
        self.text = text

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            from httpx import HTTPStatusError, Request, Response

            req = Request("GET", "https://example.com")
            resp = Response(self.status_code, request=req)
            raise HTTPStatusError("err", request=req, response=resp)


class _FakeAsyncClient:
    def __init__(self, *, get_return=None, post_return=None, delete_return=None, **_kw):
        self._get_return = get_return or _FakeResponse({})
        self._post_return = post_return or _FakeResponse({})
        self._delete_return = delete_return or _FakeResponse({})

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get(self, *_a, **_kw):
        return self._get_return

    async def post(self, *_a, **_kw):
        return self._post_return

    async def delete(self, *_a, **_kw):
        return self._delete_return


class TestFacebookOAuthAsyncWrappers:
    async def test_exchange_code_returns_access_token(self):
        fake = _FakeAsyncClient(get_return=_FakeResponse({"access_token": "TOKEN_XYZ"}))
        with patch("backend.services.facebook_oauth.httpx.AsyncClient", return_value=fake):
            token = await facebook_oauth.exchange_code_for_user_token(
                "app", "secret", "https://x/cb", "code-abc",
            )
        assert token == "TOKEN_XYZ"

    async def test_fetch_managed_pages_returns_list(self):
        fake = _FakeAsyncClient(
            get_return=_FakeResponse(
                {"data": [{"id": "p1", "name": "Biz", "access_token": "T1"}]}
            )
        )
        with patch("backend.services.facebook_oauth.httpx.AsyncClient", return_value=fake):
            pages = await facebook_oauth.fetch_managed_pages("user-token")
        assert pages == [{"id": "p1", "name": "Biz", "access_token": "T1"}]

    async def test_fetch_managed_pages_empty(self):
        fake = _FakeAsyncClient(get_return=_FakeResponse({}))
        with patch("backend.services.facebook_oauth.httpx.AsyncClient", return_value=fake):
            pages = await facebook_oauth.fetch_managed_pages("user-token")
        assert pages == []

    async def test_subscribe_page_returns_status_and_snippet(self):
        fake = _FakeAsyncClient(
            post_return=_FakeResponse({}, status_code=200, text='{"success":true}')
        )
        with patch("backend.services.facebook_oauth.httpx.AsyncClient", return_value=fake):
            status, body = await facebook_oauth.subscribe_page("page-1", "page-tok")
        assert status == 200
        assert "success" in body

    async def test_unsubscribe_page_returns_status_and_snippet(self):
        fake = _FakeAsyncClient(
            delete_return=_FakeResponse({}, status_code=200, text='{"success":true}')
        )
        with patch("backend.services.facebook_oauth.httpx.AsyncClient", return_value=fake):
            status, body = await facebook_oauth.unsubscribe_page("page-1", "page-tok")
        assert status == 200
        assert "success" in body


# ---------------------------------------------------------------------------
# facebook_webhook — signature verification
# ---------------------------------------------------------------------------


def _sign(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


class TestFacebookWebhookSignature:
    def test_returns_false_when_secret_missing(self):
        with patch("backend.services.facebook_webhook.settings") as mock_settings:
            mock_settings.facebook_app_secret = ""
            assert facebook_webhook.verify_signature(b"body", _sign("x", b"body")) is False

    def test_returns_false_when_header_missing(self):
        with patch("backend.services.facebook_webhook.settings") as mock_settings:
            mock_settings.facebook_app_secret = "shh"
            assert facebook_webhook.verify_signature(b"body", None) is False

    def test_returns_false_when_header_malformed(self):
        with patch("backend.services.facebook_webhook.settings") as mock_settings:
            mock_settings.facebook_app_secret = "shh"
            assert facebook_webhook.verify_signature(b"body", "md5=abc") is False

    def test_returns_true_for_matching_signature(self):
        with patch("backend.services.facebook_webhook.settings") as mock_settings:
            mock_settings.facebook_app_secret = "shh"
            body = b'{"hello": "world"}'
            assert facebook_webhook.verify_signature(body, _sign("shh", body)) is True

    def test_returns_false_for_mismatched_signature(self):
        with patch("backend.services.facebook_webhook.settings") as mock_settings:
            mock_settings.facebook_app_secret = "shh"
            body = b'{"hello": "world"}'
            assert (
                facebook_webhook.verify_signature(body, _sign("other-secret", body))
                is False
            )


# ---------------------------------------------------------------------------
# facebook_webhook — event processor
# ---------------------------------------------------------------------------


class TestFacebookWebhookProcessEvent:
    async def test_empty_payload_noop(self):
        with patch(
            "backend.services.facebook_webhook.ingest_channel_message"
        ) as ingest:
            result = await facebook_webhook.process_event({})
            assert result is None
            assert ingest.call_count == 0

    async def test_skips_echo_messages(self):
        payload = {
            "entry": [
                {
                    "id": "page-1",
                    "messaging": [
                        {
                            "sender": {"id": "psid-1"},
                            "message": {"is_echo": True, "text": "echo!"},
                            "timestamp": 1700000000000,
                        }
                    ],
                }
            ]
        }
        with patch(
            "backend.services.facebook_webhook.ingest_channel_message"
        ) as ingest:
            result = await facebook_webhook.process_event(payload)
            assert result is None
            assert ingest.call_count == 0
            assert payload["entry"][0]["messaging"][0]["message"]["is_echo"] is True

    async def test_skips_missing_text(self):
        payload = {
            "entry": [
                {
                    "id": "page-1",
                    "messaging": [
                        {
                            "sender": {"id": "psid-1"},
                            "message": {"attachments": [{"type": "image"}]},
                        }
                    ],
                }
            ]
        }
        with patch(
            "backend.services.facebook_webhook.ingest_channel_message"
        ) as ingest:
            result = await facebook_webhook.process_event(payload)
            assert result is None
            assert ingest.call_count == 0
            message = payload["entry"][0]["messaging"][0]["message"]
            assert "text" not in message
            assert message["attachments"][0]["type"] == "image"

    async def test_success_path_calls_ingest(self):
        payload = {
            "entry": [
                {
                    "id": "page-1",
                    "messaging": [
                        {
                            "sender": {"id": "psid-1"},
                            "message": {"text": "hi"},
                            "timestamp": 1700000000000,
                        }
                    ],
                }
            ]
        }
        with patch(
            "backend.services.facebook_webhook.ingest_channel_message"
        ) as ingest:
            ingest.return_value = {
                "tenant_id": "tenant-1",
                "conversation_id": "conv-1",
            }
            result = await facebook_webhook.process_event(payload)
            assert result is None
            assert ingest.call_count == 1
            kwargs = ingest.call_args.kwargs
            assert kwargs["provider"] == "facebook"
            assert kwargs["page_id"] == "page-1"
            assert kwargs["sender_id"] == "psid-1"
            assert kwargs["sender_name"] is None
            assert kwargs["text"] == "hi"
            assert kwargs["timestamp_ms"] == 1700000000000

    async def test_ingest_exception_does_not_propagate(self):
        payload = {
            "entry": [
                {
                    "id": "page-1",
                    "messaging": [
                        {
                            "sender": {"id": "psid-1"},
                            "message": {"text": "hi"},
                        }
                    ],
                }
            ]
        }
        with patch(
            "backend.services.facebook_webhook.ingest_channel_message"
        ) as ingest:
            ingest.side_effect = RuntimeError("boom")
            # Must not raise — exception is swallowed and logged.
            await facebook_webhook.process_event(payload)


# ---------------------------------------------------------------------------
# Router — OAuth callback flow
# ---------------------------------------------------------------------------


class TestFacebookOAuthCallback:
    @patch("backend.routers.channels_facebook.settings")
    def test_callback_with_error_param_redirects(self, mock_settings):
        mock_settings.frontend_url = "https://app.example.com"
        resp = client.get(
            "/api/v1/channels/facebook/callback",
            params={"error": "access_denied", "error_description": "user said no"},
            follow_redirects=False,
        )
        assert resp.status_code in (302, 307)
        assert "facebook_error=access_denied" in resp.headers["location"]

    def test_callback_missing_code_or_state_returns_400(self):
        resp = client.get("/api/v1/channels/facebook/callback")
        assert resp.status_code == 400

    @patch("backend.routers.channels_facebook.get_service_supabase")
    @patch("backend.routers.channels_facebook.facebook_oauth")
    def test_callback_invalid_state_row_returns_400(self, mock_oauth, mock_db_factory):
        mock_oauth.decode_state.return_value = ("tenant-1", "nonce-1")
        db = _mock_db()
        mock_db_factory.return_value = db
        state_query = MagicMock()
        state_query.data = []
        db.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.is_.return_value.gt.return_value.limit.return_value.execute.return_value = state_query
        resp = client.get(
            "/api/v1/channels/facebook/callback",
            params={"code": "c", "state": "s"},
        )
        assert resp.status_code == 400

    @patch("backend.routers.channels_facebook.settings")
    @patch("backend.routers.channels_facebook.get_service_supabase")
    @patch("backend.routers.channels_facebook.facebook_oauth")
    def test_callback_missing_app_config_returns_503(
        self, mock_oauth, mock_db_factory, mock_settings
    ):
        mock_settings.facebook_app_id = ""
        mock_settings.facebook_app_secret = ""
        mock_settings.api_url = "https://api.example.com"
        mock_settings.frontend_url = "https://app.example.com"
        mock_oauth.decode_state.return_value = ("tenant-1", "nonce-1")
        db = _mock_db()
        mock_db_factory.return_value = db
        state_query = MagicMock()
        state_query.data = [{"nonce": "nonce-1"}]
        db.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.is_.return_value.gt.return_value.limit.return_value.execute.return_value = state_query
        db.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock()
        resp = client.get(
            "/api/v1/channels/facebook/callback",
            params={"code": "c", "state": "s"},
        )
        assert resp.status_code == 503

    @patch("backend.routers.channels_facebook.settings")
    @patch("backend.routers.channels_facebook.get_service_supabase")
    @patch("backend.routers.channels_facebook.facebook_oauth")
    def test_callback_token_exchange_failure_returns_502(
        self, mock_oauth, mock_db_factory, mock_settings
    ):
        mock_settings.facebook_app_id = "FB_APP"
        mock_settings.facebook_app_secret = "FB_SECRET"
        mock_settings.api_url = "https://api.example.com"
        mock_settings.frontend_url = "https://app.example.com"
        mock_oauth.decode_state.return_value = ("tenant-1", "nonce-1")
        mock_oauth.exchange_code_for_user_token = AsyncMock(
            side_effect=RuntimeError("graph down")
        )
        db = _mock_db()
        mock_db_factory.return_value = db
        state_query = MagicMock()
        state_query.data = [{"nonce": "nonce-1"}]
        db.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.is_.return_value.gt.return_value.limit.return_value.execute.return_value = state_query
        db.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock()
        resp = client.get(
            "/api/v1/channels/facebook/callback",
            params={"code": "c", "state": "s"},
        )
        assert resp.status_code == 502

    @patch("backend.routers.channels_facebook.settings")
    @patch("backend.routers.channels_facebook.get_service_supabase")
    @patch("backend.routers.channels_facebook.facebook_oauth")
    def test_callback_no_pages_returns_400(
        self, mock_oauth, mock_db_factory, mock_settings
    ):
        mock_settings.facebook_app_id = "FB_APP"
        mock_settings.facebook_app_secret = "FB_SECRET"
        mock_settings.api_url = "https://api.example.com"
        mock_settings.frontend_url = "https://app.example.com"
        mock_oauth.decode_state.return_value = ("tenant-1", "nonce-1")
        mock_oauth.exchange_code_for_user_token = AsyncMock(return_value="UTOK")
        mock_oauth.fetch_managed_pages = AsyncMock(return_value=[])
        db = _mock_db()
        mock_db_factory.return_value = db
        state_query = MagicMock()
        state_query.data = [{"nonce": "nonce-1"}]
        db.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.is_.return_value.gt.return_value.limit.return_value.execute.return_value = state_query
        db.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock()
        resp = client.get(
            "/api/v1/channels/facebook/callback",
            params={"code": "c", "state": "s"},
        )
        assert resp.status_code == 400

    @patch("backend.routers.channels_facebook.settings")
    @patch("backend.routers.channels_facebook.get_service_supabase")
    @patch("backend.routers.channels_facebook.facebook_oauth")
    def test_callback_success_redirects_to_frontend(
        self, mock_oauth, mock_db_factory, mock_settings
    ):
        mock_settings.facebook_app_id = "FB_APP"
        mock_settings.facebook_app_secret = "FB_SECRET"
        mock_settings.api_url = "https://api.example.com"
        mock_settings.frontend_url = "https://app.example.com"
        mock_oauth.decode_state.return_value = ("tenant-1", "nonce-1")
        mock_oauth.exchange_code_for_user_token = AsyncMock(return_value="UTOK")
        mock_oauth.fetch_managed_pages = AsyncMock(
            return_value=[
                {"id": "page-1", "name": "Biz", "access_token": "PTOK"},
            ]
        )
        mock_oauth.subscribe_page = AsyncMock(return_value=(200, "ok"))

        db = _mock_db()
        mock_db_factory.return_value = db

        state_query = MagicMock()
        state_query.data = [{"nonce": "nonce-1"}]
        existing_query = MagicMock()
        existing_query.data = []

        # First call to db.table().select()...execute is state lookup,
        # second is integrations existing lookup. Use side_effect.
        select_chain = (
            db.table.return_value.select.return_value.eq.return_value
        )
        select_chain.eq.return_value.eq.return_value.is_.return_value.gt.return_value.limit.return_value.execute.return_value = state_query
        select_chain.eq.return_value.limit.return_value.execute.return_value = existing_query

        db.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock()
        db.table.return_value.insert.return_value.execute.return_value = MagicMock()

        resp = client.get(
            "/api/v1/channels/facebook/callback",
            params={"code": "c", "state": "s"},
            follow_redirects=False,
        )
        assert resp.status_code in (302, 307)
        assert "facebook_connected=true" in resp.headers["location"]


# ---------------------------------------------------------------------------
# Router — auth-url endpoint
# ---------------------------------------------------------------------------


class TestFacebookAuthUrlEndpoint:
    @patch("backend.routers.auth.settings")
    @patch("backend.routers.channels_facebook.settings")
    def test_auth_url_missing_app_id_returns_503(
        self, mock_fb_settings, mock_auth_settings
    ):
        mock_auth_settings.api_secret_key = _TEST_SECRET
        mock_fb_settings.facebook_app_id = ""
        resp = client.get(
            "/api/v1/channels/facebook/tenant-001/auth-url",
            headers=_auth(),
        )
        assert resp.status_code == 503

    @patch("backend.routers.auth.settings")
    @patch("backend.routers.channels_facebook.settings")
    @patch("backend.routers.channels_facebook.get_service_supabase")
    def test_auth_url_success_returns_url(
        self, mock_db_factory, mock_fb_settings, mock_auth_settings
    ):
        mock_auth_settings.api_secret_key = _TEST_SECRET
        mock_fb_settings.facebook_app_id = "FB_APP"
        mock_fb_settings.api_url = "https://api.example.com"
        db = _mock_db()
        mock_db_factory.return_value = db
        db.table.return_value.insert.return_value.execute.return_value = MagicMock()
        resp = client.get(
            "/api/v1/channels/facebook/tenant-001/auth-url",
            headers=_auth(),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "auth_url" in body
        assert "client_id=FB_APP" in body["auth_url"]
        assert "state=" in body["auth_url"]

    @patch("backend.routers.auth.settings")
    @patch("backend.routers.channels_facebook.settings")
    @patch("backend.routers.channels_facebook.get_service_supabase")
    def test_auth_url_db_failure_returns_500(
        self, mock_db_factory, mock_fb_settings, mock_auth_settings
    ):
        mock_auth_settings.api_secret_key = _TEST_SECRET
        mock_fb_settings.facebook_app_id = "FB_APP"
        mock_fb_settings.api_url = "https://api.example.com"
        db = _mock_db()
        mock_db_factory.return_value = db
        db.table.return_value.insert.return_value.execute.side_effect = RuntimeError(
            "db down"
        )
        resp = client.get(
            "/api/v1/channels/facebook/tenant-001/auth-url",
            headers=_auth(),
        )
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# Router — disconnect endpoint
# ---------------------------------------------------------------------------


class TestFacebookDisconnectEndpoint:
    @patch("backend.routers.auth.settings")
    @patch("backend.routers.channels_facebook.get_service_supabase")
    def test_disconnect_no_integration_returns_404(
        self, mock_db_factory, mock_auth_settings
    ):
        mock_auth_settings.api_secret_key = _TEST_SECRET
        db = _mock_db()
        mock_db_factory.return_value = db
        result = MagicMock()
        result.data = []
        db.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = result
        resp = client.delete(
            "/api/v1/channels/facebook/tenant-001/disconnect",
            headers=_auth(),
        )
        assert resp.status_code == 404

    @patch("backend.routers.auth.settings")
    @patch("backend.routers.channels_facebook.get_service_supabase")
    @patch("backend.routers.channels_facebook.facebook_oauth")
    def test_disconnect_success_unsubscribes_and_deletes(
        self, mock_oauth, mock_db_factory, mock_auth_settings
    ):
        mock_auth_settings.api_secret_key = _TEST_SECRET
        mock_oauth.unsubscribe_page = AsyncMock(return_value=(200, "ok"))
        db = _mock_db()
        mock_db_factory.return_value = db
        select_result = MagicMock()
        select_result.data = [
            {
                "id": "intg-1",
                "access_token": "PTOK",
                "metadata": {"page_id": "page-1", "page_name": "Biz"},
            }
        ]
        db.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = select_result
        db.table.return_value.delete.return_value.eq.return_value.execute.return_value = MagicMock()
        resp = client.delete(
            "/api/v1/channels/facebook/tenant-001/disconnect",
            headers=_auth(),
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        mock_oauth.unsubscribe_page.assert_awaited_once_with("page-1", "PTOK")

    @patch("backend.routers.auth.settings")
    @patch("backend.routers.channels_facebook.get_service_supabase")
    @patch("backend.routers.channels_facebook.facebook_oauth")
    def test_disconnect_unsubscribe_failure_still_deletes(
        self, mock_oauth, mock_db_factory, mock_auth_settings
    ):
        mock_auth_settings.api_secret_key = _TEST_SECRET
        mock_oauth.unsubscribe_page = AsyncMock(
            side_effect=RuntimeError("graph down")
        )
        db = _mock_db()
        mock_db_factory.return_value = db
        select_result = MagicMock()
        select_result.data = [
            {
                "id": "intg-1",
                "access_token": "PTOK",
                "metadata": {"page_id": "page-1", "page_name": "Biz"},
            }
        ]
        db.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = select_result
        db.table.return_value.delete.return_value.eq.return_value.execute.return_value = MagicMock()
        resp = client.delete(
            "/api/v1/channels/facebook/tenant-001/disconnect",
            headers=_auth(),
        )
        # unsubscribe failure is non-fatal — still 200
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Router — webhook POST signature path
# ---------------------------------------------------------------------------


class TestFacebookWebhookInbound:
    @patch("backend.routers.channels_facebook.facebook_webhook")
    def test_invalid_signature_returns_403(self, mock_fb_webhook):
        mock_fb_webhook.verify_signature.return_value = False
        resp = client.post(
            "/api/v1/channels/facebook/webhook",
            json={"object": "page", "entry": []},
        )
        assert resp.status_code == 403

    @patch("backend.routers.channels_facebook.facebook_webhook")
    def test_invalid_json_returns_400(self, mock_fb_webhook):
        mock_fb_webhook.verify_signature.return_value = True
        resp = client.post(
            "/api/v1/channels/facebook/webhook",
            content=b"not-json{{",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 400

    @patch("backend.routers.channels_facebook.facebook_webhook")
    def test_valid_signature_schedules_background_task(self, mock_fb_webhook):
        mock_fb_webhook.verify_signature.return_value = True
        mock_fb_webhook.process_event = AsyncMock(return_value=None)
        payload = {"object": "page", "entry": []}
        resp = client.post(
            "/api/v1/channels/facebook/webhook",
            content=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}
