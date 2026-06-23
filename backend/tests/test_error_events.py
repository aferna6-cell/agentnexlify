"""Tests for backend/services/error_events.py.

Run with:
    .venv/bin/python -m pytest backend/tests/test_error_events.py --noconftest

Design goals:
- Mock supabase so no live DB call is made.
- Verify the happy path inserts the expected row shape.
- Verify that a DB insert failure is swallowed and never raises to the caller.
"""

import importlib
import sys
import types
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_supabase():
    """Return a mock supabase client whose table().insert().execute() works."""
    mock_execute = MagicMock(return_value=MagicMock(data=[{"id": "fake-uuid"}]))
    mock_insert = MagicMock(return_value=MagicMock(execute=mock_execute))
    mock_table = MagicMock(return_value=MagicMock(insert=mock_insert))
    mock_client = MagicMock()
    mock_client.table = mock_table
    return mock_client, mock_table, mock_insert, mock_execute


def _reload_module():
    """Reload error_events so each test starts with a clean module state."""
    mod_name = "backend.services.error_events"
    if mod_name in sys.modules:
        del sys.modules[mod_name]
    return importlib.import_module(mod_name)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRecordErrorEventHappyPath:
    """record_error_event inserts the expected row when supabase works."""

    def test_inserts_expected_fields(self):
        mock_client, mock_table, mock_insert, mock_execute = _make_mock_supabase()

        with patch(
            "backend.models.database.get_service_supabase",
            return_value=mock_client,
        ):
            mod = _reload_module()
            exc = ValueError("something broke")

            mod.record_error_event(
                message="something broke",
                level="error",
                source="api",
                path="/api/v1/widget/chat",
                status_code=500,
                exc=exc,
                context={"method": "POST"},
            )

        mock_table.assert_called_once_with("error_events")
        insert_call_args = mock_insert.call_args
        assert insert_call_args is not None, "insert() was not called"

        row = insert_call_args[0][0]
        assert row["level"] == "error"
        assert row["source"] == "api"
        assert row["message"] == "something broke"
        assert row["path"] == "/api/v1/widget/chat"
        assert row["status_code"] == 500
        assert row["context"] == {"method": "POST"}
        # Stack should contain the traceback
        assert row["stack"] is not None
        assert "ValueError" in row["stack"]

        # execute() must have been called
        mock_execute.assert_called_once()

    def test_no_exc_inserts_null_stack(self):
        mock_client, mock_table, mock_insert, _ = _make_mock_supabase()

        with patch(
            "backend.models.database.get_service_supabase",
            return_value=mock_client,
        ):
            mod = _reload_module()
            mod.record_error_event(message="manual error", source="automation")

        row = mock_insert.call_args[0][0]
        assert row["stack"] is None
        assert row["message"] == "manual error"
        assert row["source"] == "automation"

    def test_minimal_call_does_not_raise(self):
        mock_client, _, _, _ = _make_mock_supabase()

        with patch(
            "backend.models.database.get_service_supabase",
            return_value=mock_client,
        ):
            mod = _reload_module()
            # Should not raise with only message supplied
            mod.record_error_event(message="bare minimum")


class TestRecordErrorEventSwallowsDBFailure:
    """record_error_event never raises even when the DB insert fails."""

    def test_swallows_execute_exception(self):
        mock_execute = MagicMock(side_effect=RuntimeError("DB is down"))
        mock_insert = MagicMock(return_value=MagicMock(execute=mock_execute))
        mock_table = MagicMock(return_value=MagicMock(insert=mock_insert))
        mock_client = MagicMock()
        mock_client.table = mock_table

        with patch(
            "backend.models.database.get_service_supabase",
            return_value=mock_client,
        ):
            mod = _reload_module()
            # This must not raise
            mod.record_error_event(message="will fail silently", exc=ValueError("x"))

    def test_swallows_get_service_supabase_exception(self):
        with patch(
            "backend.models.database.get_service_supabase",
            side_effect=RuntimeError("no supabase config"),
        ):
            mod = _reload_module()
            # This must not raise
            mod.record_error_event(message="no client available")

    def test_swallows_table_exception(self):
        mock_client = MagicMock()
        mock_client.table.side_effect = Exception("unexpected table error")

        with patch(
            "backend.models.database.get_service_supabase",
            return_value=mock_client,
        ):
            mod = _reload_module()
            mod.record_error_event(message="table access fails")
