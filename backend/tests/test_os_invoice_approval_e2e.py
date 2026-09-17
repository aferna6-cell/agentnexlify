"""Billing Automation v1 PR3 — invoice approval path through the real API.

These tests close the gap between the invoice data-plane unit tests and the
Agent OS approval endpoint. They prove that an owner-approved invoice action is
claimed exactly once, executes through ``run_invoice_l2``, records verification,
and never guesses or auto-replays an unknown provider outcome.
"""

import os
from unittest.mock import patch

os.environ.setdefault("TESTING", "1")

import pytest

from backend.dependencies import _get_current_tenant
from backend.main import app
from backend.routers import os_tool_executions as router_mod
from backend.services.agent_os_gate import require_agent_os_access
from backend.services import os_invoice_actions
from backend.tests.conftest import SyncASGITestClient
from backend.tests.fake_supabase_store import FakeSupabase


CLIENT = "11111111-1111-1111-1111-111111111111"
OTHER = "22222222-2222-2222-2222-222222222222"
LEAD = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
INVOICE = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
EXECUTION = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
OWNER = {
    "tenant_id": CLIENT,
    "role": "owner",
    "email": "maya@sunsetauto.test",
}


@pytest.fixture(autouse=True)
def _invoice_flag(monkeypatch):
    monkeypatch.setenv("INVOICE_ACTIONS_ENABLED", "1")


def _lead(**overrides):
    row = {
        "id": LEAD,
        "client_id": CLIENT,
        "name": "Steve",
        "email": "steve@example.com",
        "phone": "555-0100",
        "status": "new",
    }
    row.update(overrides)
    return row


def _invoice(**overrides):
    row = {
        "id": INVOICE,
        "tenant_id": CLIENT,
        "lead_id": LEAD,
        "invoice_number": "INV-1111-001",
        "items_json": [
            {"description": "Termite treatment", "quantity": 1, "unit_price": 850}
        ],
        "subtotal": 850.0,
        "tax_rate": 0,
        "tax_amount": 0.0,
        "total": 850.0,
        "status": "draft",
        "due_date": "2026-09-17",
        "notes": None,
        "stripe_payment_link": None,
        "created_at": "2026-09-03T12:00:00Z",
    }
    row.update(overrides)
    return row


def _execution(tool_id="send_invoice", **overrides):
    row = {
        "id": EXECUTION,
        "client_id": CLIENT,
        "engine_run_id": "engine_run_invoice_1",
        "agent_id": "invoicing",
        "tool_id": tool_id,
        "status": "pending_approval",
        "approval_state": "pending",
        "risk_level": 2,
        "mutating": True,
        "requires_approval": True,
        "input": {"invoice_id": INVOICE, "method": "email"},
        "policy_reason": "risk level 2 requires owner approval",
        "attempts": 0,
        "idempotency_key": f"{tool_id}:{INVOICE}:email",
        "created_at": "2026-09-03T12:00:00Z",
    }
    row.update(overrides)
    return row


def _db(*, invoice=None, execution=None):
    return FakeSupabase(
        {
            "os_tool_executions": [execution or _execution()],
            "leads": [_lead()],
            "invoices": [invoice or _invoice()],
            "activity_log": [],
            "tenants": [],
        }
    )


def _client():
    app.dependency_overrides[_get_current_tenant] = lambda: OWNER
    app.dependency_overrides[require_agent_os_access] = lambda: OWNER
    return SyncASGITestClient(app)


def _teardown():
    app.dependency_overrides.pop(_get_current_tenant, None)
    app.dependency_overrides.pop(require_agent_os_access, None)


def test_owner_approval_sends_invoice_once_and_persists_verified_success():
    db = _db()
    calls = []

    async def _channels(*_args, **_kwargs):
        calls.append("send")
        return {
            "email_sent": True,
            "sms_sent": False,
            "payment_link": "https://pay.stripe.test/inv",
            "errors": [],
            "lead": _lead(),
        }

    client = _client()
    try:
        with patch.object(router_mod, "get_service_supabase", return_value=db), patch.object(
            os_invoice_actions, "_send_channels", side_effect=_channels
        ):
            first = client.post(f"/api/v1/os/tool-executions/{EXECUTION}/approve")
            second = client.post(f"/api/v1/os/tool-executions/{EXECUTION}/approve")
    finally:
        _teardown()

    assert first.status_code == 200
    assert first.json()["already_decided"] is False
    assert first.json()["execution"]["status"] == "succeeded"
    assert first.json()["execution"]["approval_state"] == "approved"
    assert first.json()["execution"]["verification_state"] == "passed"
    assert first.json()["execution"]["result"]["invoiceId"] == INVOICE
    assert first.json()["execution"]["result"]["emailSent"] is True

    assert second.status_code == 200
    assert second.json()["already_decided"] is True
    assert calls == ["send"], "a repeated approval must not re-send the invoice"

    invoice = db.rows("invoices")[0]
    assert invoice["status"] == "sent"
    assert invoice["stripe_payment_link"] == "https://pay.stripe.test/inv"
    assert invoice["status"] != "paid"


def test_unknown_invoice_provider_outcome_stays_running_and_is_not_replayed():
    db = _db()
    calls = []

    async def _timeout(*_args, **_kwargs):
        calls.append("send")
        raise TimeoutError("provider timed out")

    client = _client()
    try:
        with patch.object(router_mod, "get_service_supabase", return_value=db), patch.object(
            os_invoice_actions, "_send_channels", side_effect=_timeout
        ):
            first = client.post(f"/api/v1/os/tool-executions/{EXECUTION}/approve")
            second = client.post(f"/api/v1/os/tool-executions/{EXECUTION}/approve")
    finally:
        _teardown()

    assert first.status_code == 200
    assert first.json()["already_decided"] is False
    assert first.json()["outcome"]["unknown"] is True
    assert first.json()["execution"]["status"] == "running"
    assert first.json()["execution"]["error"]["code"] == "engine_unavailable"

    assert second.status_code == 200
    assert second.json()["already_decided"] is True
    assert calls == ["send"], "unknown provider outcomes must never be auto-replayed"
    assert db.rows("invoices")[0]["status"] == "draft"


def test_paid_invoice_reminder_is_refused_without_any_provider_effect():
    db = _db(
        invoice=_invoice(status="paid", due_date="2026-08-01"),
        execution=_execution(tool_id="send_invoice_reminder"),
    )
    calls = []

    async def _channels(*_args, **_kwargs):
        calls.append("send")
        raise AssertionError("paid reminders must never reach a provider")

    client = _client()
    try:
        with patch.object(router_mod, "get_service_supabase", return_value=db), patch.object(
            os_invoice_actions, "_send_channels", side_effect=_channels
        ):
            resp = client.post(f"/api/v1/os/tool-executions/{EXECUTION}/approve")
    finally:
        _teardown()

    assert resp.status_code == 200
    assert resp.json()["execution"]["status"] == "failed"
    assert resp.json()["execution"]["verification_state"] == "failed"
    assert resp.json()["execution"]["error"]["code"] == "invoice_already_paid"
    assert calls == []
    assert db.rows("invoices")[0]["status"] == "paid"


def test_invoice_approval_cannot_cross_tenants():
    db = _db(execution=_execution(client_id=OTHER))
    client = _client()
    try:
        with patch.object(router_mod, "get_service_supabase", return_value=db):
            resp = client.post(f"/api/v1/os/tool-executions/{EXECUTION}/approve")
    finally:
        _teardown()

    assert resp.status_code == 404
    assert db.rows("os_tool_executions")[0]["status"] == "pending_approval"
