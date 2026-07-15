"""Staff reschedule/cancel from the dashboard must notify the CUSTOMER.

Found 2026-07-15: booking.update_appointment / cancel_appointment (the
PATCH/DELETE dashboard endpoints) changed the appointment but sent the customer
nothing — no "your time moved" or "your appointment was cancelled" notice — and
a staff reschedule left stale appointment_reminders rows so the new slot got no
reminder. This is the higher-traffic mirror of the customer-initiated cancel
alert already shipped.
"""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
os.environ.setdefault("TESTING", "1")

from backend.services import appointment_customer_notify as notify
from backend.services import appointment_reminders
from backend.services import booking


def _tenant_chain(business_name="Keys Koffee", business_phone="+15550001111"):
    chain = MagicMock()
    res = MagicMock()
    res.data = [{"business_name": business_name, "business_phone": business_phone}]
    chain.select.return_value.limit.return_value.execute.return_value = res
    return chain


APPT = {
    "id": "appt-1",
    "tenant_id": "t-1",
    "customer_name": "Jane",
    "customer_email": "jane@example.com",
    "customer_phone": "+15559998888",
    "start_time": "2026-08-01T15:00:00+00:00",
    "end_time": "2026-08-01T15:30:00+00:00",
}


class TestCustomerNotices:
    @pytest.mark.asyncio
    async def test_reschedule_notice_emails_and_texts_customer(self):
        email, sms = AsyncMock(), AsyncMock()
        with patch.object(notify, "tenant_table", return_value=_tenant_chain()), \
             patch.object(notify, "get_service_supabase", return_value=MagicMock()), \
             patch("backend.services.email_sender.send_email", email), \
             patch("backend.services.twilio_service.send_sms", sms):
            await notify.send_reschedule_notice("t-1", APPT)

        email.assert_awaited_once()
        assert email.await_args.kwargs["to"] == "jane@example.com"
        assert "rescheduled" in email.await_args.kwargs["subject"].lower()
        sms.assert_awaited_once()
        assert sms.await_args.kwargs["to"] == "+15559998888"
        assert sms.await_args.kwargs["tenant_id"] == "t-1"
        assert "rescheduled" in sms.await_args.kwargs["body"].lower()

    @pytest.mark.asyncio
    async def test_cancellation_notice_emails_and_texts_customer(self):
        email, sms = AsyncMock(), AsyncMock()
        with patch.object(notify, "tenant_table", return_value=_tenant_chain()), \
             patch.object(notify, "get_service_supabase", return_value=MagicMock()), \
             patch("backend.services.email_sender.send_email", email), \
             patch("backend.services.twilio_service.send_sms", sms):
            await notify.send_cancellation_notice("t-1", APPT)

        email.assert_awaited_once()
        assert "cancelled" in email.await_args.kwargs["subject"].lower()
        sms.assert_awaited_once()
        assert "cancelled" in sms.await_args.kwargs["body"].lower()

    @pytest.mark.asyncio
    async def test_no_contact_is_a_noop(self):
        email, sms = AsyncMock(), AsyncMock()
        appt = {**APPT, "customer_email": None, "customer_phone": None}
        with patch("backend.services.email_sender.send_email", email), \
             patch("backend.services.twilio_service.send_sms", sms):
            await notify.send_reschedule_notice("t-1", appt)
            await notify.send_cancellation_notice("t-1", appt)
        email.assert_not_awaited()
        sms.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_send_failure_never_raises(self):
        boom = AsyncMock(side_effect=RuntimeError("smtp down"))
        with patch.object(notify, "tenant_table", return_value=_tenant_chain()), \
             patch.object(notify, "get_service_supabase", return_value=MagicMock()), \
             patch("backend.services.email_sender.send_email", boom), \
             patch("backend.services.twilio_service.send_sms", boom):
            # Must not raise even though both channels blow up.
            await notify.send_reschedule_notice("t-1", APPT)
            await notify.send_cancellation_notice("t-1", APPT)

    @pytest.mark.asyncio
    async def test_tenant_lookup_failure_degrades_to_defaults(self):
        email = AsyncMock()
        with patch.object(notify, "tenant_table", side_effect=RuntimeError("db down")), \
             patch.object(notify, "get_service_supabase", return_value=MagicMock()), \
             patch("backend.services.email_sender.send_email", email), \
             patch("backend.services.twilio_service.send_sms", AsyncMock()):
            await notify.send_reschedule_notice("t-1", {**APPT, "customer_phone": None})
        # Still emails, using the "Our business" default identity.
        email.assert_awaited_once()
        assert "Our business" in email.await_args.kwargs["subject"]


class TestRescheduleReminders:
    def test_clears_then_reschedules(self):
        db = MagicMock()
        chain = MagicMock()
        chain.delete.return_value.eq.return_value.execute.return_value = MagicMock()
        with patch.object(appointment_reminders, "get_service_supabase", return_value=db), \
             patch.object(appointment_reminders, "tenant_table", return_value=chain), \
             patch.object(
                 appointment_reminders, "schedule_reminders_for_appointment",
                 return_value=[{"reminder_type": "24h"}],
             ) as sched:
            out = appointment_reminders.reschedule_reminders_for_appointment(APPT)
        chain.delete.return_value.eq.assert_called_once_with("appointment_id", "appt-1")
        sched.assert_called_once_with(APPT)
        assert out == [{"reminder_type": "24h"}]

    def test_missing_id_skips(self):
        with patch.object(
            appointment_reminders, "schedule_reminders_for_appointment"
        ) as sched:
            assert appointment_reminders.reschedule_reminders_for_appointment({}) == []
            sched.assert_not_called()

    def test_delete_failure_does_not_reschedule(self):
        chain = MagicMock()
        chain.delete.return_value.eq.return_value.execute.side_effect = RuntimeError("boom")
        with patch.object(appointment_reminders, "get_service_supabase", return_value=MagicMock()), \
             patch.object(appointment_reminders, "tenant_table", return_value=chain), \
             patch.object(appointment_reminders, "schedule_reminders_for_appointment") as sched:
            assert appointment_reminders.reschedule_reminders_for_appointment(APPT) == []
            sched.assert_not_called()


def _update_chain(returned):
    chain = MagicMock()
    res = MagicMock()
    res.data = [returned]
    chain.update.return_value.eq.return_value.execute.return_value = res
    return chain


class TestUpdateAppointmentNotifies:
    @pytest.mark.asyncio
    async def test_time_change_rearms_reminders_and_notifies(self):
        moved = {**APPT, "google_event_id": None, "start_time": "2026-08-02T10:00:00+00:00"}
        chain = _update_chain(moved)
        resched = AsyncMock()
        with patch.object(booking, "get_service_supabase", return_value=MagicMock()), \
             patch.object(booking, "tenant_table", return_value=chain), \
             patch("backend.services.appointment_reminders.reschedule_reminders_for_appointment") as rearm, \
             patch("backend.services.appointment_customer_notify.send_reschedule_notice", resched), \
             patch("backend.services.appointment_customer_notify.send_cancellation_notice", AsyncMock()) as cancel:
            booking.update_appointment("t-1", "appt-1", {"start_time": "2026-08-02T10:00:00+00:00"})
            await asyncio.sleep(0)
        rearm.assert_called_once()
        resched.assert_awaited_once()
        cancel.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_cancel_status_notifies_customer(self):
        cancelled = {**APPT, "google_event_id": None, "status": "cancelled"}
        chain = _update_chain(cancelled)
        cancel = AsyncMock()
        with patch.object(booking, "get_service_supabase", return_value=MagicMock()), \
             patch.object(booking, "tenant_table", return_value=chain), \
             patch("backend.services.appointment_customer_notify.send_cancellation_notice", cancel), \
             patch("backend.services.appointment_customer_notify.send_reschedule_notice", AsyncMock()) as resched:
            booking.update_appointment("t-1", "appt-1", {"status": "cancelled"})
            await asyncio.sleep(0)
        cancel.assert_awaited_once()
        resched.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_notes_only_change_does_not_notify(self):
        chain = _update_chain({**APPT, "google_event_id": None, "notes": "VIP"})
        with patch.object(booking, "get_service_supabase", return_value=MagicMock()), \
             patch.object(booking, "tenant_table", return_value=chain), \
             patch("backend.services.appointment_customer_notify.send_reschedule_notice", AsyncMock()) as resched, \
             patch("backend.services.appointment_customer_notify.send_cancellation_notice", AsyncMock()) as cancel:
            booking.update_appointment("t-1", "appt-1", {"notes": "VIP"})
            await asyncio.sleep(0)
        resched.assert_not_awaited()
        cancel.assert_not_awaited()

    def test_no_running_loop_closes_coroutine(self):
        """Sync context: notice coroutine is closed, no leak, update still returns."""
        chain = _update_chain({**APPT, "google_event_id": None, "status": "cancelled"})
        cancel = AsyncMock()
        with patch.object(booking, "get_service_supabase", return_value=MagicMock()), \
             patch.object(booking, "tenant_table", return_value=chain), \
             patch("backend.services.appointment_customer_notify.send_cancellation_notice", cancel):
            result = booking.update_appointment("t-1", "appt-1", {"status": "cancelled"})
        assert result["status"] == "cancelled"
        cancel.assert_called_once()

    @pytest.mark.asyncio
    async def test_cancel_appointment_routes_through_and_notifies(self):
        existing = MagicMock()
        existing.data = [{"google_event_id": None}]
        cancelled = {**APPT, "google_event_id": None, "status": "cancelled"}
        upd = _update_chain(cancelled)

        def _tt(_db, name, _tid):
            if name == "appointments":
                # first call: select google_event_id; later: the update
                m = MagicMock()
                m.select.return_value.eq.return_value.limit.return_value.execute.return_value = existing
                m.update.return_value.eq.return_value.execute.return_value = upd.update.return_value.eq.return_value.execute.return_value
                return m
            return MagicMock()

        cancel = AsyncMock()
        with patch.object(booking, "get_service_supabase", return_value=MagicMock()), \
             patch.object(booking, "tenant_table", side_effect=_tt), \
             patch("backend.services.appointment_customer_notify.send_cancellation_notice", cancel):
            result = booking.cancel_appointment("t-1", "appt-1")
            await asyncio.sleep(0)
        assert result["status"] == "cancelled"
        cancel.assert_awaited_once()
