"""Billing Automation v1 — invoice Action Executor data plane.

Covers flag-off, L1 draft apply (customer/amount/items, no guess, idempotent),
L2 send/reminder (approval claim path, no false success, no paid reminders,
no spam), and the persist bridge. Payment status is stored state only.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import patch

import pytest

from backend.services import os_invoice_actions as svc
from backend.services.m8_action_flags import invoice_actions_enabled
from backend.services import os_tool_executions as persist_svc
from backend.tests.fake_supabase_store import FakeSupabase


CLIENT = "11111111-1111-1111-1111-111111111111"
OTHER = "22222222-2222-2222-2222-222222222222"
STEVE = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
INV = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
EXEC_ID = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"


TERMITE_ITEMS = [{"description": "Termite treatment", "quantity": 1, "unitPrice": 850}]
TERMITE_ITEMS_SNAKE = [
    {"description": "Termite treatment", "quantity": 1, "unit_price": 850}
]


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


def _invoice(**overrides):
    row = {
        "id": INV,
        "tenant_id": CLIENT,
        "lead_id": STEVE,
        "invoice_number": "INV-1111-001",
        "items_json": TERMITE_ITEMS_SNAKE,
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


def _draft_bundle(**overrides):
    row = {
        "id": "inv_engine_tmp",
        "_op": "create",
        "customerId": STEVE,
        "items": TERMITE_ITEMS,
        "taxRate": 0,
        "total": 850,
        "dueDate": "2026-09-17",
        "notes": "Termite treatment",
        "idempotencyKey": "steve-termite-850",
    }
    row.update(overrides)
    return row


def test_invoice_actions_flag_defaults_off(monkeypatch):
    monkeypatch.delenv("INVOICE_ACTIONS_ENABLED", raising=False)
    assert invoice_actions_enabled() is False
    monkeypatch.setenv("INVOICE_ACTIONS_ENABLED", "0")
    assert invoice_actions_enabled() is False
    monkeypatch.setenv("INVOICE_ACTIONS_ENABLED", "false")
    assert invoice_actions_enabled() is False


def test_refuse_when_flag_off(monkeypatch):
    monkeypatch.setenv("INVOICE_ACTIONS_ENABLED", "0")
    reason = svc.refuse_invoice_tool(tool_id="send_invoice")
    assert reason
    assert "INVOICE_ACTIONS_ENABLED" in reason
    assert "mark_invoice_paid" not in svc.INVOICE_TOOL_IDS


def test_apply_skipped_when_flag_off(monkeypatch):
    monkeypatch.setenv("INVOICE_ACTIONS_ENABLED", "0")
    db = FakeSupabase({"leads": [_lead()], "invoices": []})
    out = svc.apply_invoice_mutations(db, CLIENT, [_draft_bundle()])
    assert out == []
    assert db.rows("invoices") == []


def test_create_draft_preserves_customer_amount_items():
    db = FakeSupabase({"leads": [_lead()], "invoices": []})
    out = svc.apply_invoice_mutations(db, CLIENT, [_draft_bundle()])
    assert out[0]["applied"] is True
    assert out[0]["detail"] == "created"
    rows = db.rows("invoices")
    assert len(rows) == 1
    inv = rows[0]
    assert inv["lead_id"] == STEVE
    assert float(inv["total"]) == 850.0
    assert inv["items_json"][0]["description"] == "Termite treatment"
    assert float(inv["items_json"][0]["unit_price"]) == 850
    assert inv["status"] == "draft"
    assert inv["due_date"] == "2026-09-17"
    assert inv["status"] != "paid"


def test_create_draft_never_guesses_missing_or_cross_tenant_customer():
    db = FakeSupabase(
        {
            "leads": [_lead(client_id=OTHER, id="lead_other")],
            "invoices": [],
        }
    )
    missing = svc.apply_invoice_mutations(
        db, CLIENT, [_draft_bundle(customerId="lead_unknown")]
    )
    assert missing[0]["applied"] is False
    assert missing[0]["detail"] == "customer_not_found"

    foreign = svc.apply_invoice_mutations(
        db, CLIENT, [_draft_bundle(customerId="lead_other")]
    )
    assert foreign[0]["applied"] is False
    assert foreign[0]["detail"] == "customer_not_found"
    assert db.rows("invoices") == []


def test_create_draft_is_idempotent_on_fingerprint():
    db = FakeSupabase({"leads": [_lead()], "invoices": []})
    first = svc.apply_invoice_mutations(db, CLIENT, [_draft_bundle()])
    second = svc.apply_invoice_mutations(db, CLIENT, [_draft_bundle()])
    assert first[0]["applied"] is True
    assert second[0]["applied"] is True
    assert second[0]["detail"] == "deduplicated"
    assert first[0]["invoice_id"] == second[0]["invoice_id"]
    assert len(db.rows("invoices")) == 1


def test_apply_never_sets_paid():
    db = FakeSupabase({"leads": [_lead()], "invoices": []})
    svc.apply_invoice_mutations(
        db, CLIENT, [_draft_bundle(status="paid")]
    )
    assert db.rows("invoices")[0]["status"] == "draft"


def test_persist_applies_invoice_bundle():
    db = FakeSupabase(
        {
            "os_tool_executions": [],
            "leads": [_lead()],
            "invoices": [],
        }
    )
    record = {
        "toolExecutions": [
            {
                "id": EXEC_ID,
                "accountId": CLIENT,
                "toolId": "create_invoice_draft",
                "riskLevel": 1,
                "mutating": True,
                "requiresApproval": False,
                "approvalState": "not_required",
                "status": "succeeded",
                "input": {"customer_id": STEVE, "items": TERMITE_ITEMS_SNAKE},
                "result": {"customerId": STEVE, "total": 850},
                "verificationState": "passed",
                "attempts": 1,
                "createdAt": "2026-09-03T12:00:00Z",
            }
        ],
        "invoices": [_draft_bundle()],
    }
    persist_svc.persist_tool_executions(db, CLIENT, None, record)
    invoices = db.rows("invoices")
    assert len(invoices) == 1
    assert invoices[0]["lead_id"] == STEVE
    assert float(invoices[0]["total"]) == 850
    assert invoices[0]["status"] == "draft"


def test_l2_send_creates_payment_link_and_marks_sent():
    db = FakeSupabase({"leads": [_lead()], "invoices": [_invoice()], "tenants": []})

    async def _channels(*_a, **_k):
        return {
            "email_sent": True,
            "sms_sent": False,
            "payment_link": "https://pay.stripe.test/inv",
            "errors": [],
            "lead": _lead(),
        }

    with patch.object(svc, "_send_channels", side_effect=_channels):
        out = svc.run_invoice_l2(
            db,
            CLIENT,
            {
                "tool_id": "send_invoice",
                "input": {"invoice_id": INV, "method": "email"},
            },
        )
    assert out["executed"] is True
    assert out["verified"] is True
    row = db.rows("invoices")[0]
    assert row["status"] == "sent"
    assert row["stripe_payment_link"] == "https://pay.stripe.test/inv"
    assert row["status"] != "paid"


def test_l2_send_already_sent_is_adopted_not_duplicated():
    db = FakeSupabase(
        {
            "leads": [_lead()],
            "invoices": [
                _invoice(status="sent", stripe_payment_link="https://pay.stripe.test/inv")
            ],
        }
    )
    out = svc.run_invoice_l2(
        db,
        CLIENT,
        {"tool_id": "send_invoice", "input": {"invoice_id": INV}},
    )
    assert out["adopted"] is True
    assert out["verified"] is True
    assert out["executed"] is False
    assert out["result"]["deduplicated"] is True


def test_l2_send_cross_tenant_not_found():
    db = FakeSupabase(
        {
            "leads": [_lead()],
            "invoices": [_invoice(tenant_id=OTHER)],
        }
    )
    out = svc.run_invoice_l2(
        db,
        CLIENT,
        {"tool_id": "send_invoice", "input": {"invoice_id": INV}},
    )
    assert out["refused"] is True
    assert out["code"] == "invoice_not_found"


def test_l2_send_provider_failure_is_not_success():
    db = FakeSupabase({"leads": [_lead()], "invoices": [_invoice()], "tenants": []})

    async def _channels(*_a, **_k):
        return {
            "email_sent": False,
            "sms_sent": False,
            "payment_link": "",
            "errors": ["Email failed: provider down"],
            "lead": _lead(),
        }

    with patch.object(svc, "_send_channels", side_effect=_channels):
        out = svc.run_invoice_l2(
            db,
            CLIENT,
            {"tool_id": "send_invoice", "input": {"invoice_id": INV}},
        )
    assert out.get("verified") is False
    assert out.get("code") == "send_failed"
    assert db.rows("invoices")[0]["status"] == "draft"


def test_l2_send_refuses_when_flag_off(monkeypatch):
    monkeypatch.setenv("INVOICE_ACTIONS_ENABLED", "0")
    out = svc.run_invoice_l2(
        FakeSupabase({"invoices": [_invoice()]}),
        CLIENT,
        {"tool_id": "send_invoice", "input": {"invoice_id": INV}},
    )
    assert out["refused"] is True
    assert out["executed"] is False


def test_reminder_refuses_paid_and_not_overdue():
    paid = FakeSupabase({"invoices": [_invoice(status="paid")]})
    paid_out = svc.run_invoice_l2(
        paid, CLIENT, {"tool_id": "send_invoice_reminder", "input": {"invoice_id": INV}}
    )
    assert paid_out["refused"] is True
    assert paid_out["code"] == "invoice_already_paid"

    draft = FakeSupabase({"invoices": [_invoice(status="sent", due_date="2099-01-01")]})
    not_due = svc.run_invoice_l2(
        draft,
        CLIENT,
        {"tool_id": "send_invoice_reminder", "input": {"invoice_id": INV}},
    )
    assert not_due["refused"] is True
    assert not_due["code"] == "invoice_not_overdue"


def test_reminder_does_not_spam_same_day():
    db = FakeSupabase(
        {
            "leads": [_lead()],
            "invoices": [_invoice(status="overdue", due_date="2026-08-01")],
            "activity_log": [],
            "tenants": [],
        }
    )

    async def _channels(*_a, **_k):
        return {
            "email_sent": True,
            "sms_sent": False,
            "payment_link": "https://pay.stripe.test/inv",
            "errors": [],
            "lead": _lead(),
        }

    with patch.object(svc, "_send_channels", side_effect=_channels):
        first = svc.run_invoice_l2(
            db,
            CLIENT,
            {"tool_id": "send_invoice_reminder", "input": {"invoice_id": INV}},
        )
        second = svc.run_invoice_l2(
            db,
            CLIENT,
            {"tool_id": "send_invoice_reminder", "input": {"invoice_id": INV}},
        )
    assert first["executed"] is True
    assert first["verified"] is True
    assert second["adopted"] is True
    assert second["result"]["deduplicated"] is True
    tags = [r["activity_type"] for r in db.rows("activity_log")]
    today = datetime.now(timezone.utc).date().isoformat()
    assert tags.count(f"invoice_reminder_{today}") == 1
    assert db.rows("invoices")[0]["status"] != "paid"


def test_reminder_does_not_mark_paid():
    db = FakeSupabase(
        {
            "leads": [_lead()],
            "invoices": [_invoice(status="overdue", due_date="2026-08-01")],
            "activity_log": [],
            "tenants": [],
        }
    )

    async def _channels(*_a, **_k):
        return {
            "email_sent": True,
            "sms_sent": False,
            "payment_link": "https://pay.stripe.test/inv",
            "errors": [],
            "lead": _lead(),
        }

    with patch.object(svc, "_send_channels", side_effect=_channels):
        out = svc.run_invoice_l2(
            db,
            CLIENT,
            {"tool_id": "send_invoice_reminder", "input": {"invoice_id": INV}},
        )
    assert out["verified"] is True
    assert db.rows("invoices")[0]["status"] == "overdue"
