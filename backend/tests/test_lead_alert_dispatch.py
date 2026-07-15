"""Owner-alert coverage on the non-widget lead-capture entry points.

Round N closes a gap found in the 2026-07-15 architecture audit: three
paths create a NEW lead but only the widget path fired the instant owner
alert (email + SMS). This locks the contract for the two paths brought to
parity here:

  1. ``lead_alerts.fire_new_lead_alert_background`` — sync-context scheduler
     that mirrors ``webhook_dispatcher.fire_event_background``. Schedules the
     async alert on the running loop; no loop => skip, never raise. Threads
     ``source_label`` through so the owner email says where the lead came from.
  2. Public form submit (``/api/v1/forms/public/{token}/submit``) fires the
     alert once for a genuinely new lead and NOT for a dedup match.
  3. Facebook Messenger ingest (``channel_manager.ingest_channel_message``)
     fires once for a first-contact sender and NOT for a returning sender.

The missed-call recovery path is intentionally excluded: it already files a
staff-inbox OS thread ("Missed call from X"), which is its owner notification.
"""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
os.environ.setdefault("TESTING", "1")

from backend.services import lead_alerts
from backend.services import channel_manager


# ---------------------------------------------------------------------------
# Scripted fake Supabase — returns queued responses per (table, op).
# ---------------------------------------------------------------------------
class _Resp:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, table, script):
        self._table = table
        self._script = script
        self._op = "select"

    # chainable no-ops
    def select(self, *a, **k):
        self._op = "select"
        return self

    def insert(self, *a, **k):
        self._op = "insert"
        return self

    def update(self, *a, **k):
        self._op = "update"
        return self

    def eq(self, *a, **k):
        return self

    def contains(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def execute(self):
        key = (self._table, self._op)
        queued = self._script.get(key)
        if isinstance(queued, list) and queued:
            return _Resp(queued.pop(0))
        return _Resp([])


class _ScriptedDB:
    """db.table(name).<chain>.execute() -> next queued (table, op) response."""

    def __init__(self, script):
        self._script = script

    def table(self, name):
        return _Query(name, self._script)


# ---------------------------------------------------------------------------
# 1. fire_new_lead_alert_background
# ---------------------------------------------------------------------------
def test_background_helper_schedules_alert_with_source_label():
    """With a running loop, the coroutine is scheduled and source_label flows."""
    seen = {}

    async def _fake_alert(tenant_id, lead_name, lead_info, lead_id="", source_label="x"):
        seen.update(
            tenant_id=tenant_id,
            lead_name=lead_name,
            lead_info=lead_info,
            lead_id=lead_id,
            source_label=source_label,
        )

    async def _drive():
        with patch.object(lead_alerts, "send_new_lead_alert", _fake_alert):
            lead_alerts.fire_new_lead_alert_background(
                "tenant-1",
                "Jane",
                {"email": "j@x.test"},
                lead_id="lead-1",
                source_label="your website contact form",
            )
            # let the scheduled task run
            await asyncio.sleep(0)

    asyncio.run(_drive())
    assert seen["tenant_id"] == "tenant-1"
    assert seen["lead_id"] == "lead-1"
    assert seen["source_label"] == "your website contact form"


def test_background_helper_no_running_loop_is_noop():
    """No event loop -> skip silently, never raise, never call the alert."""
    called = MagicMock()
    with patch.object(lead_alerts, "send_new_lead_alert", called):
        # asyncio.get_running_loop() raises RuntimeError outside a loop
        lead_alerts.fire_new_lead_alert_background("t", "n", {}, lead_id="l")
    called.assert_not_called()


def test_background_helper_swallows_schedule_failure():
    """If create_task can't schedule (non-coroutine), the failure is swallowed."""

    async def _drive():
        # A plain MagicMock is not awaitable, so loop.create_task raises
        # TypeError — the helper's inner guard must swallow it, not propagate.
        with patch.object(lead_alerts, "send_new_lead_alert", MagicMock()):
            lead_alerts.fire_new_lead_alert_background("t", "n", {}, lead_id="l")

    asyncio.run(_drive())  # no exception == pass


# ---------------------------------------------------------------------------
# 2. source_label rendering in the email body
# ---------------------------------------------------------------------------
def test_email_body_default_source_unchanged():
    html = lead_alerts._build_email_html("Acme", "Jane", {"email": "j@x.test"})
    assert "captured from your chat widget" in html


def test_email_body_custom_source_label_rendered_and_escaped():
    html = lead_alerts._build_email_html(
        "Acme", "Jane", {}, source_label="Facebook Messenger"
    )
    assert "captured from Facebook Messenger" in html
    # escaping still applies to the source label
    html2 = lead_alerts._build_email_html("Acme", "Jane", {}, source_label="<b>x</b>")
    assert "<b>x</b>" not in html2
    assert "&lt;b&gt;" in html2


# ---------------------------------------------------------------------------
# 3. Facebook Messenger ingest fires once per new contact
# ---------------------------------------------------------------------------
_FB_INTEGRATION = [{"tenant_id": "tenant-fb", "metadata": {"page_id": "PAGE1"}}]


def _fb_script(existing_lead):
    leads_select = [[{"id": "lead-existing"}]] if existing_lead else [[]]
    return {
        ("integrations", "select"): [_FB_INTEGRATION],
        ("leads", "select"): leads_select,
        ("leads", "insert"): [[{"id": "lead-new-1"}]],
        ("conversations", "select"): [[]],
        ("conversations", "insert"): [[{"id": "conv-1"}]],
        ("chat_messages", "insert"): [[{"id": "msg-1"}]],
    }


def test_messenger_new_sender_fires_owner_alert():
    fire = MagicMock()
    db = _ScriptedDB(_fb_script(existing_lead=False))
    with (
        patch.object(channel_manager, "get_service_supabase", return_value=db),
        patch.object(lead_alerts, "fire_new_lead_alert_background", fire),
    ):
        result = channel_manager.ingest_channel_message(
            provider="facebook",
            page_id="PAGE1",
            sender_id="PSID123456",
            sender_name="Bob Buyer",
            text="hi there",
        )
    assert result["tenant_id"] == "tenant-fb"
    assert fire.call_count == 1
    _, kwargs = fire.call_args
    assert kwargs["source_label"] == "Facebook Messenger"
    assert kwargs["lead_id"] == "lead-new-1"


def test_messenger_alert_failure_does_not_break_ingest():
    """A raising dispatcher is swallowed — ingest still returns its result."""
    boom = MagicMock(side_effect=RuntimeError("alert down"))
    db = _ScriptedDB(_fb_script(existing_lead=False))
    with (
        patch.object(channel_manager, "get_service_supabase", return_value=db),
        patch.object(lead_alerts, "fire_new_lead_alert_background", boom),
    ):
        result = channel_manager.ingest_channel_message(
            provider="facebook",
            page_id="PAGE1",
            sender_id="PSID999",
            sender_name=None,
            text="hi",
        )
    assert result["tenant_id"] == "tenant-fb"


def test_messenger_returning_sender_does_not_fire_owner_alert():
    fire = MagicMock()
    db = _ScriptedDB(_fb_script(existing_lead=True))
    with (
        patch.object(channel_manager, "get_service_supabase", return_value=db),
        patch.object(lead_alerts, "fire_new_lead_alert_background", fire),
    ):
        channel_manager.ingest_channel_message(
            provider="facebook",
            page_id="PAGE1",
            sender_id="PSID123456",
            sender_name="Bob Buyer",
            text="following up",
        )
    fire.assert_not_called()


# ---------------------------------------------------------------------------
# 4. Public form submit fires once for a new lead, not for a dedup match
# ---------------------------------------------------------------------------
_FORM_ROW = {
    "id": "form-1",
    "tenant_id": "tenant-form",
    "fields_json": [
        {"id": "email", "type": "email"},
        {"id": "name", "type": "text"},
    ],
    "success_message": "Thanks!",
    "is_active": True,
    "submission_count": 3,
}


def _form_script(existing_lead):
    leads_select = [[{"id": "lead-existing"}]] if existing_lead else [[]]
    return {
        ("forms", "select"): [[_FORM_ROW]],
        ("leads", "select"): leads_select,
        ("leads", "insert"): [[{"id": "lead-form-new"}]],
        ("form_submissions", "insert"): [[{"id": "sub-1"}]],
        ("forms", "update"): [[{}]],
    }


def _post_form(monkeypatch, existing_lead):
    from backend.tests.conftest import SyncASGITestClient
    from backend.main import app
    from backend.routers import forms as forms_router
    from backend.services import webhook_dispatcher

    fire = MagicMock()
    db = _ScriptedDB(_form_script(existing_lead))
    monkeypatch.setattr(forms_router, "get_service_supabase", lambda: db)
    monkeypatch.setattr(lead_alerts, "fire_new_lead_alert_background", fire)
    # keep the webhook fire a no-op so no event loop task leaks
    monkeypatch.setattr(webhook_dispatcher, "fire_event_background", lambda *a, **k: None)

    client = SyncASGITestClient(app)
    resp = client.post(
        "/api/v1/forms/public/tok-123/submit",
        json={"data_json": {"email": "buyer@x.test", "name": "Buyer"}},
    )
    return resp, fire


def test_form_new_lead_fires_owner_alert(monkeypatch):
    resp, fire = _post_form(monkeypatch, existing_lead=False)
    assert resp.status_code == 200
    assert fire.call_count == 1
    _, kwargs = fire.call_args
    assert kwargs["source_label"] == "your website contact form"
    assert kwargs["lead_id"] == "lead-form-new"


def test_form_dedup_match_does_not_fire_owner_alert(monkeypatch):
    resp, fire = _post_form(monkeypatch, existing_lead=True)
    assert resp.status_code == 200
    fire.assert_not_called()


def test_form_alert_failure_does_not_break_submission(monkeypatch):
    """A raising dispatcher is swallowed — the submission still succeeds."""
    from backend.tests.conftest import SyncASGITestClient
    from backend.main import app
    from backend.routers import forms as forms_router
    from backend.services import webhook_dispatcher

    db = _ScriptedDB(_form_script(existing_lead=False))
    boom = MagicMock(side_effect=RuntimeError("alert down"))
    monkeypatch.setattr(forms_router, "get_service_supabase", lambda: db)
    monkeypatch.setattr(lead_alerts, "fire_new_lead_alert_background", boom)
    monkeypatch.setattr(webhook_dispatcher, "fire_event_background", lambda *a, **k: None)

    client = SyncASGITestClient(app)
    resp = client.post(
        "/api/v1/forms/public/tok-123/submit",
        json={"data_json": {"email": "buyer@x.test", "name": "Buyer"}},
    )
    assert resp.status_code == 200
