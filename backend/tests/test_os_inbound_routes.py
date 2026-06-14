"""Tests for Agent OS inbound bridge toggle + config routes.

Covers:
  - GET  /api/v1/os/inbound/bridge-config — any authenticated role can read
  - POST /api/v1/os/inbound/bridge-toggle — owner can flip, persists
  - POST /api/v1/os/inbound/bridge-toggle — non-owner gets 403
  - POST /api/v1/os/inbound/bridge-toggle — invalid source returns 422
  - GET after POST reflects the new state
"""

from datetime import datetime, timedelta, timezone


from backend.main import app
from backend.tests.conftest import SyncASGITestClient, _make_auth_token

_CLIENT_ID = "00000000-0000-0000-0000-000000000aa1"


def _owner_headers():
    return {"Authorization": f"Bearer {_make_auth_token(_CLIENT_ID)}"}


def _make_token_with_role(tenant_id: str, role: str) -> str:
    """Mint a JWT with an explicit non-owner role for 403 tests."""
    from jose import jwt
    from backend.config import settings

    payload = {
        "tenant_id": tenant_id,
        "email": f"{role}@test.com",
        "plan": "growth",
        "business_name": "Test Business",
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=24),
    }
    return jwt.encode(payload, settings.api_secret_key, algorithm="HS256")


def _member_headers():
    return {"Authorization": f"Bearer {_make_token_with_role(_CLIENT_ID, 'member')}"}


def _make_client():
    return SyncASGITestClient(app)


# ---------------------------------------------------------------------------
# GET /bridge-config
# ---------------------------------------------------------------------------


class TestGetBridgeConfig:
    def test_returns_default_config_for_authenticated_caller(self, monkeypatch):
        captured: dict = {}

        def _fake_get_bridge_config(db, client_id):
            captured["client_id"] = client_id
            return {
                "widget_enabled": True,
                "email_enabled": False,
                "sms_enabled": False,
                "facebook_enabled": False,
                "email_provider": None,
                "email_inbound_address": None,
            }

        from backend.services import os_inbound_bridge

        monkeypatch.setattr(
            os_inbound_bridge, "get_bridge_config", _fake_get_bridge_config
        )

        client = _make_client()
        try:
            resp = client.get(
                "/api/v1/os/inbound/bridge-config", headers=_owner_headers()
            )
        finally:
            client.close()

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["widget_enabled"] is True
        assert body["email_enabled"] is False
        assert captured["client_id"] == _CLIENT_ID

    def test_member_role_can_read_config(self, monkeypatch):
        """GET is open to any authenticated user, not just owners."""
        from backend.services import os_inbound_bridge

        monkeypatch.setattr(
            os_inbound_bridge,
            "get_bridge_config",
            lambda db, client_id: {"widget_enabled": True},
        )

        client = _make_client()
        try:
            resp = client.get(
                "/api/v1/os/inbound/bridge-config", headers=_member_headers()
            )
        finally:
            client.close()

        assert resp.status_code == 200, resp.text

    def test_unauthenticated_request_rejected(self):
        client = _make_client()
        try:
            resp = client.get("/api/v1/os/inbound/bridge-config")
        finally:
            client.close()

        # 401/403/422 — project convention for "unauthenticated rejection"
        # (matches test_tenant_isolation.py + test_managed_agents.py). 422 comes
        # from FastAPI's required-Header validation in get_current_tenant.
        assert resp.status_code in (401, 403, 422), resp.text


# ---------------------------------------------------------------------------
# POST /bridge-toggle
# ---------------------------------------------------------------------------


class TestPostBridgeToggle:
    def test_owner_can_toggle_widget_off(self, monkeypatch):
        captured: dict = {}

        def _fake_set_bridge_toggle(db, client_id, source, enabled):
            captured["args"] = (client_id, source, enabled)
            return {
                "widget_enabled": enabled,
                "email_enabled": False,
                "sms_enabled": False,
                "facebook_enabled": False,
                "email_provider": None,
                "email_inbound_address": None,
            }

        from backend.services import os_inbound_bridge

        monkeypatch.setattr(
            os_inbound_bridge, "set_bridge_toggle", _fake_set_bridge_toggle
        )

        client = _make_client()
        try:
            resp = client.post(
                "/api/v1/os/inbound/bridge-toggle",
                headers=_owner_headers(),
                json={"source": "widget", "enabled": False},
            )
        finally:
            client.close()

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["widget_enabled"] is False
        assert captured["args"] == (_CLIENT_ID, "widget", False)

    def test_owner_can_toggle_email_on(self, monkeypatch):
        from backend.services import os_inbound_bridge

        monkeypatch.setattr(
            os_inbound_bridge,
            "set_bridge_toggle",
            lambda db, client_id, source, enabled: {f"{source}_enabled": enabled},
        )

        client = _make_client()
        try:
            resp = client.post(
                "/api/v1/os/inbound/bridge-toggle",
                headers=_owner_headers(),
                json={"source": "email", "enabled": True},
            )
        finally:
            client.close()

        assert resp.status_code == 200, resp.text
        assert resp.json()["email_enabled"] is True

    def test_non_owner_gets_403(self, monkeypatch):
        """member role must NOT be able to flip a bridge."""
        call_log: list = []

        from backend.services import os_inbound_bridge

        def _should_not_be_called(*args, **kwargs):
            call_log.append((args, kwargs))
            return {}

        monkeypatch.setattr(
            os_inbound_bridge, "set_bridge_toggle", _should_not_be_called
        )

        client = _make_client()
        try:
            resp = client.post(
                "/api/v1/os/inbound/bridge-toggle",
                headers=_member_headers(),
                json={"source": "widget", "enabled": True},
            )
        finally:
            client.close()

        assert resp.status_code == 403, resp.text
        assert call_log == [], "service must not run when role check fails"

    def test_invalid_source_returns_422(self, monkeypatch):
        """Pydantic Literal restricts to widget/email/sms/facebook."""
        from backend.services import os_inbound_bridge

        call_log: list = []
        monkeypatch.setattr(
            os_inbound_bridge,
            "set_bridge_toggle",
            lambda *a, **k: call_log.append((a, k)) or {},
        )

        client = _make_client()
        try:
            resp = client.post(
                "/api/v1/os/inbound/bridge-toggle",
                headers=_owner_headers(),
                json={"source": "slack", "enabled": True},
            )
        finally:
            client.close()

        assert resp.status_code == 422, resp.text
        assert call_log == [], "service must not run when source validation fails"

    def test_missing_field_returns_422(self):
        client = _make_client()
        try:
            resp = client.post(
                "/api/v1/os/inbound/bridge-toggle",
                headers=_owner_headers(),
                json={"source": "widget"},  # missing "enabled"
            )
        finally:
            client.close()

        assert resp.status_code == 422, resp.text


# ---------------------------------------------------------------------------
# GET after POST integration
# ---------------------------------------------------------------------------


class TestPostThenGet:
    def test_get_reflects_state_after_post(self, monkeypatch):
        """End-to-end: POST flips a flag, GET returns the new state.

        Both calls are stubbed against the same in-memory dict to simulate
        persistence without hitting Supabase.
        """
        state = {
            "widget_enabled": True,
            "email_enabled": False,
            "sms_enabled": False,
            "facebook_enabled": False,
            "email_provider": None,
            "email_inbound_address": None,
        }

        def _fake_get(db, client_id):
            return dict(state)

        def _fake_set(db, client_id, source, enabled):
            state[f"{source}_enabled"] = enabled
            return dict(state)

        from backend.services import os_inbound_bridge

        monkeypatch.setattr(os_inbound_bridge, "get_bridge_config", _fake_get)
        monkeypatch.setattr(os_inbound_bridge, "set_bridge_toggle", _fake_set)

        client = _make_client()
        try:
            before = client.get(
                "/api/v1/os/inbound/bridge-config", headers=_owner_headers()
            )
            assert before.json()["sms_enabled"] is False

            flip = client.post(
                "/api/v1/os/inbound/bridge-toggle",
                headers=_owner_headers(),
                json={"source": "sms", "enabled": True},
            )
            assert flip.status_code == 200, flip.text

            after = client.get(
                "/api/v1/os/inbound/bridge-config", headers=_owner_headers()
            )
        finally:
            client.close()

        assert after.json()["sms_enabled"] is True


# ---------------------------------------------------------------------------
# POST /bridge-config (non-toggle config setter)
# ---------------------------------------------------------------------------


class TestPostBridgeConfig:
    def test_owner_can_set_email_inbound_address(self, monkeypatch):
        captured: dict = {}

        def _fake_set_bridge_config(db, client_id, updates):
            captured["args"] = (client_id, dict(updates))
            return {
                "widget_enabled": True,
                "email_enabled": False,
                "sms_enabled": False,
                "facebook_enabled": False,
                "email_provider": "postmark",
                "email_inbound_address": updates.get("email_inbound_address"),
            }

        from backend.services import os_inbound_bridge

        monkeypatch.setattr(
            os_inbound_bridge, "set_bridge_config", _fake_set_bridge_config
        )

        client = _make_client()
        try:
            resp = client.post(
                "/api/v1/os/inbound/bridge-config",
                headers=_owner_headers(),
                json={
                    "email_inbound_address": "support@tenant.example",
                    "email_provider": "postmark",
                },
            )
        finally:
            client.close()

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["email_provider"] == "postmark"
        assert captured["args"][0] == _CLIENT_ID
        assert captured["args"][1] == {
            "email_inbound_address": "support@tenant.example",
            "email_provider": "postmark",
        }

    def test_partial_update_only_includes_sent_fields(self, monkeypatch):
        """model_fields_set must filter out fields the client did NOT send.

        Otherwise a caller patching only ``email_provider`` would
        accidentally clear ``email_inbound_address`` because the absent
        field defaults to ``None``.
        """
        captured: dict = {}

        def _fake_set_bridge_config(db, client_id, updates):
            captured["updates"] = dict(updates)
            return {"email_provider": updates.get("email_provider")}

        from backend.services import os_inbound_bridge

        monkeypatch.setattr(
            os_inbound_bridge, "set_bridge_config", _fake_set_bridge_config
        )

        client = _make_client()
        try:
            resp = client.post(
                "/api/v1/os/inbound/bridge-config",
                headers=_owner_headers(),
                json={"email_provider": "mailgun"},
            )
        finally:
            client.close()

        assert resp.status_code == 200, resp.text
        assert captured["updates"] == {"email_provider": "mailgun"}
        assert "email_inbound_address" not in captured["updates"]

    def test_non_owner_gets_403(self, monkeypatch):
        call_log: list = []
        from backend.services import os_inbound_bridge

        monkeypatch.setattr(
            os_inbound_bridge,
            "set_bridge_config",
            lambda *a, **k: call_log.append((a, k)) or {},
        )

        client = _make_client()
        try:
            resp = client.post(
                "/api/v1/os/inbound/bridge-config",
                headers=_member_headers(),
                json={"email_inbound_address": "x@y.com"},
            )
        finally:
            client.close()

        assert resp.status_code == 403, resp.text
        assert call_log == [], "service must not run when role check fails"

    def test_invalid_provider_returns_422(self):
        """Pydantic Literal rejects unknown providers before service runs."""
        client = _make_client()
        try:
            resp = client.post(
                "/api/v1/os/inbound/bridge-config",
                headers=_owner_headers(),
                json={"email_provider": "sendgrid"},
            )
        finally:
            client.close()

        assert resp.status_code == 422, resp.text

    def test_empty_body_returns_current_config(self, monkeypatch):
        """No fields sent → endpoint returns current config (no-op write)."""
        from backend.services import os_inbound_bridge

        monkeypatch.setattr(
            os_inbound_bridge,
            "get_bridge_config",
            lambda db, client_id: {"email_inbound_address": "existing@x.com"},
        )

        called = {"set": 0}

        def _fake_set(*args, **kwargs):
            called["set"] += 1
            return {}

        monkeypatch.setattr(os_inbound_bridge, "set_bridge_config", _fake_set)

        client = _make_client()
        try:
            resp = client.post(
                "/api/v1/os/inbound/bridge-config",
                headers=_owner_headers(),
                json={},
            )
        finally:
            client.close()

        assert resp.status_code == 200, resp.text
        assert resp.json()["email_inbound_address"] == "existing@x.com"
        assert called["set"] == 0, "no-op body must not invoke setter"

    def test_service_validation_error_returns_400(self, monkeypatch):
        """ValueError from service (unknown field/bad provider) → 400."""
        from backend.services import os_inbound_bridge

        def _raise_value_error(db, client_id, updates):
            raise ValueError("Unknown bridge config fields: ['rogue']")

        monkeypatch.setattr(os_inbound_bridge, "set_bridge_config", _raise_value_error)

        client = _make_client()
        try:
            resp = client.post(
                "/api/v1/os/inbound/bridge-config",
                headers=_owner_headers(),
                json={"email_inbound_address": "x@y.com"},
            )
        finally:
            client.close()

        assert resp.status_code == 400, resp.text
        assert "Unknown bridge config fields" in resp.json()["detail"]
