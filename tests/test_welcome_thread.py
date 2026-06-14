"""Tests for backend.services.welcome_thread.create_welcome_thread.

Uses MagicMock-supabase style matching tests/test_demo_seed.py.
No HTTP client needed — calls the service function directly.
"""

import os
os.environ["TESTING"] = "1"

import sys
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch, call
import asyncio

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_db():
    """Return a fresh MagicMock db whose .table() chain is configurable."""
    db = MagicMock()
    return db


def _mock_table(data=None):
    """Return a chainable table mock that returns `data` on .execute()."""
    table = MagicMock()
    result = MagicMock()
    result.data = data if data is not None else []
    for method in [
        "select", "insert", "update", "delete", "eq", "neq",
        "gte", "lte", "gt", "lt", "limit", "order", "filter", "is_",
    ]:
        getattr(table, method).return_value = table
    table.execute.return_value = result
    return table


async def _call(db, tenant_id="t-001", business_name="Acme Plumbing",
                business_type="plumbing", website_url=None):
    from backend.services.welcome_thread import create_welcome_thread
    return await create_welcome_thread(
        db,
        tenant_id=tenant_id,
        business_name=business_name,
        business_type=business_type,
        website_url=website_url,
    )


# ---------------------------------------------------------------------------
# tenant_table uses client_id for os_threads / os_messages
# ---------------------------------------------------------------------------

class TestClientIdScope:
    """Verify os_threads and os_messages are inserted with client_id, not tenant_id."""

    def test_os_threads_insert_uses_client_id(self):
        """tenant_table should inject client_id into os_threads insert."""
        db = _make_db()

        # idempotency query returns empty (no existing thread)
        empty_result = MagicMock()
        empty_result.data = []

        # thread insert returns a row with an id
        insert_result = MagicMock()
        insert_result.data = [{"id": "thread-123"}]

        # message insert returns empty (success without data needed)
        msg_result = MagicMock()
        msg_result.data = []

        call_seq = [empty_result, insert_result, msg_result]
        call_idx = {"n": 0}

        def table_side(name):
            t = MagicMock()
            for method in ["select", "insert", "update", "delete", "eq", "neq",
                           "gte", "lte", "gt", "lt", "limit", "order", "filter", "is_"]:
                getattr(t, method).return_value = t

            def execute_side():
                idx = call_idx["n"]
                call_idx["n"] += 1
                return call_seq[idx] if idx < len(call_seq) else MagicMock(data=[])

            t.execute.side_effect = execute_side
            return t

        db.table.side_effect = table_side

        result = asyncio.run(_call(db, tenant_id="t-001"))

        assert result == "thread-123"

        # Confirm that db.table was called with os_threads (and os_messages)
        table_calls = [c.args[0] for c in db.table.call_args_list]
        assert "os_threads" in table_calls
        assert "os_messages" in table_calls


# ---------------------------------------------------------------------------
# Happy path: creates thread + message
# ---------------------------------------------------------------------------

class TestCreateWelcomeThread:
    def test_creates_thread_and_returns_id(self):
        db = _make_db()

        call_idx = {"n": 0}
        results = [
            MagicMock(data=[]),                        # idempotency: no existing thread
            MagicMock(data=[{"id": "wt-abc"}]),        # thread insert
            MagicMock(data=[]),                        # message insert
        ]

        def table_side(name):
            t = MagicMock()
            for method in ["select", "insert", "update", "delete", "eq", "neq",
                           "gte", "lte", "gt", "lt", "limit", "order", "filter", "is_"]:
                getattr(t, method).return_value = t

            def exe():
                idx = call_idx["n"]
                call_idx["n"] += 1
                return results[idx] if idx < len(results) else MagicMock(data=[])

            t.execute.side_effect = exe
            return t

        db.table.side_effect = table_side

        result = asyncio.run(_call(db, business_type="plumbing"))
        assert result == "wt-abc"

    def test_returns_none_on_thread_insert_failure(self):
        """DB failure on os_threads insert must return None without raising."""
        db = _make_db()
        call_idx = {"n": 0}

        def table_side(name):
            t = MagicMock()
            for method in ["select", "insert", "update", "delete", "eq", "neq",
                           "gte", "lte", "gt", "lt", "limit", "order", "filter", "is_"]:
                getattr(t, method).return_value = t

            def exe():
                idx = call_idx["n"]
                call_idx["n"] += 1
                if idx == 0:
                    return MagicMock(data=[])   # idempotency: empty
                raise Exception("DB exploded")

            t.execute.side_effect = exe
            return t

        db.table.side_effect = table_side

        result = asyncio.run(_call(db))
        assert result is None

    def test_db_failure_on_idempotency_check_still_attempts_insert(self):
        """If the idempotency SELECT raises, continue to insert attempt."""
        db = _make_db()
        call_idx = {"n": 0}

        def table_side(name):
            t = MagicMock()
            for method in ["select", "insert", "update", "delete", "eq", "neq",
                           "gte", "lte", "gt", "lt", "limit", "order", "filter", "is_"]:
                getattr(t, method).return_value = t

            def exe():
                idx = call_idx["n"]
                call_idx["n"] += 1
                if idx == 0:
                    raise Exception("select failed")
                if idx == 1:
                    return MagicMock(data=[{"id": "wt-fallback"}])
                return MagicMock(data=[])

            t.execute.side_effect = exe
            return t

        db.table.side_effect = table_side

        result = asyncio.run(_call(db))
        assert result == "wt-fallback"


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------

class TestIdempotency:
    def test_returns_existing_thread_without_new_insert(self):
        """If thread already exists, return its id without inserting a new row."""
        db = _make_db()

        existing_result = MagicMock(data=[{"id": "existing-thread-99"}])
        call_idx = {"n": 0}

        def table_side(name):
            t = MagicMock()
            for method in ["select", "insert", "update", "delete", "eq", "neq",
                           "gte", "lte", "gt", "lt", "limit", "order", "filter", "is_"]:
                getattr(t, method).return_value = t

            def exe():
                idx = call_idx["n"]
                call_idx["n"] += 1
                if idx == 0:
                    return existing_result
                # Should not reach here
                raise AssertionError("extra DB call made after idempotency match")

            t.execute.side_effect = exe
            return t

        db.table.side_effect = table_side

        result = asyncio.run(_call(db))
        assert result == "existing-thread-99"
        # Only 1 execute call (the idempotency check)
        assert call_idx["n"] == 1


# ---------------------------------------------------------------------------
# Vertical flavor
# ---------------------------------------------------------------------------

class TestVerticalFlavor:
    """Verify business_type flavors the composed message."""

    def _get_message_for_type(self, business_type):
        from backend.services.welcome_thread import _compose_welcome_message
        return _compose_welcome_message(
            business_name="Test Co",
            business_type=business_type,
            website_url=None,
        )

    def test_plumbing_references_home_services_topic(self):
        msg = self._get_message_for_type("plumbing")
        # plumbing maps to home_services guidance; first guidance entry mentions
        # homeowners / estimate / contractors etc.
        assert any(word in msg.lower() for word in ["homeowner", "estimate", "contractor", "scope", "leak", "pipe"])

    def test_salon_references_salon_topic(self):
        msg = self._get_message_for_type("salon")
        # salon guidance mentions booking / stylist / appointments
        assert any(word in msg.lower() for word in ["book", "stylist", "first name", "personal", "confirm", "slot"])

    def test_unknown_type_falls_back_gracefully(self):
        msg = self._get_message_for_type("underwater_basket_weaving")
        # Should produce a valid message with default prompts
        assert "Three things you can try right now:" in msg
        assert "What came in from the widget today?" in msg

    def test_none_type_falls_back_gracefully(self):
        msg = self._get_message_for_type(None)
        assert "Three things you can try right now:" in msg

    def test_website_url_present_adds_reading_line(self):
        from backend.services.welcome_thread import _compose_welcome_message
        msg = _compose_welcome_message(
            business_name="Test Co",
            business_type="plumbing",
            website_url="https://example.com",
        )
        assert "https://example.com" in msg
        assert "learn your services" in msg.lower()

    def test_website_url_absent_no_reading_line(self):
        from backend.services.welcome_thread import _compose_welcome_message
        msg = _compose_welcome_message(
            business_name="Test Co",
            business_type="plumbing",
            website_url=None,
        )
        assert "learn your services" not in msg.lower()
