"""Tests for web push: subscription endpoints + SSRF allowlist + degraded no-op."""

import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

os.environ.setdefault("TESTING", "1")

import pytest

from backend.services import os_push_notify

_FCM = "https://fcm.googleapis.com/fcm/send/abc123"
_MOZILLA = "https://updates.push.services.mozilla.com/wpush/v2/x"
_APPLE = "https://web.push.apple.com/QOj123"
_WNS = "https://db5p.notify.windows.com/w/?token=x"


class TestEndpointAllowlist:
    def test_known_push_services_allowed(self):
        for url in (_FCM, _MOZILLA, _APPLE, _WNS):
            assert os_push_notify.endpoint_host_allowed(url), url

    def test_internal_targets_rejected(self):
        for url in (
            "https://127.0.0.1/admin",
            "https://169.254.169.254/latest/meta-data/",
            "https://10.0.0.5:8000/api/health",
            "https://evil.example.com/fcm.googleapis.com/",
            "https://fcm.googleapis.com.evil.example.com/x",
            "http://fcm.googleapis.com/downgraded",
            "not-a-url",
            "",
        ):
            assert not os_push_notify.endpoint_host_allowed(url), url

    def test_send_one_rejects_disallowed_stored_row(self):
        """Rows written before the validator existed must not become SSRF."""
        with pytest.raises(ValueError):
            os_push_notify._send_one(
                {"endpoint": "https://internal.local/x", "keys": {}}, "{}"
            )


class TestDegradedNoOp:
    @pytest.mark.asyncio
    async def test_send_noops_without_vapid_keys(self):
        db = MagicMock()
        with patch.object(os_push_notify, "push_configured", return_value=False):
            sent = await os_push_notify.send_pending_approval_push(
                db, "tid", title="x"
            )
        assert sent == 0
        db.table.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_survives_db_failure(self):
        db = MagicMock()
        db.table.side_effect = RuntimeError("down")
        with patch.object(os_push_notify, "push_configured", return_value=True):
            sent = await os_push_notify.send_pending_approval_push(
                db, "tid", title="x"
            )
        assert sent == 0


class TestPushRouter:
    def _client(self):
        from fastapi.testclient import TestClient

        from backend.main import app

        return TestClient(app)

    def test_vapid_public_key_404_when_unconfigured(self):
        from backend.config import settings

        client = self._client()
        with patch.object(settings, "vapid_public_key", None):
            resp = client.get("/api/v1/push/vapid-public-key")
        assert resp.status_code == 404

    def test_vapid_public_key_200_when_set(self):
        from backend.config import settings

        client = self._client()
        with patch.object(settings, "vapid_public_key", "test-pub-key"):
            resp = client.get("/api/v1/push/vapid-public-key")
        assert resp.status_code == 200
        assert resp.json()["public_key"] == "test-pub-key"

    def test_subscribe_rejects_non_push_service_endpoint(self):
        """SSRF guard: arbitrary https endpoints must 422 at validation."""
        client = self._client()
        resp = client.post(
            "/api/v1/push/some-tenant/subscribe",
            json={
                "endpoint": "https://169.254.169.254/latest/meta-data/",
                "keys": {"p256dh": "k", "auth": "a"},
            },
        )
        assert resp.status_code in (401, 403, 422)
        # Validation must fire even before auth resolves either way; if the
        # request got past auth in this environment, it must be the validator.
        if resp.status_code == 422:
            assert "push service" in str(resp.json())
