"""Regression tests for backend.services.daily_briefing.

Focus: _format_briefing_sms rendering, specifically the dangling em-dash
case that was fixed in the hard-debug pass (2026-04-09) — when an
appointment's start_time is unparseable we must fall back to the
customer name on its own instead of emitting a bare `  •  — Name` row.
"""

from backend.services import daily_briefing


class TestFormatBriefingSms:
    def test_no_new_data_baseline(self):
        sms = daily_briefing._format_briefing_sms(
            "Acme", {"new_leads": 0, "appointment_count": 0}
        )
        assert sms.startswith("Good morning! Here's your Acme daily briefing:")
        assert "📬 No new leads" in sms
        assert "📅 No appointments today" in sms

    def test_valid_appointment_time_renders_with_em_dash(self):
        sms = daily_briefing._format_briefing_sms(
            "Acme",
            {
                "new_leads": 2,
                "appointment_count": 1,
                "appointments": [
                    {
                        "customer_name": "Jane Doe",
                        "start_time": "2026-04-09T13:30:00Z",
                    }
                ],
            },
        )
        assert "📬 2 new leads" in sms
        # Good parse → time string appears before the em-dash.
        assert "Jane Doe" in sms
        assert " — Jane Doe" in sms

    def test_unparseable_start_time_skips_em_dash(self):
        """Regression: previously we appended `  •  — Customer` when the time
        failed to parse, leaving a lonely em-dash in the SMS. Now we render
        the name on its own."""
        sms = daily_briefing._format_briefing_sms(
            "Acme",
            {
                "appointment_count": 1,
                "appointments": [
                    {"customer_name": "Jane Doe", "start_time": "not-a-date"}
                ],
            },
        )
        # The row must contain the name, but NOT the em-dash separator
        # (which would have been a dangling marker with no time to its left).
        assert "Jane Doe" in sms
        assert " — Jane Doe" not in sms
        assert "  • Jane Doe" in sms

    def test_missing_customer_name_defaults(self):
        sms = daily_briefing._format_briefing_sms(
            "Acme",
            {
                "appointment_count": 1,
                "appointments": [{"start_time": "2026-04-09T09:00:00Z"}],
            },
        )
        # Anonymous customer gets a "Customer" fallback.
        assert "Customer" in sms

    def test_truncates_after_three_appointments(self):
        appts = [
            {"customer_name": f"C{i}", "start_time": "2026-04-09T10:00:00Z"}
            for i in range(5)
        ]
        sms = daily_briefing._format_briefing_sms(
            "Acme", {"appointment_count": 5, "appointments": appts}
        )
        assert "+ 2 more" in sms
        assert "C0" in sms and "C2" in sms
        # Fourth + fifth must not render as their own rows.
        assert "C3" not in sms
        assert "C4" not in sms
