"""Tests for appointment reminders — scheduling + sending. Offline, mocked Supabase + Twilio."""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("TESTING", "1")

from backend.services import appointment_reminders as ar


def _chainable(mock_table):
    """Make every chain method on a MagicMock table return itself."""
    for method in [
        "select", "eq", "lte", "gte", "limit", "insert", "update", "upsert", "order",
    ]:
        getattr(mock_table, method).return_value = mock_table
    return mock_table


def _future_iso(hours: float) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


# ── schedule_reminders_for_appointment ───────────────────────────────────


class TestScheduleReminders:
    @patch("backend.services.appointment_reminders.get_service_supabase")
    def test_creates_24h_and_2h_rows(self, mock_get_db):
        tenants_table = _chainable(MagicMock())
        tenants_table.execute.return_value = MagicMock(
            data=[{"appointment_reminders_enabled": True}]
        )

        reminders_table = _chainable(MagicMock())
        reminders_table.execute.side_effect = [
            MagicMock(data=[{"id": "r-24h", "reminder_type": "24h"}]),
            MagicMock(data=[{"id": "r-2h", "reminder_type": "2h"}]),
        ]

        db = MagicMock()
        db.table.side_effect = lambda name: {
            "tenants": tenants_table,
            "appointment_reminders": reminders_table,
        }[name]
        mock_get_db.return_value = db

        appointment = {
            "id": "appt-1",
            "tenant_id": "tenant-1",
            "start_time": _future_iso(48),
        }

        created = ar.schedule_reminders_for_appointment(appointment)

        assert len(created) == 2
        assert reminders_table.upsert.call_count == 2

        payloads = [call.args[0] for call in reminders_table.upsert.call_args_list]
        types = [p["reminder_type"] for p in payloads]
        assert types == ["24h", "2h"]
        for p in payloads:
            assert p["tenant_id"] == "tenant-1"
            assert p["appointment_id"] == "appt-1"
            assert p["status"] == "pending"

    @patch("backend.services.appointment_reminders.get_service_supabase")
    def test_disabled_tenant_schedules_nothing(self, mock_get_db):
        tenants_table = _chainable(MagicMock())
        tenants_table.execute.return_value = MagicMock(
            data=[{"appointment_reminders_enabled": False}]
        )
        reminders_table = _chainable(MagicMock())

        db = MagicMock()
        db.table.side_effect = lambda name: {
            "tenants": tenants_table,
            "appointment_reminders": reminders_table,
        }[name]
        mock_get_db.return_value = db

        created = ar.schedule_reminders_for_appointment(
            {"id": "appt-1", "tenant_id": "tenant-1", "start_time": _future_iso(48)}
        )

        assert created == []
        reminders_table.upsert.assert_not_called()

    @patch("backend.services.appointment_reminders.get_service_supabase")
    def test_skips_window_already_in_the_past(self, mock_get_db):
        """Booked 1 hour out — the 24h and 2h windows are both already past."""
        tenants_table = _chainable(MagicMock())
        tenants_table.execute.return_value = MagicMock(
            data=[{"appointment_reminders_enabled": True}]
        )
        reminders_table = _chainable(MagicMock())

        db = MagicMock()
        db.table.side_effect = lambda name: {
            "tenants": tenants_table,
            "appointment_reminders": reminders_table,
        }[name]
        mock_get_db.return_value = db

        created = ar.schedule_reminders_for_appointment(
            {"id": "appt-1", "tenant_id": "tenant-1", "start_time": _future_iso(1)}
        )

        assert created == []
        reminders_table.upsert.assert_not_called()

    def test_missing_fields_returns_empty(self):
        assert ar.schedule_reminders_for_appointment({}) == []
        assert ar.schedule_reminders_for_appointment({"id": "x"}) == []


# ── send_due_reminders ────────────────────────────────────────────────────


def _due_row(reminder_id="r-1", reminder_type="24h", tenant_id="tenant-1", appointment_id="appt-1"):
    return {
        "id": reminder_id,
        "tenant_id": tenant_id,
        "appointment_id": appointment_id,
        "reminder_type": reminder_type,
        "status": "pending",
    }


def _appointment_row(appointment_id="appt-1", tenant_id="tenant-1", phone="+15551234567", status="confirmed"):
    return {
        "id": appointment_id,
        "tenant_id": tenant_id,
        "status": status,
        "customer_name": "Jane",
        "customer_phone": phone,
        "start_time": _future_iso(2),
    }


def _tenant_row(business_name="Test Biz", enabled=True):
    return {"business_name": business_name, "appointment_reminders_enabled": enabled}


class TestSendDueReminders:
    @patch("backend.services.appointment_reminders.send_sms", new_callable=AsyncMock)
    @patch("backend.services.appointment_reminders.sms_compliance.is_suppressed")
    @patch("backend.services.appointment_reminders.get_service_supabase")
    @pytest.mark.asyncio
    async def test_sends_only_due_pending_and_marks_sent(
        self, mock_get_db, mock_suppressed, mock_send_sms
    ):
        mock_suppressed.return_value = False
        mock_send_sms.return_value = True

        reminders_table = _chainable(MagicMock())
        reminders_table.execute.side_effect = [
            MagicMock(data=[_due_row()]),  # query due
            MagicMock(data=[{"id": "r-1", "status": "sending"}]),  # claim
            MagicMock(data=[{"id": "r-1", "status": "sent"}]),  # finalize
        ]

        appointments_table = _chainable(MagicMock())
        appointments_table.execute.return_value = MagicMock(data=[_appointment_row()])

        tenants_table = _chainable(MagicMock())
        tenants_table.execute.return_value = MagicMock(data=[_tenant_row()])

        db = MagicMock()
        db.table.side_effect = lambda name: {
            "appointment_reminders": reminders_table,
            "appointments": appointments_table,
            "tenants": tenants_table,
        }[name]
        mock_get_db.return_value = db

        counts = await ar.send_due_reminders()

        assert counts == {"checked": 1, "sent": 1, "skipped": 0, "failed": 0}
        mock_send_sms.assert_awaited_once()
        # Query filtered on status=pending and scheduled_for<=now.
        reminders_table.eq.assert_any_call("status", "pending")
        assert any(c.args[0] == "scheduled_for" for c in reminders_table.lte.call_args_list)
        # Finalize wrote status=sent + sent_at.
        finalize_call = reminders_table.update.call_args_list[-1]
        assert finalize_call.args[0]["status"] == "sent"
        assert "sent_at" in finalize_call.args[0]

    @patch("backend.services.appointment_reminders.send_sms", new_callable=AsyncMock)
    @patch("backend.services.appointment_reminders.sms_compliance.is_suppressed")
    @patch("backend.services.appointment_reminders.get_service_supabase")
    @pytest.mark.asyncio
    async def test_twilio_failure_on_one_does_not_break_batch(
        self, mock_get_db, mock_suppressed, mock_send_sms
    ):
        mock_suppressed.return_value = False
        # First reminder's send raises, second succeeds.
        mock_send_sms.side_effect = [RuntimeError("twilio down"), True]

        row1 = _due_row(reminder_id="r-1", appointment_id="appt-1")
        row2 = _due_row(reminder_id="r-2", appointment_id="appt-2")

        reminders_table = _chainable(MagicMock())
        reminders_table.execute.side_effect = [
            MagicMock(data=[row1, row2]),  # query due
            MagicMock(data=[{"id": "r-1", "status": "sending"}]),  # claim r-1
            MagicMock(data=[{"id": "r-1", "status": "failed"}]),  # finalize r-1 failed
            MagicMock(data=[{"id": "r-2", "status": "sending"}]),  # claim r-2
            MagicMock(data=[{"id": "r-2", "status": "sent"}]),  # finalize r-2 sent
        ]

        appointments_table = _chainable(MagicMock())
        appointments_table.execute.side_effect = [
            MagicMock(data=[_appointment_row(appointment_id="appt-1")]),
            MagicMock(data=[_appointment_row(appointment_id="appt-2")]),
        ]

        tenants_table = _chainable(MagicMock())
        tenants_table.execute.side_effect = [
            MagicMock(data=[_tenant_row()]),
            MagicMock(data=[_tenant_row()]),
        ]

        db = MagicMock()
        db.table.side_effect = lambda name: {
            "appointment_reminders": reminders_table,
            "appointments": appointments_table,
            "tenants": tenants_table,
        }[name]
        mock_get_db.return_value = db

        counts = await ar.send_due_reminders()

        assert counts["checked"] == 2
        assert counts["sent"] == 1
        assert counts["failed"] == 1
        assert mock_send_sms.await_count == 2

    @patch("backend.services.appointment_reminders.send_sms", new_callable=AsyncMock)
    @patch("backend.services.appointment_reminders.sms_compliance.is_suppressed")
    @patch("backend.services.appointment_reminders.get_service_supabase")
    @pytest.mark.asyncio
    async def test_opt_out_suppresses_send(self, mock_get_db, mock_suppressed, mock_send_sms):
        mock_suppressed.return_value = True

        reminders_table = _chainable(MagicMock())
        reminders_table.execute.side_effect = [
            MagicMock(data=[_due_row()]),  # query due
            MagicMock(data=[{"id": "r-1", "status": "skipped"}]),  # finalize skipped
        ]

        appointments_table = _chainable(MagicMock())
        appointments_table.execute.return_value = MagicMock(data=[_appointment_row()])

        tenants_table = _chainable(MagicMock())
        tenants_table.execute.return_value = MagicMock(data=[_tenant_row()])

        db = MagicMock()
        db.table.side_effect = lambda name: {
            "appointment_reminders": reminders_table,
            "appointments": appointments_table,
            "tenants": tenants_table,
        }[name]
        mock_get_db.return_value = db

        counts = await ar.send_due_reminders()

        assert counts == {"checked": 1, "sent": 0, "skipped": 1, "failed": 0}
        mock_send_sms.assert_not_awaited()

    @patch("backend.services.appointment_reminders.send_sms", new_callable=AsyncMock)
    @patch("backend.services.appointment_reminders.get_service_supabase")
    @pytest.mark.asyncio
    async def test_cancelled_appointment_skips_without_sending(self, mock_get_db, mock_send_sms):
        reminders_table = _chainable(MagicMock())
        reminders_table.execute.side_effect = [
            MagicMock(data=[_due_row()]),
            MagicMock(data=[{"id": "r-1", "status": "skipped"}]),
        ]

        appointments_table = _chainable(MagicMock())
        appointments_table.execute.return_value = MagicMock(
            data=[_appointment_row(status="cancelled")]
        )

        db = MagicMock()
        db.table.side_effect = lambda name: {
            "appointment_reminders": reminders_table,
            "appointments": appointments_table,
        }[name]
        mock_get_db.return_value = db

        counts = await ar.send_due_reminders()

        assert counts == {"checked": 1, "sent": 0, "skipped": 1, "failed": 0}
        mock_send_sms.assert_not_awaited()

    @patch("backend.services.appointment_reminders.get_service_supabase")
    @pytest.mark.asyncio
    async def test_no_due_reminders_is_a_noop(self, mock_get_db):
        reminders_table = _chainable(MagicMock())
        reminders_table.execute.return_value = MagicMock(data=[])

        db = MagicMock()
        db.table.return_value = reminders_table
        mock_get_db.return_value = db

        counts = await ar.send_due_reminders()

        assert counts == {"checked": 0, "sent": 0, "skipped": 0, "failed": 0}

    @patch("backend.services.appointment_reminders.get_service_supabase")
    @pytest.mark.asyncio
    async def test_lost_claim_race_is_skipped_not_double_sent(self, mock_get_db):
        """Another worker already claimed the row — _claim_pending returns no rows."""
        reminders_table = _chainable(MagicMock())
        reminders_table.execute.side_effect = [
            MagicMock(data=[_due_row()]),  # query due
            MagicMock(data=[]),  # claim: lost the race, no rows updated
        ]

        appointments_table = _chainable(MagicMock())
        appointments_table.execute.return_value = MagicMock(data=[_appointment_row()])

        tenants_table = _chainable(MagicMock())
        tenants_table.execute.return_value = MagicMock(data=[_tenant_row()])

        db = MagicMock()
        db.table.side_effect = lambda name: {
            "appointment_reminders": reminders_table,
            "appointments": appointments_table,
            "tenants": tenants_table,
        }[name]
        mock_get_db.return_value = db

        with patch(
            "backend.services.appointment_reminders.sms_compliance.is_suppressed",
            return_value=False,
        ), patch(
            "backend.services.appointment_reminders.send_sms", new_callable=AsyncMock
        ) as mock_send_sms:
            counts = await ar.send_due_reminders()
            mock_send_sms.assert_not_awaited()

        assert counts == {"checked": 1, "sent": 0, "skipped": 1, "failed": 0}
