"""Reschedule must reset reminder markers so the new slot gets a reminder.

Found 2026-07-15: reschedule_submit updated start_time/end_time but left
reminder_24h_sent_at / reminder_1h_sent_at (and the reminder_*_sent note tags)
set from the ORIGINAL time. The reminder job dedups on those, so a reschedule
after the first reminder fired left the new slot with NO reminder → no-show.
Compounds the reminder-status fix (reminders only started working recently).
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
os.environ.setdefault("TESTING", "1")

from backend.routers import booking_page
from backend.services.booking import _generate_reschedule_token


class TestStripReminderTags:
    def test_removes_tag_lines_only(self):
        notes = "Service: haircut\nreminder_24h_sent\nreminder_1h_sent\nVIP customer"
        out = booking_page._strip_reminder_tags(notes)
        assert "reminder_24h_sent" not in out
        assert "reminder_1h_sent" not in out
        assert "Service: haircut" in out
        assert "VIP customer" in out

    def test_empty_and_none(self):
        assert booking_page._strip_reminder_tags("") == ""
        assert booking_page._strip_reminder_tags(None) == ""

    def test_keeps_notes_without_tags(self):
        assert booking_page._strip_reminder_tags("just notes") == "just notes"


class TestRescheduleResetsReminders:
    @pytest.mark.asyncio
    async def test_reschedule_nulls_reminder_columns_and_strips_tags(self):
        appt_id = "appt-1"
        token = _generate_reschedule_token(appt_id)

        appointment = {
            "id": appt_id,
            "tenant_id": "t-1",
            "status": "confirmed",
            "notes": "Service: cut\nreminder_24h_sent",
            "reminder_24h_sent_at": "2026-07-14T10:00:00+00:00",
            "start_time": "2026-07-15T10:00:00",
            "end_time": "2026-07-15T10:30:00",
            "lead_id": None,
        }

        captured = {}

        # db.table("appointments").select().eq().limit().execute() -> the appt
        db = MagicMock()
        appt_res = MagicMock()
        appt_res.data = [appointment]
        db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = appt_res

        # tenant_table(...) is used for the slot-conflict check AND the update.
        def _tenant_table(_db, _name, _tid):
            chain = MagicMock()
            # slot-conflict check: .select().neq().neq().lt().gt().limit().execute() -> empty
            empty = MagicMock()
            empty.data = []
            chain.select.return_value.neq.return_value.neq.return_value.lt.return_value.gt.return_value.limit.return_value.execute.return_value = empty

            # update payload capture
            def _update(payload):
                captured["payload"] = payload
                upd = MagicMock()
                res = MagicMock()
                res.data = [{**appointment, **payload}]
                upd.eq.return_value.execute.return_value = res
                return upd
            chain.update = _update
            return chain

        body = booking_page._RescheduleBody(
            token=token, new_start="2026-07-22T14:00:00", new_end="2026-07-22T14:30:00"
        )

        with patch.object(booking_page, "get_service_supabase", return_value=db), \
             patch.object(booking_page, "tenant_table", _tenant_table), \
             patch("backend.services.booking._send_appointment_confirmation", new=MagicMock(return_value=None)), \
             patch("backend.services.task_utils.safe_create_task"), \
             patch("backend.services.activity.log_activity"):
            result = await booking_page.reschedule_submit.__wrapped__(  # bypass slowapi decorator
                MagicMock(), appt_id, body
            )

        assert result["success"] is True
        # The core fix: reminder columns nulled so the new slot re-reminds.
        assert captured["payload"]["reminder_24h_sent_at"] is None
        assert captured["payload"]["reminder_1h_sent_at"] is None
        # And the stale reminder note-tag was stripped.
        assert "reminder_24h_sent" not in captured["payload"]["notes"]
        assert captured["payload"]["start_time"] == "2026-07-22T14:00:00"


class TestCancelNotifiesOwner:
    @pytest.mark.asyncio
    async def test_cancel_marks_cancelled_and_alerts_owner(self):
        appt_id = "appt-9"
        token = _generate_reschedule_token(appt_id)

        appointment = {
            "id": appt_id,
            "tenant_id": "t-1",
            "lead_id": None,
            "status": "confirmed",
            "customer_name": "Jane",
            "start_time": "2026-07-22T14:00:00",
            "end_time": "2026-07-22T14:30:00",
        }

        db = MagicMock()
        appt_res = MagicMock()
        appt_res.data = [appointment]
        db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = appt_res

        update_chain = MagicMock()
        def _tenant_table(_db, _name, _tid):
            return update_chain

        alert = AsyncMock()
        with patch.object(booking_page, "get_service_supabase", return_value=db), \
             patch.object(booking_page, "tenant_table", _tenant_table), \
             patch.object(booking_page, "fire_event_background"), \
             patch("backend.services.booking_alerts.send_cancellation_alert", alert), \
             patch("backend.services.activity.log_activity"):
            result = await booking_page.reschedule_cancel.__wrapped__(
                MagicMock(), appt_id, booking_page._CancelBody(token=token)
            )

        assert result["success"] is True
        # status set to cancelled
        update_chain.update.assert_called_once()
        assert update_chain.update.call_args[0][0] == {"status": "cancelled"}
        # owner alerted with the customer + slot info
        alert.assert_awaited_once()
        kwargs = alert.await_args.kwargs
        assert kwargs["customer_name"] == "Jane"
        assert kwargs["appointment_id"] == appt_id

    @pytest.mark.asyncio
    async def test_cancel_of_already_cancelled_is_noop(self):
        appt_id = "appt-10"
        token = _generate_reschedule_token(appt_id)
        db = MagicMock()
        res = MagicMock()
        res.data = [{"id": appt_id, "tenant_id": "t-1", "lead_id": None, "status": "cancelled"}]
        db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = res

        alert = AsyncMock()
        with patch.object(booking_page, "get_service_supabase", return_value=db), \
             patch("backend.services.booking_alerts.send_cancellation_alert", alert):
            result = await booking_page.reschedule_cancel.__wrapped__(
                MagicMock(), appt_id, booking_page._CancelBody(token=token)
            )
        assert "Already cancelled" in result["message"]
        alert.assert_not_awaited()
