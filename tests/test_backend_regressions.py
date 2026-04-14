"""Regression tests for backend wiring and analytics period handling."""

import os
from pathlib import Path
from unittest.mock import MagicMock

os.environ["TESTING"] = "1"

from fastapi.testclient import TestClient
import pytest

import backend.config as backend_config
import backend.main as backend_main
from backend.main import app
from backend.routers.auth import _get_current_tenant
from backend.routers.analytics import _period_to_days


class _StopAutomationLoop(Exception):
    """Raised by tests to break the infinite automation loop."""


async def _owner_claims_override():
    return {"tenant_id": "tenant-123", "role": "owner"}


def test_resend_webhook_route_is_registered():
    """The Resend webhook should be reachable through the main FastAPI app."""
    client = TestClient(app)

    response = client.post("/api/v1/webhooks/resend", json={})

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid webhook signature"}


def test_healthz_readyz_and_version_are_registered():
    """Process health endpoints should work without touching tenant data."""
    client = TestClient(app)

    health_response = client.get("/api/v1/healthz")
    ready_response = client.get("/api/v1/readyz")
    version_response = client.get("/api/v1/version")

    assert health_response.status_code == 200
    assert health_response.json()["status"] == "ok"
    assert ready_response.status_code == 200
    assert ready_response.json()["status"] == "ready"
    assert version_response.status_code == 200
    assert version_response.json()["service"] == "agentnexlify"
    assert version_response.json()["version"]


def test_version_metadata_prefers_explicit_release_env(monkeypatch):
    """Deploy metadata should not depend only on files inside the image."""
    monkeypatch.setenv("APP_VERSION", "2026.04.14")
    monkeypatch.setenv("APP_COMMIT_SHA", "a" * 40)

    assert backend_main._app_version() == "2026.04.14"
    assert backend_main._build_sha() == "a" * 40


def test_production_secret_check_allows_api_secret_fallbacks():
    """Missing dedicated secrets should still boot when API_SECRET_KEY is strong."""
    strong_secret = "x" * 32

    failures = backend_config._production_secret_failures(strong_secret, "", "")

    assert failures == []


def test_production_secret_check_rejects_explicit_weak_dedicated_secrets():
    """Explicit weak dedicated secrets should fail even if API fallback is strong."""
    strong_secret = "x" * 32

    failures = backend_config._production_secret_failures(
        strong_secret,
        "too-short",
        "still-too-short",
    )

    assert failures == ["JWT_SECRET_KEY", "ADMIN_API_SECRET_KEY"]


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
    monkeypatch.setattr("backend.routers.webhook_deliveries.get_service_supabase", lambda: mock_supabase)
    app.dependency_overrides[_get_current_tenant] = _owner_claims_override
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


def test_dashboard_returns_business_profile_for_hvac(mock_supabase, monkeypatch):
    """Dashboard should return a business-type-aware profile for industry-specific defaults."""
    mock_supabase.set_table_data(
        "tenants",
        [{
            "business_name": "Polar Air",
            "business_type": "hvac",
            "plan": "free",
            "plan_status": "active",
            "conversations_used_this_month": 0,
            "monthly_conversation_limit": None,
            "free_trial_started_at": "2026-04-01T00:00:00Z",
        }],
    )
    mock_supabase.set_table_data(
        "widget_configs",
        [{
            "api_key": "anx_test_key",
            "bot_name": "Polar Air Dispatch",
            "primary_color": "#f97316",
            "greeting_message": "Hi! Thanks for contacting Polar Air. Do you need AC repair, heating service, or an estimate for a new system?",
            "position": "bottom-right",
            "branding": None,
            "is_online": True,
            "offline_message": None,
            "teaser_message": None,
            "teaser_delay_seconds": 3,
            "teaser_enabled": True,
        }],
    )
    mock_supabase.set_table_data("leads", [], count=0)
    mock_supabase.set_table_data("faq_entries", [], count=0)
    mock_supabase.set_table_data("chat_messages", [])
    mock_supabase.set_table_data("activity_log", [], count=0)
    monkeypatch.setattr("backend.routers.auth.get_service_supabase", lambda: mock_supabase)
    app.dependency_overrides[_get_current_tenant] = _owner_claims_override
    client = TestClient(app)

    try:
        response = client.get("/api/v1/auth/dashboard/tenant-123")
    finally:
        app.dependency_overrides.pop(_get_current_tenant, None)

    assert response.status_code == 200
    body = response.json()
    assert body["business_type"] == "hvac"
    assert body["business_profile"]["key"] == "hvac"
    assert body["business_profile"]["label"] == "HVAC"
    assert body["widget_config"]["bot_name"] == "Polar Air Dispatch"
    assert any(action["label"] == "Book Job" for action in body["business_profile"]["quick_actions"])


class _OnboardingRecordingQuery:
    """Small query double that records onboarding widget updates."""

    def __init__(self, state: dict, table_name: str):
        self.state = state
        self.table_name = table_name
        self.operation = None
        self.payload = None

    def select(self, *args, **kwargs):
        self.operation = "select"
        return self

    def update(self, data):
        self.operation = "update"
        self.payload = data
        return self

    def insert(self, data):
        self.operation = "insert"
        self.payload = data
        return self

    def eq(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def execute(self):
        if self.table_name == "tenants" and self.operation == "select":
            return MagicMock(data=[{"id": "tenant-123", "business_name": "Polar Air", "business_page_enabled": False}])
        if self.table_name == "tenants" and self.operation == "update":
            self.state["tenant_updates"].append(self.payload)
            return MagicMock(data=[self.payload])
        if self.table_name == "widget_configs" and self.operation == "select":
            return MagicMock(data=[{
                "bot_name": "Custom Comfort Team",
                "primary_color": "#123456",
                "greeting_message": "Custom greeting already configured",
                "position": "bottom-left",
            }])
        if self.table_name == "widget_configs" and self.operation == "update":
            self.state["widget_updates"].append(self.payload)
            return MagicMock(data=[self.payload])
        if self.table_name == "faq_entries" and self.operation == "insert":
            self.state["faq_inserts"].append(self.payload)
            return MagicMock(data=[self.payload])
        raise AssertionError(f"Unexpected onboarding query: {self.table_name} {self.operation}")


class _OnboardingRecordingDb:
    def __init__(self):
        self.state = {"tenant_updates": [], "widget_updates": [], "faq_inserts": []}

    def table(self, table_name: str):
        return _OnboardingRecordingQuery(self.state, table_name)


def test_onboarding_preserves_existing_widget_customizations_when_fields_are_omitted(monkeypatch):
    """Preset defaults should not overwrite an already customized widget on re-run."""
    db = _OnboardingRecordingDb()
    monkeypatch.setattr("backend.routers.onboarding.get_service_supabase", lambda: db)

    async def _no_ai_content(*args, **kwargs):
        return None

    monkeypatch.setattr("backend.routers.onboarding._generate_ai_content", _no_ai_content)
    app.dependency_overrides[_get_current_tenant] = _owner_claims_override
    client = TestClient(app)

    try:
        response = client.post(
            "/api/v1/onboarding/tenant-123/complete",
            json={
                "business_name": "Polar Air",
                "business_type": "hvac",
                "city": "Austin, TX",
            },
        )
    finally:
        app.dependency_overrides.pop(_get_current_tenant, None)

    assert response.status_code == 200
    assert db.state["widget_updates"] == [{
        "bot_name": "Custom Comfort Team",
        "primary_color": "#123456",
        "greeting_message": "Custom greeting already configured",
        "position": "bottom-left",
    }]


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
    monkeypatch.setattr(main, "_try_acquire_automation_lock", lambda lock_name: True)
    monkeypatch.setattr(main, "_release_automation_lock", lambda lock_name: None)
    monkeypatch.setattr(main.asyncio, "gather", fake_gather)
    monkeypatch.setattr(main.asyncio, "sleep", fake_sleep)

    with pytest.raises(_StopAutomationLoop):
        await main._automation_loop()

    assert "process_recurring_invoices" in scheduled_names


@pytest.mark.asyncio
async def test_automation_loop_skips_work_when_lock_is_not_acquired(monkeypatch):
    """A worker that misses the DB lease must not execute scheduler work."""
    import backend.main as main

    scheduled_names = []
    sleep_calls = 0

    async def fake_safe_run(name, fn, timeout=30.0):
        scheduled_names.append(name)
        return 0

    async def fake_sleep(seconds):
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls >= 2:
            raise _StopAutomationLoop()
        return None

    monkeypatch.setattr(main, "_safe_run", fake_safe_run)
    monkeypatch.setattr(main, "_try_acquire_automation_lock", lambda lock_name: False)
    monkeypatch.setattr(main, "_release_automation_lock", lambda lock_name: None)
    monkeypatch.setattr(main.asyncio, "sleep", fake_sleep)

    with pytest.raises(_StopAutomationLoop):
        await main._automation_loop()

    assert scheduled_names == []
