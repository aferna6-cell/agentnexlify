"""Tests for backend.services.appointment_booker.

Two focused tests, patched at use-site inside appointment_booker module.
No new conftest fixtures — uses existing _stub_supabase_singletons autouse.
"""

from unittest.mock import MagicMock, patch

from backend.services.appointment_booker import (
    AppointmentBooker,
    AppointmentBookerInput,
)


class TestAppointmentBooker:
    def test_happy_path_returns_booked(self):
        """Valid input with a preferred_window → status booked."""
        inp = AppointmentBookerInput(
            client_id="client_1",
            lead_id="lead_1",
            service="Oil Change",
            preferred_window="Monday 9am-11am",
            notes="First visit",
        )

        lead_row = {
            "id": "lead_1",
            "client_id": "client_1",
            "name": "Alice",
            "email": "alice@example.com",
            "phone": "555-1234",
        }

        mock_db = MagicMock()
        (
            mock_db.table.return_value
            .select.return_value
            .eq.return_value
            .eq.return_value
            .limit.return_value
            .execute.return_value
        ).data = [lead_row]
        mock_db.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        events = iter([
            {
                "type": "agent.message",
                "id": "sevt_1",
                "content": [{"type": "text", "text": "apt-uuid-1234"}],
            },
            {
                "type": "session.status_idle",
                "id": "sevt_2",
                "stop_reason": {"type": "end_turn"},
            },
        ])
        mock_agent_client = MagicMock()
        mock_agent_client.create_session.return_value = {"id": "sess_abc"}
        mock_agent_client.stream_events.return_value = events
        mock_agent_client.send_user_message.return_value = None

        mock_handle = MagicMock()
        mock_handle.agent_id = "agent_xyz"
        mock_handle.environment_id = "env_xyz"

        with (
            patch(
                "backend.services.appointment_booker.get_service_supabase",
                return_value=mock_db,
            ),
            patch(
                "backend.services.appointment_booker.ManagedAgentsClient",
                return_value=mock_agent_client,
            ),
            patch(
                "backend.services.appointment_booker._appointment_booker_handle",
                return_value=mock_handle,
            ),
        ):
            output = AppointmentBooker().run(inp)

        assert output.status == "booked"
        assert output.appointment_id == "apt-uuid-1234"
        assert "apt-uuid-1234" in output.confirmation_message

    def test_empty_preferred_window_returns_needs_human(self):
        """Empty preferred_window → needs_human, no agent call."""
        inp = AppointmentBookerInput(
            client_id="client_1",
            lead_id="lead_1",
            service="Consultation",
            preferred_window="",
        )

        with patch(
            "backend.services.appointment_booker.ManagedAgentsClient"
        ) as mock_client_cls:
            output = AppointmentBooker().run(inp)

        assert output.status == "needs_human"
        assert output.appointment_id is None
        mock_client_cls.assert_not_called()
