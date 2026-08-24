"""Tests for backend.services.appointment_booker.

Patched at use-site inside the appointment_booker module. No new conftest
fixtures — uses the existing _stub_supabase_singletons autouse.

NOTE ON THE REWRITTEN HAPPY PATH (2026-08-24): the previous version of
`test_happy_path_returns_booked` asserted that the agent replying
`"apt-uuid-1234"` produced `status="booked"` with that string as the
appointment_id. That test encoded a bug, not a contract: `AppointmentBooker.run`
documents `booked` as "agent confirmed AND an appointment row exists", and the
code never checked the second half. Any prose the agent emitted became a
customer-facing "Appointment confirmed. Reference: ..." with no appointment
behind it. The happy path now uses a real UUID and mocks the row lookup; the
cases the old test would have passed are pinned below as needs_human.
"""

from unittest.mock import MagicMock, patch

from backend.services.appointment_booker import (
    AppointmentBooker,
    AppointmentBookerInput,
    _extract_appointment_id,
)

_APPT_UUID = "3f2504e0-4f89-41d3-9a0c-0305e82c3301"


def _make_input(**overrides):
    base = dict(
        client_id="client_1",
        lead_id="lead_1",
        service="Oil Change",
        preferred_window="Monday 9am-11am",
        notes="First visit",
    )
    base.update(overrides)
    return AppointmentBookerInput(**base)


def _make_db(*, appointment_rows):
    """Supabase double where `leads` resolves a lead and `appointments`
    resolves whatever `appointment_rows` says (use [] for "no such row")."""
    lead_row = {
        "id": "lead_1",
        "client_id": "client_1",
        "name": "Alice",
        "email": "alice@example.com",
        "phone": "555-1234",
    }

    leads_tbl = MagicMock()
    (
        leads_tbl.select.return_value.eq.return_value.eq.return_value
        .limit.return_value.execute.return_value
    ).data = [lead_row]
    leads_tbl.update.return_value.eq.return_value.execute.return_value = MagicMock()

    appts_tbl = MagicMock()
    (
        appts_tbl.select.return_value.eq.return_value.eq.return_value
        .limit.return_value.execute.return_value
    ).data = appointment_rows

    db = MagicMock()
    db.table.side_effect = lambda name: appts_tbl if name == "appointments" else leads_tbl
    return db


def _make_agent(reply_text):
    events = iter([
        {"type": "agent.message", "id": "sevt_1",
         "content": [{"type": "text", "text": reply_text}]},
        {"type": "session.status_idle", "id": "sevt_2",
         "stop_reason": {"type": "end_turn"}},
    ])
    client = MagicMock()
    client.create_session.return_value = {"id": "sess_abc"}
    client.stream_events.return_value = events
    client.send_user_message.return_value = None
    return client


def _run(inp, db, agent):
    handle = MagicMock()
    handle.agent_id = "agent_xyz"
    handle.environment_id = "env_xyz"
    with (
        patch("backend.services.appointment_booker.get_service_supabase", return_value=db),
        patch("backend.services.appointment_booker.ManagedAgentsClient", return_value=agent),
        patch("backend.services.appointment_booker._appointment_booker_handle",
              return_value=handle),
    ):
        return AppointmentBooker().run(inp)


class TestExtractAppointmentId:
    def test_bare_uuid(self):
        assert _extract_appointment_id(_APPT_UUID) == _APPT_UUID

    def test_uuid_inside_prose(self):
        assert _extract_appointment_id(f"Done! The id is {_APPT_UUID}.") == _APPT_UUID

    def test_uppercase_uuid_normalized(self):
        assert _extract_appointment_id(_APPT_UUID.upper()) == _APPT_UUID

    def test_prose_without_uuid_is_none(self):
        assert _extract_appointment_id("I've booked you for Tuesday at 3pm") is None

    def test_old_style_fake_id_is_rejected(self):
        """The exact string the previous test treated as a valid id."""
        assert _extract_appointment_id("apt-uuid-1234") is None

    def test_empty(self):
        assert _extract_appointment_id("") is None


class TestAppointmentBooker:
    def test_happy_path_returns_booked(self):
        """Real UUID + a matching appointment row → booked."""
        output = _run(
            _make_input(),
            _make_db(appointment_rows=[{"id": _APPT_UUID}]),
            _make_agent(_APPT_UUID),
        )
        assert output.status == "booked"
        assert output.appointment_id == _APPT_UUID
        assert _APPT_UUID in output.confirmation_message

    def test_uuid_but_no_appointment_row_is_needs_human(self):
        """The core regression: the agent claims a booking that does not exist.

        Before the fix this returned booked and told the customer
        "Appointment confirmed" for an appointment nobody would honour.
        """
        output = _run(
            _make_input(),
            _make_db(appointment_rows=[]),
            _make_agent(_APPT_UUID),
        )
        assert output.status == "needs_human"
        assert output.appointment_id is None
        assert "confirmed" not in output.confirmation_message.lower()

    def test_prose_reply_is_needs_human(self):
        """A chatty confirmation with no UUID must not become a reference."""
        output = _run(
            _make_input(),
            _make_db(appointment_rows=[{"id": _APPT_UUID}]),
            _make_agent("I've booked you for Tuesday at 3pm"),
        )
        assert output.status == "needs_human"
        assert output.appointment_id is None

    def test_lookup_error_fails_closed(self):
        """A DB error during verification must not confirm the booking."""
        db = _make_db(appointment_rows=[{"id": _APPT_UUID}])
        appts = db.table("appointments")
        appts.select.side_effect = RuntimeError("connection lost")
        output = _run(_make_input(), db, _make_agent(_APPT_UUID))
        assert output.status == "needs_human"
        assert output.appointment_id is None

    def test_lead_not_flipped_when_unverified(self):
        """An unverified booking must not mark the lead appointment_booked."""
        db = _make_db(appointment_rows=[])
        _run(_make_input(), db, _make_agent(_APPT_UUID))
        leads_tbl = db.table("leads")
        assert not leads_tbl.update.called

    def test_session_is_budget_capped(self):
        """This path is non-interactive, so it must carry a hard spend cap."""
        agent = _make_agent(_APPT_UUID)
        _run(_make_input(), _make_db(appointment_rows=[{"id": _APPT_UUID}]), agent)
        kwargs = agent.create_session.call_args.kwargs
        assert kwargs.get("budget_cents") == 500

    def test_empty_preferred_window_returns_needs_human(self):
        """Empty preferred_window → needs_human, no agent call."""
        with patch(
            "backend.services.appointment_booker.ManagedAgentsClient"
        ) as mock_client_cls:
            output = AppointmentBooker().run(_make_input(preferred_window=""))

        assert output.status == "needs_human"
        assert output.appointment_id is None
        mock_client_cls.assert_not_called()
