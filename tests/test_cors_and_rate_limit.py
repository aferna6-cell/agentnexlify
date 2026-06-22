"""Tests for CORS configuration, rate limiting, and automation sequences.

Validates that:
- CORS headers are returned correctly for allowed and disallowed origins
- Rate limiting is configured on key endpoints
- Automation sequence CRUD works with templates and stats
"""

import os
os.environ["TESTING"] = "1"

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def test_client(mock_settings):
    """Create a FastAPI TestClient with mocked Supabase everywhere."""
    mock_settings.sentry_dsn = None
    mock_settings.supabase_service_key = "fake-key"

    # Patch get_supabase in every module that imports it
    db_mock = MagicMock()
    patches = [
        patch("backend.models.database.get_supabase", return_value=db_mock),
        patch("backend.routers.auth.get_service_supabase", return_value=db_mock),
        patch("backend.routers.auth.settings", mock_settings),
        patch("backend.routers.widget_chat.get_service_supabase", return_value=db_mock),
        patch("backend.routers.widget_config.get_service_supabase", return_value=db_mock),
        patch("backend.routers.widget_lead.get_service_supabase", return_value=db_mock),
        patch("backend.routers.widget_booking.get_service_supabase", return_value=db_mock),
        patch("backend.routers.widget_chat_helpers.get_service_supabase", return_value=db_mock),
        patch("backend.routers.sequences.get_service_supabase", return_value=db_mock),
    ]
    for p in patches:
        p.start()

    # Clear widget cache to avoid state leaking between tests
    from backend.routers.widget_chat_helpers import _cache
    _cache.clear()

    from backend.main import app
    from fastapi.testclient import TestClient
    client = TestClient(app)

    yield client, db_mock

    for p in patches:
        p.stop()


def _setup_table_mock(db_mock, table_responses):
    """Configure db_mock.table() to return different data per table name.

    table_responses: dict of {table_name: [list of response dicts]}
    Supports chained calls: .select().eq().limit().execute()
    If the value for a table name is a list of lists, each successive call
    to that table name returns the next list (multi-call support).
    """
    call_counts = {}

    def mock_table(name):
        call_counts.setdefault(name, 0)
        call_counts[name] += 1

        table = MagicMock()
        data = table_responses.get(name, [])

        # Multi-call support: list of lists
        if data and isinstance(data[0], list):
            idx = min(call_counts[name] - 1, len(data) - 1)
            current_data = data[idx]
        else:
            current_data = data

        # Make all chainable methods return the same mock
        for method in [
            "select", "insert", "update", "delete", "eq", "neq",
            "gte", "lte", "gt", "lt", "limit", "order", "ilike",
            "in_", "is_", "or_", "contains",
        ]:
            getattr(table, method).return_value = table

        # Execute returns the data
        result = MagicMock()
        result.data = current_data
        result.count = len(current_data) if current_data else 0
        table.execute.return_value = result

        return table

    db_mock.table = mock_table


def _make_jwt(tenant_id="test-tenant-001", role="owner"):
    """Create a valid JWT token for test requests."""
    from backend.routers.auth import _create_token
    return _create_token(
        tenant_id=tenant_id,
        email="test@example.com",
        plan="growth",
        business_name="Test Business",
        role=role,
    )


# ===========================================================================
# Test Group 1: CORS
# ===========================================================================


class TestCORS:
    """Verify CORSMiddleware configuration in main.py.

    The app uses allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
    allow_credentials=False. This means ALL origins are allowed (because the
    widget is embedded on arbitrary customer websites).
    """

    def test_cors_allowed_origin(self, test_client):
        """A request with any Origin header should get Access-Control-Allow-Origin back."""
        client, db_mock = test_client

        response = client.get(
            "/health",
            headers={"Origin": "https://customer-website.com"},
        )
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers
        assert response.headers["access-control-allow-origin"] == "*"

    def test_cors_disallowed_origin(self, test_client):
        """With allow_origins=['*'], even unusual origins still get the wildcard header.

        This test documents the current behavior: since CORS is set to '*',
        there are no truly disallowed origins at the middleware level.
        Per-widget domain restrictions are enforced in widget.py:_check_origin().
        """
        client, db_mock = test_client

        response = client.get(
            "/health",
            headers={"Origin": "https://evil-domain.example.com"},
        )
        assert response.status_code == 200
        # With allow_origins=["*"], the middleware returns "*" for all origins
        assert response.headers.get("access-control-allow-origin") == "*"

    def test_cors_preflight(self, test_client):
        """OPTIONS preflight to /api/v1/widget/chat should return CORS headers."""
        client, db_mock = test_client

        response = client.options(
            "/api/v1/widget/chat",
            headers={
                "Origin": "https://customer-website.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
        # Preflight returns 200
        assert response.status_code == 200
        # Must include CORS headers
        assert "access-control-allow-origin" in response.headers
        assert response.headers["access-control-allow-origin"] == "*"
        assert "access-control-allow-methods" in response.headers
        # POST must be allowed
        allowed_methods = response.headers["access-control-allow-methods"]
        assert "POST" in allowed_methods or "*" in allowed_methods


# ===========================================================================
# Test Group 2: Rate Limiting
# ===========================================================================


class TestRateLimiting:
    """Verify that slowapi rate limiting is configured on key endpoints.

    The app uses slowapi's @limiter.limit() decorator on route functions.
    headers_enabled is False (default), so we verify configuration by
    inspecting the limiter's internal _route_limits registry rather than
    checking HTTP response headers.
    """

    def test_rate_limit_header_present(self, test_client):
        """Verify that a rate-limited endpoint (support/contact) has its limit
        registered in slowapi's limiter._route_limits registry."""
        _client, _db_mock = test_client

        from backend.limiter import limiter

        # The support/contact endpoint is decorated with @limiter.limit("5/minute")
        key = "backend.routers.support.submit_contact"
        assert key in limiter._route_limits, (
            f"Expected '{key}' to be registered in limiter._route_limits. "
            f"Registered keys: {list(limiter._route_limits.keys())}"
        )
        limit_obj = limiter._route_limits[key][0]
        limit_str = str(limit_obj.limit)
        assert "5 per 1 minute" in limit_str, (
            f"Expected '5 per 1 minute' but got '{limit_str}'"
        )

    def test_rate_limit_widget_chat(self, test_client):
        """Verify the /api/v1/widget/chat endpoint has dynamic per-tier rate
        limiting registered in slowapi's limiter._dynamic_route_limits.

        steal-list 1-6 (commit b0b1fb4) replaced the static "60/minute" decorator
        with @limiter.limit(_chat_rate_limit, ...) where _chat_rate_limit is a
        callable that resolves the tenant's plan tier per request. slowapi
        registers callable limits in `_dynamic_route_limits` (separate registry
        from `_route_limits` which holds string-literal limits).
        """
        _client, _db_mock = test_client

        from backend.limiter import limiter
        from backend.middleware.rate_limit import get_tier_limit

        key = "backend.routers.widget_chat.widget_chat"
        dyn = getattr(limiter, "_dynamic_route_limits", {})
        assert key in dyn, (
            f"Expected '{key}' to be registered in limiter._dynamic_route_limits. "
            f"Registered keys: {list(dyn.keys())}"
        )
        # Verify the per-tier resolver returns sane defaults for each plan
        for tier, expected_rpm in [
            ("free", 30),
            ("chatbot", 120),
            ("agent_os", 480),
            ("growth", 120),
            ("autopilot", 240),
            ("professional", 480),
            ("enterprise", 1200),
        ]:
            assert get_tier_limit(tier) == f"{expected_rpm}/minute", (
                f"Tier '{tier}' expected {expected_rpm}/minute, "
                f"got {get_tier_limit(tier)}"
            )

    def test_rate_limit_current_plans(self, test_client):
        """Every current paid plan must resolve to a cap ABOVE the free tier.

        Regression for the silent-throttle bug: chatbot/agent_os had no entry in
        _TIER_DEFAULTS, so get_tier_limit() fell back to free (30 rpm) — a paying
        agent_os tenant was rate-limited like a free one. Tied to plan_catalog so
        the next repricing that adds a plan can't reintroduce the fallback.
        """
        _client, _db_mock = test_client

        from backend.middleware.rate_limit import get_tier_limit, _TIER_DEFAULTS
        from backend.services.plan_catalog import CURRENT_PAID_PLANS

        free_rpm = _TIER_DEFAULTS["free"]
        for plan in sorted(CURRENT_PAID_PLANS):
            assert plan in _TIER_DEFAULTS, (
                f"Current paid plan '{plan}' missing from _TIER_DEFAULTS — it "
                f"would silently fall back to the free {free_rpm} rpm cap."
            )
            rpm = int(get_tier_limit(plan).split("/")[0])
            assert rpm > free_rpm, (
                f"Current paid plan '{plan}' resolves to {rpm}/minute, not above "
                f"the free {free_rpm}/minute cap."
            )

    def test_chat_rate_limit_signature_contract(self, test_client):
        """Lock the slowapi calling convention for _chat_rate_limit.

        slowapi/wrappers.py:86-94 calls callable limit providers with NO args
        if the signature has no `key` param, OR with key_function(request) if
        the signature DOES include `key`. A signature like (request) raises
        TypeError on every request — production 500.

        This test calls the function directly with the api_key string (matching
        slowapi's calling convention) and asserts a valid limit string returns.
        It will fail loudly if anyone reverts to (request) or any other shape.
        """
        _client, _db_mock = test_client

        import inspect
        from backend.routers.widget_chat import _chat_rate_limit

        sig = inspect.signature(_chat_rate_limit)
        params = list(sig.parameters.keys())
        assert params == ["key"], (
            f"_chat_rate_limit must take exactly one param named 'key' "
            f"(slowapi convention). Got params: {params}. See "
            f"slowapi/wrappers.py:86-94."
        )

        # Direct call with an unknown key must fall back to free tier (30/min)
        # without raising. Exception → free fallback is the documented contract.
        result = _chat_rate_limit("nonexistent-api-key-xyz")
        assert result == "30/minute", (
            f"Free-tier fallback expected '30/minute', got '{result}'"
        )


# ===========================================================================
# Test Group 3: Automation Sequences
# ===========================================================================


class TestAutomationSequences:
    """Test automation sequence endpoints from backend/routers/sequences.py."""

    def test_create_sequence_from_template(self, test_client):
        """POST /{tenant_id}/templates with template_id='welcome' creates a sequence."""
        client, db_mock = test_client
        tenant_id = "test-tenant-001"

        _setup_table_mock(db_mock, {
            "automation_sequences": [
                {
                    "id": "seq-001",
                    "tenant_id": tenant_id,
                    "name": "Welcome Email Series",
                    "trigger_event": "new_lead",
                    "trigger_config": {},
                    "is_active": True,
                    "created_at": "2026-03-15T00:00:00Z",
                }
            ],
            "automation_steps": [{"id": "step-001"}, {"id": "step-002"}],
        })

        token = _make_jwt(tenant_id=tenant_id, role="owner")
        response = client.post(
            f"/api/v1/sequences/{tenant_id}/templates",
            json={"template_id": "welcome"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "sequence" in data
        assert data["sequence"]["name"] == "Welcome Email Series"
        assert data["steps_created"] == 2  # welcome template has 2 steps

    def test_list_sequences_with_stats(self, test_client):
        """GET /{tenant_id} returns sequences with step_count, total_enrolled, active_count."""
        client, db_mock = test_client
        tenant_id = "test-tenant-001"

        seq_id = "seq-001"
        _setup_table_mock(db_mock, {
            "automation_sequences": [
                {
                    "id": seq_id,
                    "tenant_id": tenant_id,
                    "name": "Welcome Email Series",
                    "trigger_event": "new_lead",
                    "is_active": True,
                    "created_at": "2026-03-15T00:00:00Z",
                }
            ],
            "automation_steps": [
                {"sequence_id": seq_id},
                {"sequence_id": seq_id},
                {"sequence_id": seq_id},
            ],
            "automation_executions": [
                {"sequence_id": seq_id, "status": "in_progress"},
                {"sequence_id": seq_id, "status": "completed"},
                {"sequence_id": seq_id, "status": "in_progress"},
            ],
        })

        token = _make_jwt(tenant_id=tenant_id, role="owner")
        response = client.get(
            f"/api/v1/sequences/{tenant_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "sequences" in data
        assert len(data["sequences"]) == 1

        seq = data["sequences"][0]
        assert seq["step_count"] == 3
        assert seq["total_enrolled"] == 3
        assert seq["active_count"] == 2
        assert seq["completed_count"] == 1
