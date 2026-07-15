"""Regression: appointment reminders fire for real ("confirmed") appointments.

Found 2026-07-15: send_appointment_reminders filtered `.eq("status", "booked")`,
but every creation path sets status "confirmed" (prod has only confirmed/
completed). Reminders therefore reached ZERO appointments — customers never got
a 24h/1h reminder, driving no-shows. This pins the status filter to the real
value so the bug can't silently return.
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
os.environ.setdefault("TESTING", "1")

from backend.services.automation.scheduled import appointment_jobs


def _confirmed_appt():
    return {
        "id": "appt-1",
        "tenant_id": "t-1",
        "customer_name": "Jane",
        "customer_email": "jane@example.com",
        "customer_phone": None,
        "start_time": "2026-08-01T15:00:00+00:00",
        "end_time": "2026-08-01T15:30:00+00:00",
        "notes": "",
        "status": "confirmed",
        "reminder_24h_sent_at": None,
        "reminder_1h_sent_at": None,
    }


def _mk_db(appt_rows):
    """Mock supporting the two query shapes the job uses:
    appointments: .select().gte().lte().in_().execute()
    tenants:      .select().eq().limit().execute()
    plus .update().eq().execute() for the sent-marker.
    Records the status filter passed to .in_() for assertion.
    """
    db = MagicMock()
    captured = {}

    appt_res = MagicMock()
    appt_res.data = appt_rows
    tenant_res = MagicMock()
    tenant_res.data = [{
        "business_name": "Acme", "owner_email": "o@acme.com", "plan": "chatbot",
        "business_type": "cleaning", "appointment_reminders_enabled": True,
    }]

    def table(name):
        chain = MagicMock()
        if name == "appointments":
            def _in(col, values):
                captured["status_col"] = col
                captured["status_values"] = values
                inner = MagicMock()
                inner.execute.return_value = appt_res
                return inner
            chain.select.return_value.gte.return_value.lte.return_value.in_ = _in
            chain.update.return_value.eq.return_value.execute.return_value = MagicMock()
        else:  # tenants
            chain.select.return_value.eq.return_value.limit.return_value.execute.return_value = tenant_res
        return chain

    db.table.side_effect = table
    return db, captured


class TestReminderStatusFilter:
    @pytest.mark.asyncio
    async def test_confirmed_appointment_gets_reminder(self):
        db, captured = _mk_db([_confirmed_appt()])
        with patch.object(appointment_jobs, "get_service_supabase", return_value=db), \
             patch.object(appointment_jobs, "send_email", new=AsyncMock()) as em, \
             patch.object(appointment_jobs, "_get_reminder_extras", return_value=[]):
            sent = await appointment_jobs.send_appointment_reminders()
        # Reminder actually sent (was 0 before the fix).
        assert em.await_count >= 1
        assert sent >= 1

    @pytest.mark.asyncio
    async def test_status_filter_includes_confirmed(self):
        db, captured = _mk_db([])
        with patch.object(appointment_jobs, "get_service_supabase", return_value=db), \
             patch.object(appointment_jobs, "send_email", new=AsyncMock()):
            await appointment_jobs.send_appointment_reminders()
        assert captured.get("status_col") == "status"
        assert "confirmed" in captured.get("status_values", [])


class TestAppointmentCreatedTrigger:
    @pytest.mark.asyncio
    async def test_confirmed_status_matches_appointment_created(self):
        from backend.services.automation import rule_engine

        res = MagicMock()
        res.data = [{"id": "a1", "status": "confirmed"}]
        tt = MagicMock()
        tt.select.return_value.eq.return_value.limit.return_value.execute.return_value = res

        with patch.object(rule_engine, "get_service_supabase", return_value=MagicMock()), \
             patch.object(rule_engine, "tenant_table", return_value=tt):
            ok, _ = await rule_engine.evaluate_trigger(
                "appointment_created", {}, "t-1", context={"appointment_id": "a1"}
            )
        assert ok is True

    @pytest.mark.asyncio
    async def test_booked_legacy_status_still_matches(self):
        from backend.services.automation import rule_engine

        res = MagicMock()
        res.data = [{"id": "a1", "status": "booked"}]
        tt = MagicMock()
        tt.select.return_value.eq.return_value.limit.return_value.execute.return_value = res

        with patch.object(rule_engine, "get_service_supabase", return_value=MagicMock()), \
             patch.object(rule_engine, "tenant_table", return_value=tt):
            ok, _ = await rule_engine.evaluate_trigger(
                "appointment_created", {}, "t-1", context={"appointment_id": "a1"}
            )
        assert ok is True

    @pytest.mark.asyncio
    async def test_completed_trigger_matches_completed_only(self):
        from backend.services.automation import rule_engine

        tt = MagicMock()

        def _result(status):
            res = MagicMock()
            res.data = [{"id": "a1", "status": status}]
            tt.select.return_value.eq.return_value.limit.return_value.execute.return_value = res

        with patch.object(rule_engine, "get_service_supabase", return_value=MagicMock()), \
             patch.object(rule_engine, "tenant_table", return_value=tt):
            _result("completed")
            ok_completed, _ = await rule_engine.evaluate_trigger(
                "appointment_completed", {}, "t-1", context={"appointment_id": "a1"}
            )
            _result("confirmed")
            ok_confirmed, _ = await rule_engine.evaluate_trigger(
                "appointment_completed", {}, "t-1", context={"appointment_id": "a1"}
            )
        assert ok_completed is True
        assert ok_confirmed is False  # a confirmed (not-yet-completed) appt must NOT fire completion
