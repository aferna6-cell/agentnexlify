"""Workforce chat calendar read + approval-gated booking.

The two production prompts must not be answered as internal appointment
counts. Google writes happen only when the approved calendar action runs.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from backend.services import biz_answers, os_calendar_chat
from backend.services.os_actions.base import ActionContext
from backend.services.os_actions.calendar import _run
from backend.tests.fake_supabase import db as _db
from backend.tests.fake_supabase import run as _run_async

READ_PROMPT = "What appointments do I have on my calendar this week?"
BOOK_PROMPT = (
    'Book a 30-minute test appointment called "OAuth demo" tomorrow at 10am'
)
WEEK_PROMPT = "what's on my calendar this week"
NOW = datetime(2026, 11, 4, 15, 0, tzinfo=timezone.utc)  # Wed 10:00 EST


class FakeExec:
    def __init__(self, payload):
        self.payload = payload

    def execute(self):
        return self.payload


class FakeEvents:
    def __init__(self, items=None):
        self.lists = []
        self.inserts = []
        self._items = items if items is not None else []

    def list(self, **kwargs):
        self.lists.append(kwargs)
        return FakeExec({"items": self._items})

    def insert(self, calendarId=None, body=None, **kwargs):
        self.inserts.append({"calendarId": calendarId, "body": body, **kwargs})
        return FakeExec({"id": "evt_oauth_demo"})


class FakeGoogle:
    """Stand-in for the Calendar API client. Only events() is implemented."""

    def __init__(self, items=None):
        self._events = FakeEvents(items)

    def events(self):
        return self._events


def _inserts(database, table):
    return [
        call[2][0]
        for call in database._sink
        if call[0] == table and call[1] == "insert" and call[2]
    ]


def _owner_db():
    return _db(
        {
            "os_threads": [{"id": "th1", "source": "chat"}],
            "os_messages": [{"id": "m-asst", "role": "assistant", "content": "ok"}],
            "os_agent_runs": [
                {
                    "id": "run-1",
                    "agent_name": "booking",
                    "status": "succeeded",
                    "deliverable_status": "pending_approval",
                    "action_type": "calendar.event.create",
                    "deliverable": {"title": "Book: OAuth demo", "channel": "calendar"},
                }
            ],
        }
    )


def _patches(google, integration):
    return (
        patch("backend.services.google_calendar._build_service", return_value=google),
        patch(
            "backend.services.google_calendar.get_integration",
            return_value=integration,
        ),
        patch(
            "backend.services.booking.get_business_hours",
            return_value={"timezone": "America/New_York"},
        ),
        patch("backend.services.activity.log_activity"),
        patch(
            "backend.services.google_calendar.create_calendar_event",
            side_effect=AssertionError("events.insert called before approval"),
        ),
    )


class TestRoutingRegression:
    def test_production_prompts_are_calendar_not_metrics(self):
        assert os_calendar_chat.classify_calendar_ask(READ_PROMPT) == "read"
        assert os_calendar_chat.classify_calendar_ask(WEEK_PROMPT) == "read"
        assert os_calendar_chat.classify_calendar_ask(BOOK_PROMPT) == "book"
        assert biz_answers.match_template(READ_PROMPT) is None
        assert biz_answers.match_template(WEEK_PROMPT) is None
        assert biz_answers.match_template(BOOK_PROMPT) is None

    def test_metric_questions_stay_on_the_count_template(self):
        metric = "how many appointments were booked this month?"
        assert os_calendar_chat.classify_calendar_ask(metric) is None
        assert biz_answers.match_template(metric) == "appointment_count"
        assert (
            biz_answers.match_template("appointments this quarter?")
            == "appointment_count"
        )
        assert (
            biz_answers.match_template("what appointments are coming up?")
            == "upcoming_appointments"
        )
        assert os_calendar_chat.classify_calendar_ask(
            "How many appointments this week?"
        ) is None

    def test_data_fast_path_does_not_steal_either_prompt(self):
        from backend.services import os_data_answers

        for prompt in (READ_PROMPT, BOOK_PROMPT, WEEK_PROMPT):
            assert (
                _run_async(
                    os_data_answers.try_data_answer(
                        _db({}), "c1", "th1", {"content": prompt}
                    )
                )
                is None
            )


class TestCalendarRead:
    def test_lists_google_events_and_does_not_insert(self):
        google = FakeGoogle(
            items=[
                {
                    "id": "evt_1",
                    "status": "confirmed",
                    "summary": "Standup",
                    "start": {"dateTime": "2026-11-04T15:00:00Z"},
                    "end": {"dateTime": "2026-11-04T15:30:00Z"},
                }
            ]
        )
        database = _owner_db()
        patches = _patches(google, {"id": "int-1"})
        with patches[0], patches[1], patches[2], patches[3] as audit, patches[4]:
            out = _run_async(
                os_calendar_chat.try_calendar_turn(
                    database,
                    "c1",
                    "th1",
                    {"content": READ_PROMPT},
                    now=NOW,
                )
            )
        assert out["calendar_read"] is True
        assert out["agent_runs"] == []
        reply = _inserts(database, "os_messages")[0]["content"]
        assert "Standup" in reply
        assert "were created" not in reply
        assert "Google Calendar" in reply
        assert google.events().inserts == []
        assert len(google.events().lists) == 1
        params = google.events().lists[0]
        assert params["calendarId"] == "primary"
        assert params["singleEvents"] is True
        assert params["timeMin"].startswith("2026-11-02T05:00:00")
        assert params["timeMax"].startswith("2026-11-09T05:00:00")
        assert _inserts(database, "os_agent_runs") == []
        assert audit.called
        assert audit.call_args.kwargs["activity_type"] == "os_calendar_read"

    def test_not_connected_does_not_call_google(self):
        google = FakeGoogle()
        database = _owner_db()
        patches = _patches(google, None)
        with patches[0], patches[1], patches[2], patches[3], patches[4]:
            out = _run_async(
                os_calendar_chat.try_calendar_turn(
                    database, "c1", "th1", {"content": WEEK_PROMPT}, now=NOW
                )
            )
        reply = _inserts(database, "os_messages")[0]["content"]
        assert "isn't connected" in reply
        assert "were created" not in reply
        assert google.events().lists == []
        assert google.events().inserts == []
        assert out["calendar_read"] is True

    def test_customer_thread_does_not_read_the_owner_calendar(self):
        google = FakeGoogle()
        database = _db({"os_threads": [{"id": "th1", "source": "widget"}]})
        patches = _patches(google, {"id": "int-1"})
        with patches[0], patches[1], patches[2], patches[3], patches[4]:
            out = _run_async(
                os_calendar_chat.try_calendar_turn(
                    database, "c1", "th1", {"content": READ_PROMPT}, now=NOW
                )
            )
        assert out is None
        assert google.events().lists == []
        assert google.events().inserts == []


class TestBookingDraft:
    def test_parks_approval_card_and_does_not_insert(self):
        google = FakeGoogle()
        database = _owner_db()
        patches = _patches(google, {"id": "int-1"})
        with patches[0], patches[1], patches[2], patches[3] as audit, patches[4]:
            out = _run_async(
                os_calendar_chat.try_calendar_turn(
                    database, "c1", "th1", {"content": BOOK_PROMPT}, now=NOW
                )
            )
        assert out["calendar_booking_draft"] is True
        assert google.events().inserts == []
        assert google.events().lists == []
        runs = _inserts(database, "os_agent_runs")
        assert len(runs) == 1
        run = runs[0]
        assert run["deliverable_status"] == "pending_approval"
        assert run["action_type"] == "calendar.event.create"
        event = run["deliverable"]["calendar_event"]
        assert event["summary"] == "OAuth demo"
        assert event["start_utc"] == "2026-11-05T15:00:00+00:00"
        assert event["end_utc"] == "2026-11-05T15:30:00+00:00"
        reply = _inserts(database, "os_messages")[0]["content"]
        assert "approve" in reply.lower()
        assert "were created" not in reply
        assert "OAuth demo" in reply
        assert audit.call_args.kwargs["activity_type"] == "os_calendar_booking_draft"

    def test_chat_turn_does_not_reach_the_engine(self):
        from backend.services import os_thread_runner

        google = FakeGoogle()
        database = _owner_db()
        patches = _patches(google, {"id": "int-1"})
        engine = AsyncMock(side_effect=AssertionError("engine should not run"))
        with (
            patches[0],
            patches[1],
            patches[2],
            patches[3],
            patches[4],
            patch.object(
                os_thread_runner.agent_sdk_client,
                "orchestrate_sync",
                engine,
            ),
            patch.object(
                os_thread_runner.os_approval_notify,
                "notify_pending_approval",
                new=AsyncMock(),
            ),
        ):
            out = _run_async(
                os_thread_runner.process_user_turn(
                    database,
                    "c1",
                    "th1",
                    {"content": BOOK_PROMPT},
                    None,
                )
            )
        engine.assert_not_called()
        assert out["calendar_booking_draft"] is True
        assert google.events().inserts == []


class TestApproveInserts:
    def test_approval_calls_events_insert_on_the_fake_client(self):
        google = FakeGoogle()
        ctx = ActionContext(
            db=_db({}),
            client_id="c1",
            deliverable_id="run-1",
            action_run_id="act-1",
            action_type="calendar.event.create",
            deliverable={
                "title": "Book: OAuth demo",
                "body": "Approve to add it.",
                "channel": "calendar",
                "calendar_event": {
                    "summary": "OAuth demo",
                    "start_utc": "2026-11-05T15:00:00+00:00",
                    "end_utc": "2026-11-05T15:30:00+00:00",
                    "description": BOOK_PROMPT,
                },
            },
            agent_run={"id": "run-1"},
        )
        with (
            patch(
                "backend.services.google_calendar._build_service",
                return_value=google,
            ),
            patch(
                "backend.services.google_calendar.get_integration",
                return_value={"id": "int-1"},
            ),
            patch(
                "backend.services.llm_runtime.call_claude_messages",
                side_effect=AssertionError("approval must not re-extract with a model"),
            ),
        ):
            result = _run_async(_run(ctx))
        assert result.status == "succeeded"
        assert result.response_payload["event_id"] == "evt_oauth_demo"
        assert len(google.events().inserts) == 1
        body = google.events().inserts[0]["body"]
        assert google.events().inserts[0]["calendarId"] == "primary"
        assert body["summary"] == "OAuth demo"
        assert body["start"]["dateTime"] == "2026-11-05T15:00:00+00:00"
        assert body["end"]["dateTime"] == "2026-11-05T15:30:00+00:00"
        assert google.events().lists == []


def test_week_prompt_also_lists_without_insert():
    google = FakeGoogle(items=[])
    database = _owner_db()
    patches = _patches(google, {"id": "int-1"})
    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        out = _run_async(
            os_calendar_chat.try_calendar_turn(
                database, "c1", "th1", {"content": WEEK_PROMPT}, now=NOW
            )
        )
    assert out["calendar_read"] is True
    reply = _inserts(database, "os_messages")[0]["content"]
    assert "Nothing is scheduled" in reply
    assert "were created" not in reply
    assert google.events().inserts == []
    assert google.events().lists
