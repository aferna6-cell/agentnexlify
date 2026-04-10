"""Tests for the automation engine service.

Covers: process_pending_steps, send_invoice_payment_reminders,
send_weekly_intelligence_briefs, trigger_sequence, check_no_response_leads.

All external dependencies (Supabase, email, SMS, Anthropic) are mocked.
asyncio_mode = auto is set in pytest.ini so no @pytest.mark.asyncio needed.
"""

import os

os.environ["TESTING"] = "1"

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_db_mock():
    """Return a (db, table) pair where every chained Supabase call returns the
    same table mock and .execute() returns an empty result by default."""
    db = MagicMock()
    table = MagicMock()
    for method in (
        "select", "insert", "update", "delete",
        "eq", "neq", "gte", "lte", "gt", "lt",
        "limit", "order", "in_", "is_", "not_",
    ):
        getattr(table, method).return_value = table
    table.execute.return_value = MagicMock(data=[], count=0)
    db.table.return_value = table
    return db, table


# Known fixed datetimes for day-of-week tests
_KNOWN_MONDAY = datetime(2026, 3, 16, 12, 0, tzinfo=timezone.utc)  # weekday() == 0
_KNOWN_TUESDAY = datetime(2026, 3, 17, 12, 0, tzinfo=timezone.utc)  # weekday() == 1


# ---------------------------------------------------------------------------
# process_pending_steps
# ---------------------------------------------------------------------------


class TestProcessPendingSteps:
    """Tests for process_pending_steps()."""

    @patch("backend.services.automation_engine.execute_step", new_callable=AsyncMock)
    @patch("backend.services.automation_engine.get_service_supabase")
    async def test_happy_path_one_due_execution(self, mock_get_db, mock_execute_step):
        """One due execution → execute_step called once → returns 1."""
        db, table = _make_db_mock()
        mock_get_db.return_value = db
        table.execute.return_value = MagicMock(data=[{"id": "exec-001"}], count=1)

        from backend.services.automation_engine import process_pending_steps

        result = await process_pending_steps()

        assert result == 1
        mock_execute_step.assert_awaited_once_with("exec-001")

    @patch("backend.services.automation_engine.get_service_supabase")
    async def test_no_pending_steps_returns_zero(self, mock_get_db):
        """Empty result from DB → returns 0 without calling execute_step."""
        db, table = _make_db_mock()
        mock_get_db.return_value = db
        table.execute.return_value = MagicMock(data=[], count=0)

        from backend.services.automation_engine import process_pending_steps

        result = await process_pending_steps()
        assert result == 0

    @patch("backend.services.automation_engine.execute_step", new_callable=AsyncMock)
    @patch("backend.services.automation_engine.get_service_supabase")
    async def test_multiple_executions_all_processed(self, mock_get_db, mock_execute_step):
        """Three due executions → execute_step called three times → returns 3."""
        db, table = _make_db_mock()
        mock_get_db.return_value = db
        table.execute.return_value = MagicMock(
            data=[{"id": "exec-001"}, {"id": "exec-002"}, {"id": "exec-003"}],
            count=3,
        )

        from backend.services.automation_engine import process_pending_steps

        result = await process_pending_steps()
        assert result == 3
        assert mock_execute_step.await_count == 3

    @patch("backend.services.automation_engine.execute_step", new_callable=AsyncMock)
    @patch("backend.services.automation_engine.get_service_supabase")
    async def test_failed_execute_step_does_not_block_others(
        self, mock_get_db, mock_execute_step
    ):
        """If execute_step raises on first execution, the second one still runs."""
        db, table = _make_db_mock()
        mock_get_db.return_value = db
        table.execute.return_value = MagicMock(
            data=[{"id": "exec-fail"}, {"id": "exec-ok"}], count=2
        )
        # First call raises, second call succeeds
        mock_execute_step.side_effect = [Exception("DB timeout"), None]

        from backend.services.automation_engine import process_pending_steps

        result = await process_pending_steps()
        # Only the successful one is counted
        assert result == 1
        assert mock_execute_step.await_count == 2


# ---------------------------------------------------------------------------
# trigger_sequence
# ---------------------------------------------------------------------------


class TestTriggerSequence:
    """Tests for trigger_sequence()."""

    @patch("backend.services.automation_engine.get_service_supabase")
    async def test_matching_stage_creates_execution(self, mock_get_db):
        """Matching sequence + first step → creates execution row → returns 1."""
        db = MagicMock()
        mock_get_db.return_value = db

        seq_id = "seq-001"

        def table_side_effect(name):
            t = MagicMock()
            for method in (
                "select", "insert", "update", "eq", "neq",
                "in_", "is_", "gte", "lte", "limit", "order",
            ):
                getattr(t, method).return_value = t

            if name == "automation_sequences":
                t.execute.return_value = MagicMock(
                    data=[{"id": seq_id, "trigger_config": None}]
                )
            elif name == "automation_steps":
                t.execute.return_value = MagicMock(
                    data=[{"sequence_id": seq_id, "step_order": 1, "delay_minutes": 0}]
                )
            elif name == "automation_executions":
                t.execute.return_value = MagicMock(data=[{"id": "new-exec"}])
            else:
                t.execute.return_value = MagicMock(data=[])
            return t

        db.table.side_effect = table_side_effect

        from backend.services.automation_engine import trigger_sequence

        result = await trigger_sequence("tenant-001", "lead-001", "new_lead")
        assert result == 1

    @patch("backend.services.automation_engine.get_service_supabase")
    async def test_non_matching_stage_skips_enrollment(self, mock_get_db):
        """Sequence targets 'closed' but new_stage='contacted' → no enrollment → 0."""
        db = MagicMock()
        mock_get_db.return_value = db

        def table_side_effect(name):
            t = MagicMock()
            for method in (
                "select", "insert", "update", "eq", "neq",
                "in_", "is_", "gte", "lte", "limit", "order",
            ):
                getattr(t, method).return_value = t

            if name == "automation_sequences":
                t.execute.return_value = MagicMock(
                    data=[
                        {
                            "id": "seq-002",
                            "trigger_config": {"target_stage": "closed"},
                        }
                    ]
                )
            else:
                t.execute.return_value = MagicMock(data=[])
            return t

        db.table.side_effect = table_side_effect

        from backend.services.automation_engine import trigger_sequence

        result = await trigger_sequence(
            "tenant-001",
            "lead-001",
            "lead_stage_change",
            trigger_context={"new_stage": "contacted"},
        )
        assert result == 0

    @patch("backend.services.automation_engine.get_service_supabase")
    async def test_no_active_sequences_returns_zero(self, mock_get_db):
        """No sequences for this tenant+trigger → returns 0 immediately."""
        db = MagicMock()
        mock_get_db.return_value = db

        def table_side_effect(name):
            t = MagicMock()
            for method in (
                "select", "insert", "update", "eq", "neq",
                "in_", "is_", "gte", "lte", "limit", "order",
            ):
                getattr(t, method).return_value = t
            t.execute.return_value = MagicMock(data=[])
            return t

        db.table.side_effect = table_side_effect

        from backend.services.automation_engine import trigger_sequence

        result = await trigger_sequence("tenant-001", "lead-001", "no_response_24h")
        assert result == 0

    @patch("backend.services.automation_engine.get_service_supabase")
    async def test_already_enrolled_insert_exception_skips(self, mock_get_db):
        """DB insert raises (UNIQUE constraint) → caught, enrollment count stays 0.

        This validates the dedup guard: trigger_sequence swallows UNIQUE violations
        so re-triggering a sequence for an already-enrolled lead is a no-op.
        """
        db = MagicMock()
        mock_get_db.return_value = db

        seq_id = "seq-003"

        def table_side_effect(name):
            t = MagicMock()
            for method in (
                "select", "insert", "update", "eq", "neq",
                "in_", "is_", "gte", "lte", "limit", "order",
            ):
                getattr(t, method).return_value = t

            if name == "automation_sequences":
                t.execute.return_value = MagicMock(
                    data=[{"id": seq_id, "trigger_config": None}]
                )
            elif name == "automation_steps":
                t.execute.return_value = MagicMock(
                    data=[{"sequence_id": seq_id, "step_order": 1, "delay_minutes": 30}]
                )
            elif name == "automation_executions":
                # Simulate UNIQUE constraint violation on insert
                t.execute.side_effect = Exception(
                    'duplicate key value violates unique constraint'
                )
            else:
                t.execute.return_value = MagicMock(data=[])
            return t

        db.table.side_effect = table_side_effect

        from backend.services.automation_engine import trigger_sequence

        result = await trigger_sequence("tenant-001", "lead-dup", "new_lead")
        assert result == 0


# ---------------------------------------------------------------------------
# send_invoice_payment_reminders
# ---------------------------------------------------------------------------


class TestSendInvoicePaymentReminders:
    """Tests for send_invoice_payment_reminders()."""

    @patch("backend.services.automation_engine.send_sms", new_callable=AsyncMock)
    @patch("backend.services.automation_engine.send_email", new_callable=AsyncMock)
    @patch("backend.services.automation_engine.get_service_supabase")
    async def test_overdue_invoice_marked_overdue_and_email_sent(
        self, mock_get_db, mock_send_email, mock_send_sms
    ):
        """Invoice past due_date → status updated to 'overdue' + email reminder sent."""
        db = MagicMock()
        mock_get_db.return_value = db
        mock_send_email.return_value = {"success": True}

        past_date = (datetime.now(timezone.utc).date() - timedelta(days=3)).isoformat()

        inv = {
            "id": "inv-001",
            "tenant_id": "tenant-001",
            "lead_id": "lead-001",
            "invoice_number": "INV-001",
            "total": 500.00,
            "due_date": past_date,
            "status": "sent",
            "stripe_payment_link": "https://pay.stripe.com/test",
        }
        lead = {"name": "Alice", "email": "alice@example.com", "phone": None}
        tenant_info = {"business_name": "Test Biz", "owner_email": "owner@testbiz.com"}

        def table_side_effect(name):
            t = MagicMock()
            for method in (
                "select", "insert", "update", "eq", "neq",
                "in_", "is_", "gte", "lte", "limit", "order",
            ):
                getattr(t, method).return_value = t

            if name == "invoices":
                t.execute.return_value = MagicMock(data=[inv])
            elif name == "activity_log":
                t.execute.return_value = MagicMock(data=[], count=0)
            elif name == "leads":
                t.execute.return_value = MagicMock(data=[lead])
            elif name == "tenants":
                t.execute.return_value = MagicMock(data=[tenant_info])
            else:
                t.execute.return_value = MagicMock(data=[])
            return t

        db.table.side_effect = table_side_effect

        # Patch log_activity so it does not attempt real DB calls
        with patch("backend.services.automation_engine.log_activity", create=True):
            from backend.services.automation_engine import send_invoice_payment_reminders
            result = await send_invoice_payment_reminders()

        assert result >= 1
        mock_send_email.assert_awaited_once()
        call_kwargs = mock_send_email.call_args.kwargs
        assert "overdue" in call_kwargs.get("subject", "").lower()

    @patch("backend.services.automation_engine.send_sms", new_callable=AsyncMock)
    @patch("backend.services.automation_engine.send_email", new_callable=AsyncMock)
    @patch("backend.services.automation_engine.get_service_supabase")
    async def test_due_tomorrow_sends_reminder(
        self, mock_get_db, mock_send_email, mock_send_sms
    ):
        """Invoice due tomorrow → email reminder sent with 'tomorrow' in subject."""
        db = MagicMock()
        mock_get_db.return_value = db
        mock_send_email.return_value = {"success": True}

        tomorrow = (datetime.now(timezone.utc).date() + timedelta(days=1)).isoformat()

        inv = {
            "id": "inv-002",
            "tenant_id": "tenant-001",
            "lead_id": "lead-002",
            "invoice_number": "INV-002",
            "total": 250.00,
            "due_date": tomorrow,
            "status": "sent",
            "stripe_payment_link": "",
        }
        lead = {"name": "Bob", "email": "bob@example.com", "phone": None}
        tenant_info = {"business_name": "Test Biz", "owner_email": "owner@testbiz.com"}

        def table_side_effect(name):
            t = MagicMock()
            for method in (
                "select", "insert", "update", "eq", "neq",
                "in_", "is_", "gte", "lte", "limit", "order",
            ):
                getattr(t, method).return_value = t

            if name == "invoices":
                t.execute.return_value = MagicMock(data=[inv])
            elif name == "activity_log":
                t.execute.return_value = MagicMock(data=[], count=0)
            elif name == "leads":
                t.execute.return_value = MagicMock(data=[lead])
            elif name == "tenants":
                t.execute.return_value = MagicMock(data=[tenant_info])
            else:
                t.execute.return_value = MagicMock(data=[])
            return t

        db.table.side_effect = table_side_effect

        with patch("backend.services.automation_engine.log_activity", create=True):
            from backend.services.automation_engine import send_invoice_payment_reminders
            result = await send_invoice_payment_reminders()

        assert result >= 1
        mock_send_email.assert_awaited_once()
        call_kwargs = mock_send_email.call_args.kwargs
        assert "tomorrow" in call_kwargs.get("subject", "").lower()

    @patch("backend.services.automation_engine.send_email", new_callable=AsyncMock)
    @patch("backend.services.automation_engine.get_service_supabase")
    async def test_already_reminded_today_skips(self, mock_get_db, mock_send_email):
        """activity_log dedup hit for today → email NOT sent → returns 0."""
        db = MagicMock()
        mock_get_db.return_value = db

        past_date = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()

        inv = {
            "id": "inv-003",
            "tenant_id": "tenant-001",
            "lead_id": "lead-003",
            "invoice_number": "INV-003",
            "total": 100.00,
            "due_date": past_date,
            "status": "sent",
            "stripe_payment_link": "",
        }

        def table_side_effect(name):
            t = MagicMock()
            for method in (
                "select", "insert", "update", "eq", "neq",
                "in_", "is_", "gte", "lte", "limit", "order",
            ):
                getattr(t, method).return_value = t

            if name == "invoices":
                t.execute.return_value = MagicMock(data=[inv])
            elif name == "activity_log":
                # Dedup hit — already reminded today
                t.execute.return_value = MagicMock(data=[{"id": "log-1"}], count=1)
            else:
                t.execute.return_value = MagicMock(data=[])
            return t

        db.table.side_effect = table_side_effect

        from backend.services.automation_engine import send_invoice_payment_reminders

        result = await send_invoice_payment_reminders()

        assert result == 0
        mock_send_email.assert_not_awaited()

    @patch("backend.services.automation_engine.send_email", new_callable=AsyncMock)
    @patch("backend.services.automation_engine.get_service_supabase")
    async def test_invoice_with_no_lead_id_skips_gracefully(
        self, mock_get_db, mock_send_email
    ):
        """Invoice with lead_id=None → skipped early without crash or email."""
        db = MagicMock()
        mock_get_db.return_value = db

        past_date = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()

        inv = {
            "id": "inv-004",
            "tenant_id": "tenant-001",
            "lead_id": None,  # Missing lead_id
            "invoice_number": "INV-004",
            "total": 75.00,
            "due_date": past_date,
            "status": "sent",
            "stripe_payment_link": "",
        }

        def table_side_effect(name):
            t = MagicMock()
            for method in (
                "select", "insert", "update", "eq", "neq",
                "in_", "is_", "gte", "lte", "limit", "order",
            ):
                getattr(t, method).return_value = t

            if name == "invoices":
                t.execute.return_value = MagicMock(data=[inv])
            else:
                t.execute.return_value = MagicMock(data=[])
            return t

        db.table.side_effect = table_side_effect

        from backend.services.automation_engine import send_invoice_payment_reminders

        result = await send_invoice_payment_reminders()
        assert result == 0
        mock_send_email.assert_not_awaited()


# ---------------------------------------------------------------------------
# send_weekly_intelligence_briefs
# ---------------------------------------------------------------------------


class TestSendWeeklyIntelligenceBriefs:
    """Tests for send_weekly_intelligence_briefs().

    The function imports `settings` locally (`from backend.config import settings
    as app_settings`) so the correct patch target is `backend.config.settings`.
    Setting anthropic_api_key to an empty string skips the AI generation block.
    """

    @patch("backend.services.automation_engine.send_email", new_callable=AsyncMock)
    @patch("backend.services.automation_engine.get_service_supabase")
    async def test_tuesday_returns_zero_immediately(self, mock_get_db, mock_send_email):
        """Non-Monday weekday → returns 0, no email sent.

        Note: get_supabase IS called before the weekday check (by design),
        so we only assert on the final result and the absence of email sends.
        """
        db, table = _make_db_mock()
        mock_get_db.return_value = db

        from backend.services.automation_engine import send_weekly_intelligence_briefs

        with patch("backend.services.automation_engine.datetime") as mock_dt:
            mock_dt.now.return_value = _KNOWN_TUESDAY
            mock_dt.fromisoformat = datetime.fromisoformat
            result = await send_weekly_intelligence_briefs()

        assert result == 0
        mock_send_email.assert_not_awaited()

    @patch("backend.services.automation_engine.send_email", new_callable=AsyncMock)
    @patch("backend.services.automation_engine.get_service_supabase")
    async def test_monday_paid_tenant_sends_brief(self, mock_get_db, mock_send_email):
        """Monday + paid tenant + no dedup hit → email sent → returns 1."""
        db = MagicMock()
        mock_get_db.return_value = db
        mock_send_email.return_value = {"success": True}

        paid_tenant = {
            "id": "tenant-paid-001",
            "business_name": "My Biz",
            "owner_email": "owner@mybiz.com",
            "owner_name": "Sam",
            "plan": "growth",
            "business_type": "plumbing",
        }

        def table_side_effect(name):
            t = MagicMock()
            for method in (
                "select", "insert", "update", "eq", "neq",
                "in_", "is_", "gte", "lte", "limit", "order",
            ):
                getattr(t, method).return_value = t

            if name == "tenants":
                t.execute.return_value = MagicMock(data=[paid_tenant])
            elif name == "activity_log":
                t.execute.return_value = MagicMock(data=[], count=0)
            else:
                t.execute.return_value = MagicMock(data=[], count=0)
            return t

        db.table.side_effect = table_side_effect

        from backend.services.automation_engine import send_weekly_intelligence_briefs

        with patch("backend.services.automation_engine.datetime") as mock_dt, \
             patch("backend.config.settings") as mock_settings, \
             patch("backend.services.activity.log_activity"):
            mock_dt.now.return_value = _KNOWN_MONDAY
            mock_dt.fromisoformat = datetime.fromisoformat
            # Empty key → AI block is skipped (`if app_settings.anthropic_api_key:`)
            mock_settings.anthropic_api_key = ""
            result = await send_weekly_intelligence_briefs()

        assert result == 1
        mock_send_email.assert_awaited_once()
        call_kwargs = mock_send_email.call_args.kwargs
        assert "My Biz" in call_kwargs.get("subject", "")

    @patch("backend.services.automation_engine.send_email", new_callable=AsyncMock)
    @patch("backend.services.automation_engine.get_service_supabase")
    async def test_already_sent_this_week_skips(self, mock_get_db, mock_send_email):
        """Monday but dedup hit in activity_log → returns 0, no email sent."""
        db = MagicMock()
        mock_get_db.return_value = db

        paid_tenant = {
            "id": "tenant-001",
            "business_name": "Biz",
            "owner_email": "owner@biz.com",
            "owner_name": "Alex",
            "plan": "professional",
            "business_type": "other",
        }

        def table_side_effect(name):
            t = MagicMock()
            for method in (
                "select", "insert", "update", "eq", "neq",
                "in_", "is_", "gte", "lte", "limit", "order",
            ):
                getattr(t, method).return_value = t

            if name == "tenants":
                t.execute.return_value = MagicMock(data=[paid_tenant])
            elif name == "activity_log":
                # Dedup hit — already sent this week
                t.execute.return_value = MagicMock(data=[{"id": "log-brief-1"}], count=1)
            else:
                t.execute.return_value = MagicMock(data=[], count=0)
            return t

        db.table.side_effect = table_side_effect

        from backend.services.automation_engine import send_weekly_intelligence_briefs

        with patch("backend.services.automation_engine.datetime") as mock_dt, \
             patch("backend.config.settings") as mock_settings:
            mock_dt.now.return_value = _KNOWN_MONDAY
            mock_dt.fromisoformat = datetime.fromisoformat
            mock_settings.anthropic_api_key = ""
            result = await send_weekly_intelligence_briefs()

        assert result == 0
        mock_send_email.assert_not_awaited()

    @patch("backend.services.automation_engine.send_email", new_callable=AsyncMock)
    @patch("backend.services.automation_engine.get_service_supabase")
    async def test_free_plan_tenant_skipped(self, mock_get_db, mock_send_email):
        """Free-plan tenants are excluded by .neq('plan', 'free') at the DB level.

        We simulate this by returning an empty tenants list (as the live DB would
        after the filter), confirming no email is sent.
        """
        db, table = _make_db_mock()
        mock_get_db.return_value = db
        # All queries return empty — simulates the neq filter excluding free tenants
        table.execute.return_value = MagicMock(data=[], count=0)

        from backend.services.automation_engine import send_weekly_intelligence_briefs

        with patch("backend.services.automation_engine.datetime") as mock_dt, \
             patch("backend.config.settings") as mock_settings:
            mock_dt.now.return_value = _KNOWN_MONDAY
            mock_dt.fromisoformat = datetime.fromisoformat
            mock_settings.anthropic_api_key = ""
            result = await send_weekly_intelligence_briefs()

        assert result == 0
        mock_send_email.assert_not_awaited()


# ---------------------------------------------------------------------------
# process_recurring_invoices
# ---------------------------------------------------------------------------


class _RecurringInvoiceQuery:
    """Shared-state query mock for recurring invoice workflow tests."""

    def __init__(self, state):
        self.state = state
        self.kind = None
        self.payload = None

    @property
    def not_(self):
        return self

    def select(self, *args, **kwargs):
        if self.kind is None:
            self.kind = "count_select" if kwargs.get("count") == "exact" else "select"
        return self

    def update(self, data):
        self.kind = "update"
        self.payload = data
        return self

    def insert(self, data):
        self.kind = "insert"
        self.payload = data
        return self

    def eq(self, *args, **kwargs):
        return self

    def neq(self, *args, **kwargs):
        return self

    def lte(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def order(self, *args, **kwargs):
        return self

    def is_(self, *args, **kwargs):
        return self

    def execute(self):
        self.state["operations"].append((self.kind, self.payload))
        response = self.state["responses"].pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class TestProcessRecurringInvoices:
    """Tests for process_recurring_invoices()."""

    def _build_db(self, responses):
        state = {"responses": list(responses), "operations": []}
        db = MagicMock()

        def table_side_effect(name):
            if name == "invoices":
                return _RecurringInvoiceQuery(state)
            raise AssertionError(f"Unexpected table access: {name}")

        db.table.side_effect = table_side_effect
        return db, state

    @patch("backend.services.automation_engine.fire_event_background")
    @patch("backend.services.automation_engine.get_service_supabase")
    async def test_claim_lost_skips_duplicate_child_invoice(self, mock_get_db, mock_fire_event):
        """If another worker advances the parent first, no duplicate child invoice is created."""
        parent = {
            "id": "inv-parent-001",
            "tenant_id": "tenant-001",
            "lead_id": "lead-001",
            "items_json": [{"quantity": 1, "unit_price": 125}],
            "tax_rate": 0,
            "notes": "Monthly service plan",
            "recurrence_interval": "monthly",
            "next_invoice_date": "2026-04-01",
            "invoice_number": "INV-PARENT-001",
        }
        db, state = self._build_db(
            [
                MagicMock(data=[parent]),
                MagicMock(data=[], count=3),
                MagicMock(data=[]),
            ]
        )
        mock_get_db.return_value = db

        from backend.services.automation_engine import process_recurring_invoices

        result = await process_recurring_invoices()

        assert result == 0
        assert [kind for kind, _ in state["operations"]] == ["select", "count_select", "update"]
        mock_fire_event.assert_not_called()

    @patch("backend.services.automation_engine.fire_event_background")
    @patch("backend.services.automation_engine.get_service_supabase")
    async def test_insert_failure_rolls_back_parent_claim(self, mock_get_db, mock_fire_event):
        """If child invoice creation fails after the claim, next_invoice_date is restored."""
        parent = {
            "id": "inv-parent-002",
            "tenant_id": "tenant-002",
            "lead_id": "lead-002",
            "items_json": [{"quantity": 2, "unit_price": 75}],
            "tax_rate": 10,
            "notes": "Quarterly tune-up",
            "recurrence_interval": "monthly",
            "next_invoice_date": "2026-04-01",
            "invoice_number": "INV-PARENT-002",
        }
        db, state = self._build_db(
            [
                MagicMock(data=[parent]),
                MagicMock(data=[], count=8),
                MagicMock(data=[{"id": parent["id"]}]),
                Exception("insert failed"),
                MagicMock(data=[{"id": parent["id"]}]),
            ]
        )
        mock_get_db.return_value = db

        from backend.services.automation_engine import process_recurring_invoices

        result = await process_recurring_invoices()

        assert result == 0
        update_payloads = [payload for kind, payload in state["operations"] if kind == "update"]
        assert len(update_payloads) == 2
        assert update_payloads[0] == {"next_invoice_date": "2026-05-01"}
        assert update_payloads[1] == {"next_invoice_date": "2026-04-01"}
        mock_fire_event.assert_not_called()


# ---------------------------------------------------------------------------
# check_no_response_leads
# ---------------------------------------------------------------------------


class TestCheckNoResponseLeads:
    """Tests for check_no_response_leads()."""

    @patch("backend.services.automation_engine.trigger_sequence", new_callable=AsyncMock)
    @patch("backend.services.automation_engine.get_service_supabase")
    async def test_lead_with_no_response_triggers_sequence(
        self, mock_get_db, mock_trigger
    ):
        """Lead created 25h ago with no conversation → trigger_sequence called."""
        db = MagicMock()
        mock_get_db.return_value = db
        mock_trigger.return_value = 1

        old_time = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()

        lead = {
            "id": "lead-stale-001",
            "client_id": "tenant-001",
            "conversation_id": None,  # No conversation → no messages to check
            "created_at": old_time,
        }

        def table_side_effect(name):
            t = MagicMock()
            for method in (
                "select", "insert", "update", "eq", "neq",
                "in_", "is_", "gte", "lte", "limit", "order",
            ):
                getattr(t, method).return_value = t

            if name == "leads":
                t.execute.return_value = MagicMock(data=[lead])
            else:
                t.execute.return_value = MagicMock(data=[])
            return t

        db.table.side_effect = table_side_effect

        from backend.services.automation_engine import check_no_response_leads

        result = await check_no_response_leads()

        assert result == 1
        mock_trigger.assert_awaited_once_with(
            "tenant-001", "lead-stale-001", "no_response_24h"
        )

    @patch("backend.services.automation_engine.trigger_sequence", new_callable=AsyncMock)
    @patch("backend.services.automation_engine.get_service_supabase")
    async def test_lead_with_recent_message_skips(self, mock_get_db, mock_trigger):
        """Lead has a message within the last 24h → skip, trigger_sequence NOT called."""
        db = MagicMock()
        mock_get_db.return_value = db

        old_time = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
        recent_msg_time = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        conv_id = "conv-recent-001"
        session_id = "sess-recent-001"

        lead = {
            "id": "lead-active-001",
            "client_id": "tenant-001",
            "conversation_id": conv_id,
            "created_at": old_time,
        }

        def table_side_effect(name):
            t = MagicMock()
            for method in (
                "select", "insert", "update", "eq", "neq",
                "in_", "is_", "gte", "lte", "limit", "order",
            ):
                getattr(t, method).return_value = t

            if name == "leads":
                t.execute.return_value = MagicMock(data=[lead])
            elif name == "automation_executions":
                t.execute.return_value = MagicMock(data=[])
            elif name == "conversations":
                t.execute.return_value = MagicMock(
                    data=[{"id": conv_id, "session_id": session_id}]
                )
            elif name == "chat_messages":
                t.execute.return_value = MagicMock(
                    data=[{"session_id": session_id, "created_at": recent_msg_time}]
                )
            else:
                t.execute.return_value = MagicMock(data=[])
            return t

        db.table.side_effect = table_side_effect

        from backend.services.automation_engine import check_no_response_leads

        result = await check_no_response_leads()

        assert result == 0
        mock_trigger.assert_not_awaited()


    @patch("backend.services.automation_engine.trigger_sequence", new_callable=AsyncMock)
    @patch("backend.services.automation_engine.get_service_supabase")
    async def test_already_enrolled_in_progress_execution_skips(
        self, mock_get_db, mock_trigger
    ):
        """Lead already has an in_progress execution for a no_response_24h sequence.

        This tests the dedup fix from bug-patterns.md (2026-03-18): the query must
        use .in_('status', ['active', 'in_progress']) since trigger_sequence inserts
        with status='in_progress', not 'active'. Without the fix, leads would be
        re-enrolled on every automation loop tick.
        """
        db = MagicMock()
        mock_get_db.return_value = db

        old_time = (datetime.now(timezone.utc) - timedelta(hours=30)).isoformat()
        seq_id = "seq-no-resp-001"

        lead = {
            "id": "lead-enrolled-001",
            "client_id": "tenant-001",
            "conversation_id": None,
            "created_at": old_time,
        }

        def table_side_effect(name):
            t = MagicMock()
            for method in (
                "select", "insert", "update", "eq", "neq",
                "in_", "is_", "gte", "lte", "limit", "order",
            ):
                getattr(t, method).return_value = t

            if name == "leads":
                t.execute.return_value = MagicMock(data=[lead])
            elif name == "automation_executions":
                # Lead IS enrolled with status='in_progress'
                t.execute.return_value = MagicMock(
                    data=[{"lead_id": "lead-enrolled-001", "sequence_id": seq_id}]
                )
            elif name == "automation_sequences":
                # That sequence is a no_response_24h sequence
                t.execute.return_value = MagicMock(
                    data=[{"id": seq_id, "trigger_event": "no_response_24h"}]
                )
            else:
                t.execute.return_value = MagicMock(data=[])
            return t

        db.table.side_effect = table_side_effect

        from backend.services.automation_engine import check_no_response_leads

        result = await check_no_response_leads()

        assert result == 0
        mock_trigger.assert_not_awaited()


    @patch("backend.services.automation_engine.trigger_sequence", new_callable=AsyncMock)
    @patch("backend.services.automation_engine.get_service_supabase")
    async def test_no_candidate_leads_returns_zero(self, mock_get_db, mock_trigger):
        """No new leads older than 24h returns 0 and does not trigger a sequence."""
        db, table = _make_db_mock()
        mock_get_db.return_value = db
        table.execute.return_value = MagicMock(data=[])

        from backend.services.automation_engine import check_no_response_leads

        result = await check_no_response_leads()

        assert result == 0
        mock_trigger.assert_not_awaited()


# ---------------------------------------------------------------------------
# Automation rules
# ---------------------------------------------------------------------------


def _chain_table(result=None):
    table = MagicMock()
    for method in (
        "select", "insert", "update", "delete",
        "eq", "neq", "gte", "lte", "gt", "lt",
        "limit", "order", "in_", "is_", "not_",
    ):
        getattr(table, method).return_value = table
    table.execute.return_value = result or MagicMock(data=[])
    return table


class TestAutomationRules:
    @patch("backend.services.automation_engine.send_email", new_callable=AsyncMock)
    @patch("backend.services.automation_engine.get_service_supabase")
    async def test_execute_rule_loads_lead_with_rule_tenant(
        self, mock_get_db, mock_send_email
    ):
        """Rule execution should load lead data using the rule tenant before actions."""
        db = MagicMock()
        mock_get_db.return_value = db
        mock_send_email.return_value = {"success": True, "detail": "sent"}

        rule = {
            "id": "rule-001",
            "tenant_id": "tenant-001",
            "trigger_type": "lead_captured",
            "trigger_config": {},
            "triggered_count": 0,
            "actions": [
                {
                    "type": "send_email",
                    "config": {"subject": "Welcome", "body": "<p>Hello</p>"},
                }
            ],
        }
        lead = {
            "id": "lead-001",
            "client_id": "tenant-001",
            "email": "lead@example.com",
        }

        table_queue = {
            "automation_rules": [
                _chain_table(MagicMock(data=[rule])),
                _chain_table(MagicMock(data=[{"id": "rule-001"}])),
            ],
            "leads": [_chain_table(MagicMock(data=[lead]))],
            "automation_rule_executions": [
                _chain_table(MagicMock(data=[{"id": "exec-001"}]))
            ],
        }

        def table_side_effect(name):
            return table_queue[name].pop(0)

        db.table.side_effect = table_side_effect

        from backend.services.automation_engine import execute_automation_rule

        result = await execute_automation_rule("rule-001", "lead-001")

        assert result["status"] == "success"
        assert result["actions_run"][0]["result"]["status"] == "sent"
        mock_send_email.assert_awaited_once()
        assert mock_send_email.call_args.kwargs["to"] == "lead@example.com"
        assert mock_send_email.call_args.kwargs["tenant_id"] == "tenant-001"

    @patch("backend.services.automation_engine.get_service_supabase")
    async def test_enroll_in_sequence_action_creates_processable_execution(
        self, mock_get_db
    ):
        """Sequence enrollment actions need current_step and next_run_at."""
        db = MagicMock()
        mock_get_db.return_value = db
        inserted = []

        sequence_table = _chain_table(MagicMock(data=[{"id": "seq-001"}]))
        step_table = _chain_table(
            MagicMock(data=[{"step_order": 2, "delay_minutes": 15}])
        )
        execution_table = _chain_table(MagicMock(data=[{"id": "exec-001"}]))

        def capture_insert(payload):
            inserted.append(payload)
            return execution_table

        execution_table.insert.side_effect = capture_insert

        table_queue = {
            "automation_sequences": [sequence_table],
            "automation_steps": [step_table],
            "automation_executions": [execution_table],
        }
        db.table.side_effect = lambda name: table_queue[name].pop(0)

        from backend.services.automation_engine import _execute_action

        result = await _execute_action(
            action_type="enroll_in_sequence",
            action_config={"sequence_id": "seq-001"},
            lead_data={"id": "lead-001"},
            tenant_id="tenant-001",
            context={},
        )

        assert result == {"status": "success", "sequence_id": "seq-001"}
        assert inserted[0]["sequence_id"] == "seq-001"
        assert inserted[0]["lead_id"] == "lead-001"
        assert inserted[0]["tenant_id"] == "tenant-001"
        assert inserted[0]["current_step"] == 2
        assert inserted[0]["status"] == "in_progress"
        assert inserted[0]["next_run_at"]

    def test_scheduled_rule_skips_when_already_fired_today(self):
        from backend.services.automation_engine import _scheduled_rule_already_fired

        now = datetime(2026, 4, 7, 9, 0, tzinfo=timezone.utc)
        rule = {
            "trigger_type": "scheduled_daily",
            "last_triggered_at": "2026-04-07T08:55:00+00:00",
        }

        assert _scheduled_rule_already_fired(rule, now) is True
