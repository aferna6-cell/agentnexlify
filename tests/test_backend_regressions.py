"""Regression tests for backend wiring and analytics period handling."""

import os

os.environ["TESTING"] = "1"

from fastapi.testclient import TestClient
import pytest

from backend.main import app
from backend.routers.analytics import _period_to_days


class _StopAutomationLoop(Exception):
    """Raised by tests to break the infinite automation loop."""


def test_resend_webhook_route_is_registered():
    """The Resend webhook should be reachable through the main FastAPI app."""
    client = TestClient(app)

    response = client.post("/api/v1/webhooks/resend", json={})

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_snapshot_period_mapping_supports_14_days():
    """Snapshot endpoints accepting 14d should not silently fall back to 30d."""
    assert _period_to_days("14d") == 14


@pytest.mark.asyncio
async def test_automation_loop_schedules_recurring_invoices(monkeypatch):
    """Recurring invoices should run in the 30-minute automation tier."""
    import backend.main as main

    scheduled_names = []
    sleep_calls = 0

    async def fake_safe_run(name, fn, timeout=30.0):
        scheduled_names.append(name)
        return 0

    async def fake_gather(*tasks):
        return [await task for task in tasks]

    async def fake_sleep(seconds):
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls > 30:
            raise _StopAutomationLoop()
        return None

    monkeypatch.setattr(main, "_safe_run", fake_safe_run)
    monkeypatch.setattr(main.asyncio, "gather", fake_gather)
    monkeypatch.setattr(main.asyncio, "sleep", fake_sleep)

    with pytest.raises(_StopAutomationLoop):
        await main._automation_loop()

    assert "process_recurring_invoices" in scheduled_names
