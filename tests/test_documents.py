"""Tests for documents, item templates, and partial payments.

Uses the same mock pattern as test_appointments.py.
"""

import os
os.environ["TESTING"] = "1"

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

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


def _setup_table_mock(db_mock, table_responses):
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


@pytest.fixture
def test_client(mock_settings):
    mock_settings.sentry_dsn = None
    mock_settings.supabase_service_key = "fake-key"
    db_mock = MagicMock()
    patches = [
        patch("backend.models.database.get_supabase", return_value=db_mock),
        patch("backend.routers.auth.get_supabase", return_value=db_mock),
        patch("backend.routers.auth.settings", mock_settings),
        patch("backend.routers.documents.get_supabase", return_value=db_mock),
        patch("backend.routers.invoices.get_supabase", return_value=db_mock),
        patch("backend.routers.widget_chat.get_supabase", return_value=db_mock),
        patch("backend.routers.widget_config.get_supabase", return_value=db_mock),
        patch("backend.routers.widget_lead.get_supabase", return_value=db_mock),
        patch("backend.routers.widget_booking.get_supabase", return_value=db_mock),
        patch("backend.routers.widget_helpers.get_supabase", return_value=db_mock),
    ]
    for p in patches:
        p.start()
    from backend.main import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
    yield client, db_mock
    for p in patches:
        p.stop()


# --- Document Tests ---

class TestDocumentList:
    def test_list_documents(self, test_client):
        client, db = test_client
        _setup_table_mock(db, {"documents": [{"id": "d1", "title": "Contract", "status": "draft"}]})
        resp = client.get("/api/v1/documents/t1", headers={"Authorization": f"Bearer {_make_jwt()}"})
        assert resp.status_code == 200
        assert "documents" in resp.json()


class TestDocumentCreate:
    def test_create_document(self, test_client):
        client, db = test_client
        _setup_table_mock(db, {"documents": [{"id": "d1", "title": "Agreement", "status": "draft"}]})
        resp = client.post("/api/v1/documents/t1", json={
            "title": "Service Agreement",
            "template_html": "<h1>Terms</h1>",
            "signer_name": "John",
            "signer_email": "john@example.com",
        }, headers={"Authorization": f"Bearer {_make_jwt()}"})
        assert resp.status_code == 200


class TestDocumentDelete:
    def test_delete_draft(self, test_client):
        client, db = test_client
        _setup_table_mock(db, {"documents": [{"status": "draft"}]})
        resp = client.delete("/api/v1/documents/t1/d1", headers={"Authorization": f"Bearer {_make_jwt()}"})
        assert resp.status_code == 200

    def test_delete_sent_fails(self, test_client):
        client, db = test_client
        _setup_table_mock(db, {"documents": [{"status": "sent"}]})
        resp = client.delete("/api/v1/documents/t1/d1", headers={"Authorization": f"Bearer {_make_jwt()}"})
        assert resp.status_code == 400


class TestDocumentSigning:
    def test_sign_not_found(self, test_client):
        client, db = test_client
        _setup_table_mock(db, {"documents": []})
        resp = client.get("/api/v1/documents/public/sign/bad-token")
        assert resp.status_code == 404

    def test_already_signed(self, test_client):
        client, db = test_client
        _setup_table_mock(db, {"documents": [{"id": "d1", "title": "C", "status": "signed", "signer_name": "J", "tenant_id": "t1", "expires_at": None}]})
        resp = client.get("/api/v1/documents/public/sign/tok")
        assert resp.status_code == 200
        assert resp.json()["status"] == "already_signed"

    def test_sign_success(self, test_client):
        client, db = test_client
        _setup_table_mock(db, {
            "documents": [{"id": "d1", "status": "viewed", "tenant_id": "t1", "title": "Contract", "signer_email": "j@e.com", "lead_id": None, "expires_at": None}],
            "tenants": [{"business_name": "Biz"}],
            "activity_log": [],
        })
        resp = client.post("/api/v1/documents/public/sign/tok", json={
            "signature_data": "data:image/png;base64,ABC",
            "signer_name": "Jane",
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "signed"


class TestPartialPayment:
    def test_record_payment(self, test_client):
        client, db = test_client
        _setup_table_mock(db, {"invoices": [{"id": "inv1", "total": 500, "amount_paid": 0, "status": "sent"}]})
        resp = client.post("/api/v1/invoices/t1/inv1/record-payment", json={"amount": 200},
                          headers={"Authorization": f"Bearer {_make_jwt()}"})
        assert resp.status_code == 200

    def test_payment_on_paid_fails(self, test_client):
        client, db = test_client
        _setup_table_mock(db, {"invoices": [{"id": "inv1", "total": 500, "amount_paid": 500, "status": "paid"}]})
        resp = client.post("/api/v1/invoices/t1/inv1/record-payment", json={"amount": 100},
                          headers={"Authorization": f"Bearer {_make_jwt()}"})
        assert resp.status_code == 400


class TestItemTemplates:
    def test_list_templates(self, test_client):
        client, db = test_client
        _setup_table_mock(db, {"invoice_item_templates": [{"id": "it1", "description": "Repair", "unit_price": 150}]})
        resp = client.get("/api/v1/invoices/t1/item-templates", headers={"Authorization": f"Bearer {_make_jwt()}"})
        assert resp.status_code == 200

    def test_create_template(self, test_client):
        client, db = test_client
        _setup_table_mock(db, {"invoice_item_templates": [{"id": "it2", "description": "Drain", "unit_price": 200}]})
        resp = client.post("/api/v1/invoices/t1/item-templates", json={
            "description": "Drain Cleaning", "unit_price": 200,
        }, headers={"Authorization": f"Bearer {_make_jwt()}"})
        assert resp.status_code == 200
