"""Workforce chat calendar read + approval-gated booking.

The two production prompts must not be answered as internal appointment
counts. Google writes happen only when the approved calendar action runs.
"""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from googleapiclient.errors import HttpError

from backend.services import biz_answers, google_calendar, os_calendar_chat
from backend.services.os_actions.base import ActionContext
from backend.services.os_actions.calendar import _run, claim_calendar_approval
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


class _HttpResp:
    def __init__(self, status):
        self.status = status
        self.reason = "error"


class FakeEvents:
    def __init__(self, items=None):
        self.lists = []
        self.inserts = []
        self.gets = []
        self.store = {}
        self._items = items if items is not None else []

    def list(self, **kwargs):
        self.lists.append(kwargs)
        return FakeExec({"items": self._items})

    def insert(self, calendarId=None, body=None, sendUpdates=None, **kwargs):
        self.inserts.append(
            {"calendarId": calendarId, "body": body, "sendUpdates": sendUpdates, **kwargs}
        )
        if getattr(self, "insert_error", None) is not None:
            raise self.insert_error
        event_id = (body or {}).get("id") or "evt_oauth_demo"
        stored = {"id": event_id, "status": "confirmed", "summary": (body or {}).get("summary")}
        self.store[event_id] = stored
        if getattr(self, "timeout_on_insert", False):
            self.timeout_on_insert = False
            raise TimeoutError("deadline exceeded")
        return FakeExec(stored)

    def get(self, calendarId=None, eventId=None, **kwargs):
        self.gets.append(eventId)
        found = self.store.get(eventId)
        if not found:
            raise HttpError(_HttpResp(404), b"not found")
        return FakeExec(found)


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
        assert event["duration_minutes"] == 30
        assert "Duration: 30 minutes" in run["deliverable"]["body"]
        assert event["start_utc"] == "2026-11-05T15:00:00+00:00"
        assert event["end_utc"] == "2026-11-05T15:30:00+00:00"
        assert "Duration: 30 minutes" in _inserts(database, "os_messages")[0]["content"]
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


def _approved_run(status="approved", body=None, **event_overrides):
    event = {
        "summary": "OAuth demo",
        "start_utc": "2026-11-05T15:00:00+00:00",
        "end_utc": "2026-11-05T15:30:00+00:00",
        "duration_minutes": 30,
        "description": BOOK_PROMPT,
        "attendee_email": None,
    }
    event.update(event_overrides)
    card = body if body is not None else "Approve to add it."
    event["card_body"] = card
    return {
        "id": "run-1",
        "client_id": "c1",
        "deliverable_status": status,
        "action_type": "calendar.event.create",
        "deliverable": {
            "title": "Book: OAuth demo",
            "body": card,
            "channel": "calendar",
            "calendar_event": event,
        },
    }


class TestApproveInserts:
    def test_approval_calls_events_insert_on_the_fake_client(self):
        google = FakeGoogle()
        run = _approved_run()
        ctx = ActionContext(
            db=_db({"os_agent_runs": [run]}),
            client_id="c1",
            deliverable_id="run-1",
            action_run_id="act-1",
            action_type="calendar.event.create",
            deliverable=run["deliverable"],
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
        assert result.response_payload["event_id"] == google_calendar.deterministic_event_id(
            "run-1"
        )
        assert len(google.events().inserts) == 1
        body = google.events().inserts[0]["body"]
        assert google.events().inserts[0]["calendarId"] == "primary"
        assert body["summary"] == "OAuth demo"
        assert body["start"]["dateTime"] == "2026-11-05T15:00:00+00:00"
        assert body["end"]["dateTime"] == "2026-11-05T15:30:00+00:00"
        assert google.events().inserts[0]["sendUpdates"] == "none"
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


class _MemoryQuery:
    def __init__(self, db, table):
        self.db = db
        self.table = table
        self.filters = []
        self.op = "select"
        self.payload = None

    def select(self, *args, **kwargs):
        self.op = "select"
        return self

    def update(self, payload):
        self.op = "update"
        self.payload = dict(payload)
        return self

    def insert(self, payload):
        self.op = "insert"
        self.payload = dict(payload)
        return self

    def eq(self, column, value):
        self.filters.append((column, value))
        return self

    def limit(self, _n):
        return self

    def execute(self):
        rows = self.db.tables.setdefault(self.table, [])

        def matches(row):
            return all(row.get(column) == value for column, value in self.filters)

        if self.op == "insert":
            row = dict(self.payload)
            rows.append(row)
            return SimpleNamespace(data=[row])
        if self.op == "update":
            updated = []
            for row in rows:
                if matches(row):
                    row.update(self.payload)
                    updated.append(row)
            return SimpleNamespace(data=updated)
        return SimpleNamespace(data=[row for row in rows if matches(row)])


class MemoryDB:
    def __init__(self, tables):
        self.tables = {name: [dict(row) for row in rows] for name, rows in tables.items()}

    def table(self, name):
        return _MemoryQuery(self, name)


SECRET = "ya29.SUPER_SECRET_TOKEN"


def _http_error(status, body=b"nope"):
    return HttpError(_HttpResp(status), body)


class TestInsertRequiresApproval:
    def test_direct_insert_without_approval_is_refused(self):
        google = FakeGoogle()
        pending = _approved_run(status="pending_approval")
        database = MemoryDB({"os_agent_runs": [pending]})

        def _explode(*_args, **_kwargs):
            raise AssertionError("events.insert path built a Google client")

        with patch("backend.services.google_calendar._build_service", side_effect=_explode):
            result = google_calendar.insert_approved_calendar_event(database, "c1", "run-1")
        assert result["ok"] is False
        assert result["code"] == "not_approved"
        assert result["event_id"] is None
        assert "not approved" in result["message"]
        assert google.events().inserts == []

    def test_other_tenant_and_someone_elses_card_do_nothing(self):
        google = FakeGoogle()
        database = MemoryDB({"os_agent_runs": [_approved_run()]})
        with patch("backend.services.google_calendar._build_service", return_value=google):
            missing = google_calendar.insert_approved_calendar_event(
                database, "other-tenant", "run-1"
            )
            unknown = google_calendar.insert_approved_calendar_event(
                database, "c1", "someone-elses-run"
            )
        assert missing["code"] == "not_found"
        assert unknown["code"] == "not_found"
        assert google.events().inserts == []
        assert google.events().gets == []

    @pytest.mark.parametrize("status", ["rejected", "expired"])
    def test_rejected_or_expired_card_never_inserts(self, status):
        google = FakeGoogle()
        database = MemoryDB({"os_agent_runs": [_approved_run(status=status)]})
        with patch("backend.services.google_calendar._build_service", return_value=google):
            result = google_calendar.insert_approved_calendar_event(database, "c1", "run-1")
        assert result["code"] == "not_approved"
        assert google.events().inserts == []


class TestIdempotentInsert:
    def test_double_approve_creates_one_event(self):
        google = FakeGoogle()
        database = MemoryDB({"os_agent_runs": [_approved_run()]})
        with patch("backend.services.google_calendar._build_service", return_value=google):
            first = google_calendar.insert_approved_calendar_event(database, "c1", "run-1")
            second = google_calendar.insert_approved_calendar_event(database, "c1", "run-1")
        assert first["ok"] and second["ok"]
        assert first["event_id"] == second["event_id"]
        assert second["deduplicated"] is True
        assert len(google.events().inserts) == 1
        stored = database.tables["os_agent_runs"][0]["deliverable"]["google_event_id"]
        assert stored == first["event_id"]

    def test_second_claim_does_not_approve_again(self):
        database = MemoryDB({"os_agent_runs": [_approved_run(status="pending_approval")]})
        first = claim_calendar_approval(database, "c1", "run-1")
        second = claim_calendar_approval(database, "other-tenant", "run-1")
        third = claim_calendar_approval(database, "c1", "run-1")
        assert first["deliverable_status"] == "approved"
        assert second is None
        assert third is None

    def test_retry_after_timeout_does_not_insert_twice(self):
        google = FakeGoogle()
        google.events().timeout_on_insert = True
        database = MemoryDB({"os_agent_runs": [_approved_run()]})
        with patch("backend.services.google_calendar._build_service", return_value=google):
            first = google_calendar.insert_approved_calendar_event(database, "c1", "run-1")
            second = google_calendar.insert_approved_calendar_event(database, "c1", "run-1")
        assert first["ok"] and first["deduplicated"] is True
        assert second["event_id"] == first["event_id"]
        assert len(google.events().inserts) == 1


class TestProviderFailures:
    def test_revoked_token_on_list_and_insert_creates_nothing(self):
        leaked = {"id": "int-1", "access_token": SECRET, "refresh_token": "1//" + SECRET}
        google = FakeGoogle()
        database = _owner_db()
        with (
            patch("backend.services.google_calendar.get_integration", return_value=leaked),
            patch("backend.services.google_calendar._build_service", return_value=None),
            patch(
                "backend.services.booking.get_business_hours",
                return_value={"timezone": "America/New_York"},
            ),
            patch("backend.services.activity.log_activity"),
        ):
            listed = _run_async(
                os_calendar_chat.try_calendar_turn(
                    database, "c1", "th1", {"content": READ_PROMPT}, now=NOW
                )
            )
        reply = _inserts(database, "os_messages")[0]["content"]
        assert "expired or was revoked" in reply
        assert SECRET not in reply
        assert "were created" not in reply
        assert listed["calendar_read"] is True

        approved = MemoryDB({"os_agent_runs": [_approved_run()]})
        with (
            patch("backend.services.google_calendar.get_integration", return_value=leaked),
            patch("backend.services.google_calendar._build_service", return_value=None),
        ):
            created = google_calendar.insert_approved_calendar_event(approved, "c1", "run-1")
        assert created["code"] == "token_unavailable"
        assert "expired or was revoked" in created["message"]
        assert SECRET not in created["message"]
        assert created["event_id"] is None
        assert google.events().inserts == []

    def test_google_403_on_list_and_insert_creates_nothing(self):
        secret_body = SECRET.encode()
        google = FakeGoogle()
        google.events().list = lambda **kwargs: FakeExec(None)

        class _ForbiddenList:
            def execute(self):
                raise _http_error(403, secret_body)

        google.events().list = lambda **kwargs: _ForbiddenList()
        database = _owner_db()
        with (
            patch("backend.services.google_calendar.get_integration", return_value={"id": "int-1"}),
            patch("backend.services.google_calendar._build_service", return_value=google),
            patch(
                "backend.services.booking.get_business_hours",
                return_value={"timezone": "America/New_York"},
            ),
            patch("backend.services.activity.log_activity"),
        ):
            _run_async(
                os_calendar_chat.try_calendar_turn(
                    database, "c1", "th1", {"content": WEEK_PROMPT}, now=NOW
                )
            )
        reply = _inserts(database, "os_messages")[0]["content"]
        assert "access denied" in reply
        assert SECRET not in reply
        assert google.events().inserts == []

        insert_google = FakeGoogle()
        insert_google.events().insert_error = _http_error(403, secret_body)
        approved = MemoryDB({"os_agent_runs": [_approved_run()]})
        with patch(
            "backend.services.google_calendar._build_service", return_value=insert_google
        ):
            created = google_calendar.insert_approved_calendar_event(approved, "c1", "run-1")
        assert created["code"] == "http_403"
        assert "access denied" in created["message"]
        assert SECRET not in created["message"]
        assert created["event_id"] is None
        assert insert_google.events().store == {}


class TestCardAndDisconnect:
    def test_edited_card_is_refused(self):
        google = FakeGoogle()
        run = _approved_run()
        run["deliverable"]["body"] = "Title: Something else\nWhen: tomorrow at 9am\nDuration: 15 minutes"
        database = MemoryDB({"os_agent_runs": [run]})
        with patch("backend.services.google_calendar._build_service", return_value=google):
            result = google_calendar.insert_approved_calendar_event(database, "c1", "run-1")
        assert result["code"] == "body_mismatch"
        assert "edited" in result["message"]
        assert google.events().inserts == []

    def test_attendee_insert_does_not_send_invites(self):
        google = FakeGoogle()
        database = MemoryDB(
            {"os_agent_runs": [_approved_run(attendee_email="guest@example.com")]}
        )
        with patch("backend.services.google_calendar._build_service", return_value=google):
            result = google_calendar.insert_approved_calendar_event(database, "c1", "run-1")
        assert result["ok"] is True
        call = google.events().inserts[0]
        assert call["sendUpdates"] == "none"
        assert call["body"]["attendees"] == [{"email": "guest@example.com"}]
        assert call["sendUpdates"] != "all"
        assert call["sendUpdates"] != "externalOnly"

    def test_disconnect_rejects_pending_calendar_cards_only(self):
        database = MemoryDB(
            {
                "os_agent_runs": [
                    _approved_run(status="pending_approval"),
                    {
                        "id": "email-1",
                        "client_id": "c1",
                        "action_type": "email.send",
                        "deliverable_status": "pending_approval",
                        "deliverable": {"title": "Email"},
                    },
                ]
            }
        )
        cancelled = os_calendar_chat.cancel_pending_calendar_approvals(database, "c1")
        assert cancelled == 1
        rows = {row["id"]: row for row in database.tables["os_agent_runs"]}
        assert rows["run-1"]["deliverable_status"] == "rejected"
        assert rows["email-1"]["deliverable_status"] == "pending_approval"
        google = FakeGoogle()
        with patch("backend.services.google_calendar._build_service", return_value=google):
            refused = google_calendar.insert_approved_calendar_event(database, "c1", "run-1")
        assert refused["code"] == "not_approved"
        assert google.events().inserts == []


class TestBizAnswerSplit:
    def test_calendar_wording_is_not_an_appointment_count(self):
        database = _db({"appointments": [{"id": "a1"}, {"id": "a2"}]})
        for prompt in (READ_PROMPT, WEEK_PROMPT, BOOK_PROMPT):
            out = biz_answers.answer_question(database, "c1", prompt)
            assert out["matched"] is False
            assert "appointment(s) were created" not in out["answer"]

    def test_real_appointment_count_still_counts(self):
        database = _db({"appointments": [{"id": "a1"}, {"id": "a2"}]})
        out = biz_answers.answer_question(
            database, "c1", "how many appointments were booked this month?"
        )
        assert out["matched"] is True
        assert out["template"] == "appointment_count"
        assert out["data"]["appointments"] == 2
        assert "were created" in out["answer"]
