"""Unit tests for voice_phone_routing._find_tenant_by_phone (G3 Phase 2 routing).

Contract: exact indexed match on tenants.twilio_number wins; the legacy
suffix scan against notification_phone (and twilio_number) only runs as a
fallback, so pre-migration tenants keep routing. Never raises into the
webhook path.
"""

from unittest.mock import MagicMock, patch

from backend.services import voice_phone_routing

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


def _db(exact_rows, scan_pages, exact_raises=False):
    """table("tenants") queries: exact (.eq.limit) then a paginated scan (.range).

    scan_pages: list of page row-lists returned by successive .range() calls.
    The scan switched from a single silently-capped .limit(200) to .range()
    pagination (audit 2026-07-14 L4) so tenants past row 200 stay routable;
    this harness models that paginated contract.
    """
    db = MagicMock()
    # ONE shared iterator across table() calls — the scan fetches each page
    # via a fresh db.table() chain, so a per-chain side_effect list would
    # replay page 1 forever. Exhausted iterator returns an empty page, which
    # terminates the scan loop.
    pages_iter = iter([_result(rows) for rows in scan_pages])

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
        chain.select.return_value.range.return_value.execute.side_effect = (
            lambda: next(pages_iter, _result([]))
        )
        return chain

    db.table.side_effect = table
    return db


def test_exact_twilio_number_match_wins():
    db = _db(exact_rows=[TENANT], scan_pages=[[]])
    with patch.object(voice_phone_routing, "get_service_supabase", return_value=db):
        found = voice_phone_routing._find_tenant_by_phone("+15550001111")
    assert found["id"] == "t-1"


def test_exact_miss_falls_back_to_notification_phone_suffix():
    legacy = {**TENANT, "twilio_number": None}
    db = _db(exact_rows=[], scan_pages=[[legacy]])
    with patch.object(voice_phone_routing, "get_service_supabase", return_value=db):
        found = voice_phone_routing._find_tenant_by_phone("+1 555-999-8888")
    assert found["id"] == "t-1"


def test_scan_also_matches_twilio_number_suffix():
    row = {**TENANT, "notification_phone": None}
    db = _db(exact_rows=[], scan_pages=[[row]])
    with patch.object(voice_phone_routing, "get_service_supabase", return_value=db):
        found = voice_phone_routing._find_tenant_by_phone("+1 555-000-1111")
    assert found["id"] == "t-1"


def test_no_match_returns_none():
    db = _db(exact_rows=[], scan_pages=[[TENANT]])
    with patch.object(voice_phone_routing, "get_service_supabase", return_value=db):
        assert voice_phone_routing._find_tenant_by_phone("+15551234567") is None


def test_exact_lookup_error_degrades_to_scan():
    db = _db(exact_rows=[], scan_pages=[[TENANT]], exact_raises=True)
    with patch.object(voice_phone_routing, "get_service_supabase", return_value=db):
        found = voice_phone_routing._find_tenant_by_phone("+15559998888")
    assert found["id"] == "t-1"


def test_scan_paginates_past_first_page():
    """Regression for the silent 200-row cap (audit L4): a tenant whose row
    sits beyond the first scan page must still route. Page 1 is a full page
    of non-matching tenants; the match is on page 2."""
    filler = [
        {"id": f"f-{i}", "business_name": "x", "twilio_number": None,
         "notification_phone": f"+1444000{i:04d}"}
        for i in range(1000)  # full page -> loop must fetch the next page
    ]
    legacy = {**TENANT, "twilio_number": None}
    db = _db(exact_rows=[], scan_pages=[filler, [legacy]])
    with patch.object(voice_phone_routing, "get_service_supabase", return_value=db):
        found = voice_phone_routing._find_tenant_by_phone("+1 555-999-8888")
    assert found["id"] == "t-1"


def test_scan_query_error_returns_none():
    """A failing paginated scan degrades to no-match (never raises into the
    Twilio webhook path)."""
    db = MagicMock()

    def table(_name):
        chain = MagicMock()
        chain.select.return_value.eq.return_value.limit.return_value.execute.return_value = _result([])
        chain.select.return_value.range.return_value.execute.side_effect = RuntimeError("db down")
        return chain

    db.table.side_effect = table
    with patch.object(voice_phone_routing, "get_service_supabase", return_value=db):
        assert voice_phone_routing._find_tenant_by_phone("+15559998888") is None
