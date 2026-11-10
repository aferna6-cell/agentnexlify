"""Regression tests for the MTOptions support-chat incident (2026-11-09).

An existing customer wrote "I seem to have stopped getting text message
alerts." The widget bot replied "I'll pass this along to support@... to
troubleshoot your text alerts", but:

1. nothing was escalated — no escalations row, conversations.notified_at
   stayed null, nobody was notified; and
2. lead capture enrolled the paying customer in the free-trial welcome
   sequence three minutes later.

These tests drive the real widget pipeline functions with an in-memory
Supabase stand-in and assert what the system actually does: rows written,
emails sent, sequences triggered, and the text the visitor sees.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.models.schemas import WidgetChatRequest
from backend.routers import widget_chat_effects
from backend.services.support_intent import is_support_request, promises_handoff

TENANT_ID = "6d76f24b-dd71-470c-9b86-03ee35b7e887"
CONVERSATION_ID = "bcf4a488-2b6d-4d10-8263-94b8836c80ac"
SESSION_ID = "web_mw9dhjbi_4eelf8bh"

SUPPORT_MESSAGE = "I seem to have stopped getting text message alerts."
CONTACT_MESSAGE = "chris swann, chris@chrisswann.com, 601-918-3202"
PRIOR_TURNS = [
    {"role": "user", "content": SUPPORT_MESSAGE},
    {
        "role": "assistant",
        "content": (
            "That sounds like a delivery or account setting issue — our support "
            "team can look into it. Could you share your name and email (or phone)?"
        ),
    },
]
PROMISE_REPLY = (
    "Thanks, Chris! I'll pass this along to support@mtoptions.com to "
    "troubleshoot your text alerts."
)


class _FakeDB:
    """Minimal supabase-py stand-in: per-table select data, records writes."""

    def __init__(self, select_data=None):
        self.select_data = select_data or {}
        self.inserts: dict[str, list[dict]] = {}
        self.updates: dict[str, list[dict]] = {}

    def table(self, name):
        return _FakeQuery(self, name)


class _FakeQuery:
    def __init__(self, db, name):
        self._db = db
        self._name = name
        self._data = list(db.select_data.get(name, []))

    def select(self, *a, **k):
        return self

    def insert(self, row, *a, **k):
        self._db.inserts.setdefault(self._name, []).append(row)
        self._data = [{"id": f"{self._name}-new", **row}]
        return self

    def update(self, row, *a, **k):
        self._db.updates.setdefault(self._name, []).append(row)
        return self

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return lambda *a, **k: self

    def execute(self):
        return MagicMock(data=self._data)


def _tenant(**overrides):
    tenant = {
        "id": TENANT_ID,
        "business_name": "MTOptions",
        "owner_email": "owner@mtoptions.test",
        "conversation_notify_email": None,
        "notification_phone": None,
        "sms_notifications_enabled": False,
    }
    tenant.update(overrides)
    return tenant


def _req(message=CONTACT_MESSAGE):
    return WidgetChatRequest(api_key="anx_unit", session_id=SESSION_ID, message=message)


def _run_handoff(db, tenant, reply, messages=PRIOR_TURNS, message=CONTACT_MESSAGE):
    email = AsyncMock()
    sms = AsyncMock()
    with patch("backend.services.email_sender.send_email", new=email), patch(
        "backend.services.twilio_service.send_sms", new=sms
    ), patch("backend.routers.widget_chat_effects.fire_event_background"):
        text, handoff = asyncio.run(
            widget_chat_effects.handle_handoff_detection(
                db, tenant, _req(message), CONVERSATION_ID, reply, messages
            )
        )
    return text, handoff, email, sms


def _conversation_row(**extra):
    return {"conversations": [{"id": CONVERSATION_ID, "tags": [], **extra}]}


# ---------------------------------------------------------------------------
# Bug 1 — a promised handoff must become a real, notified escalation
# ---------------------------------------------------------------------------


def test_promised_support_handoff_creates_notified_escalation():
    db = _FakeDB(_conversation_row(notified_at=None))

    text, handoff, email, _sms = _run_handoff(db, _tenant(), PROMISE_REPLY)

    escalations = db.inserts["escalations"]
    assert len(escalations) == 1
    assert escalations[0]["conversation_id"] == CONVERSATION_ID
    assert escalations[0]["reason"] == SUPPORT_MESSAGE
    assert escalations[0]["metadata"]["contact"]["email"] == "chris@chrisswann.com"
    assert escalations[0]["metadata"]["notified"] is True

    sent = email.await_args.kwargs
    assert sent["to"] == "owner@mtoptions.test"
    assert "stopped getting text message alerts" in sent["body_html"]
    assert "chris@chrisswann.com" in sent["body_html"]
    assert "601-918-3202" in sent["body_html"]

    assert any(u.get("notified_at") for u in db.updates["conversations"])
    # The reply was truthful (someone was told), and the bot is not paused.
    assert text == PROMISE_REPLY
    assert handoff is False
    assert not any("tags" in u for u in db.updates["conversations"])


def test_support_alert_goes_to_configured_alert_address_and_sms():
    db = _FakeDB(_conversation_row(notified_at=None))
    tenant = _tenant(
        conversation_notify_email="support@mtoptions.test",
        notification_phone="+15550001111",
        sms_notifications_enabled=True,
    )

    _text, _handoff, email, sms = _run_handoff(db, tenant, PROMISE_REPLY)

    assert email.await_args.kwargs["to"] == "support@mtoptions.test"
    sms_body = sms.await_args.args[1]
    assert "chris@chrisswann.com" in sms_body
    assert "601-918-3202" in sms_body


def test_promise_without_any_notify_channel_is_rewritten_honestly():
    db = _FakeDB(_conversation_row(notified_at=None))
    tenant = _tenant(owner_email=None)

    text, _handoff, email, sms = _run_handoff(db, tenant, PROMISE_REPLY)

    assert text == widget_chat_effects.HANDOFF_NOT_NOTIFIED_TEXT
    assert "pass this along" not in text
    assert db.inserts["escalations"][0]["metadata"]["notified"] is False
    assert not any(u.get("notified_at") for u in db.updates.get("conversations", []))
    assert email.await_count == 0 and sms.await_count == 0


def test_already_notified_conversation_is_not_re_alerted():
    db = _FakeDB(_conversation_row(notified_at="2026-11-09T14:45:31+00:00"))

    text, _handoff, email, _sms = _run_handoff(db, _tenant(), PROMISE_REPLY)

    assert email.await_count == 0
    assert text == PROMISE_REPLY


def test_conversation_marked_spam_never_alerts_or_escalates():
    db = _FakeDB(_conversation_row(notified_at=None, tags=["spam"]))

    text, handoff, email, sms = _run_handoff(db, _tenant(), PROMISE_REPLY)

    email.assert_not_awaited()
    sms.assert_not_awaited()
    assert "escalations" not in db.inserts
    assert not any(u.get("notified_at") for u in db.updates.get("conversations", []))
    assert text == PROMISE_REPLY and handoff is False


def test_support_issue_with_contact_escalates_even_without_promise():
    db = _FakeDB(_conversation_row(notified_at=None))

    _text, _handoff, email, _sms = _run_handoff(
        db, _tenant(), "Thanks Chris, got it. Anything else going on with your alerts?"
    )

    assert db.inserts["escalations"][0]["metadata"]["trigger"] == "support_request"
    assert "chris@chrisswann.com" in email.await_args.kwargs["body_html"]


def test_marker_handoff_still_tags_and_reports_handoff():
    db = _FakeDB(_conversation_row(notified_at=None))

    text, handoff, _email, _sms = _run_handoff(
        db, _tenant(), "Let me connect you with a team member.\nHANDOFF_REQUESTED"
    )

    assert handoff is True
    assert "HANDOFF_REQUESTED" not in text
    assert {"tags": ["handoff"]} in db.updates["conversations"]


def test_ordinary_sales_reply_is_left_alone():
    db = _FakeDB(_conversation_row(notified_at=None))
    reply = "Our plans start at $49/mo. I'll send you a link to sign up!"

    text, handoff, email, _sms = _run_handoff(
        db,
        _tenant(),
        reply,
        messages=[{"role": "user", "content": "How much is a subscription?"}],
        message="jane@example.com",
    )

    assert (text, handoff) == (reply, False)
    assert "escalations" not in db.inserts
    assert email.await_count == 0


@pytest.mark.parametrize(
    "message,expected",
    [
        (SUPPORT_MESSAGE, True),
        ("I can't log in to my account", True),
        ("I'm a current subscriber and was double charged", True),
        ("What's your refund policy?", False),
        ("Do you offer text alerts?", False),
        ("How much is a subscription?", False),
    ],
)
def test_support_request_detection(message, expected):
    assert is_support_request([{"role": "user", "content": message}]) is expected


@pytest.mark.parametrize(
    "reply,expected",
    [
        (PROMISE_REPLY, True),
        ("I’ll forward your request to our team.", True),
        ("I've notified the team.", True),
        ("Let me get a team member to help.", True),
        ("I'll send you a link to sign up.", False),
        ("I'll alert you when it's ready.", False),
        ("Our support team can look into it — what's your email?", False),
    ],
)
def test_handoff_promise_detection(reply, expected):
    assert promises_handoff(reply) is expected


# ---------------------------------------------------------------------------
# Bug 2 — support / escalated chats must not enter sales sequences
# ---------------------------------------------------------------------------


def _capture(history, escalations=()):
    """Run _capture_leads_from_session for a brand-new contact and report
    the inserted lead row, the final tags write, and which sequence entry
    points fired."""
    from backend.routers import widget_lead_helpers as helpers

    db = _FakeDB({"leads": [], "escalations": list(escalations)})
    trigger = AsyncMock(return_value=0)
    enroll = AsyncMock()
    with patch(
        "backend.routers.widget_chat_helpers._load_chat_history", return_value=history
    ), patch.object(helpers, "get_service_supabase", return_value=db), patch.object(
        helpers, "log_activity"
    ), patch.object(helpers, "fire_event_background"), patch.object(
        helpers, "score_lead_background"
    ), patch.object(
        helpers, "_extract_tags_from_conversation", return_value=["issue: text alerts"]
    ), patch(
        "backend.services.automation_engine.trigger_sequence", new=trigger
    ), patch(
        "backend.routers.email_enrollment.enroll_lead_in_sequences", new=enroll
    ), patch(
        "backend.services.lead_alerts.send_new_lead_alert", new=AsyncMock()
    ):
        asyncio.run(
            helpers._capture_leads_from_session(TENANT_ID, SESSION_ID, CONVERSATION_ID)
        )
    lead_row = db.inserts["leads"][0]
    tag_writes = [u["tags"] for u in db.updates.get("leads", []) if "tags" in u]
    return lead_row, tag_writes, trigger.await_count, enroll.await_count


def test_support_chat_contact_is_tagged_support_and_not_enrolled():
    history = PRIOR_TURNS + [
        {"role": "user", "content": CONTACT_MESSAGE},
        {"role": "assistant", "content": PROMISE_REPLY},
    ]

    lead_row, tag_writes, triggers, enrolls = _capture(history)

    assert lead_row["email"] == "chris@chrisswann.com"
    assert lead_row["tags"] == ["support"]
    assert tag_writes[-1] == ["support", "issue: text alerts"]
    assert (triggers, enrolls) == (0, 0)


def test_escalated_chat_is_not_enrolled_even_without_support_wording():
    history = [
        {"role": "user", "content": "Can I talk to someone? jane@example.com"},
        {"role": "assistant", "content": "Let me connect you with a team member."},
    ]

    _lead_row, _tags, triggers, enrolls = _capture(history, escalations=[{"id": "esc-1"}])

    assert (triggers, enrolls) == (0, 0)


def test_sales_chat_still_enrolls_new_lead():
    history = [
        {"role": "user", "content": "How much is a subscription? jane@example.com"},
        {"role": "assistant", "content": "Plans start at $49/mo."},
    ]

    lead_row, _tags, triggers, enrolls = _capture(history)

    assert "tags" not in lead_row
    assert (triggers, enrolls) == (1, 1)
