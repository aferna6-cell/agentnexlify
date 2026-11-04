"""Hit the shared activity counters through the HTTP handlers."""

import os

os.environ.setdefault("TESTING", "1")
os.environ.setdefault("API_SECRET_KEY", "test-secret-key-for-jwt")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-jwt")

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from jose import jwt

from backend.main import app

TENANT = "00000000-0000-0000-0000-0000000000aa"


def _headers():
    token = jwt.encode(
        {
            "tenant_id": TENANT,
            "email": "owner@test.com",
            "plan": "agent_os",
            "business_name": "Acme",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        },
        "test-secret-key-for-jwt",
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


def _db():
    db = MagicMock()

    def table(name):
        chain = MagicMock()
        result = MagicMock()
        result.count = 0
        if name == "tenants":
            result.data = [{
                "id": TENANT,
                "business_name": "Acme",
                "business_type": "plumbing",
                "plan": "free",
                "plan_status": "active",
                "conversations_used_this_month": 16,
                "monthly_conversation_limit": None,
                "free_trial_started_at": None,
            }]
            result.count = 1
        elif name == "pipeline_stages":
            result.data = [
                {"name": "New Lead", "sort_order": 0, "color": "#3b82f6", "is_won": False, "is_lost": False},
                {"name": "Won", "sort_order": 1, "color": "#10b981", "is_won": True, "is_lost": False},
            ]
        elif name == "leads":
            result.data = [
                {"id": "l1", "status": "new", "deal_value": 0, "lead_score": 9, "created_at": "2026-08-01T00:00:00Z", "updated_at": "2026-11-03T00:00:00Z"},
            ]
            result.count = 1
        else:
            result.data = []
        chain.select.return_value = chain
        chain.insert.return_value = chain
        chain.update.return_value = chain
        chain.eq.return_value = chain
        chain.gte.return_value = chain
        chain.lt.return_value = chain
        chain.neq.return_value = chain
        chain.order.return_value = chain
        chain.limit.return_value = chain
        chain.execute.return_value = result
        return chain

    db.table.side_effect = table
    return db


def test_dashboard_billing_and_analytics_share_the_activity_handlers():
    db = _db()
    with patch("backend.models.database.get_service_supabase", return_value=db), patch(
        "backend.routers.auth.get_service_supabase", return_value=db
    ), patch(
        "backend.routers.analytics.dashboard.get_service_supabase", return_value=db
    ), patch(
        "backend.routers.pipeline.get_service_supabase", return_value=db
    ):
        client = TestClient(app)
        headers = _headers()
        dashboard = client.get(f"/api/v1/auth/dashboard/{TENANT}", headers=headers)
        overview = client.get(
            f"/api/v1/analytics/{TENANT}/overview?period=month", headers=headers
        )
        health = client.get(f"/api/v1/analytics/{TENANT}/health", headers=headers)
        board = client.get(f"/api/v1/pipeline/{TENANT}/board", headers=headers)

    assert dashboard.status_code == 200, dashboard.text
    assert overview.status_code == 200, overview.text
    assert health.status_code == 200, health.text
    assert board.status_code == 200, board.text
    body = overview.json()
    assert "leads_all_time" in body
    assert "total_conversations" in body
    assert health.json()["last_activity_at"] is not None
    assert board.json()["leads_by_stage"]["New Lead"][0]["status"] == "new"
    assert dashboard.json()["conversations_used_this_month"] == 0
    assert dashboard.json()["leads_count"] == 1
