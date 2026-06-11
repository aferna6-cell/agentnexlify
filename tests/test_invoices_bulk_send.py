"""Tests for the bulk-send invoices endpoint, including batched DB access.

The endpoint must do one batched invoices read, one batched leads read, and
one batched status update — regardless of how many invoices are sent.
Uses the same JWT + mock-supabase pattern as test_documents.py.
"""

import os
os.environ["TESTING"] = "1"

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _make_jwt(tenant_id="t1", role="owner", secret="test-secret-key-for-jwt"):
    from jose import jwt
    payload = {
        "tenant_id": tenant_id, "sub": tenant_id, "email": "o@e.com",
        "plan": "professional", "business_name": "Test Biz", "role": role,
        "is_team_member": False,
        "exp": datetime.now(timezone.utc) + timedelta(days=1),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def _counting_table_mock(db_mock, table_responses):
    """Chainable table mock that records call counts per table name.

    table_responses maps table name → list of result-row lists, consumed one
    per db.table(name) call (last entry repeats).
    """
    call_counts = {}

    def mock_table(name):
        call_counts.setdefault(name, 0)
        call_counts[name] += 1
        table = MagicMock()
        data = table_responses.get(name, [])
        if data and isinstance(data[0], list):
            idx = min(call_counts[name] - 1, len(data) - 1)
            current_data = data[idx]
        else:
            current_data = data
        for m in ["select", "insert", "update", "delete", "eq", "neq", "gte", "lte",
                  "gt", "lt", "limit", "order", "ilike", "in_", "is_", "or_", "contains", "not_"]:
            getattr(table, m).return_value = table
        result = MagicMock()
        result.data = current_data
        result.count = len(current_data) if current_data else 0
        table.execute.return_value = result
        return table

    db_mock.table = mock_table
    return call_counts


@pytest.fixture
def test_client(mock_settings):
    mock_settings.sentry_dsn = None
    mock_settings.supabase_service_key = "fake-key"
    db_mock = MagicMock()
    patches = [
        patch("backend.models.database.get_supabase", return_value=db_mock),
        patch("backend.routers.auth.get_service_supabase", return_value=db_mock),
        patch("backend.routers.auth.settings", mock_settings),
        patch("backend.routers.invoices.get_service_supabase", return_value=db_mock),
        patch("backend.routers.invoices.send_email", new_callable=AsyncMock),
        patch("backend.routers.invoices.send_sms", new_callable=AsyncMock),
    ]
    started = [p.start() for p in patches]
    send_email_mock = started[4]
    send_sms_mock = started[5]
    send_email_mock.return_value = {"success": True}
    send_sms_mock.return_value = True
    from backend.main import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
    yield client, db_mock, send_email_mock, send_sms_mock
    for p in patches:
        p.stop()


def _invoice(inv_id, lead_id, status="draft", number="INV-1"):
    return {
        "id": inv_id, "lead_id": lead_id, "status": status,
        "invoice_number": number, "total": 100.0,
        "stripe_payment_link": "https://pay.example/x",
    }


class TestBulkSend:
    def test_sends_all_with_batched_queries(self, test_client):
        client, db, send_email_mock, _ = test_client
        counts = _counting_table_mock(db, {
            "tenants": [{"business_name": "Test Biz"}],
            "invoices": [
                # 1st call: batched select; 2nd call: batched status update
                [_invoice("inv1", "lead1", number="INV-1"), _invoice("inv2", "lead2", number="INV-2")],
                [{"id": "inv1"}, {"id": "inv2"}],
            ],
            "leads": [
                [{"id": "lead1", "name": "A", "email": "a@e.com", "phone": None},
                 {"id": "lead2", "name": "B", "email": "b@e.com", "phone": None}],
            ],
        })

        resp = client.post(
            "/api/v1/invoices/t1/bulk-send",
            json={"invoice_ids": ["inv1", "inv2"], "channel": "email"},
            headers={"Authorization": f"Bearer {_make_jwt()}"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["sent"] == 2
        assert body["failed"] == 0
        assert send_email_mock.await_count == 2
        # Batched access: 1 select + 1 update on invoices, 1 select on leads
        assert counts["invoices"] == 2
        assert counts["leads"] == 1

    def test_missing_and_paid_invoices_reported(self, test_client):
        client, db, send_email_mock, _ = test_client
        _counting_table_mock(db, {
            "tenants": [{"business_name": "Test Biz"}],
            "invoices": [
                [_invoice("inv1", "lead1", status="paid", number="INV-1")],
            ],
            "leads": [],
        })

        resp = client.post(
            "/api/v1/invoices/t1/bulk-send",
            json={"invoice_ids": ["inv1", "ghost"], "channel": "email"},
            headers={"Authorization": f"Bearer {_make_jwt()}"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["sent"] == 0
        assert body["failed"] == 2
        joined = " ".join(body["errors"])
        assert "already paid" in joined
        assert "ghost: not found" in joined
        send_email_mock.assert_not_awaited()

    def test_invoice_without_contact_info_fails(self, test_client):
        client, db, _, _ = test_client
        _counting_table_mock(db, {
            "tenants": [{"business_name": "Test Biz"}],
            "invoices": [[_invoice("inv1", "lead1", number="INV-9")]],
            "leads": [[{"id": "lead1", "name": "A", "email": None, "phone": None}]],
        })

        resp = client.post(
            "/api/v1/invoices/t1/bulk-send",
            json={"invoice_ids": ["inv1"], "channel": "email"},
            headers={"Authorization": f"Bearer {_make_jwt()}"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["sent"] == 0
        assert body["failed"] == 1
        assert "no contact info" in body["errors"][0]
