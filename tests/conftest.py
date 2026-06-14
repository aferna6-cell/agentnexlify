"""Shared test fixtures for AgentNexLiFy tests."""

import os
import sys

os.environ["TESTING"] = "1"
# JWT secret used by all test modules (`_TEST_SECRET = "test-secret-key-for-jwt"`).
# Set before backend.config imports so pydantic-settings picks it up at load time.
# Without this, _jwt_secret() returns "" when tests patch backend.routers.auth.settings
# (wrong target — auth_service reads backend.config.settings directly), causing 401.
os.environ.setdefault("API_SECRET_KEY", "test-secret-key-for-jwt")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-jwt")
os.environ.setdefault("ADMIN_API_SECRET_KEY", "test-admin-secret-key-for-jwt")
from pathlib import Path
from unittest.mock import MagicMock, patch

import asyncio
import httpx
import fastapi.testclient as fastapi_testclient
import pytest
import starlette.background as starlette_background
import starlette.concurrency as starlette_concurrency
import starlette.testclient as starlette_testclient

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_REAL_ASGI_TRANSPORT = httpx.ASGITransport
_REAL_ASYNC_CLIENT = httpx.AsyncClient


class SyncASGITestClient:
    """Drop-in test client for environments where Starlette TestClient stalls."""
    __test__ = False

    def __init__(
        self,
        app,
        base_url="http://testserver",
        raise_server_exceptions=True,
        **_,
    ):
        self.app = app
        self.base_url = base_url
        self.raise_server_exceptions = raise_server_exceptions

    async def _request(self, method, url, **kwargs):
        transport = _REAL_ASGI_TRANSPORT(
            app=self.app,
            raise_app_exceptions=self.raise_server_exceptions,
        )
        async with _REAL_ASYNC_CLIENT(
            transport=transport,
            base_url=self.base_url,
        ) as client:
            return await client.request(method, url, **kwargs)

    def request(self, method, url, **kwargs):
        return asyncio.run(self._request(method, url, **kwargs))

    def get(self, url, **kwargs):
        return self.request("GET", url, **kwargs)

    def post(self, url, **kwargs):
        return self.request("POST", url, **kwargs)

    def put(self, url, **kwargs):
        return self.request("PUT", url, **kwargs)

    def patch(self, url, **kwargs):
        return self.request("PATCH", url, **kwargs)

    def delete(self, url, **kwargs):
        return self.request("DELETE", url, **kwargs)

    def options(self, url, **kwargs):
        return self.request("OPTIONS", url, **kwargs)

    def head(self, url, **kwargs):
        return self.request("HEAD", url, **kwargs)

    def close(self):
        return None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


fastapi_testclient.TestClient = SyncASGITestClient
starlette_testclient.TestClient = SyncASGITestClient


async def _run_threadpool_inline(func, *args, **kwargs):
    return func(*args, **kwargs)


async def _skip_background_tasks(self):
    return None


@pytest.fixture(autouse=True)
def _stable_asgi_test_execution(monkeypatch):
    """Keep ASGI response tests deterministic in the local sandbox.

    The installed async stack can stall while waiting for threadpool wakeups,
    and ASGITransport waits for Starlette BackgroundTasks before returning.
    Unit tests cover the background callables directly, so response-level
    tests skip task execution and inline explicitly patched threadpool work.
    """
    monkeypatch.setattr(
        starlette_background,
        "run_in_threadpool",
        _run_threadpool_inline,
    )
    monkeypatch.setattr(
        starlette_concurrency,
        "run_in_threadpool",
        _run_threadpool_inline,
    )
    monkeypatch.setattr(
        starlette_background.BackgroundTasks,
        "__call__",
        _skip_background_tasks,
    )
    import fastapi.concurrency as fastapi_concurrency
    from backend.routers import managed_agent_runs

    monkeypatch.setattr(
        fastapi_concurrency,
        "run_in_threadpool",
        _run_threadpool_inline,
    )
    monkeypatch.setattr(
        managed_agent_runs,
        "run_in_threadpool",
        _run_threadpool_inline,
    )


class MockSupabaseResponse:
    """Mock Supabase query response."""

    def __init__(self, data=None, count=None):
        self.data = data or []
        self.count = count


class MockSupabaseTable:
    """Mock Supabase table with chainable query methods."""

    def __init__(self, data=None, count=None):
        self._data = data or []
        self._count = count

    def select(self, *args, **kwargs):
        return self

    def insert(self, data):
        # Return the inserted data with a fake id
        if isinstance(data, dict):
            result = {"id": "test-uuid-001", **data}
            self._data = [result]
        return self

    def update(self, data):
        return self

    def delete(self):
        return self

    def eq(self, *args):
        return self

    def neq(self, *args):
        return self

    def gte(self, *args):
        return self

    def lte(self, *args):
        return self

    def limit(self, *args):
        return self

    def order(self, *args, **kwargs):
        return self

    def in_(self, *args):
        return self

    def or_(self, *args):
        return self

    def range(self, *args):
        return self

    def not_(self):
        return self

    def is_(self, *args):
        return self

    def lt(self, *args):
        return self

    def gt(self, *args):
        return self

    def execute(self):
        return MockSupabaseResponse(data=self._data, count=self._count)


class MockSupabaseClient:
    """Mock Supabase client that returns configurable table data."""

    def __init__(self):
        self._tables = {}

    def set_table_data(self, table_name, data, count=None):
        self._tables[table_name] = (data, count)

    def table(self, name):
        data, count = self._tables.get(name, ([], None))
        return MockSupabaseTable(data=data, count=count)


@pytest.fixture
def mock_supabase():
    """Provide a mock Supabase client and patch get_supabase."""
    client = MockSupabaseClient()
    with patch("backend.models.database.get_supabase", return_value=client):
        yield client


async def _allow_marketing_access_for_tests():
    return {
        "tenant_id": "test-tenant",
        "email": "test@example.com",
        "role": "owner",
        "plan": "professional",
        "is_team_member": False,
    }


@pytest.fixture(autouse=True)
def _allow_marketing_addon_gate_for_endpoint_tests():
    """Keep marketing endpoint tests focused on endpoint behavior.

    The plan gate (require_marketing_access — replaced the retired add-on
    gate 2026-06-10) has dedicated tests; broad router tests should not need
    real Supabase state just to enter the endpoint under test.
    """
    from backend.main import app
    from backend.services.plan_gate import require_marketing_access

    sentinel = object()
    previous = app.dependency_overrides.get(require_marketing_access, sentinel)
    app.dependency_overrides[require_marketing_access] = _allow_marketing_access_for_tests
    try:
        yield
    finally:
        if previous is sentinel:
            app.dependency_overrides.pop(require_marketing_access, None)
        else:
            app.dependency_overrides[require_marketing_access] = previous


@pytest.fixture(autouse=True)
def _clear_widget_cache():
    """Clear the widget module's in-memory cache between tests to prevent contamination."""
    yield
    try:
        from backend.routers.widget_chat_helpers import _cache
        _cache.clear()
    except Exception:
        pass


@pytest.fixture
def mock_settings():
    """Patch settings with test values."""
    with patch("backend.config.settings") as mock:
        mock.api_secret_key = "test-secret-key-for-jwt"
        mock.anthropic_api_key = "test-anthropic-key"
        mock.supabase_url = "https://test.supabase.co"
        mock.supabase_key = "test-supabase-key"
        mock.frontend_url = "http://localhost:5173"
        mock.twilio_account_sid = "test-sid"
        mock.twilio_auth_token = "test-token"
        mock.twilio_phone_number = "+15550000000"
        mock.resend_api_key = "test-resend"
        mock.sentry_dsn = None
        yield mock
