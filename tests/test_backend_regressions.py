"""Regression tests for backend wiring and analytics period handling."""

import os
from pathlib import Path

os.environ["TESTING"] = "1"

from fastapi.testclient import TestClient
import pytest

from backend.main import app
from backend.routers.auth import _get_current_tenant
from backend.routers.analytics import _period_to_days


class _StopAutomationLoop(Exception):
    """Raised by tests to break the infinite automation loop."""


def test_resend_webhook_route_is_registered():
    """The Resend webhook should be reachable through the main FastAPI app."""
    client = TestClient(app)

    response = client.post("/api/v1/webhooks/resend", json={})

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_webhook_delivery_route_is_registered_and_returns_summary(mock_supabase, monkeypatch):
    """Webhook delivery inspection route should stay reachable and return summary data."""
    mock_supabase.set_table_data("webhooks", [{"id": "wh-123"}])
    mock_supabase.set_table_data(
        "webhook_logs",
        [
            {"id": "log-1", "webhook_id": "wh-123", "event": "lead.created", "payload": {}, "response_status": 200, "success": True, "created_at": "2026-04-03T12:00:00Z"},
            {"id": "log-2", "webhook_id": "wh-123", "event": "lead.updated", "payload": {}, "response_status": 500, "success": False, "created_at": "2026-04-03T11:00:00Z"},
        ],
    )
    monkeypatch.setattr("backend.routers.webhook_deliveries.get_supabase", lambda: mock_supabase)
    app.dependency_overrides[_get_current_tenant] = lambda: {"tenant_id": "tenant-123", "role": "owner"}
    client = TestClient(app)

    try:
        response = client.get("/api/v1/webhooks/tenant-123/wh-123/deliveries")
    finally:
        app.dependency_overrides.pop(_get_current_tenant, None)

    assert response.status_code == 200
    body = response.json()
    assert body["summary"] == {"total": 2, "succeeded": 1, "failed": 1}
    assert len(body["deliveries"]) == 2


def test_snapshot_period_mapping_supports_14_days():
    """Snapshot endpoints accepting 14d should not silently fall back to 30d."""
    assert _period_to_days("14d") == 14


def test_frontend_webhook_helpers_match_backend_routes():
    """Frontend webhook helper paths should match the backend contract."""
    contents = Path("frontend/src/utils/api/webhooks.js").read_text(encoding="utf-8")

    assert "/api/v1/webhooks/${tenantId}/logs/recent?limit=${limit}" in contents
    assert "/api/v1/webhooks/${tenantId}/${webhookId}/toggle" in contents
    assert 'method: "PATCH"' in contents


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
