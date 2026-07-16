"""Accepted opportunity suggestions become real drafts.

Contract:
  1. Accepting a cold-leads suggestion drafts one follow-up per cold
     warm/hot lead that has contact info: channel email when the lead has
     an email (sms only as fallback), recipient pre-filled on the
     deliverable, action_type matching the channel, and deliverable_status
     ALWAYS pending_approval - the suggestion card promises "you approve
     every message before it sends".
  2. Contactless leads are skipped; drafts are capped per acceptance.
  3. Accepting an overdue-invoices suggestion drafts one reminder per
     overdue invoice whose linked lead has an email.
  4. One shared OS thread collects the batch; one owner notification fires
     for the batch (not one per draft).
  5. Dispatch is keyed on the suggestion wording our own scanner produced;
     non-opportunity rows and unrecognized summaries do nothing.
  6. Never raises - any DB failure degrades to zero drafts.
"""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
os.environ.setdefault("TESTING", "1")

from backend.services import os_opportunity_fulfill as fulfill

_TENANT = "aaaaaaaa-0000-0000-0000-000000000001"


def _lead(i, email=None, phone=None, temp="warm"):
    return {
        "id": f"lead-{i}",
        "name": f"Lead {i}",
        "email": email,
        "phone": phone,
        "lead_temperature": temp,
        "areas_of_interest": "brake service",
    }


class _Query:
    """Chainable fake for tenant_table/db.table queries."""

    def __init__(self, rows):
        self._rows = rows
        self.inserted = None

    def __getattr__(self, name):
        def chain(*args, **kwargs):
            return self

        return chain

    def insert(self, row):
        self.inserted = row
        self._rows = [dict(row, id=f"new-{id(row) % 1000}")]
        return self

    def execute(self):
        return MagicMock(data=self._rows)


def _env(leads=None, invoices=None, tenant_row=None):
    """(db, tables) where tables records every tenant_table call by name."""
    created = {"os_threads": [], "os_agent_runs": [], "os_messages": []}

    def tenant_table(db, table, client_id):
        if table == "leads":
            return _Query(list(leads or []))
        if table == "invoices":
            return _Query(list(invoices or []))
        if table == "tenants":
            return _Query([tenant_row or {"business_name": "Acme Auto", "owner_name": "Sam"}])
        q = _Query([])
        orig_insert = q.insert

        def insert(row, _table=table, _q=q):
            created[_table].append(row)
            return orig_insert(row)

        q.insert = insert
        return q

    return MagicMock(), tenant_table, created


def _run_leads(leads, notify=None):
    db, tables, created = _env(leads=leads)
    with (
        patch.object(fulfill, "tenant_table", tables),
        patch.object(
            fulfill.os_approval_notify,
            "notify_pending_approval",
            notify or AsyncMock(return_value=True),
        ),
    ):
        n = asyncio.run(fulfill._draft_lead_followups(db, _TENANT))
    return n, created


def test_lead_followups_create_pending_drafts_with_recipients():
    n, created = _run_leads([_lead(1, email="a@x.com"), _lead(2, phone="+15555550123")])
    assert n == 2
    runs = created["os_agent_runs"]
    assert len(runs) == 2
    email_run = next(r for r in runs if r["deliverable"]["channel"] == "email")
    sms_run = next(r for r in runs if r["deliverable"]["channel"] == "sms")
    assert email_run["action_type"] == "email.send"
    assert email_run["deliverable"]["recipient"] == "a@x.com"
    assert sms_run["action_type"] == "sms.send"
    assert sms_run["deliverable"]["recipient"] == "+15555550123"
    for r in runs:
        assert r["deliverable_status"] == "pending_approval"
        assert r["agent_name"] == "sales"


def test_email_preferred_over_phone():
    n, created = _run_leads([_lead(1, email="a@x.com", phone="+15555550123")])
    assert n == 1
    d = created["os_agent_runs"][0]["deliverable"]
    assert d["channel"] == "email"
    assert d["recipient"] == "a@x.com"


def test_contactless_leads_are_skipped():
    n, created = _run_leads([_lead(1), _lead(2, email="b@x.com")])
    assert n == 1
    assert len(created["os_agent_runs"]) == 1


def test_drafts_are_capped_per_acceptance():
    leads = [_lead(i, email=f"l{i}@x.com") for i in range(25)]
    n, created = _run_leads(leads)
    assert n == fulfill._MAX_DRAFTS
    assert len(created["os_agent_runs"]) == fulfill._MAX_DRAFTS


def test_batch_gets_one_thread_and_one_notification():
    notify = AsyncMock(return_value=True)
    n, created = _run_leads(
        [_lead(1, email="a@x.com"), _lead(2, email="b@x.com")], notify=notify
    )
    assert n == 2
    assert len(created["os_threads"]) == 1
    assert len(created["os_messages"]) == 1
    notify.assert_awaited_once()


def test_draft_body_is_personalized():
    _, created = _run_leads([_lead(1, email="a@x.com")])
    body = created["os_agent_runs"][0]["deliverable"]["body"]
    assert "Lead" in body  # greeted by first name ("Lead 1" -> "Lead")
    assert "Acme Auto" in body


# --- invoice reminders ---------------------------------------------------------
def test_invoice_reminders_draft_via_linked_lead_email():
    invoices = [
        {"id": "inv-1", "invoice_number": "INV-7", "total": 800, "due_date": "2026-07-01", "lead_id": "lead-1"},
        {"id": "inv-2", "invoice_number": "INV-8", "total": 200, "due_date": "2026-07-02", "lead_id": None},
    ]
    db, tables, created = _env(
        leads=[_lead(1, email="payer@x.com")], invoices=invoices
    )
    with (
        patch.object(fulfill, "tenant_table", tables),
        patch.object(
            fulfill.os_approval_notify, "notify_pending_approval", AsyncMock()
        ),
    ):
        n = asyncio.run(fulfill._draft_invoice_reminders(db, _TENANT))
    assert n == 1
    run = created["os_agent_runs"][0]
    assert run["agent_name"] == "invoicing"
    assert run["deliverable"]["recipient"] == "payer@x.com"
    assert run["deliverable"]["channel"] == "email"
    assert "INV-7" in run["deliverable"]["body"]
    assert run["deliverable_status"] == "pending_approval"


# --- dispatch ---------------------------------------------------------------------
def test_dispatch_routes_on_scanner_wording():
    with (
        patch.object(fulfill, "_draft_lead_followups", AsyncMock(return_value=3)) as leads_fn,
        patch.object(fulfill, "_draft_invoice_reminders", AsyncMock(return_value=2)) as inv_fn,
    ):
        n = asyncio.run(
            fulfill.fulfill_accepted_suggestion(
                MagicMock(),
                _TENANT,
                {"reason": "opportunity", "summary": "5 leads went cold this week — want me to follow up?"},
            )
        )
        assert n == 3
        leads_fn.assert_awaited_once()
        inv_fn.assert_not_awaited()

    with (
        patch.object(fulfill, "_draft_lead_followups", AsyncMock(return_value=3)) as leads_fn,
        patch.object(fulfill, "_draft_invoice_reminders", AsyncMock(return_value=2)) as inv_fn,
    ):
        n = asyncio.run(
            fulfill.fulfill_accepted_suggestion(
                MagicMock(),
                _TENANT,
                {"reason": "opportunity", "summary": "2 unpaid invoices ($900) past due — want me to send reminders?"},
            )
        )
        assert n == 2
        inv_fn.assert_awaited_once()
        leads_fn.assert_not_awaited()


def test_dispatch_ignores_non_opportunity_and_unknown():
    with patch.object(fulfill, "_draft_lead_followups", AsyncMock()) as leads_fn:
        n = asyncio.run(
            fulfill.fulfill_accepted_suggestion(
                MagicMock(), _TENANT, {"reason": "no_fit", "summary": "5 leads went cold"}
            )
        )
        assert n == 0
        n2 = asyncio.run(
            fulfill.fulfill_accepted_suggestion(
                MagicMock(), _TENANT, {"reason": "opportunity", "summary": "build me a rocket"}
            )
        )
        assert n2 == 0
        leads_fn.assert_not_awaited()


def test_no_cold_leads_creates_nothing():
    n, created = _run_leads([])
    assert n == 0
    assert created["os_threads"] == []
    assert created["os_agent_runs"] == []


def test_degrades_gracefully_when_side_tables_fail():
    """Tenant lookup, thread, message, and notify failures never block drafts."""
    leads = [_lead(1, email="a@x.com")]

    def tenant_table(db, table, client_id):
        if table == "leads":
            return _Query(list(leads))
        if table == "os_agent_runs":
            return _Query([])
        raise RuntimeError(f"{table} down")

    notify = AsyncMock(side_effect=RuntimeError("resend down"))
    with (
        patch.object(fulfill, "tenant_table", tenant_table),
        patch.object(fulfill.os_approval_notify, "notify_pending_approval", notify),
    ):
        n = asyncio.run(fulfill._draft_lead_followups(MagicMock(), _TENANT))
    # The draft still lands: business identity fell back to defaults, the
    # thread is simply absent, and the notify failure was swallowed.
    assert n == 1


def test_run_insert_failure_is_not_counted():
    leads = [_lead(1, email="a@x.com"), _lead(2, email="b@x.com")]
    inserted = []

    def tenant_table(db, table, client_id):
        if table == "leads":
            return _Query(list(leads))
        if table == "os_agent_runs":
            if not inserted:
                inserted.append(True)
                raise RuntimeError("insert down")
            return _Query([])
        if table == "tenants":
            return _Query([{"business_name": "Acme", "owner_name": "Sam"}])
        return _Query([])

    with (
        patch.object(fulfill, "tenant_table", tenant_table),
        patch.object(
            fulfill.os_approval_notify, "notify_pending_approval", AsyncMock()
        ),
    ):
        n = asyncio.run(fulfill._draft_lead_followups(MagicMock(), _TENANT))
    assert n == 1  # first insert failed, second landed


def test_invoice_with_unreachable_lead_is_skipped():
    invoices = [
        {"id": "inv-1", "invoice_number": "INV-7", "total": 800, "due_date": "2026-07-01", "lead_id": "lead-1"},
    ]

    def tenant_table(db, table, client_id):
        if table == "invoices":
            return _Query(list(invoices))
        if table == "leads":
            raise RuntimeError("lead lookup down")
        if table == "tenants":
            return _Query([{"business_name": "Acme", "owner_name": "Sam"}])
        return _Query([])

    with (
        patch.object(fulfill, "tenant_table", tenant_table),
        patch.object(
            fulfill.os_approval_notify, "notify_pending_approval", AsyncMock()
        ),
    ):
        n = asyncio.run(fulfill._draft_invoice_reminders(MagicMock(), _TENANT))
    assert n == 0


def test_no_overdue_invoices_creates_nothing():
    db, tables, created = _env(invoices=[])
    with patch.object(fulfill, "tenant_table", tables):
        n = asyncio.run(fulfill._draft_invoice_reminders(db, _TENANT))
    assert n == 0
    assert created["os_threads"] == []


def test_never_raises_on_db_failure():
    def exploding_table(db, table, client_id):
        raise RuntimeError("db down")

    with patch.object(fulfill, "tenant_table", exploding_table):
        n = asyncio.run(
            fulfill.fulfill_accepted_suggestion(
                MagicMock(),
                _TENANT,
                {"reason": "opportunity", "summary": "5 leads went cold this week"},
            )
        )
    assert n == 0


# --- endpoint wiring -----------------------------------------------------------------
def _run_decide(decision, row):
    from fastapi import BackgroundTasks

    from backend.routers import os_backlog as router_mod

    load = _Query([row])
    update = _Query([dict(row, status=decision)])
    calls = iter([load, update])

    background = BackgroundTasks()
    with (
        patch.object(router_mod, "get_service_supabase", return_value=MagicMock()),
        patch.object(router_mod, "tenant_table", lambda db, t, c: next(calls)),
    ):
        result = asyncio.run(
            router_mod.decide_backlog(
                "req-1",
                router_mod.BacklogDecisionRequest(decision=decision),
                background,
                claims={"tenant_id": _TENANT, "role": "owner"},
            )
        )
    return result, background


def test_accept_schedules_fulfillment():
    row = {"id": "req-1", "reason": "opportunity", "summary": "3 leads went cold", "status": "pending"}
    result, background = _run_decide("accepted", row)
    assert result["status"] == "accepted"
    assert len(background.tasks) == 1


def test_decline_schedules_nothing():
    row = {"id": "req-1", "reason": "opportunity", "summary": "3 leads went cold", "status": "pending"}
    _, background = _run_decide("declined", row)
    assert len(background.tasks) == 0
