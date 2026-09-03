"""GH #669 follow-up — residual authenticated demo-write routes.

These paths sit under the DemoRoleBlockMiddleware allowlist
(``/api/v1/auth``, ``/api/v1/widget``) so the central middleware cannot
block them. Each residual write must carry ``block_demo_role`` or an
equivalent role guard (``require_role("owner", "admin")``).

Public auth / webhook / widget ingress stays open.
"""

import os

os.environ["TESTING"] = "1"

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.dependencies import block_demo_role
from backend.middleware.demo_role_guard import DEMO_BLOCK_DETAIL


TENANT = "demo-t1"
FAQ_BODY = {"question": "Hours?", "answer": "9-5", "category": "general"}


def _make_jwt(role="demo", tenant_id=TENANT, secret="test-secret-key-for-jwt"):
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


def _auth(role="demo"):
    return {"Authorization": f"Bearer {_make_jwt(role=role)}"}


def _walk_dep_calls(dependant):
    calls = []
    if dependant.call is not None:
        calls.append(dependant.call)
    for child in dependant.dependencies:
        calls.extend(_walk_dep_calls(child))
    return calls


def _route(app, method, path):
    for route in app.routes:
        if getattr(route, "path", None) == path and method in getattr(
            route, "methods", set()
        ):
            return route
    raise AssertionError(f"route not found: {method} {path}")


RESIDUAL_WRITES = (
    ("PUT", "/api/v1/auth/widget-config/{tenant_id}"),
    ("PUT", "/api/v1/widget/config/{tenant_id}/online-status"),
    ("PUT", "/api/v1/widget/config/{tenant_id}/allowed-domains"),
    ("POST", "/api/v1/auth/faq/{tenant_id}"),
    ("DELETE", "/api/v1/auth/faq/{tenant_id}/{faq_id}"),
    ("PUT", "/api/v1/auth/conversations/{tenant_id}/{session_id}/tags"),
    ("DELETE", "/api/v1/widget/feedback/{tenant_id}/{feedback_id}"),
)


@pytest.fixture
def test_client(mock_settings):
    mock_settings.sentry_dsn = None
    mock_settings.supabase_service_key = "fake-key"
    mock_settings.jwt_secret_key = "test-secret-key-for-jwt"
    mock_settings.api_secret_key = "test-secret-key-for-jwt"
    db_mock = MagicMock()
    table = MagicMock()
    for m in (
        "select",
        "insert",
        "update",
        "delete",
        "eq",
        "order",
        "limit",
        "range",
    ):
        getattr(table, m).return_value = table
    table.execute.return_value = MagicMock(
        data=[
            {
                "id": "row-1",
                "tenant_id": TENANT,
                "allowed_domains": ["example.com"],
                "is_online": True,
                "bot_name": "Bot",
                "primary_color": "#00BFFF",
                "greeting_message": "Hi",
                "position": "bottom-right",
                "branding": None,
                "teaser_message": None,
                "teaser_delay_seconds": 3,
                "teaser_enabled": True,
                "enable_ai_fallback": False,
                "enable_structured_lead_parser": False,
                "question": "Hours?",
                "answer": "9-5",
                "category": "general",
                "is_active": True,
            }
        ]
    )
    db_mock.table.return_value = table
    patches = [
        patch("backend.models.database.get_supabase", return_value=db_mock),
        patch("backend.models.database.get_service_supabase", return_value=db_mock),
        patch("backend.routers.auth.get_service_supabase", return_value=db_mock),
        patch(
            "backend.routers.widget_config.get_service_supabase", return_value=db_mock
        ),
        patch("backend.routers.auth_demo.get_service_supabase", return_value=db_mock),
        patch("backend.services.auth_service.settings", mock_settings),
        patch(
            "backend.middleware.demo_role_guard._jwt_secret",
            return_value="test-secret-key-for-jwt",
        ),
        patch(
            "backend.services.faq_service.create_faq",
            return_value={
                "id": "faq-1",
                "question": "Hours?",
                "answer": "9-5",
                "category": "general",
                "is_active": True,
            },
        ),
        patch("backend.services.faq_service.delete_faq"),
        patch(
            "backend.services.faq_service.update_faq",
            return_value={
                "id": "faq-1",
                "question": "Hours?",
                "answer": "9-5",
                "category": "general",
                "is_active": True,
            },
        ),
        patch(
            "backend.services.conversations_service.update_conversation_tags",
            return_value={"tags": ["hot"]},
        ),
        patch(
            "backend.services.widget_config_service.update_widget_config_service",
            return_value={
                "bot_name": "Bot",
                "primary_color": "#00BFFF",
                "greeting_message": "Hi",
                "position": "bottom-right",
                "branding": None,
                "teaser_message": None,
                "teaser_delay_seconds": 3,
                "teaser_enabled": True,
                "enable_ai_fallback": False,
                "enable_structured_lead_parser": False,
            },
        ),
    ]
    for p in patches:
        p.start()
    from backend.main import app

    client = TestClient(app)
    yield client, db_mock, app
    for p in patches:
        p.stop()


class TestResidualWriteGuardsStructural:
    def test_residual_writes_carry_demo_or_owner_guard(self, test_client):
        _client, _db, app = test_client
        for method, path in RESIDUAL_WRITES:
            route = _route(app, method, path)
            calls = _walk_dep_calls(route.dependant)
            assert block_demo_role in calls, (
                f"{method} {path} missing block_demo_role"
            )

    def test_faq_update_keeps_owner_admin_role_guard(self, test_client):
        _client, _db, app = test_client
        route = _route(app, "PUT", "/api/v1/auth/faq/{tenant_id}/{faq_id}")
        calls = _walk_dep_calls(route.dependant)
        # require_role("owner", "admin") is the existing equivalent on update.
        assert any(getattr(fn, "__name__", "") == "checker" for fn in calls), (
            "FAQ update must keep require_role('owner', 'admin')"
        )

    def test_public_widget_feedback_post_has_no_demo_guard(self, test_client):
        _client, _db, app = test_client
        route = _route(app, "POST", "/api/v1/widget/feedback")
        calls = _walk_dep_calls(route.dependant)
        assert block_demo_role not in calls


class TestResidualWriteGuardsBehavior:
    def test_demo_widget_config_update_is_403(self, test_client):
        client, _db, _app = test_client
        resp = client.put(
            f"/api/v1/auth/widget-config/{TENANT}",
            json={"bot_name": "X"},
            headers=_auth("demo"),
        )
        assert resp.status_code == 403
        assert resp.json()["detail"] == DEMO_BLOCK_DETAIL

    def test_owner_widget_config_update_not_demo_blocked(self, test_client):
        client, _db, _app = test_client
        resp = client.put(
            f"/api/v1/auth/widget-config/{TENANT}",
            json={"bot_name": "X"},
            headers=_auth("owner"),
        )
        assert resp.status_code != 403

    def test_admin_widget_config_update_not_demo_blocked(self, test_client):
        client, _db, _app = test_client
        resp = client.put(
            f"/api/v1/auth/widget-config/{TENANT}",
            json={"bot_name": "X"},
            headers=_auth("admin"),
        )
        assert resp.status_code != 403

    def test_demo_online_status_is_403(self, test_client):
        client, _db, _app = test_client
        resp = client.put(
            f"/api/v1/widget/config/{TENANT}/online-status",
            json={"is_online": False},
            headers=_auth("demo"),
        )
        assert resp.status_code == 403
        assert resp.json()["detail"] == DEMO_BLOCK_DETAIL

    def test_owner_online_status_not_demo_blocked(self, test_client):
        client, _db, _app = test_client
        resp = client.put(
            f"/api/v1/widget/config/{TENANT}/online-status",
            json={"is_online": False},
            headers=_auth("owner"),
        )
        assert resp.status_code != 403

    def test_demo_allowed_domains_is_403(self, test_client):
        client, _db, _app = test_client
        resp = client.put(
            f"/api/v1/widget/config/{TENANT}/allowed-domains",
            json={"allowed_domains": ["example.com"]},
            headers=_auth("demo"),
        )
        assert resp.status_code == 403
        assert resp.json()["detail"] == DEMO_BLOCK_DETAIL

    def test_owner_allowed_domains_not_demo_blocked(self, test_client):
        client, _db, _app = test_client
        resp = client.put(
            f"/api/v1/widget/config/{TENANT}/allowed-domains",
            json={"allowed_domains": ["example.com"]},
            headers=_auth("owner"),
        )
        assert resp.status_code != 403

    def test_demo_faq_create_is_403(self, test_client):
        client, _db, _app = test_client
        resp = client.post(
            f"/api/v1/auth/faq/{TENANT}",
            json=FAQ_BODY,
            headers=_auth("demo"),
        )
        assert resp.status_code == 403
        assert resp.json()["detail"] == DEMO_BLOCK_DETAIL

    def test_owner_faq_create_not_demo_blocked(self, test_client):
        client, _db, _app = test_client
        resp = client.post(
            f"/api/v1/auth/faq/{TENANT}",
            json=FAQ_BODY,
            headers=_auth("owner"),
        )
        assert resp.status_code != 403

    def test_demo_faq_update_is_403(self, test_client):
        client, _db, _app = test_client
        resp = client.put(
            f"/api/v1/auth/faq/{TENANT}/faq-1",
            json=FAQ_BODY,
            headers=_auth("demo"),
        )
        assert resp.status_code == 403

    def test_owner_faq_update_not_demo_blocked(self, test_client):
        client, _db, _app = test_client
        resp = client.put(
            f"/api/v1/auth/faq/{TENANT}/faq-1",
            json=FAQ_BODY,
            headers=_auth("owner"),
        )
        assert resp.status_code != 403

    def test_demo_faq_delete_is_403(self, test_client):
        client, _db, _app = test_client
        resp = client.delete(
            f"/api/v1/auth/faq/{TENANT}/faq-1",
            headers=_auth("demo"),
        )
        assert resp.status_code == 403
        assert resp.json()["detail"] == DEMO_BLOCK_DETAIL

    def test_owner_faq_delete_not_demo_blocked(self, test_client):
        client, _db, _app = test_client
        resp = client.delete(
            f"/api/v1/auth/faq/{TENANT}/faq-1",
            headers=_auth("owner"),
        )
        assert resp.status_code != 403

    def test_demo_conversation_tags_is_403(self, test_client):
        client, _db, _app = test_client
        resp = client.put(
            f"/api/v1/auth/conversations/{TENANT}/sess-1/tags",
            json={"tags": ["hot"]},
            headers=_auth("demo"),
        )
        assert resp.status_code == 403
        assert resp.json()["detail"] == DEMO_BLOCK_DETAIL

    def test_owner_conversation_tags_not_demo_blocked(self, test_client):
        client, _db, _app = test_client
        resp = client.put(
            f"/api/v1/auth/conversations/{TENANT}/sess-1/tags",
            json={"tags": ["hot"]},
            headers=_auth("owner"),
        )
        assert resp.status_code != 403

    def test_demo_feedback_delete_is_403(self, test_client):
        client, _db, _app = test_client
        resp = client.delete(
            f"/api/v1/widget/feedback/{TENANT}/fb-1",
            headers=_auth("demo"),
        )
        assert resp.status_code == 403
        assert resp.json()["detail"] == DEMO_BLOCK_DETAIL

    def test_owner_feedback_delete_not_demo_blocked(self, test_client):
        client, _db, _app = test_client
        resp = client.delete(
            f"/api/v1/widget/feedback/{TENANT}/fb-1",
            headers=_auth("owner"),
        )
        assert resp.status_code != 403

    def test_demo_login_still_allowlisted(self, test_client):
        client, db, _app = test_client
        db.table.return_value.execute.return_value = MagicMock(
            data=[
                {
                    "id": TENANT,
                    "business_name": "Reliable Plumbing Co. (DEMO)",
                    "plan": "professional",
                    "business_type": "plumbing",
                }
            ]
        )
        resp = client.post("/api/v1/auth/demo-login")
        assert resp.status_code == 200
        assert resp.json()["demo"] is True

    def test_public_widget_feedback_post_not_demo_blocked(self, test_client):
        client, _db, _app = test_client
        with patch(
            "backend.routers.widget_config._get_widget_config",
            return_value={"tenant_id": TENANT},
        ):
            resp = client.post(
                "/api/v1/widget/feedback",
                json={
                    "api_key": "anx_test_key",
                    "session_id": "sess-1",
                    "message_index": 0,
                    "rating": "thumbs_up",
                },
            )
        assert resp.status_code != 403 or resp.json().get("detail") != DEMO_BLOCK_DETAIL
