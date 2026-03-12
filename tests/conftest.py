"""Shared test fixtures for AgentNexLiFy tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


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
