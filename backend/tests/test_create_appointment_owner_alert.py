"""create_appointment fires the owner booking alert on EVERY path.

Found 2026-07-15: the owner alert (send_new_booking_alert) was wired only into
the public booking page, so voice/phone bookings — which go through
booking.create_appointment — created an appointment the owner never heard about.
Firing it inside create_appointment covers voice + any future caller.
"""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
os.environ.setdefault("TESTING", "1")

from backend.services import booking


def _mk_db(appointment):
    """tenant_table chain: overlap-check select (empty), insert (appointment),
    update (lead_id/google). All via one MagicMock."""
    chain = MagicMock()
    empty = MagicMock(); empty.data = []
    chain.select.return_value.neq.return_value.lt.return_value.gt.return_value.limit.return_value.execute.return_value = empty
    ins = MagicMock(); ins.data = [appointment]
    chain.insert.return_value.execute.return_value = ins
    chain.update.return_value.eq.return_value.execute.return_value = MagicMock()
    return chain


class TestOwnerAlertScheduled:
    @pytest.mark.asyncio
    async def test_create_appointment_schedules_owner_alert(self):
        appointment = {
            "id": "appt-1",
            "tenant_id": "t-1",
            "customer_name": "Jane",
            "customer_email": "",           # phone booking → no email
            "customer_phone": "+15551234567",
            "start_time": "2026-08-01T15:00:00+00:00",
            "end_time": "2026-08-01T15:30:00+00:00",
            "status": "confirmed",
        }
        chain = _mk_db(appointment)
        alert = AsyncMock()

        with patch.object(booking, "get_service_supabase", return_value=MagicMock()), \
             patch.object(booking, "tenant_table", return_value=chain), \
             patch.object(booking, "link_appointment_to_lead", return_value=None), \
             patch.object(booking, "_send_appointment_confirmation", new=MagicMock(return_value=None)), \
             patch("backend.services.appointment_reminders.schedule_reminders_for_appointment"), \
             patch("backend.services.google_calendar.get_integration", return_value=None), \
             patch("backend.services.booking_alerts.send_new_booking_alert", alert):
            result = booking.create_appointment(
                tenant_id="t-1",
                customer_name="Jane",
                customer_email="",
                customer_phone="+15551234567",
                start_time="2026-08-01T15:00:00+00:00",
                end_time="2026-08-01T15:30:00+00:00",
                notes="Booked by AI phone assistant",
            )
            # let the scheduled task run
            await asyncio.sleep(0)

        assert result["id"] == "appt-1"
        alert.assert_awaited_once()
        kwargs = alert.await_args.kwargs
        assert kwargs["tenant_id"] == "t-1"
        assert kwargs["customer_name"] == "Jane"
        assert kwargs["appointment_id"] == "appt-1"
        assert kwargs["booking_info"]["date"] == "2026-08-01"
        assert kwargs["booking_info"]["start_time"] == "15:00"

    @pytest.mark.asyncio
    async def test_owner_alert_failure_never_breaks_booking(self):
        appointment = {
            "id": "appt-2", "tenant_id": "t-1", "customer_name": "Bob",
            "customer_email": "b@x.com", "customer_phone": None,
            "start_time": "2026-08-01T15:00:00+00:00",
            "end_time": "2026-08-01T15:30:00+00:00", "status": "confirmed",
        }
        chain = _mk_db(appointment)

        # A non-RuntimeError raised while scheduling the alert must be swallowed
        # by the generic handler — the booking still returns.
        with patch.object(booking, "get_service_supabase", return_value=MagicMock()), \
             patch.object(booking, "tenant_table", return_value=chain), \
             patch.object(booking, "link_appointment_to_lead", return_value=None), \
             patch.object(booking, "_send_appointment_confirmation", new=MagicMock(return_value=None)), \
             patch("backend.services.appointment_reminders.schedule_reminders_for_appointment"), \
             patch("backend.services.google_calendar.get_integration", return_value=None), \
             patch("backend.services.booking_alerts.send_new_booking_alert",
                   new=MagicMock(side_effect=ValueError("boom"))):
            # MagicMock (not AsyncMock) so the error raises at call time, hitting
            # the generic except in the scheduling block, not on a deferred await.
            result = booking.create_appointment(
                tenant_id="t-1", customer_name="Bob", customer_email="b@x.com",
                start_time="2026-08-01T15:00:00+00:00", end_time="2026-08-01T15:30:00+00:00",
            )
        assert result["id"] == "appt-2"

    def test_no_running_loop_closes_coroutine_and_still_books(self):
        """Called from a SYNC context (no running event loop) — the alert
        coroutine must be closed (no 'never awaited' leak) and the booking must
        still return. Covers the RuntimeError fallback branch."""
        appointment = {
            "id": "appt-3", "tenant_id": "t-1", "customer_name": "Sync",
            "customer_email": "s@x.com", "customer_phone": None,
            "start_time": "2026-08-01T15:00:00+00:00",
            "end_time": "2026-08-01T15:30:00+00:00", "status": "confirmed",
        }
        chain = _mk_db(appointment)
        alert = AsyncMock()

        with patch.object(booking, "get_service_supabase", return_value=MagicMock()), \
             patch.object(booking, "tenant_table", return_value=chain), \
             patch.object(booking, "link_appointment_to_lead", return_value=None), \
             patch.object(booking, "_send_appointment_confirmation", new=MagicMock(return_value=None)), \
             patch("backend.services.appointment_reminders.schedule_reminders_for_appointment"), \
             patch("backend.services.google_calendar.get_integration", return_value=None), \
             patch("backend.services.booking_alerts.send_new_booking_alert", alert):
            # No @pytest.mark.asyncio → no running loop → get_running_loop raises.
            result = booking.create_appointment(
                tenant_id="t-1", customer_name="Sync", customer_email="s@x.com",
                start_time="2026-08-01T15:00:00+00:00", end_time="2026-08-01T15:30:00+00:00",
            )
        assert result["id"] == "appt-3"
        # The coroutine was created but never awaited; it must have been closed.
        alert.assert_called_once()
