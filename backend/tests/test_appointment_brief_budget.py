"""Focused spend-safety regressions for appointment AI calls.

These tests exercise the reservation branches added by PR #791 without
calling a real provider or weakening changed-lines coverage policy.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.tests.fake_supabase import db, run
from backend.services import appointment_brief
from backend.services.ai_usage_guard import AIUsageReservation


_TENANT = {
    "id": "t1",
    "plan": "agent_os",
    "ai_monthly_token_alert_threshold": None,
    "ai_monthly_token_hard_limit": None,
}

_APPT = {
    "id": "a1",
    "customer_name": "Cara Diaz",
    "customer_email": "cara@example.com",
    "customer_phone": None,
    "start_time": "2026-08-06T15:00:00Z",
    "end_time": "2026-08-06T16:00:00Z",
    "status": "confirmed",
    "notes": "Prefers afternoon",
    "lead_id": None,
}


def _fixture():
    return db({"appointments": [_APPT], "tenants": [_TENANT]})


def _reservation(*, allowed: bool) -> AIUsageReservation:
    return AIUsageReservation(
        allowed=allowed,
        tenant_id="t1",
        period_month="2026-09-01",
        estimated_tokens=900,
        alert_threshold_tokens=4_000_000,
        hard_limit_tokens=5_000_000,
    )


def test_generate_brief_budget_denial_blocks_provider(monkeypatch):
    """A denied reservation must fail before any paid provider call."""
    provider_called = False

    async def fake_call(**_kwargs):
        nonlocal provider_called
        provider_called = True
        return MagicMock(text="should not be returned")

    monkeypatch.setattr(appointment_brief, "call_claude_messages", fake_call)
    monkeypatch.setattr(
        appointment_brief,
        "reserve_ai_tokens",
        lambda **_kwargs: _reservation(allowed=False),
    )

    with pytest.raises(appointment_brief.AppointmentBudgetExceeded):
        run(appointment_brief.generate_brief(_fixture(), "t1", "a1", "Acme"))

    assert provider_called is False


def test_generate_brief_provider_failure_releases_reservation(monkeypatch):
    """Provider failure must release the reservation and never record usage."""
    reservation = _reservation(allowed=True)
    released = []
    recorded = []

    async def fake_call(**_kwargs):
        raise RuntimeError("synthetic provider failure")

    monkeypatch.setattr(appointment_brief, "call_claude_messages", fake_call)
    monkeypatch.setattr(
        appointment_brief,
        "reserve_ai_tokens",
        lambda **_kwargs: reservation,
    )
    monkeypatch.setattr(
        appointment_brief,
        "release_ai_token_reservation",
        lambda value: released.append(value),
    )
    monkeypatch.setattr(
        appointment_brief,
        "record_ai_usage",
        lambda **kwargs: recorded.append(kwargs),
    )

    with pytest.raises(RuntimeError, match="synthetic provider failure"):
        run(appointment_brief.generate_brief(_fixture(), "t1", "a1", "Acme"))

    assert released == [reservation]
    assert recorded == []


def test_generate_brief_success_records_reserved_usage(monkeypatch):
    """Successful provider completion must record against the reservation."""
    reservation = _reservation(allowed=True)
    recorded = []
    released = []

    async def fake_call(**_kwargs):
        return MagicMock(text="## Who they are\nCara.")

    monkeypatch.setattr(appointment_brief, "call_claude_messages", fake_call)
    monkeypatch.setattr(
        appointment_brief,
        "reserve_ai_tokens",
        lambda **_kwargs: reservation,
    )
    monkeypatch.setattr(
        appointment_brief,
        "record_ai_usage",
        lambda **kwargs: recorded.append(kwargs),
    )
    monkeypatch.setattr(
        appointment_brief,
        "release_ai_token_reservation",
        lambda value: released.append(value),
    )

    out = run(appointment_brief.generate_brief(_fixture(), "t1", "a1", "Acme"))

    assert out["brief"].startswith("## Who they are")
    assert len(recorded) == 1
    assert recorded[0]["reservation"] is reservation
    assert recorded[0]["operation"] == "appointments.brief"
    assert recorded[0]["session_id"] == "a1"
    assert released == []
