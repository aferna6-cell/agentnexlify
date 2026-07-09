"""Tests for _seed_default_business_hours (onboarding booking-hours seed).

Added 2026-07-09: booking_enabled defaults true (migration 163) but a tenant
without a business_hours row generates zero slots for every date, so the
widget booking calendar dead-ends. Onboarding now seeds Mon-Fri 9-5 defaults
when no row exists.

Run with:
    pytest backend/tests/test_onboarding_default_hours.py --noconftest -v
"""

import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
os.environ.setdefault("TESTING", "1")

from backend.routers.onboarding import _seed_default_business_hours


TENANT = "tenant-uuid-1"


class TestSeedDefaultBusinessHours:
    def test_seeds_when_no_hours_row(self):
        with patch(
            "backend.services.booking.get_business_hours", return_value=None
        ), patch(
            "backend.services.booking.upsert_business_hours"
        ) as upsert:
            assert _seed_default_business_hours(TENANT) is True
            upsert.assert_called_once_with(TENANT, {})

    def test_skips_when_hours_row_exists(self):
        existing = {"tenant_id": TENANT, "hours": {"monday": {"enabled": True}}}
        with patch(
            "backend.services.booking.get_business_hours", return_value=existing
        ), patch(
            "backend.services.booking.upsert_business_hours"
        ) as upsert:
            assert _seed_default_business_hours(TENANT) is False
            upsert.assert_not_called()

    def test_never_raises_on_lookup_failure(self):
        with patch(
            "backend.services.booking.get_business_hours",
            side_effect=RuntimeError("db down"),
        ):
            assert _seed_default_business_hours(TENANT) is False

    def test_never_raises_on_upsert_failure(self):
        with patch(
            "backend.services.booking.get_business_hours", return_value=None
        ), patch(
            "backend.services.booking.upsert_business_hours",
            side_effect=RuntimeError("insert failed"),
        ):
            assert _seed_default_business_hours(TENANT) is False


class TestDefaultHoursShape:
    def test_default_hours_are_bookable_weekdays(self):
        """DEFAULT_HOURS (what upsert falls back to for {}) must produce
        actual slots: at least one enabled weekday with end > start."""
        from backend.services.booking import DEFAULT_HOURS

        enabled = {d: v for d, v in DEFAULT_HOURS.items() if v.get("enabled")}
        assert len(enabled) >= 5  # Mon-Fri
        for day, v in enabled.items():
            assert v["end"] > v["start"], (
                f"{day} has end <= start — impossible hours generate zero "
                "slots (this exact bug hid 914 Exterior's calendar in prod)"
            )
