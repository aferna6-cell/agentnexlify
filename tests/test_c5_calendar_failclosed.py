"""Audit C5 — Google Calendar outage must not cause external double-booking.

get_busy_times returns None (not []) when the calendar can't be verified, and
generate_available_slots fails closed (hides the day's slots) in that case so it
never offers a time already booked in the tenant's Google Calendar.
"""

import os
os.environ["TESTING"] = "1"

import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import backend.services.google_calendar as gcal
from backend.services.booking import generate_available_slots, DAY_NAMES


def _now_window():
    a = datetime.now(timezone.utc)
    return a, a + timedelta(days=1)


def test_get_busy_times_none_when_service_unavailable():
    with patch("backend.services.google_calendar._build_service", return_value=None):
        t0, t1 = _now_window()
        assert gcal.get_busy_times("tenant-1", t0, t1) is None


def test_get_busy_times_none_on_api_error():
    with patch("backend.services.google_calendar._build_service", side_effect=RuntimeError("boom")):
        t0, t1 = _now_window()
        assert gcal.get_busy_times("tenant-1", t0, t1) is None


def _slots_config():
    hours = {d: {"enabled": True, "start": "09:00", "end": "17:00"} for d in DAY_NAMES}
    return {
        "timezone": "America/New_York",
        "hours": hours,
        "slot_duration_minutes": 30,
        "buffer_minutes": 0,
    }


def _booked_table_mock():
    tbl = MagicMock()
    for m in ("select", "eq", "gte", "lte"):
        getattr(tbl, m).return_value = tbl
    tbl.execute.return_value = MagicMock(data=[])
    return tbl


def _run_generate(busy_return):
    future = date(2030, 1, 2)  # well in the future so no slots are filtered as past
    with patch("backend.services.booking.get_business_hours", return_value=_slots_config()), \
         patch("backend.services.booking.get_service_supabase", return_value=MagicMock()), \
         patch("backend.services.booking.tenant_table", return_value=_booked_table_mock()), \
         patch("backend.services.google_calendar.get_integration", return_value={"id": "int-1"}), \
         patch("backend.services.google_calendar.get_busy_times", return_value=busy_return):
        return generate_available_slots("tenant-1", future)


def test_generate_slots_fails_closed_when_calendar_unverifiable():
    # get_busy_times returns None (could-not-verify) -> hide the day's slots.
    assert _run_generate(None) == []


def test_generate_slots_returns_slots_when_calendar_verified_free():
    # get_busy_times returns [] (verified free) -> slots are still offered.
    result = _run_generate([])
    assert len(result) > 0
