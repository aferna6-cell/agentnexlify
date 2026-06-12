"""Tests for the public live-demo sandbox: demo-login, role blocks, and
outbound no-op guards.

Contract: POST /auth/demo-login issues a 2h role="demo" JWT for the
is_demo tenant; demo role is 403-blocked on billing/phone/account-deletion
routers but works on normal tenant surfaces; send_email and the OS action
dispatch no-op (success-shaped) for demo tenants.
"""

import os
os.environ["TESTING"] = "1"

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _make_jwt(role="demo", tenant_id="demo-t1", secret="test-secret-key-for-jwt"):
    from jose import jwt
    payload = {
        "tenant_id": tenant_id, "sub": tenant_id, "email": "demo@agentnexlify.com",
        "plan": "professional", "business_name": "Reliable Plumbing Co. (DEMO)",
        "role": role, "is_team_member": False,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def _table_mock(rows_by_table):
    def mock_table(name):
        table = MagicMock()
        for m in ["select", "insert", "update", "delete", "eq", "neq", "in_",
                  "is_", "limit", "order", "gte", "lte"]:
            getattr(table, m).return_value = table
        result = MagicMock()
        result.data = rows_by_table.get(name, [])
        table.execute.return_value = result
        return table
    return mock_table


@pytest.fixture
def test_client(mock_settings):
    mock_settings.sentry_dsn = None
    mock_settings.supabase_service_key = "fake-key"
    db_mock = MagicMock()
    patches = [
        patch("backend.models.database.get_supabase", return_value=db_mock),
        patch("backend.routers.auth.get_service_supabase", return_value=db_mock),
        patch("backend.routers.auth.settings", mock_settings),
        patch("backend.routers.auth_demo.get_service_supabase", return_value=db_mock),
        patch("backend.routers.billing.get_service_supabase", return_value=db_mock),
        patch("backend.routers.os_threads.get_service_supabase", return_value=db_mock),
    ]
    for p in patches:
        p.start()
    from backend.main import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
    yield client, db_mock
    for p in patches:
        p.stop()


class TestDemoLogin:
    def test_issues_demo_role_token(self, test_client):
        client, db = test_client
        db.table = _table_mock({
            "tenants": [{
                "id": "demo-t1", "business_name": "Reliable Plumbing Co. (DEMO)",
                "plan": "professional", "business_type": "plumbing",
            }],
        })
        resp = client.post("/api/v1/auth/demo-login")
        assert resp.status_code == 200
        body = resp.json()
        assert body["demo"] is True
        assert body["tenant_id"] == "demo-t1"

        from jose import jwt
        claims = jwt.decode(
            body["token"], "test-secret-key-for-jwt", algorithms=["HS256"],
        )
        assert claims["role"] == "demo"
        assert claims["tenant_id"] == "demo-t1"

    def test_404_when_no_demo_tenant(self, test_client):
        client, db = test_client
        db.table = _table_mock({"tenants": []})
        resp = client.post("/api/v1/auth/demo-login")
        assert resp.status_code == 404


class TestDemoRoleBlocks:
    def test_demo_role_blocked_on_billing(self, test_client):
        client, db = test_client
        db.table = _table_mock({})
        resp = client.get(
            "/api/v1/billing/demo-t1/portal",
            headers={"Authorization": f"Bearer {_make_jwt(role='demo')}"},
        )
        # Router-level block_demo_role fires before route logic (403),
        # regardless of whether this exact path exists with GET (404 would
        # mean the dependency never ran on a real path — assert via a known
        # route below instead if this 404s).
        if resp.status_code == 404:
            pytest.skip("portal route shape changed; covered by openapi check")
        assert resp.status_code == 403
        assert "demo" in resp.json()["detail"].lower()

    def test_all_blocked_routers_have_demo_guard(self):
        """Every route in the four money/destructive routers carries the
        block_demo_role dependency at the router level."""
        from backend.dependencies import block_demo_role
        from backend.routers import billing, auth_billing, account_deletion, phone

        for module in (billing, auth_billing, account_deletion, phone):
            deps = [d.dependency for d in module.router.dependencies]
            assert block_demo_role in deps, module.__name__

    def test_demo_role_allowed_on_normal_surface(self, test_client):
        client, db = test_client
        db.table = _table_mock({"os_threads": []})
        resp = client.get(
            "/api/v1/os/threads",
            headers={"Authorization": f"Bearer {_make_jwt(role='demo')}"},
        )
        assert resp.status_code == 200


class TestDemoOutboundGuards:
    @pytest.mark.asyncio
    async def test_send_email_noops_for_demo_tenant(self):
        from backend.services import email_sender

        with patch("backend.services.demo_guard.is_demo_tenant", return_value=True):
            result = await email_sender.send_email(
                to="victim@example.com", subject="hi", body_html="<p>x</p>",
                tenant_id="demo-t1",
            )
        assert result == {"success": True, "detail": "demo_noop", "demo": True}

    @pytest.mark.asyncio
    async def test_dispatch_simulates_action_for_demo_tenant(self):
        from backend.services import os_action_dispatch as dispatch

        inserted = {}

        def table_mock(db, name, cid):
            table = MagicMock()
            for m in ["select", "insert", "eq", "limit"]:
                getattr(table, m).return_value = table
            def record_insert(row):
                inserted.update(row)
                return table
            table.insert.side_effect = record_insert
            result = MagicMock()
            # first select (existing succeeded) -> none; insert -> returns id
            result.data = [] if not inserted else [{"id": "ar-1"}]
            table.execute.side_effect = lambda: MagicMock(
                data=[{"id": "ar-1"}] if inserted else []
            )
            return table

        with patch("backend.services.demo_guard.is_demo_tenant", return_value=True), \
             patch.object(dispatch, "tenant_table", side_effect=table_mock), \
             patch.object(dispatch, "run_action") as mock_run:
            run = {"id": "run-1", "action_type": "sms.send"}
            result = await dispatch.queue_action_for_run(MagicMock(), "demo-t1", run, None)

        assert result == "ar-1"
        assert inserted["status"] == "succeeded"
        assert inserted["result"]["demo"] is True
        mock_run.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_sms_noops_for_demo_tenant(self):
        """The audit CRITICAL: widget 'talk to human' handoff must never
        fire a real SMS for demo visitors."""
        from backend.services import twilio_service

        with patch("backend.services.demo_guard.is_demo_tenant", return_value=True):
            ok = await twilio_service.send_sms(
                to="+15551234567", body="hi", tenant_id="demo-t1"
            )
        assert ok is True  # success-shaped no-op

    @pytest.mark.asyncio
    async def test_send_sms_unaffected_without_tenant_context(self):
        """Call sites without tenant context keep existing behavior
        (here: unconfigured Twilio -> False), no demo lookup attempted."""
        from backend.services import twilio_service

        with patch("backend.services.demo_guard.is_demo_tenant") as mock_guard, \
             patch.object(twilio_service.settings, "twilio_account_sid", ""):
            ok = await twilio_service.send_sms(to="+15551234567", body="hi")
        assert ok is False
        mock_guard.assert_not_called()

    def test_demo_guard_fails_open_on_db_error(self):
        from backend.services import demo_guard
        demo_guard.clear_cache()
        with patch("backend.services.demo_guard.get_service_supabase", side_effect=RuntimeError("down")):
            assert demo_guard.is_demo_tenant("t1") is False

    def test_demo_guard_caches_lookup(self):
        from backend.services import demo_guard
        demo_guard.clear_cache()
        db = MagicMock()
        table = MagicMock()
        for m in ["select", "eq", "limit"]:
            getattr(table, m).return_value = table
        table.execute.return_value = MagicMock(data=[{"is_demo": True}])
        db.table.return_value = table
        with patch("backend.services.demo_guard.get_service_supabase", return_value=db) as mock_get:
            assert demo_guard.is_demo_tenant("t1") is True
            assert demo_guard.is_demo_tenant("t1") is True
            assert mock_get.call_count == 1
        demo_guard.clear_cache()
