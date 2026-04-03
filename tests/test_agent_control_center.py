"""Tests for the Agent Control Center analytics payload."""

import os
os.environ["TESTING"] = "1"

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch
import sys

from fastapi.testclient import TestClient
from jose import jwt
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _make_jwt(tenant_id="t1", role="owner", secret="test-secret-key-for-jwt"):
    payload = {
        "tenant_id": tenant_id,
        "sub": tenant_id,
        "email": "owner@example.com",
        "plan": "professional",
        "business_name": "Test Biz",
        "role": role,
        "is_team_member": False,
        "exp": datetime.now(timezone.utc) + timedelta(days=1),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


class _StaticQuery:
    def __init__(self, data):
        self._data = data
        self._single = False

    def select(self, *args, **kwargs):
        return self

    def insert(self, *args, **kwargs):
        return self

    def update(self, *args, **kwargs):
        return self

    def delete(self, *args, **kwargs):
        return self

    def eq(self, *args, **kwargs):
        return self

    def neq(self, *args, **kwargs):
        return self

    def gte(self, *args, **kwargs):
        return self

    def lte(self, *args, **kwargs):
        return self

    def gt(self, *args, **kwargs):
        return self

    def lt(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def order(self, *args, **kwargs):
        return self

    def in_(self, *args, **kwargs):
        return self

    def ilike(self, *args, **kwargs):
        return self

    def contains(self, *args, **kwargs):
        return self

    def or_(self, *args, **kwargs):
        return self

    def single(self):
        self._single = True
        return self

    def execute(self):
        result = MagicMock()
        if self._single:
            result.data = self._data[0] if self._data else {}
        else:
            result.data = self._data
        result.count = len(self._data)
        return result


class _StaticDb:
    def __init__(self, tables):
        self.tables = tables

    def table(self, name):
        return _StaticQuery(self.tables.get(name, []))


@pytest.fixture
def control_center_client(mock_settings):
    mock_settings.sentry_dsn = None
    mock_settings.api_secret_key = "test-secret-key-for-jwt"
    db = _StaticDb({})
    patches = [
        patch("backend.models.database.get_supabase", return_value=db),
        patch("backend.routers.analytics.get_supabase", return_value=db),
        patch("backend.routers.auth.settings", mock_settings),
    ]
    for item in patches:
        item.start()
    from backend.main import app
    yield TestClient(app), db
    for item in patches:
        item.stop()


def test_control_center_aggregates_wins_risks_and_recovery_queue(control_center_client):
    client, db = control_center_client
    now = datetime.now(timezone.utc)
    t0 = now - timedelta(days=1)

    db.tables.update({
        "chat_messages": [
            {"session_id": "session-hot-stalled", "role": "user", "content": "How much does it cost? I need help today.", "created_at": (t0 - timedelta(minutes=10)).isoformat()},
            {"session_id": "session-won", "role": "user", "content": "Can I book an install this week?", "created_at": (t0 - timedelta(minutes=9)).isoformat()},
            {"session_id": "session-won", "role": "assistant", "content": "Yes, I can help with that.", "created_at": (t0 - timedelta(minutes=7)).isoformat()},
            {"session_id": "session-lead-no-book", "role": "user", "content": "Are you available next week?", "created_at": (t0 - timedelta(minutes=8)).isoformat()},
            {"session_id": "session-lead-no-book", "role": "assistant", "content": "Yes, I can get you on the schedule.", "created_at": (t0 - timedelta(minutes=6)).isoformat()},
            {"session_id": "session-lead-no-book", "role": "user", "content": "Great, send me the details.", "created_at": (t0 - timedelta(minutes=5)).isoformat()},
        ],
        "conversations": [
            {
                "id": "conv-1",
                "session_id": "session-hot-stalled",
                "lead_id": None,
                "assigned_to": None,
                "channel": "widget",
                "lead_captured": False,
                "created_at": (t0 - timedelta(minutes=10)).isoformat(),
                "last_message_at": (t0 - timedelta(minutes=10)).isoformat(),
            },
            {
                "id": "conv-2",
                "session_id": "session-won",
                "lead_id": "lead-2",
                "assigned_to": "tm-1",
                "channel": "sms",
                "lead_captured": True,
                "created_at": (t0 - timedelta(minutes=9)).isoformat(),
                "last_message_at": (t0 - timedelta(minutes=7)).isoformat(),
            },
            {
                "id": "conv-3",
                "session_id": "session-lead-no-book",
                "lead_id": "lead-3",
                "assigned_to": "tm-2",
                "channel": "widget",
                "lead_captured": True,
                "created_at": (t0 - timedelta(minutes=8)).isoformat(),
                "last_message_at": (t0 - timedelta(minutes=5)).isoformat(),
            },
        ],
        "leads": [
            {
                "id": "lead-2",
                "conversation_id": "conv-2",
                "name": "Jane Install",
                "email": "jane@example.com",
                "status": "closed",
                "lead_temperature": "hot",
                "deal_value": 2400,
                "assigned_to": "tm-1",
                "source": "widget",
                "created_at": (t0 - timedelta(minutes=9)).isoformat(),
            },
            {
                "id": "lead-3",
                "conversation_id": "conv-3",
                "name": "Chris Followup",
                "email": "chris@example.com",
                "status": "contacted",
                "lead_temperature": "hot",
                "deal_value": 900,
                "assigned_to": "tm-2",
                "source": "widget",
                "created_at": (t0 - timedelta(minutes=8)).isoformat(),
            },
        ],
        "appointments": [
            {
                "id": "appt-1",
                "lead_id": "lead-2",
                "status": "completed",
                "created_at": (t0 - timedelta(minutes=4)).isoformat(),
                "start_time": (t0 + timedelta(days=1)).isoformat(),
            },
        ],
        "invoices": [
            {
                "id": "inv-1",
                "lead_id": "lead-2",
                "status": "paid",
                "total": 1800,
                "amount_paid": 1800,
                "created_at": (t0 - timedelta(minutes=3)).isoformat(),
                "paid_at": (t0 - timedelta(minutes=1)).isoformat(),
            },
        ],
        "team_members": [
            {"id": "tm-1", "name": "Alice Ops", "email": "alice@example.com"},
            {"id": "tm-2", "name": "Bob Sales", "email": "bob@example.com"},
        ],
    })

    from backend.routers.analytics import _cache
    _cache.clear()

    response = client.get(
        "/api/v1/analytics/t1/control-center?period=30d",
        headers={"Authorization": f"Bearer {_make_jwt()}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["total_conversations"] == 3
    assert body["summary"]["assisted_conversations"] == 2
    assert body["summary"]["active_recovery_queue"] >= 2
    assert body["roi"]["revenue_won"] == 1800
    assert body["roi"]["pipeline_value"] == 3300

    won_card = next(item for item in body["scorecards"] if item["session_id"] == "session-won")
    assert won_card["resolution_status"] == "won"
    assert won_card["assigned_to_name"] == "Alice Ops"
    assert won_card["revenue_won"] == 1800

    recovery_item = next(item for item in body["recovery_queue"] if item["session_id"] == "session-hot-stalled")
    assert recovery_item["urgency"] == "high"
    assert "pricing" in recovery_item["reason"].lower() or "high-intent" in recovery_item["reason"].lower()

    assert body["recommendations"]


def test_control_center_returns_empty_state_when_no_messages(control_center_client):
    client, db = control_center_client
    db.tables.update({
        "chat_messages": [],
        "conversations": [],
        "leads": [],
        "appointments": [],
        "invoices": [],
        "team_members": [],
    })

    from backend.routers.analytics import _cache
    _cache.clear()

    response = client.get(
        "/api/v1/analytics/t1/control-center?period=14d",
        headers={"Authorization": f"Bearer {_make_jwt()}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["period"] == "14d"
    assert body["summary"]["total_conversations"] == 0
    assert body["scorecards"] == []
    assert body["recovery_queue"] == []
