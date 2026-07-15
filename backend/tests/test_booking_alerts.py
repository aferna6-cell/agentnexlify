"""Tests for owner booking alerts (backend/services/booking_alerts.py).

Regression for the 2026-07-15 gap: a public-page booking notified the customer
+ a webhook but NEVER the business owner — a booking was less-notified than a
mere lead capture.
"""

from unittest.mock import AsyncMock, patch

import pytest

from backend.services import booking_alerts
from backend.services.booking_alerts import (
    send_cancellation_alert,
    send_new_booking_alert,
)


@pytest.fixture(autouse=True)
def _clear_cache():
    booking_alerts.reset_idempotency_cache()
    yield
    booking_alerts.reset_idempotency_cache()


BOOKING = {"email": "c@x.com", "phone": "+15551234567", "date": "2026-07-20", "start_time": "10:00", "end_time": "10:30"}


def _mk_db(rows):
    """Minimal Supabase stub: table().select().eq().limit().execute().data."""
    from unittest.mock import MagicMock

    db = MagicMock()
    res = MagicMock()
    res.data = rows
    db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = res
    return db


def _config(**over):
    base = {
        "business_name": "Acme Cleaning",
        "owner_email": "owner@acme.com",
        "notification_phone": "+15559998888",
        "sms_notifications_enabled": True,
    }
    base.update(over)
    return base


class TestChannels:
    @pytest.mark.asyncio
    async def test_emails_and_smses_owner_when_both_configured(self):
        with patch.object(booking_alerts, "_fetch_tenant_alert_config", return_value=_config()), \
             patch.object(booking_alerts, "_send_email_alert", new=AsyncMock()) as em, \
             patch.object(booking_alerts, "_send_sms_alert", new=AsyncMock()) as sm:
            await send_new_booking_alert("t1", "Jane", BOOKING, appointment_id="a1")
        em.assert_awaited_once()
        sm.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_no_email_when_owner_email_missing(self):
        with patch.object(booking_alerts, "_fetch_tenant_alert_config", return_value=_config(owner_email=None)), \
             patch.object(booking_alerts, "_send_email_alert", new=AsyncMock()) as em, \
             patch.object(booking_alerts, "_send_sms_alert", new=AsyncMock()) as sm:
            await send_new_booking_alert("t1", "Jane", BOOKING, appointment_id="a1")
        em.assert_not_awaited()
        sm.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_no_sms_when_disabled(self):
        with patch.object(booking_alerts, "_fetch_tenant_alert_config", return_value=_config(sms_notifications_enabled=False)), \
             patch.object(booking_alerts, "_send_email_alert", new=AsyncMock()) as em, \
             patch.object(booking_alerts, "_send_sms_alert", new=AsyncMock()) as sm:
            await send_new_booking_alert("t1", "Jane", BOOKING, appointment_id="a1")
        em.assert_awaited_once()
        sm.assert_not_awaited()


class TestIdempotency:
    @pytest.mark.asyncio
    async def test_same_appointment_alerted_once(self):
        with patch.object(booking_alerts, "_fetch_tenant_alert_config", return_value=_config()), \
             patch.object(booking_alerts, "_send_email_alert", new=AsyncMock()) as em, \
             patch.object(booking_alerts, "_send_sms_alert", new=AsyncMock()):
            await send_new_booking_alert("t1", "Jane", BOOKING, appointment_id="a1")
            await send_new_booking_alert("t1", "Jane", BOOKING, appointment_id="a1")
        assert em.await_count == 1


class TestResilience:
    @pytest.mark.asyncio
    async def test_never_raises_on_config_failure(self):
        with patch.object(booking_alerts, "_fetch_tenant_alert_config", side_effect=RuntimeError("db down")):
            # Must not propagate — called inside the booking response cycle.
            await send_new_booking_alert("t1", "Jane", BOOKING, appointment_id="a1")

    @pytest.mark.asyncio
    async def test_empty_config_skips_silently(self):
        with patch.object(booking_alerts, "_fetch_tenant_alert_config", return_value={}), \
             patch.object(booking_alerts, "_send_email_alert", new=AsyncMock()) as em:
            await send_new_booking_alert("t1", "Jane", BOOKING, appointment_id="a1")
        em.assert_not_awaited()


class TestContent:
    def test_email_html_escapes_and_includes_slot(self):
        html = booking_alerts._build_email_html("Acme <b>", "Jane <script>", BOOKING)
        assert "2026-07-20 10:00–10:30" in html
        assert "<script>" not in html  # escaped
        assert "Acme &lt;b&gt;" in html

    def test_sms_body_has_customer_and_slot(self):
        body = booking_alerts._build_sms_body("Acme", "Jane", BOOKING)
        assert "Jane" in body and "2026-07-20 10:00–10:30" in body

    def test_when_handles_missing_end_time(self):
        assert booking_alerts._when({"date": "2026-07-20", "start_time": "10:00"}) == "2026-07-20 10:00"


class TestAlreadyAlerted:
    def test_missing_ids_never_dedup(self):
        assert booking_alerts._already_alerted("", "a1") is False
        assert booking_alerts._already_alerted("t1", "") is False

    def test_first_call_false_second_true(self):
        assert booking_alerts._already_alerted("t1", "a1") is False
        assert booking_alerts._already_alerted("t1", "a1") is True

    def test_cache_clears_at_cap(self):
        booking_alerts._alerted.clear()
        for i in range(booking_alerts._MAX_TRACKED):
            booking_alerts._alerted.add(("t", str(i)))
        # At cap, the next new key triggers a clear then re-adds.
        assert booking_alerts._already_alerted("t", "overflow") is False
        assert ("t", "overflow") in booking_alerts._alerted


class TestFetchConfig:
    def test_returns_row_on_success(self):
        db = _mk_db([{"business_name": "Acme", "owner_email": "o@x.com"}])
        with patch.object(booking_alerts, "get_service_supabase", return_value=db):
            assert booking_alerts._fetch_tenant_alert_config("t1")["business_name"] == "Acme"

    def test_empty_on_no_rows(self):
        db = _mk_db([])
        with patch.object(booking_alerts, "get_service_supabase", return_value=db):
            assert booking_alerts._fetch_tenant_alert_config("t1") == {}

    def test_empty_on_exception(self):
        with patch.object(booking_alerts, "get_service_supabase", side_effect=RuntimeError("down")):
            assert booking_alerts._fetch_tenant_alert_config("t1") == {}


class TestSendHelpers:
    @pytest.mark.asyncio
    async def test_email_helper_calls_send_email(self):
        sent = AsyncMock()
        with patch("backend.services.email_sender.send_email", sent):
            await booking_alerts._send_email_alert("t1", "Acme", "o@x.com", "Jane", BOOKING)
        sent.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_email_helper_swallows_failure(self):
        with patch("backend.services.email_sender.send_email", AsyncMock(side_effect=RuntimeError("boom"))):
            await booking_alerts._send_email_alert("t1", "Acme", "o@x.com", "Jane", BOOKING)  # no raise

    @pytest.mark.asyncio
    async def test_sms_helper_calls_send_sms(self):
        sent = AsyncMock()
        with patch("backend.services.twilio_service.send_sms", sent):
            await booking_alerts._send_sms_alert("t1", "Acme", "+15550001111", "Jane", BOOKING)
        sent.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_sms_helper_swallows_failure(self):
        with patch("backend.services.twilio_service.send_sms", AsyncMock(side_effect=RuntimeError("boom"))):
            await booking_alerts._send_sms_alert("t1", "Acme", "+15550001111", "Jane", BOOKING)  # no raise


class TestCancellationAlert:
    @pytest.mark.asyncio
    async def test_cancel_emails_and_smses_owner(self):
        with patch.object(booking_alerts, "_fetch_tenant_alert_config", return_value=_config()), \
             patch.object(booking_alerts, "_send_cancel_email_alert", new=AsyncMock()) as em, \
             patch.object(booking_alerts, "_send_cancel_sms_alert", new=AsyncMock()) as sm:
            await send_cancellation_alert("t1", "Jane", BOOKING, appointment_id="a1")
        em.assert_awaited_once()
        sm.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_cancel_dedup_independent_of_booking(self):
        # A booking alert must NOT dedup out a later cancellation for the same
        # appointment (namespaced dedup keys).
        with patch.object(booking_alerts, "_fetch_tenant_alert_config", return_value=_config()), \
             patch.object(booking_alerts, "_send_email_alert", new=AsyncMock()) as booked_em, \
             patch.object(booking_alerts, "_send_sms_alert", new=AsyncMock()), \
             patch.object(booking_alerts, "_send_cancel_email_alert", new=AsyncMock()) as cancel_em, \
             patch.object(booking_alerts, "_send_cancel_sms_alert", new=AsyncMock()):
            await send_new_booking_alert("t1", "Jane", BOOKING, appointment_id="a1")
            await send_cancellation_alert("t1", "Jane", BOOKING, appointment_id="a1")
        booked_em.assert_awaited_once()
        cancel_em.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_cancel_deduped_on_repeat(self):
        with patch.object(booking_alerts, "_fetch_tenant_alert_config", return_value=_config()), \
             patch.object(booking_alerts, "_send_cancel_email_alert", new=AsyncMock()) as em, \
             patch.object(booking_alerts, "_send_cancel_sms_alert", new=AsyncMock()):
            await send_cancellation_alert("t1", "Jane", BOOKING, appointment_id="a1")
            await send_cancellation_alert("t1", "Jane", BOOKING, appointment_id="a1")
        assert em.await_count == 1

    @pytest.mark.asyncio
    async def test_cancel_never_raises_on_config_failure(self):
        with patch.object(booking_alerts, "_fetch_tenant_alert_config", side_effect=RuntimeError("db down")):
            await send_cancellation_alert("t1", "Jane", BOOKING, appointment_id="a1")

    def test_cancel_email_html_escapes_and_notes_slot_open(self):
        html = booking_alerts._build_cancel_email_html("Acme <b>", "Jane <script>", BOOKING)
        assert "cancelled" in html.lower()
        assert "open again" in html.lower()
        assert "<script>" not in html

    def test_cancel_sms_mentions_open_slot(self):
        body = booking_alerts._build_cancel_sms_body("Acme", "Jane", BOOKING)
        assert "Jane" in body and "open again" in body.lower()

    def test_cancel_email_handles_missing_slot_fields(self):
        html = booking_alerts._build_cancel_email_html("Acme", "Jane", {})
        assert "cancelled" in html.lower()  # no slot info, still valid
