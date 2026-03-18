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
    """Return a MagicMock that makes every chained Supabase call return itself,
    with .execute() returning an empty result by default."""
    db = MagicMock()
    table = MagicMock()
    for method in (
        "select", "insert", "update", "delete",
        "eq", "neq", "gte", "lte", "gt", "lt",
        "limit", "order", "in_", "is_", "not_",
    ):
        getattr(table, method).return_value = table

    # count attribute on not_ sub-mock
    table.not_.is_.return_value = table
    table.execute.return_value = MagicMock(data=[], count=0)
    db.table.return_value = table
    return db, table


def _monday_utc() -> datetime:
    """Return a UTC datetime that falls on a Monday."""
    now = datetime.now(timezone.utc)
    days_until_monday = (7 - now.weekday()) % 7
    if days_until_monday == 0:
        return now
    return now + timedelta(days=days_until_monday)


def _tuesday_utc() -> datetime:
    """Return a UTC datetime that falls on a Tuesday."""
    monday = _monday_utc()
    return monday + timedelta(days=1)


# ---------------------------------------------------------------------------
# process_pending_steps
# ---------------------------------------------------------------------------


class TestProcessPendingSteps:
    """Tests for process_pending_steps()."""

    @patch("backend.services.automation_engine.execute_step", new_callable=AsyncMock)
    @patch("backend.services.automation_engine.get_supabase")
    async def test_happy_path_one_due_execution(self, mock_get_db, mock_execute_step):
        """One due execution → execute_step called once → returns 1."""
        db, table = _make_db_mock()
        mock_get_db.return_value = db

        # automation_executions returns one row
        table.execute.return_value = MagicMock(data=[{"id": "exec-001"}], count=1)

        from backend.services.automation_engine import process_pending_steps

        result = await process_pending_steps()

        assert result == 1
        mock_execute_step.assert_awaited_once_with("exec-001")

    @patch("backend.services.automation_engine.get_supabase")
    async def test_no_pending_steps_returns_zero(self, mock_get_db):
        """Empty result from DB → returns 0 without touching execute_step."""
        db, table = _make_db_mock()
        mock_get_db.return_value = db
        table.execute.return_value = MagicMock(data=[], count=0)

        from backend.services.automation_engine import process_pending_steps

        result = await process_pending_steps()
        assert result == 0

    @patch("backend.services.automation_engine.execute_step", new_callable=AsyncMock)
    @patch("backend.services.automation_engine.get_supabase")
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
    @patch("backend.services.automation_engine.get_supabase")
    async def test_failed_execute_step_does_not_block_others(
        self, mock_get_db, mock_execute_step
    ):
        """If execute_step raises on first execution, second one still runs."""
        db, table = _make_db_mock()
        mock_get_db.return_value = db
        table.execute.return_value = MagicMock(
            data=[{"id": "exec-fail"}, {"id": "exec-ok"}], count=2
        )

        # First call raises, second call succeeds
        mock_execute_step.side_effect = [Exception("DB timeout"), None]

        from backend.services.automation_engine import process_pending_steps

        # Only the successful one counts
        result = await process_pending_steps()
        assert result == 1
        assert mock_execute_step.await_count == 2


# ---------------------------------------------------------------------------
# trigger_sequence
# ---------------------------------------------------------------------------


class TestTriggerSequence:
    """Tests for trigger_sequence()."""

    @patch("backend.services.automation_engine.get_supabase")
    async def test_matching_stage_creates_execution(self, mock_get_db):
        """Matching sequence + first step → creates execution → returns 1."""
        db = MagicMock()
        mock_get_db.return_value = db

        seq_id = "seq-001"
        step_id = "step-001"

        # Call counter to return different data per table
        call_count = [0]

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

    @patch("backend.services.automation_engine.get_supabase")
    async def test_non_matching_stage_skips_enrollment(self, mock_get_db):
        """Sequence with different target_stage → no enrollment → returns 0."""
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

        # trigger_context has new_stage=contacted, but sequence wants closed
        result = await trigger_sequence(
            "tenant-001",
            "lead-001",
            "lead_stage_change",
            trigger_context={"new_stage": "contacted"},
        )
        assert result == 0

    @patch("backend.services.automation_engine.get_supabase")
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

    @patch("backend.services.automation_engine.get_supabase")
    async def test_already_enrolled_skips_dedup(self, mock_get_db):
        """DB insert raises (UNIQUE constraint) → logged as duplicate, enrolled stays 0."""
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
                    'duplicate key value violates unique constraint "automation_executions_sequence_id_lead_id_key"'
                )
            else:
                t.execute.return_value = MagicMock(data=[])
            return t

        db.table.side_effect = table_side_effect

        from backend.services.automation_engine import trigger_sequence

        # Should swallow the duplicate exception and return 0
        result = await trigger_sequence("tenant-001", "lead-dup", "new_lead")
        assert result == 0


# ---------------------------------------------------------------------------
# send_invoice_payment_reminders
# ---------------------------------------------------------------------------


class TestSendInvoicePaymentReminders:
    """Tests for send_invoice_payment_reminders()."""

    @patch("backend.services.automation_engine.send_sms", new_callable=AsyncMock)
    @patch("backend.services.automation_engine.send_email", new_callable=AsyncMock)
    @patch("backend.services.automation_engine.get_supabase")
    async def test_overdue_invoice_marked_overdue_and_email_sent(
        self, mock_get_db, mock_send_email, mock_send_sms
    ):
        """Invoice past due_date → status set to overdue + email reminder sent."""
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
                # No dedup hit
                t.execute.return_value = MagicMock(data=[], count=0)
            elif name == "leads":
                t.execute.return_value = MagicMock(data=[lead])
            elif name == "tenants":
                t.execute.return_value = MagicMock(data=[tenant_info])
            else:
                t.execute.return_value = MagicMock(data=[])
            return t

        db.table.side_effect = table_side_effect

        from backend.services.automation_engine import send_invoice_payment_reminders

        result = await send_invoice_payment_reminders()

        assert result >= 1
        mock_send_email.assert_awaited_once()
        # Confirm "overdue" language in subject
        call_kwargs = mock_send_email.call_args.kwargs
        assert "overdue" in call_kwargs.get("subject", "").lower()

    @patch("backend.services.automation_engine.send_sms", new_callable=AsyncMock)
    @patch("backend.services.automation_engine.send_email", new_callable=AsyncMock)
    @patch("backend.services.automation_engine.get_supabase")
    async def test_due_tomorrow_sends_reminder(
        self, mock_get_db, mock_send_email, mock_send_sms
    ):
        """Invoice due tomorrow → email reminder sent with 'due tomorrow' language."""
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

        from backend.services.automation_engine import send_invoice_payment_reminders

        result = await send_invoice_payment_reminders()

        assert result >= 1
        mock_send_email.assert_awaited_once()
        call_kwargs = mock_send_email.call_args.kwargs
        assert "tomorrow" in call_kwargs.get("subject", "").lower()

    @patch("backend.services.automation_engine.send_email", new_callable=AsyncMock)
    @patch("backend.services.automation_engine.get_supabase")
    async def test_already_reminded_today_skips(self, mock_get_db, mock_send_email):
        """activity_log dedup hit → email NOT sent → returns 0."""
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
    @patch("backend.services.automation_engine.get_supabase")
    async def test_invoice_with_no_lead_id_skips_gracefully(
        self, mock_get_db, mock_send_email
    ):
        """Invoice missing lead_id → gracefully skipped, no crash."""
        db = MagicMock()
        mock_get_db.return_value = db

        past_date = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()

        inv = {
            "id": "inv-004",
            "tenant_id": "tenant-001",
            "lead_id": None,          # No lead_id
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

        # Must not raise
        result = await send_invoice_payment_reminders()
        assert result == 0
        mock_send_email.assert_not_awaited()


# ---------------------------------------------------------------------------
# send_weekly_intelligence_briefs
# ---------------------------------------------------------------------------


class TestSendWeeklyIntelligenceBriefs:
    """Tests for send_weekly_intelligence_briefs()."""

    @patch("backend.services.automation_engine.send_email", new_callable=AsyncMock)
    @patch("backend.services.automation_engine.get_supabase")
    async def test_tuesday_returns_zero_immediately(self, mock_get_db, mock_send_email):
        """Non-Monday weekday → returns 0 without any DB queries."""
        tuesday = _tuesday_utc()

        from backend.services.automation_engine import send_weekly_intelligence_briefs

        with patch(
            "backend.services.automation_engine.datetime",
            wraps=datetime,
        ) as mock_dt:
            mock_dt.now.return_value = tuesday
            result = await send_weekly_intelligence_briefs()

        assert result == 0
        mock_get_db.assert_not_called()
        mock_send_email.assert_not_awaited()

    @patch("backend.services.automation_engine.send_email", new_callable=AsyncMock)
    @patch("backend.services.automation_engine.get_supabase")
    async def test_monday_paid_tenant_sends_brief(self, mock_get_db, mock_send_email):
        """Monday + paid tenant + no dedup hit → email sent → returns 1."""
        monday = _monday_utc()
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
                # No dedup hit
                t.execute.return_value = MagicMock(data=[], count=0)
            else:
                # All metric queries (leads, conversations, etc.) return empty
                t.execute.return_value = MagicMock(data=[], count=0)
            return t

        db.table.side_effect = table_side_effect

        from backend.services.automation_engine import send_weekly_intelligence_briefs

        with patch(
            "backend.services.automation_engine.datetime",
            wraps=datetime,
        ) as mock_dt:
            mock_dt.now.return_value = monday
            # Anthropic not needed — ANTHROPIC_API_KEY absent skips AI
            with patch(
                "backend.services.automation_engine.send_weekly_intelligence_briefs.__globals__",
                {},
                create=True,
            ):
                # Patch settings so anthropic_api_key is falsy → AI block skipped
                with patch("backend.config.settings") as mock_settings:
                    mock_settings.anthropic_api_key = ""
                    result = await send_weekly_intelligence_briefs()

        assert result == 1
        mock_send_email.assert_awaited_once()
        call_kwargs = mock_send_email.call_args.kwargs
        assert "My Biz" in call_kwargs.get("subject", "")

    @patch("backend.services.automation_engine.send_email", new_callable=AsyncMock)
    @patch("backend.services.automation_engine.get_supabase")
    async def test_already_sent_this_week_skips(self, mock_get_db, mock_send_email):
        """Monday but dedup hit in activity_log → returns 0, no email."""
        monday = _monday_utc()
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

        with patch("backend.services.automation_engine.datetime", wraps=datetime) as mock_dt:
            mock_dt.now.return_value = monday
            with patch("backend.config.settings") as mock_settings:
                mock_settings.anthropic_api_key = ""
                result = await send_weekly_intelligence_briefs()

        assert result == 0
        mock_send_email.assert_not_awaited()

    @patch("backend.services.automation_engine.send_email", new_callable=AsyncMock)
    @patch("backend.services.automation_engine.get_supabase")
    async def test_free_plan_tenant_skipped(self, mock_get_db, mock_send_email):
        """Free-plan tenants are excluded by the .neq('plan', 'free') query.

        We simulate this by having the tenants query return empty (as the DB
        would when filtering free tenants), confirming no email is sent.
        """
        monday = _monday_utc()
        db = MagicMock()
        mock_get_db.return_value = db

        def table_side_effect(name):
            t = MagicMock()
            for method in (
                "select", "insert", "update", "eq", "neq",
                "in_", "is_", "gte", "lte", "limit", "order",
            ):
                getattr(t, method).return_value = t

            # tenants query (with .neq("plan", "free")) returns empty list
            t.execute.return_value = MagicMock(data=[], count=0)
            return t

        db.table.side_effect = table_side_effect

        from backend.services.automation_engine import send_weekly_intelligence_briefs

        with patch("backend.services.automation_engine.datetime", wraps=datetime) as mock_dt:
            mock_dt.now.return_value = monday
            with patch("backend.config.settings") as mock_settings:
                mock_settings.anthropic_api_key = ""
                result = await send_weekly_intelligence_briefs()

        assert result == 0
        mock_send_email.assert_not_awaited()


# ---------------------------------------------------------------------------
# check_no_response_leads
# ---------------------------------------------------------------------------


class TestCheckNoResponseLeads:
    """Tests for check_no_response_leads()."""

    @patch("backend.services.automation_engine.trigger_sequence", new_callable=AsyncMock)
    @patch("backend.services.automation_engine.get_supabase")
    async def test_lead_with_no_response_triggers_sequence(
        self, mock_get_db, mock_trigger
    ):
        """Lead created 25h ago with no messages → trigger_sequence called."""
        db = MagicMock()
        mock_get_db.return_value = db
        mock_trigger.return_value = 1

        old_time = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()

        lead = {
            "id": "lead-stale-001",
            "client_id": "tenant-001",
            "conversation_id": None,
            "created_at": old_time,
        }

        call_count = [0]

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
                # Not enrolled in any sequence
                t.execute.return_value = MagicMock(data=[])
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
    @patch("backend.services.automation_engine.get_supabase")
    async def test_lead_with_recent_message_skips(self, mock_get_db, mock_trigger):
        """Lead has a chat message within last 24h → skip, trigger_sequence NOT called."""
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
    @patch("backend.services.automation_engine.get_supabase")
    async def test_already_enrolled_in_progress_execution_skips(
        self, mock_get_db, mock_trigger
    ):
        """Lead already has in_progress execution for a no_response_24h sequence → skip.

        This is the dedup fix from bug-patterns.md: the check must match
        status 'in_progress' (not just 'active') since trigger_sequence inserts
        with status='in_progress'.
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
                # Lead IS enrolled, with status='in_progress'
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
    @patch("backend.services.automation_engine.get_supabase")
    async def test_no_candidate_leads_returns_zero(self, mock_get_db, mock_trigger):
        """No 'new' leads older than 24h → returns 0 immediately."""
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

        from backend.services.automation_engine import check_no_response_leads

        result = await check_no_response_leads()

        assert result == 0
        mock_trigger.assert_not_awaited()
