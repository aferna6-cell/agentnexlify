"""Unit tests for calls._find_tenant_by_phone (G3 Phase 2 routing).

Contract: exact indexed match on tenants.twilio_number wins; the legacy
suffix scan against notification_phone (and twilio_number) only runs as a
fallback, so pre-migration tenants keep routing. Never raises into the
webhook path.
"""

from unittest.mock import MagicMock, patch

from backend.routers import calls

TENANT = {
    "id": "t-1",
    "business_name": "Exact Match Co",
    "twilio_number": "+15550001111",
    "notification_phone": "+15559998888",
}


def _result(rows):
    r = MagicMock()
    r.data = rows
    return r


def _db(exact_rows, scan_rows, exact_raises=False):
    """table("tenants") twice: exact (.eq.limit) then scan (.limit)."""
    db = MagicMock()

    def table(_name):
        chain = MagicMock()
        if exact_raises:
            chain.select.return_value.eq.return_value.limit.return_value.execute.side_effect = (
                RuntimeError("index offline")
            )
        else:
            chain.select.return_value.eq.return_value.limit.return_value.execute.return_value = _result(
                exact_rows
            )
        chain.select.return_value.limit.return_value.execute.return_value = _result(scan_rows)
        return chain

    db.table.side_effect = table
    return db


def test_exact_twilio_number_match_wins():
    db = _db(exact_rows=[TENANT], scan_rows=[])
    with patch.object(calls, "get_service_supabase", return_value=db):
        found = calls._find_tenant_by_phone("+15550001111")
    assert found["id"] == "t-1"


def test_exact_miss_falls_back_to_notification_phone_suffix():
    legacy = {**TENANT, "twilio_number": None}
    db = _db(exact_rows=[], scan_rows=[legacy])
    with patch.object(calls, "get_service_supabase", return_value=db):
        found = calls._find_tenant_by_phone("+1 555-999-8888")
    assert found["id"] == "t-1"


def test_scan_also_matches_twilio_number_suffix():
    row = {**TENANT, "notification_phone": None}
    db = _db(exact_rows=[], scan_rows=[row])
    with patch.object(calls, "get_service_supabase", return_value=db):
        found = calls._find_tenant_by_phone("+1 555-000-1111")
    assert found["id"] == "t-1"


def test_no_match_returns_none():
    db = _db(exact_rows=[], scan_rows=[TENANT])
    with patch.object(calls, "get_service_supabase", return_value=db):
        assert calls._find_tenant_by_phone("+15551234567") is None


def test_exact_lookup_error_degrades_to_scan():
    db = _db(exact_rows=[], scan_rows=[TENANT], exact_raises=True)
    with patch.object(calls, "get_service_supabase", return_value=db):
        found = calls._find_tenant_by_phone("+15559998888")
    assert found["id"] == "t-1"
