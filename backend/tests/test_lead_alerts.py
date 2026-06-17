"""Tests for instant owner lead alerts (backend/services/lead_alerts.py).

Contract pinned here:
  1. On a new lead with both channels configured, email AND SMS fire.
  2. SMS is sent with tenant_id so the demo no-op guard applies.
  3. An email failure is swallowed and does NOT stop the SMS, and vice
     versa. send_new_lead_alert never raises.
  4. Demo tenants no-op: the Twilio/Resend wrappers suppress sends; we
     assert the alert path still completes without raising.
  5. Idempotent: alerting the same (tenant_id, lead_id) twice sends each
     channel exactly once.
  6. Channels gate on config: no owner_email => no email; sms disabled or
     no phone => no SMS.
"""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
os.environ.setdefault("TESTING", "1")

from backend.services import lead_alerts

_TENANT = "aaaaaaaa-0000-0000-0000-000000000001"
_LEAD = "bbbbbbbb-0000-0000-0000-000000000002"


def _config_db(config):
    """Mock Supabase client whose tenants lookup returns `config`."""
    db = MagicMock()
    chain = db.table.return_value.select.return_value.eq.return_value.limit.return_value
    chain.execute.return_value = MagicMock(data=[config] if config else [])
    return db


def _run(coro):
    return asyncio.run(coro)


def setup_function(_fn):
    lead_alerts.reset_idempotency_cache()


def test_both_channels_fire_when_configured():
    config = {
        "business_name": "Acme Plumbing",
        "owner_email": "owner@acme.test",
        "notification_phone": "+15551234567",
        "sms_notifications_enabled": True,
    }
    send_email = AsyncMock(return_value={"success": True})
    send_sms = AsyncMock(return_value=True)

    with (
        patch.object(lead_alerts, "get_service_supabase", return_value=_config_db(config)),
        patch("backend.services.email_sender.send_email", send_email),
        patch("backend.services.twilio_service.send_sms", send_sms),
    ):
        _run(lead_alerts.send_new_lead_alert(
            _TENANT, "Jane Doe", {"email": "jane@x.test", "phone": "+15559998888"}, lead_id=_LEAD,
        ))

    assert send_email.await_count == 1, "email should fire exactly once"
    assert send_sms.await_count == 1, "SMS should fire exactly once"
    # SMS must carry tenant_id so the demo no-op guard can apply.
    _, sms_kwargs = send_sms.await_args
    assert sms_kwargs.get("tenant_id") == _TENANT, "SMS must pass tenant_id for demo guard"
    assert "Acme Plumbing" in sms_kwargs.get("body", "")


def test_email_failure_does_not_block_sms():
    config = {
        "business_name": "Acme",
        "owner_email": "owner@acme.test",
        "notification_phone": "+15551234567",
        "sms_notifications_enabled": True,
    }
    send_email = AsyncMock(side_effect=RuntimeError("resend down"))
    send_sms = AsyncMock(return_value=True)

    with (
        patch.object(lead_alerts, "get_service_supabase", return_value=_config_db(config)),
        patch("backend.services.email_sender.send_email", send_email),
        patch("backend.services.twilio_service.send_sms", send_sms),
    ):
        # Must not raise.
        _run(lead_alerts.send_new_lead_alert(_TENANT, "Jane", {"email": "j@x.test"}, lead_id=_LEAD))

    assert send_email.await_count == 1
    assert send_sms.await_count == 1, "SMS should still fire after email failure"


def test_sms_failure_does_not_block_email():
    config = {
        "business_name": "Acme",
        "owner_email": "owner@acme.test",
        "notification_phone": "+15551234567",
        "sms_notifications_enabled": True,
    }
    send_email = AsyncMock(return_value={"success": True})
    send_sms = AsyncMock(side_effect=RuntimeError("twilio down"))

    with (
        patch.object(lead_alerts, "get_service_supabase", return_value=_config_db(config)),
        patch("backend.services.email_sender.send_email", send_email),
        patch("backend.services.twilio_service.send_sms", send_sms),
    ):
        _run(lead_alerts.send_new_lead_alert(_TENANT, "Jane", {"email": "j@x.test"}, lead_id=_LEAD))

    assert send_email.await_count == 1, "email should still fire despite SMS failure"
    assert send_sms.await_count == 1


def test_demo_tenant_no_op_completes_cleanly():
    """For demo tenants the real wrappers no-op (return success-shaped) and
    nothing leaves the system. We assert the alert path completes and still
    invokes the wrappers, which themselves perform the suppression."""
    config = {
        "business_name": "Demo Co",
        "owner_email": "owner@demo.test",
        "notification_phone": "+15550000000",
        "sms_notifications_enabled": True,
    }
    # Real wrappers return success-shaped no-ops for demo tenants.
    send_email = AsyncMock(return_value={"success": True, "detail": "demo_noop", "demo": True})
    send_sms = AsyncMock(return_value=True)

    with (
        patch.object(lead_alerts, "get_service_supabase", return_value=_config_db(config)),
        patch("backend.services.email_sender.send_email", send_email),
        patch("backend.services.twilio_service.send_sms", send_sms),
    ):
        _run(lead_alerts.send_new_lead_alert(_TENANT, "Demo Lead", {"email": "d@x.test"}, lead_id=_LEAD))

    # Wrappers are invoked with tenant_id; the demo suppression lives inside them.
    assert send_email.await_count == 1
    assert send_sms.await_count == 1
    _, sms_kwargs = send_sms.await_args
    assert sms_kwargs.get("tenant_id") == _TENANT


def test_idempotent_no_double_send():
    config = {
        "business_name": "Acme",
        "owner_email": "owner@acme.test",
        "notification_phone": "+15551234567",
        "sms_notifications_enabled": True,
    }
    send_email = AsyncMock(return_value={"success": True})
    send_sms = AsyncMock(return_value=True)

    with (
        patch.object(lead_alerts, "get_service_supabase", return_value=_config_db(config)),
        patch("backend.services.email_sender.send_email", send_email),
        patch("backend.services.twilio_service.send_sms", send_sms),
    ):
        _run(lead_alerts.send_new_lead_alert(_TENANT, "Jane", {"email": "j@x.test"}, lead_id=_LEAD))
        # Second call for the SAME lead — both channels must be deduped.
        _run(lead_alerts.send_new_lead_alert(_TENANT, "Jane", {"email": "j@x.test"}, lead_id=_LEAD))

    assert send_email.await_count == 1, "email must not double-send for same lead_id"
    assert send_sms.await_count == 1, "SMS must not double-send for same lead_id"


def test_two_shim_calls_send_each_channel_once():
    """The widget calls SMS shim then email shim for one lead. Both delegate
    to send_new_lead_alert; idempotency must yield exactly one of each."""
    from backend.routers import widget_lead_helpers as wlh

    config = {
        "business_name": "Acme",
        "owner_email": "owner@acme.test",
        "notification_phone": "+15551234567",
        "sms_notifications_enabled": True,
    }
    send_email = AsyncMock(return_value={"success": True})
    send_sms = AsyncMock(return_value=True)

    with (
        patch.object(lead_alerts, "get_service_supabase", return_value=_config_db(config)),
        patch("backend.services.email_sender.send_email", send_email),
        patch("backend.services.twilio_service.send_sms", send_sms),
    ):
        _run(wlh._send_new_lead_sms_notification(_TENANT, "Jane", {"email": "j@x.test"}, lead_id=_LEAD))
        _run(wlh._send_new_lead_email_notification(_TENANT, "Jane", {"email": "j@x.test"}, lead_id=_LEAD))

    assert send_email.await_count == 1
    assert send_sms.await_count == 1


def test_no_email_when_owner_email_missing():
    config = {
        "business_name": "Acme",
        "owner_email": None,
        "notification_phone": "+15551234567",
        "sms_notifications_enabled": True,
    }
    send_email = AsyncMock(return_value={"success": True})
    send_sms = AsyncMock(return_value=True)

    with (
        patch.object(lead_alerts, "get_service_supabase", return_value=_config_db(config)),
        patch("backend.services.email_sender.send_email", send_email),
        patch("backend.services.twilio_service.send_sms", send_sms),
    ):
        _run(lead_alerts.send_new_lead_alert(_TENANT, "Jane", {"phone": "+15559998888"}, lead_id=_LEAD))

    assert send_email.await_count == 0, "no email when owner_email unset"
    assert send_sms.await_count == 1


def test_no_sms_when_disabled_or_no_phone():
    # SMS disabled
    config = {
        "business_name": "Acme",
        "owner_email": "owner@acme.test",
        "notification_phone": "+15551234567",
        "sms_notifications_enabled": False,
    }
    send_email = AsyncMock(return_value={"success": True})
    send_sms = AsyncMock(return_value=True)
    with (
        patch.object(lead_alerts, "get_service_supabase", return_value=_config_db(config)),
        patch("backend.services.email_sender.send_email", send_email),
        patch("backend.services.twilio_service.send_sms", send_sms),
    ):
        _run(lead_alerts.send_new_lead_alert(_TENANT, "Jane", {"email": "j@x.test"}, lead_id=_LEAD))
    assert send_sms.await_count == 0, "no SMS when sms_notifications_enabled is False"
    assert send_email.await_count == 1

    # No phone configured
    lead_alerts.reset_idempotency_cache()
    config2 = {
        "business_name": "Acme",
        "owner_email": "owner@acme.test",
        "notification_phone": None,
        "sms_notifications_enabled": True,
    }
    send_email2 = AsyncMock(return_value={"success": True})
    send_sms2 = AsyncMock(return_value=True)
    with (
        patch.object(lead_alerts, "get_service_supabase", return_value=_config_db(config2)),
        patch("backend.services.email_sender.send_email", send_email2),
        patch("backend.services.twilio_service.send_sms", send_sms2),
    ):
        _run(lead_alerts.send_new_lead_alert(_TENANT, "Jane", {"email": "j@x.test"}, lead_id=_LEAD))
    assert send_sms2.await_count == 0, "no SMS when notification_phone unset"


def test_missing_tenant_config_skips_silently():
    send_email = AsyncMock(return_value={"success": True})
    send_sms = AsyncMock(return_value=True)
    with (
        patch.object(lead_alerts, "get_service_supabase", return_value=_config_db(None)),
        patch("backend.services.email_sender.send_email", send_email),
        patch("backend.services.twilio_service.send_sms", send_sms),
    ):
        _run(lead_alerts.send_new_lead_alert(_TENANT, "Jane", {"email": "j@x.test"}, lead_id=_LEAD))
    assert send_email.await_count == 0
    assert send_sms.await_count == 0


def test_config_lookup_failure_never_raises():
    db = MagicMock()
    db.table.side_effect = RuntimeError("db down")
    send_email = AsyncMock(return_value={"success": True})
    send_sms = AsyncMock(return_value=True)
    with (
        patch.object(lead_alerts, "get_service_supabase", return_value=db),
        patch("backend.services.email_sender.send_email", send_email),
        patch("backend.services.twilio_service.send_sms", send_sms),
    ):
        # Must not raise even though the config lookup blows up.
        _run(lead_alerts.send_new_lead_alert(_TENANT, "Jane", {"email": "j@x.test"}, lead_id=_LEAD))
    assert send_email.await_count == 0
    assert send_sms.await_count == 0
