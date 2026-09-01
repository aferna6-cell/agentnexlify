"""Unit tests for Google Calendar event description normalization.

Write-path callers match subsequent events against the normalized description
(booking notes / M8 marker live here, not only in summary).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.services import google_calendar as gcal


def test_normalize_calendar_event_includes_description():
    event = {
        "id": "evt_1",
        "status": "confirmed",
        "summary": "Appointment with Customer",
        "description": "Notes: M8 smoke internal m8-cal-abc12345",
        "start": {"dateTime": "2026-09-05T15:00:00Z"},
        "end": {"dateTime": "2026-09-05T16:00:00Z"},
        "attendees": [{"email": "guest@example.com", "displayName": "Guest"}],
        "htmlLink": "https://calendar.google.com/event?eid=evt_1",
    }
    normalized = gcal._normalize_calendar_event(event)
    assert normalized["description"] == "Notes: M8 smoke internal m8-cal-abc12345"
    assert normalized["summary"] == "Appointment with Customer"
    assert normalized["start"] == "2026-09-05T15:00:00Z"
    assert normalized["end"] == "2026-09-05T16:00:00Z"


def test_normalize_calendar_event_same_description_matches_across_writes():
    """Two writes of the same notes/marker normalize to the same description."""
    first = gcal._normalize_calendar_event(
        {
            "id": "evt_write_1",
            "status": "confirmed",
            "summary": "Appointment with Customer",
            "description": "Notes: M8 smoke internal m8-cal-abc12345",
            "start": {"dateTime": "2026-09-05T15:00:00Z"},
            "end": {"dateTime": "2026-09-05T16:00:00Z"},
        }
    )
    second = gcal._normalize_calendar_event(
        {
            "id": "evt_write_1",
            "status": "confirmed",
            "summary": "Appointment with Customer",
            "description": "Notes: M8 smoke internal m8-cal-abc12345",
            "start": {"dateTime": "2026-09-05T15:00:00Z"},
            "end": {"dateTime": "2026-09-05T16:00:00Z"},
        }
    )
    assert first["description"]
    assert first["description"] == second["description"]
    assert first["id"] == second["id"]
