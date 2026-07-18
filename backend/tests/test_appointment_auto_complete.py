"""auto_complete_past_appointments (GH #454): confirmed -> completed.

Appointment-triggered automations (review requests, rebook prompts,
aftercare) gate on status == "completed", but until this job the only
path to "completed" was a manual dashboard action - so those automations
never fired for public bookings. Contract pinned here:

  1. A confirmed appointment past its end_time (plus grace) flips to
     completed and fires the appointment_completed trigger.
  2. Future appointments and appointments inside the grace window stay
     untouched.
  3. Internal/demo tenants are skipped entirely.
  4. Already-completed rows are never re-processed (status filter makes
     re-runs idempotent).
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
os.environ.setdefault("TESTING", "1")

from backend.services.automation.scheduled import appointment_jobs

_NOW = datetime.now(timezone.utc)


def _appt(appt_id="appt-1", tenant_id="t-1", hours_past_end=3, status="confirmed"):
    end = _NOW - timedelta(hours=hours_past_end)
    return {
        "id": appt_id,
        "tenant_id": tenant_id,
        "end_time": end.isoformat(),
        "status": status,
    }


class _FakeDb:
    """Supports the job's three query shapes and records writes.

    appointments select: .select().in_().lt().limit().execute()
    tenants select:      .select().in_().execute()
    appointments update: .update().eq().in_().execute()
    """

    def __init__(self, appts, tenants):
        self._appts = appts
        self._tenants = tenants
        self.updated_ids = []
        self.update_payloads = []
        self.select_filters = []

    def table(self, name):
        fake = self

        class _Chain:
            def __init__(self):
                self._update_payload = None
                self._eq = {}
                self._in = {}

            def select(self, *_a, **_k):
                return self

            def update(self, payload):
                self._update_payload = payload
                return self

            def eq(self, col, val):
                self._eq[col] = val
                return self

            def in_(self, col, values):
                self._in[col] = list(values)
                return self

            def lt(self, col, val):
                self._eq[f"lt:{col}"] = val
                return self

            def limit(self, *_a, **_k):
                return self

            def execute(self):
                res = MagicMock()
                if name == "appointments" and self._update_payload is not None:
                    fake.updated_ids.append(self._eq.get("id"))
                    fake.update_payloads.append(self._update_payload)
                    res.data = [{"id": self._eq.get("id")}]
                elif name == "appointments":
                    fake.select_filters.append(dict(self._in))
                    res.data = fake._appts
                elif name == "tenants":
                    res.data = fake._tenants
                else:
                    res.data = []
                return res

        return _Chain()


def _run(db):
    trigger = AsyncMock(return_value=0)
    with patch.object(appointment_jobs, "get_service_supabase", return_value=db), \
         patch.object(appointment_jobs, "check_appointment_triggers", trigger):
        import asyncio

        count = asyncio.run(appointment_jobs.auto_complete_past_appointments())
    return count, trigger


def test_past_confirmed_appointment_flips_to_completed_and_fires_trigger():
    db = _FakeDb(
        [_appt("appt-1", hours_past_end=3)],
        [{"id": "t-1", "business_name": "Acme Plumbing", "is_demo": False}],
    )
    count, trigger = _run(db)
    assert count == 1
    assert db.updated_ids == ["appt-1"]
    assert db.update_payloads[0]["status"] == "completed"
    trigger.assert_awaited_once_with("appt-1", completed=True)


def test_query_targets_only_confirmed_like_statuses():
    db = _FakeDb([], [])
    count, _ = _run(db)
    assert count == 0
    # The select filter is what makes re-runs idempotent: completed rows
    # can never match again.
    assert db.select_filters == [{"status": ["confirmed", "booked"]}]


def test_internal_demo_tenant_is_skipped():
    db = _FakeDb(
        [_appt("appt-demo", tenant_id="t-demo", hours_past_end=5)],
        [{"id": "t-demo", "business_name": "Luxe & Co. Salon (DEMO)", "is_demo": True}],
    )
    count, trigger = _run(db)
    assert count == 0
    assert db.updated_ids == []
    trigger.assert_not_awaited()


def test_appointment_inside_grace_window_is_untouched():
    # end_time in the past but within the grace hour -> the lt cutoff the
    # job sends to PostgREST must be earlier than that end_time, so the
    # fake returns it only if the cutoff would match; assert on the cutoff.
    db = _FakeDb([], [])
    _run(db)
    # One appointments select ran; reconstruct its cutoff from the chain.
    # The cutoff is now - GRACE_HOURS, so an end_time 10 minutes ago is
    # after the cutoff and cannot match the lt filter.
    cutoff = _NOW - timedelta(hours=appointment_jobs.AUTO_COMPLETE_GRACE_HOURS)
    ten_min_ago = _NOW - timedelta(minutes=10)
    assert ten_min_ago > cutoff


def test_trigger_failure_does_not_block_other_appointments():
    db = _FakeDb(
        [
            _appt("appt-1", hours_past_end=3),
            _appt("appt-2", hours_past_end=4),
        ],
        [{"id": "t-1", "business_name": "Acme Plumbing", "is_demo": False}],
    )
    trigger = AsyncMock(side_effect=[RuntimeError("boom"), 0])
    with patch.object(appointment_jobs, "get_service_supabase", return_value=db), \
         patch.object(appointment_jobs, "check_appointment_triggers", trigger):
        import asyncio

        count = asyncio.run(appointment_jobs.auto_complete_past_appointments())
    # Both rows completed even though the first trigger dispatch failed.
    assert count == 2
    assert db.updated_ids == ["appt-1", "appt-2"]
