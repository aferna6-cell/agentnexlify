"""Billing Automation PR3 — Agent OS invoicing E2E proof.

Stitches the persist + owner-approve data plane that PR1/PR2 wired:

  create draft (resolver payload) → exact customer/amount/items
  → send parks for approval → no pre-approval send
  → approve executes once + verification
  → overdue reminder approval path
  → paid / non-overdue never remind
  → tenant isolation
  → unknown outcome stays non-terminal and is not replayed

Provider I/O is stubbed. Invoice rows, audit rows, and the claim gate are real.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from backend.dependencies import _get_current_tenant
from backend.main import app
from backend.routers import os_tool_executions as router_mod
from backend.services import os_invoice_actions as invoice_svc
from backend.services import os_tool_executions as persist_svc
from backend.services.agent_os_gate import require_agent_os_access
from backend.tests.conftest import SyncASGITestClient
from backend.tests.fake_supabase_store import FakeSupabase

CLIENT = "11111111-1111-1111-1111-111111111111"
OTHER = "22222222-2222-2222-2222-222222222222"
STEVE = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
INV = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
CREATE_ID = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
SEND_ID = "dddddddd-dddd-4ddd-8ddd-dddddddddddd"
REMIND_ID = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"
RUN_ID = "ffffffff-ffff-4fff-8fff-ffffffffffff"

OWNER = {"tenant_id": CLIENT, "role": "owner", "email": "maya@sunsetauto.test"}
OTHER_OWNER = {"tenant_id": OTHER, "role": "owner", "email": "other@example.test"}

# Exact create_invoice_draft input from Invoicing resolveAction on
# "Bill Steve $850 for termite treatment, due in 14 days."
RESOLVER_CREATE_INPUT = {
    "customer_id": STEVE,
    "items": [
        {"description": "termite treatment", "quantity": 1, "unit_price": 850}
    ],
    "tax_rate": 0,
    "due_in_days": 14,
}

# CollectingInvoicePort.toBundle() shape FastAPI persist applies.
RESOLVER_INVOICE_BUNDLE = {
    "id": INV,
    "accountId": CLIENT,
    "customerId": STEVE,
    "customerName": "Steve",
    "invoiceNumber": "INV-MEM-001",
    "items": [
        {"description": "termite treatment", "quantity": 1, "unitPrice": 850}
    ],
    "subtotal": 850,
    "taxRate": 0,
    "taxAmount": 0,
    "total": 850,
    "status": "draft",
    "dueDate": "2026-09-17",
    "notes": None,
    "createdAt": "2026-09-03T12:00:00Z",
    "updatedAt": "2026-09-03T12:00:00Z",
    "idempotencyKey": "steve-termite-850",
    "_op": "create",
}

PAY_LINK = "https://pay.stripe.test/inv-e2e"


@pytest.fixture(autouse=True)
def _flags_on(monkeypatch):
    monkeypatch.setenv("INVOICE_ACTIONS_ENABLED", "1")


def _lead(**overrides):
    row = {
        "id": STEVE,
        "client_id": CLIENT,
        "name": "Steve",
        "email": "steve@example.com",
        "phone": "555-0100",
        "status": "new",
    }
    row.update(overrides)
    return row


def _fresh_db(*, invoices=None):
    return FakeSupabase(
        {
            "leads": [_lead()],
            "invoices": list(invoices or []),
            "os_tool_executions": [],
            "activity_log": [],
            "tenants": [
                {
                    "id": CLIENT,
                    "business_name": "Sunset Auto Care",
                    "owner_email": "maya@sunsetauto.test",
                    "phone": "555-0100",
                }
            ],
        }
    )


def _create_execution(**overrides):
    record = {
        "id": CREATE_ID,
        "accountId": CLIENT,
        "runId": "engine_run_create",
        "agentId": "invoicing",
        "toolId": "create_invoice_draft",
        "riskLevel": 1,
        "mutating": True,
        "requiresApproval": False,
        "approvalState": "not_required",
        "status": "succeeded",
        "input": dict(RESOLVER_CREATE_INPUT),
        "result": {
            "invoiceId": INV,
            "customerId": STEVE,
            "total": 850,
            "status": "draft",
        },
        "verificationState": "passed",
        "attempts": 1,
        "createdAt": "2026-09-03T12:00:00Z",
    }
    record.update(overrides)
    return record


def _l2_execution(tool_id, execution_id, invoice_id=INV, **overrides):
    record = {
        "id": execution_id,
        "accountId": CLIENT,
        "runId": "engine_run_l2",
        "agentId": "invoicing",
        "toolId": tool_id,
        "riskLevel": 2,
        "mutating": True,
        "requiresApproval": True,
        "approvalState": "pending",
        "status": "pending_approval",
        "input": {"invoice_id": invoice_id, "method": "email"},
        "result": None,
        "policyReason": "level 2 requires approval",
        "idempotencyKey": f"{tool_id}:{invoice_id}",
        "attempts": 0,
        "createdAt": "2026-09-03T12:00:00Z",
    }
    record.update(overrides)
    return record


def _delivered_send(*_a, **_k):
    return {
        "email_sent": True,
        "sms_sent": False,
        "payment_link": PAY_LINK,
        "errors": [],
        "lead": _lead(),
    }


async def _real_threadpool(func, *args, **kwargs):
    """Run sync claim/L2 in a worker thread so asyncio.run inside L2 is safe."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: func(*args, **kwargs))


def _client(claims=OWNER):
    app.dependency_overrides[_get_current_tenant] = lambda: claims
    app.dependency_overrides[require_agent_os_access] = lambda: claims
    return SyncASGITestClient(app)


def _teardown():
    app.dependency_overrides.pop(_get_current_tenant, None)
    app.dependency_overrides.pop(require_agent_os_access, None)


def _invoice_row(db, invoice_id=INV):
    return next((r for r in db.rows("invoices") if r["id"] == invoice_id), None)


def test_create_draft_preserves_resolver_payload_then_send_parks():
    db = _fresh_db()
    persist_svc.persist_tool_executions(
        db,
        CLIENT,
        RUN_ID,
        {
            "toolExecutions": [_create_execution()],
            "invoices": [RESOLVER_INVOICE_BUNDLE],
        },
    )

    inv = _invoice_row(db)
    assert inv is not None
    assert inv["lead_id"] == STEVE
    assert float(inv["total"]) == 850.0
    assert float(inv["subtotal"]) == 850.0
    assert inv["items_json"][0]["description"] == "termite treatment"
    assert float(inv["items_json"][0]["unit_price"]) == 850
    assert float(inv["items_json"][0]["quantity"]) == 1
    assert inv["due_date"] == "2026-09-17"
    assert inv["status"] == "draft"
    assert inv.get("stripe_payment_link") in (None, "")
    assert inv.get("sent_at") in (None, "")

    persist_svc.persist_tool_executions(
        db,
        CLIENT,
        RUN_ID,
        {"toolExecutions": [_l2_execution("send_invoice", SEND_ID)]},
    )
    parked = persist_svc.get_tool_execution(db, CLIENT, SEND_ID)
    assert parked["status"] == "pending_approval"
    assert parked["approval_state"] == "pending"
    assert parked["input"]["invoice_id"] == INV
    assert parked["input"]["method"] == "email"

    after = _invoice_row(db)
    assert after["status"] == "draft"
    assert after.get("stripe_payment_link") in (None, "")
    assert after.get("sent_at") in (None, "")
    assert len(db.rows("activity_log")) == 0


def test_approve_send_runs_once_and_verifies_then_second_approve_is_noop():
    db = _fresh_db()
    persist_svc.persist_tool_executions(
        db,
        CLIENT,
        RUN_ID,
        {
            "toolExecutions": [_create_execution()],
            "invoices": [RESOLVER_INVOICE_BUNDLE],
        },
    )
    persist_svc.persist_tool_executions(
        db,
        CLIENT,
        RUN_ID,
        {"toolExecutions": [_l2_execution("send_invoice", SEND_ID)]},
    )
    send_calls = []

    async def _channels(*_a, **_k):
        send_calls.append(_k)
        return _delivered_send()

    client = _client()
    try:
        with patch.object(router_mod, "get_service_supabase", return_value=db), patch.object(
            router_mod, "run_in_threadpool", side_effect=_real_threadpool
        ), patch.object(invoice_svc, "_send_channels", side_effect=_channels):
            first = client.post(f"/api/v1/os/tool-executions/{SEND_ID}/approve")
            second = client.post(f"/api/v1/os/tool-executions/{SEND_ID}/approve")
    finally:
        _teardown()

    assert first.status_code == 200
    body = first.json()
    assert body["already_decided"] is False
    assert body["execution"]["status"] == "succeeded"
    assert body["execution"]["verification_state"] == "passed"
    assert body["execution"]["result"]["invoiceId"] == INV
    assert body["execution"]["result"]["paymentLink"] == PAY_LINK
    assert body["execution"]["result"]["emailSent"] is True
    assert body["execution"]["input"]["invoice_id"] == INV

    inv = _invoice_row(db)
    assert inv["status"] == "sent"
    assert inv["stripe_payment_link"] == PAY_LINK
    assert inv["status"] != "paid"
    assert float(inv["total"]) == 850.0
    assert inv["lead_id"] == STEVE

    assert second.status_code == 200
    assert second.json()["already_decided"] is True
    assert len(send_calls) == 1
    assert db.rows("invoices")[0]["status"] == "sent"


def test_overdue_reminder_approval_path_and_paid_non_overdue_never_remind():
    """Overdue reminder approves once. Paid/non-overdue reminder parks are
    executor defense-in-depth: refuse without sending. The Agent OS resolver
    must not propose send_invoice or send_invoice_reminder for those asks.
    """
    overdue = {
        **{
            "id": INV,
            "tenant_id": CLIENT,
            "lead_id": STEVE,
            "invoice_number": "INV-MEM-001",
            "items_json": [
                {
                    "description": "termite treatment",
                    "quantity": 1,
                    "unit_price": 850,
                }
            ],
            "subtotal": 850.0,
            "tax_rate": 0,
            "tax_amount": 0.0,
            "total": 850.0,
            "status": "overdue",
            "due_date": "2026-08-01",
            "stripe_payment_link": PAY_LINK,
        }
    }
    db = _fresh_db(invoices=[overdue])
    persist_svc.persist_tool_executions(
        db,
        CLIENT,
        RUN_ID,
        {"toolExecutions": [_l2_execution("send_invoice_reminder", REMIND_ID)]},
    )
    send_calls = []

    async def _channels(*_a, **kwargs):
        send_calls.append(kwargs)
        return _delivered_send()

    client = _client()
    try:
        with patch.object(router_mod, "get_service_supabase", return_value=db), patch.object(
            router_mod, "run_in_threadpool", side_effect=_real_threadpool
        ), patch.object(invoice_svc, "_send_channels", side_effect=_channels):
            resp = client.post(f"/api/v1/os/tool-executions/{REMIND_ID}/approve")
    finally:
        _teardown()

    assert resp.status_code == 200
    assert resp.json()["already_decided"] is False
    assert resp.json()["execution"]["status"] == "succeeded"
    assert resp.json()["execution"]["verification_state"] == "passed"
    assert len(send_calls) == 1
    assert send_calls[0].get("reminder") is True
    after = _invoice_row(db)
    assert after["status"] == "overdue"
    assert after["status"] != "paid"
    today = datetime.now(timezone.utc).date().isoformat()
    tags = [r["activity_type"] for r in db.rows("activity_log")]
    assert tags.count(f"invoice_reminder_{today}") == 1

    paid_id = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa1"
    not_due_id = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa2"
    paid_exec = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbb1"
    not_due_exec = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbb2"
    db2 = FakeSupabase(
        {
            "leads": [_lead()],
            "invoices": [
                {**overdue, "id": paid_id, "status": "paid"},
                {
                    **overdue,
                    "id": not_due_id,
                    "status": "sent",
                    "due_date": "2099-01-01",
                },
            ],
            "os_tool_executions": [],
            "activity_log": [],
            "tenants": [],
        }
    )
    persist_svc.persist_tool_executions(
        db2,
        CLIENT,
        RUN_ID,
        {
            "toolExecutions": [
                _l2_execution(
                    "send_invoice_reminder",
                    paid_exec,
                    invoice_id=paid_id,
                    idempotencyKey=f"send_invoice_reminder:{paid_id}",
                ),
                _l2_execution(
                    "send_invoice_reminder",
                    not_due_exec,
                    invoice_id=not_due_id,
                    idempotencyKey=f"send_invoice_reminder:{not_due_id}",
                ),
            ]
        },
    )
    reminder_sends = []

    async def _must_not_send(*_a, **_k):
        reminder_sends.append(1)
        raise AssertionError("paid/non-overdue must not send a reminder")

    client = _client()
    try:
        with patch.object(router_mod, "get_service_supabase", return_value=db2), patch.object(
            router_mod, "run_in_threadpool", side_effect=_real_threadpool
        ), patch.object(invoice_svc, "_send_channels", side_effect=_must_not_send):
            paid = client.post(f"/api/v1/os/tool-executions/{paid_exec}/approve")
            not_due = client.post(f"/api/v1/os/tool-executions/{not_due_exec}/approve")
    finally:
        _teardown()

    assert paid.status_code == 200
    assert paid.json()["execution"]["status"] == "failed"
    assert paid.json()["execution"]["error"]["code"] == "invoice_already_paid"
    assert not_due.status_code == 200
    assert not_due.json()["execution"]["status"] == "failed"
    assert not_due.json()["execution"]["error"]["code"] == "invoice_not_overdue"
    assert reminder_sends == []
    assert db2.rows("activity_log") == []
    # Resolver must not propose send_invoice for these reminder asks;
    # this fixture only parks send_invoice_reminder to prove executor refusal.
    assert all(r["tool_id"] != "send_invoice" for r in db2.rows("os_tool_executions"))


def test_tenant_isolation_and_unknown_outcome_is_not_replayed():
    db = _fresh_db()
    persist_svc.persist_tool_executions(
        db,
        CLIENT,
        RUN_ID,
        {
            "toolExecutions": [_create_execution()],
            "invoices": [RESOLVER_INVOICE_BUNDLE],
        },
    )
    persist_svc.persist_tool_executions(
        db,
        CLIENT,
        RUN_ID,
        {"toolExecutions": [_l2_execution("send_invoice", SEND_ID)]},
    )

    other_client = _client(OTHER_OWNER)
    try:
        with patch.object(router_mod, "get_service_supabase", return_value=db):
            hidden = other_client.get(f"/api/v1/os/tool-executions/{SEND_ID}")
            approve = other_client.post(f"/api/v1/os/tool-executions/{SEND_ID}/approve")
    finally:
        _teardown()
    assert hidden.status_code == 404
    assert approve.status_code == 404
    assert persist_svc.get_tool_execution(db, OTHER, SEND_ID) is None
    assert _invoice_row(db)["status"] == "draft"

    foreign = invoice_svc.run_invoice_l2(
        db,
        OTHER,
        {"tool_id": "send_invoice", "input": {"invoice_id": INV}},
    )
    assert foreign["refused"] is True
    assert foreign["code"] == "invoice_not_found"
    assert _invoice_row(db)["status"] == "draft"

    send_calls = []

    async def _timeout(*_a, **_k):
        send_calls.append(1)
        raise TimeoutError("invoice send timed out")

    client = _client()
    try:
        with patch.object(router_mod, "get_service_supabase", return_value=db), patch.object(
            router_mod, "run_in_threadpool", side_effect=_real_threadpool
        ), patch.object(invoice_svc, "_send_channels", side_effect=_timeout):
            first = client.post(f"/api/v1/os/tool-executions/{SEND_ID}/approve")
            second = client.post(f"/api/v1/os/tool-executions/{SEND_ID}/approve")
    finally:
        _teardown()

    assert first.status_code == 200
    row = persist_svc.get_tool_execution(db, CLIENT, SEND_ID)
    assert row["status"] == "running"
    assert row["error"]["code"] == "engine_unavailable"
    assert "unknown" in (row["error"]["message"] or "").lower() or "timed out" in (
        row["error"]["message"] or ""
    ).lower()
    assert second.status_code == 200
    assert second.json()["already_decided"] is True
    assert len(send_calls) == 1
    assert _invoice_row(db)["status"] == "draft"
    assert _invoice_row(db).get("stripe_payment_link") in (None, "")
