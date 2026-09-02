"""GH #669 — DemoRoleBlockMiddleware contract tests.

Mutating methods with a verified role=demo JWT are 403 outside the allowlist;
allowlisted auth/widget/webhook paths and non-demo JWTs still pass through.
GET is never blocked by this middleware.
"""

import os

os.environ["TESTING"] = "1"

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.middleware.demo_role_guard import (
    DEMO_BLOCK_DETAIL,
    DEMO_MUTATION_ALLOWLIST_PREFIXES,
    path_is_demo_mutation_allowed,
)


def _make_jwt(role="demo", tenant_id="demo-t1", secret="test-secret-key-for-jwt"):
    from jose import jwt

    payload = {
        "tenant_id": tenant_id,
        "sub": tenant_id,
        "email": "demo@agentnexlify.com",
        "plan": "professional",
        "business_name": "Reliable Plumbing Co. (DEMO)",
        "role": role,
        "is_team_member": False,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


@pytest.fixture
def test_client(mock_settings):
    mock_settings.sentry_dsn = None
    mock_settings.supabase_service_key = "fake-key"
    mock_settings.jwt_secret_key = "test-secret-key-for-jwt"
    mock_settings.api_secret_key = "test-secret-key-for-jwt"
    db_mock = MagicMock()
    patches = [
        patch("backend.models.database.get_supabase", return_value=db_mock),
        patch("backend.routers.auth.get_service_supabase", return_value=db_mock),
        patch("backend.routers.auth.settings", mock_settings),
        patch("backend.routers.auth_demo.get_service_supabase", return_value=db_mock),
        patch("backend.routers.os_threads.get_service_supabase", return_value=db_mock),
        patch("backend.services.auth_service.settings", mock_settings),
        patch("backend.middleware.demo_role_guard._jwt_secret", return_value="test-secret-key-for-jwt"),
    ]
    for p in patches:
        p.start()
    from backend.main import app

    client = TestClient(app)
    yield client, db_mock
    for p in patches:
        p.stop()


class TestAllowlistHelper:
    def test_auth_and_widget_prefixes_allowed(self):
        assert path_is_demo_mutation_allowed("/api/v1/auth/demo-login")
        assert path_is_demo_mutation_allowed("/api/v1/widget/chat")
        assert path_is_demo_mutation_allowed("/api/v1/webhooks/stripe")
        assert path_is_demo_mutation_allowed("/api/widget/photo-quote")

    def test_dashboard_mutations_not_allowlisted(self):
        assert not path_is_demo_mutation_allowed("/api/v1/leads")
        assert not path_is_demo_mutation_allowed("/api/v1/billing/checkout")
        assert not path_is_demo_mutation_allowed("/api/v1/os/threads")

    def test_allowlist_constant_covers_ingress_surfaces(self):
        joined = " ".join(DEMO_MUTATION_ALLOWLIST_PREFIXES)
        assert "/api/v1/auth" in joined
        assert "/api/v1/webhooks" in joined
        assert "/api/v1/widget" in joined


class TestDemoRoleMiddleware:
    def test_demo_post_outside_allowlist_is_403(self, test_client):
        client, _db = test_client
        resp = client.post(
            "/api/v1/leads",
            json={"name": "x", "email": "x@example.com"},
            headers={"Authorization": f"Bearer {_make_jwt(role='demo')}"},
        )
        assert resp.status_code == 403
        assert resp.json()["detail"] == DEMO_BLOCK_DETAIL

    def test_owner_post_outside_allowlist_not_blocked_by_middleware(self, test_client):
        client, _db = test_client
        resp = client.post(
            "/api/v1/leads",
            json={"name": "x", "email": "x@example.com"},
            headers={"Authorization": f"Bearer {_make_jwt(role='owner')}"},
        )
        assert resp.status_code != 403

    def test_demo_get_never_blocked(self, test_client):
        client, db = test_client
        table = MagicMock()
        for m in ["select", "eq", "order", "limit", "range"]:
            getattr(table, m).return_value = table
        table.execute.return_value = MagicMock(data=[], count=0)
        db.table.return_value = table
        resp = client.get(
            "/api/v1/os/threads",
            headers={"Authorization": f"Bearer {_make_jwt(role='demo')}"},
        )
        assert resp.status_code == 200

    def test_demo_login_post_allowlisted(self, test_client):
        client, db = test_client
        table = MagicMock()
        for m in ["select", "eq", "limit"]:
            getattr(table, m).return_value = table
        table.execute.return_value = MagicMock(
            data=[
                {
                    "id": "demo-t1",
                    "business_name": "Reliable Plumbing Co. (DEMO)",
                    "plan": "professional",
                    "business_type": "plumbing",
                }
            ]
        )
        db.table.return_value = table
        resp = client.post("/api/v1/auth/demo-login")
        assert resp.status_code == 200
        assert resp.json()["demo"] is True

    def test_middleware_registered_on_app(self):
        from backend.main import app
        from backend.middleware.demo_role_guard import DemoRoleBlockMiddleware

        assert any(
            getattr(m, "cls", None) is DemoRoleBlockMiddleware
            for m in app.user_middleware
        ), "DemoRoleBlockMiddleware must be registered in backend/main.py"
