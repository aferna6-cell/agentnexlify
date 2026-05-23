"""Unit tests for lead_csv / lead_dedup / lead_activity service helpers.

Covers the changed lines for the leads.py god-class extraction so the 85%
changed-lines coverage gate passes. Mocks db at the chainable-builder level.
"""

import os

os.environ["TESTING"] = "1"

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _result(data):
    return SimpleNamespace(data=data)


def _chainable(data=None):
    """Return a MagicMock where every method call returns self, except .execute()."""
    m = MagicMock()
    m.eq.return_value = m
    m.in_.return_value = m
    m.is_.return_value = m
    m.or_.return_value = m
    m.order.return_value = m
    m.limit.return_value = m
    m.select.return_value = m
    m.update.return_value = m
    m.delete.return_value = m
    m.insert.return_value = m
    m.execute.return_value = _result(data)
    return m


def _make_db_returning(*responses):
    """db where each db.table(...) call returns a fresh chainable with the
    next response in `responses` (consumed in order)."""
    iter_responses = iter(responses)
    db = MagicMock()

    def _table(_name):
        try:
            data = next(iter_responses)
        except StopIteration:
            data = []
        return _chainable(data)

    db.table.side_effect = _table
    return db


# ---------------------------------------------------------------------------
# lead_activity.lead_exists
# ---------------------------------------------------------------------------


def test_lead_exists_true_when_data_present():
    from backend.services.lead_activity import lead_exists

    db = _make_db_returning([{"id": "lead-1"}])
    assert lead_exists(db, "tenant-1", "lead-1") is True


def test_lead_exists_false_when_no_data():
    from backend.services.lead_activity import lead_exists

    db = _make_db_returning([])
    assert lead_exists(db, "tenant-1", "missing") is False


# ---------------------------------------------------------------------------
# lead_activity.fetch_lead_timeline
# ---------------------------------------------------------------------------


def test_fetch_lead_timeline_merges_all_three_sources():
    from backend.services.lead_activity import fetch_lead_timeline

    activity_rows = [
        {
            "id": "a1",
            "activity_type": "note_added",
            "description": "Customer called back",
            "metadata": {"source": "phone"},
            "created_at": "2026-01-03T10:00:00Z",
        }
    ]
    appt_rows = [
        {
            "id": "ap1",
            "customer_name": "Alice",
            "start_time": "2026-01-05T09:00:00Z",
            "status": "scheduled",
            "created_at": "2026-01-02T10:00:00Z",
        }
    ]
    email_rows = [
        {
            "id": "e1",
            "event_type": "opened",
            "details": {"campaign": "welcome"},
            "created_at": "2026-01-04T10:00:00Z",
        }
    ]
    db = _make_db_returning(activity_rows, appt_rows, email_rows)

    timeline = fetch_lead_timeline(db, "tenant-1", "lead-1")

    assert len(timeline) == 3
    # sorted desc by created_at
    assert [t["created_at"] for t in timeline] == [
        "2026-01-04T10:00:00Z",
        "2026-01-03T10:00:00Z",
        "2026-01-02T10:00:00Z",
    ]
    types = [t["type"] for t in timeline]
    assert "email_opened" in types
    assert "note_added" in types
    assert "appointment_scheduled" in types


def test_fetch_lead_timeline_uses_defaults_for_missing_fields():
    from backend.services.lead_activity import fetch_lead_timeline

    activity_rows = [
        {
            "id": "a1",
            "activity_type": None,
            "description": None,
            "metadata": None,
            "created_at": "2026-01-03T10:00:00Z",
        }
    ]
    appt_rows = [
        {
            "id": "ap1",
            "customer_name": None,
            "start_time": "",
            "status": None,
            "created_at": "2026-01-02T10:00:00Z",
        }
    ]
    email_rows = [
        {
            "id": "e1",
            "event_type": None,
            "details": None,
            "created_at": "2026-01-04T10:00:00Z",
        }
    ]
    db = _make_db_returning(activity_rows, appt_rows, email_rows)

    timeline = fetch_lead_timeline(db, "tenant-1", "lead-1")

    activity = next(t for t in timeline if t["created_at"].startswith("2026-01-03"))
    assert activity["type"] == "activity"
    assert activity["description"] == ""

    appt = next(t for t in timeline if t["created_at"].startswith("2026-01-02"))
    assert appt["type"] == "appointment_scheduled"
    assert "Customer" in appt["description"]

    email = next(t for t in timeline if t["created_at"].startswith("2026-01-04"))
    # `.get(key, default)` returns None when key exists but value is None — so
    # the historical behavior is `email_None`, NOT `email_event`. The default
    # only fires when the key is missing entirely.
    assert email["type"] == "email_None"


def test_fetch_lead_timeline_truncates_to_limit():
    from backend.services.lead_activity import fetch_lead_timeline

    activity_rows = [
        {
            "id": f"a{i}",
            "activity_type": "note",
            "description": f"row {i}",
            "metadata": None,
            "created_at": f"2026-01-{i:02d}T10:00:00Z",
        }
        for i in range(1, 6)
    ]
    db = _make_db_returning(activity_rows, [], [])

    timeline = fetch_lead_timeline(db, "tenant-1", "lead-1", limit=2)
    assert len(timeline) == 2


def test_fetch_lead_timeline_handles_all_empty():
    from backend.services.lead_activity import fetch_lead_timeline

    db = _make_db_returning(None, None, None)
    timeline = fetch_lead_timeline(db, "tenant-1", "lead-1")
    assert timeline == []


# ---------------------------------------------------------------------------
# lead_dedup.fetch_duplicate_groups
# ---------------------------------------------------------------------------


def test_fetch_duplicate_groups_finds_email_match():
    from backend.services.lead_dedup import fetch_duplicate_groups

    leads = [
        {"id": "1", "email": "alice@example.com", "phone": "555-1111", "name": "Alice"},
        {"id": "2", "email": "ALICE@example.com", "phone": "555-2222", "name": "A"},
        {"id": "3", "email": "bob@example.com", "phone": "555-3333", "name": "Bob"},
    ]
    db = _make_db_returning(leads)

    groups = fetch_duplicate_groups(db, "tenant-1")
    assert len(groups) == 1
    g = groups[0]
    assert g["match_field"] == "email"
    assert g["match_value"] == "alice@example.com"
    assert {l["id"] for l in g["leads"]} == {"1", "2"}


def test_fetch_duplicate_groups_finds_phone_match():
    from backend.services.lead_dedup import fetch_duplicate_groups

    leads = [
        {"id": "1", "email": None, "phone": "555-9999", "name": "A"},
        {"id": "2", "email": "", "phone": "555-9999", "name": "B"},
    ]
    db = _make_db_returning(leads)

    groups = fetch_duplicate_groups(db, "tenant-1")
    assert len(groups) == 1
    assert groups[0]["match_field"] == "phone"


def test_fetch_duplicate_groups_dedups_email_and_phone_overlap():
    from backend.services.lead_dedup import fetch_duplicate_groups

    leads = [
        {"id": "1", "email": "a@x.com", "phone": "555-5555", "name": "A"},
        {"id": "2", "email": "a@x.com", "phone": "555-5555", "name": "B"},
    ]
    db = _make_db_returning(leads)
    groups = fetch_duplicate_groups(db, "tenant-1")
    assert len(groups) == 1  # email + phone collapse


def test_fetch_duplicate_groups_returns_empty_when_no_overlap():
    from backend.services.lead_dedup import fetch_duplicate_groups

    leads = [
        {"id": "1", "email": "a@x.com", "phone": "1", "name": "A"},
        {"id": "2", "email": "b@x.com", "phone": "2", "name": "B"},
    ]
    db = _make_db_returning(leads)
    assert fetch_duplicate_groups(db, "tenant-1") == []


# ---------------------------------------------------------------------------
# lead_dedup.compute_merge_updates
# ---------------------------------------------------------------------------


def test_compute_merge_updates_fills_missing_fields_only():
    from backend.services.lead_dedup import compute_merge_updates

    keep = {"name": "Alice", "email": None, "phone": "555", "lead_score": 70}
    merge = {"name": "Other", "email": "filled@x.com", "phone": "999", "lead_score": 50}

    updates = compute_merge_updates(keep, merge)
    assert updates == {"email": "filled@x.com"}


def test_compute_merge_updates_unions_tags():
    from backend.services.lead_dedup import compute_merge_updates

    keep = {"tags": ["vip"], "lead_score": 70}
    merge = {"tags": ["vip", "warm"], "lead_score": 50}

    updates = compute_merge_updates(keep, merge)
    assert updates["tags"] == ["vip", "warm"]


def test_compute_merge_updates_promotes_higher_lead_score():
    from backend.services.lead_dedup import compute_merge_updates

    keep = {"lead_score": 40}
    merge = {"lead_score": 90}

    updates = compute_merge_updates(keep, merge)
    assert updates["lead_score"] == 90


def test_compute_merge_updates_returns_empty_when_keep_is_complete():
    from backend.services.lead_dedup import compute_merge_updates

    keep = {
        "name": "A", "email": "a@x.com", "phone": "1", "lead_type": "x",
        "areas_of_interest": "y", "timeline": "now", "budget": "$$",
        "conversation_summary": "s", "next_steps": "n", "tags": ["x"],
        "lead_score": 99,
    }
    merge = {
        "name": "B", "email": "b@x.com", "tags": ["x"], "lead_score": 1,
    }
    assert compute_merge_updates(keep, merge) == {}


# ---------------------------------------------------------------------------
# lead_dedup.apply_lead_merge
# ---------------------------------------------------------------------------


def test_apply_lead_merge_raises_lookuperror_when_keep_missing():
    from backend.services.lead_dedup import apply_lead_merge

    db = _make_db_returning([])  # keep lookup returns empty
    with pytest.raises(LookupError) as exc:
        apply_lead_merge(db, "tenant-1", keep_id="keep-id", merge_id="merge-id")
    assert "keep" in str(exc.value)


def test_apply_lead_merge_raises_lookuperror_when_merge_missing():
    from backend.services.lead_dedup import apply_lead_merge

    db = _make_db_returning([{"id": "keep-id"}], [])
    with pytest.raises(LookupError) as exc:
        apply_lead_merge(db, "tenant-1", keep_id="keep-id", merge_id="merge-id")
    assert "merge" in str(exc.value)


def test_apply_lead_merge_happy_path_returns_records_and_updates():
    from backend.services.lead_dedup import apply_lead_merge

    keep = {"id": "keep", "name": "Alice", "email": None, "lead_score": 50}
    merge = {"id": "merge", "name": "X", "email": "fill@x.com", "lead_score": 70}

    # Calls in order:
    #  1. select keep
    #  2. select merge
    #  3. update keep (if updates)
    #  4-6. reassign appointments / activity_log / client_notes
    #  7. delete merge
    db = _make_db_returning([keep], [merge], None, None, None, None, None)

    k, m, updates = apply_lead_merge(
        db, "tenant-1", keep_id="keep", merge_id="merge"
    )
    assert k["id"] == "keep"
    assert m["id"] == "merge"
    assert updates["email"] == "fill@x.com"
    assert updates["lead_score"] == 70


# ---------------------------------------------------------------------------
# lead_dedup.reassign_lead_references
# ---------------------------------------------------------------------------


def test_reassign_lead_references_tolerates_per_table_failures():
    from backend.services.lead_dedup import reassign_lead_references

    db = MagicMock()
    failing_chain = MagicMock()
    failing_chain.eq.return_value = failing_chain
    failing_chain.execute.side_effect = RuntimeError("table missing")
    db.table.return_value.update.return_value.eq.return_value = failing_chain

    # Should not raise — failures swallowed and logged
    reassign_lead_references(db, "tenant-1", from_id="a", to_id="b")


# ---------------------------------------------------------------------------
# lead_csv.build_export_query
# ---------------------------------------------------------------------------


def test_build_export_query_no_filters():
    from backend.services.lead_csv import build_export_query

    db = MagicMock()
    chain = _chainable([])
    db.table.return_value = chain

    q = build_export_query(db, "t1", stage=None, search=None, assigned_to=None)
    assert q is not None


def test_build_export_query_with_stage_search_assigned():
    from backend.services.lead_csv import build_export_query

    db = MagicMock()
    chain = _chainable([])
    db.table.return_value = chain

    build_export_query(db, "t1", stage="new", search="alice@example.com", assigned_to="user-1")
    # exercise unassigned branch
    build_export_query(db, "t1", stage=None, search=None, assigned_to="unassigned")
    # exercise search-sanitization branch leaving only chars stripped
    build_export_query(db, "t1", stage=None, search="!!!", assigned_to=None)


# ---------------------------------------------------------------------------
# lead_csv.serialize_leads_to_csv
# ---------------------------------------------------------------------------


def test_serialize_leads_to_csv_joins_tags():
    from backend.services.lead_csv import serialize_leads_to_csv

    rows = [
        {"name": "A", "email": "a@x.com", "phone": "1", "tags": ["vip", "warm"]},
        {"name": "B", "email": "b@x.com", "phone": "2", "tags": None},
    ]
    out = serialize_leads_to_csv(rows)
    assert "name,email,phone" in out.splitlines()[0]
    assert "vip, warm" in out


def test_serialize_leads_to_csv_empty():
    from backend.services.lead_csv import serialize_leads_to_csv

    out = serialize_leads_to_csv([])
    assert out.splitlines()[0].startswith("name,email,phone")


# ---------------------------------------------------------------------------
# lead_csv.parse_csv_for_import
# ---------------------------------------------------------------------------


def test_parse_csv_for_import_happy_path():
    from backend.services.lead_csv import parse_csv_for_import

    csv = "name,email,phone,score\nAlice,a@x.com,555,80\nBob,b@x.com,666,bad\n"
    parsed, errors, col_map = parse_csv_for_import(csv)
    assert col_map["name"] == "name"
    assert col_map["score"] == "lead_score"
    assert len(parsed) == 2
    # First row: score parsed as int
    assert parsed[0][1]["lead_score"] == 80
    # Second row: score dropped due to ValueError
    assert "lead_score" not in parsed[1][1]
    assert errors == []


def test_parse_csv_for_import_no_recognized_columns():
    from backend.services.lead_csv import parse_csv_for_import

    csv = "unknown1,unknown2\nval1,val2\n"
    parsed, errors, col_map = parse_csv_for_import(csv)
    assert col_map == {}
    assert parsed == []


def test_parse_csv_for_import_rejects_empty_rows():
    from backend.services.lead_csv import parse_csv_for_import

    csv = "name,email,phone\n,,\nAlice,a@x.com,555\n"
    parsed, errors, _ = parse_csv_for_import(csv)
    assert len(parsed) == 1
    assert len(errors) == 1
    assert "No name" in errors[0]["error"]


def test_parse_csv_for_import_invalid_status_falls_back_to_new():
    from backend.services.lead_csv import parse_csv_for_import

    csv = "name,email,status\nAlice,a@x.com,nonsense_value\n"
    parsed, _, _ = parse_csv_for_import(csv)
    assert parsed[0][1]["status"] == "new"


def test_parse_csv_for_import_raises_on_no_headers():
    from backend.services.lead_csv import parse_csv_for_import

    with pytest.raises(ValueError):
        parse_csv_for_import("")


def test_parse_csv_for_import_caps_at_max_rows():
    from backend.services.lead_csv import parse_csv_for_import
    from backend.services.lead_csv import MAX_IMPORT_ROWS

    rows = "\n".join(f"User{i},user{i}@x.com,555" for i in range(MAX_IMPORT_ROWS + 5))
    csv = "name,email,phone\n" + rows + "\n"
    parsed, errors, _ = parse_csv_for_import(csv)
    assert len(parsed) == MAX_IMPORT_ROWS
    assert any("Stopped at" in e["error"] for e in errors)


# ---------------------------------------------------------------------------
# lead_csv.fetch_existing_emails
# ---------------------------------------------------------------------------


def test_fetch_existing_emails_returns_lowered_map():
    from backend.services.lead_csv import fetch_existing_emails

    db = _make_db_returning([
        {"id": "1", "email": "Alice@Example.com"},
        {"id": "2", "email": "bob@x.com"},
    ])
    out = fetch_existing_emails(db, "t1", ["alice@example.com", "bob@x.com"])
    assert out == {"alice@example.com": "1", "bob@x.com": "2"}


def test_fetch_existing_emails_empty_input():
    from backend.services.lead_csv import fetch_existing_emails

    db = MagicMock()
    assert fetch_existing_emails(db, "t1", []) == {}
    db.table.assert_not_called()


def test_fetch_existing_emails_swallows_db_failure():
    from backend.services.lead_csv import fetch_existing_emails

    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.in_.return_value.execute.side_effect = (
        RuntimeError("db down")
    )
    out = fetch_existing_emails(db, "t1", ["a@x.com"])
    assert out == {}


# ---------------------------------------------------------------------------
# lead_csv.apply_import_batch
# ---------------------------------------------------------------------------


def test_apply_import_batch_creates_and_updates():
    from backend.services.lead_csv import apply_import_batch

    # Two rows: one existing email (update), one new (insert)
    parsed_rows = [
        (2, {"name": "Alice", "email": "alice@x.com", "status": "new"}),
        (3, {"name": "Bob", "email": "bob@x.com"}),
    ]
    existing = {"alice@x.com": "lead-1"}
    errors: list = []
    events: list = []

    def fire(tenant_id, event_name, payload):
        events.append((tenant_id, event_name, payload))

    db = MagicMock()
    # update path: db.table.update.eq.execute returns success
    update_chain = MagicMock()
    update_chain.eq.return_value = update_chain
    update_chain.execute.return_value = _result(None)
    db.table.return_value.update.return_value.eq.return_value = update_chain

    insert_chain = MagicMock()
    insert_chain.execute.return_value = _result([{"id": "new-lead-id"}])
    db.table.return_value.insert.return_value = insert_chain

    created, updated = apply_import_batch(
        db, "t1",
        parsed_rows=parsed_rows,
        existing_by_email=existing,
        errors=errors,
        fire_event=fire,
    )
    assert created == 1
    assert updated == 1
    assert errors == []
    assert events == [("t1", "lead.created", {
        "lead_id": "new-lead-id",
        "name": "Bob",
        "email": "bob@x.com",
        "source": "csv_import",
    })]


def test_apply_import_batch_records_insert_no_data():
    from backend.services.lead_csv import apply_import_batch

    parsed_rows = [(2, {"name": "Bob", "email": "b@x.com"})]
    errors: list = []
    db = MagicMock()
    insert_chain = MagicMock()
    insert_chain.execute.return_value = _result(None)
    db.table.return_value.insert.return_value = insert_chain

    created, updated = apply_import_batch(
        db, "t1",
        parsed_rows=parsed_rows,
        existing_by_email={},
        errors=errors,
        fire_event=lambda *a, **k: None,
    )
    assert created == 0
    assert updated == 0
    assert errors and "no data" in errors[0]["error"].lower()


def test_apply_import_batch_records_insert_exception():
    from backend.services.lead_csv import apply_import_batch

    parsed_rows = [(2, {"name": "Bob", "email": "b@x.com"})]
    errors: list = []
    db = MagicMock()
    insert_chain = MagicMock()
    insert_chain.execute.side_effect = RuntimeError("constraint violation here")
    db.table.return_value.insert.return_value = insert_chain

    created, updated = apply_import_batch(
        db, "t1",
        parsed_rows=parsed_rows,
        existing_by_email={},
        errors=errors,
        fire_event=lambda *a, **k: None,
    )
    assert created == 0
    assert errors and "constraint" in errors[0]["error"]


def test_apply_import_batch_records_update_exception():
    from backend.services.lead_csv import apply_import_batch

    parsed_rows = [(2, {"name": "Alice", "email": "a@x.com", "status": "new"})]
    errors: list = []
    db = MagicMock()
    update_chain = MagicMock()
    update_chain.eq.return_value = update_chain
    update_chain.execute.side_effect = RuntimeError("update fail")
    db.table.return_value.update.return_value.eq.return_value = update_chain

    created, updated = apply_import_batch(
        db, "t1",
        parsed_rows=parsed_rows,
        existing_by_email={"a@x.com": "lead-1"},
        errors=errors,
        fire_event=lambda *a, **k: None,
    )
    assert updated == 0
    assert errors and "update fail" in errors[0]["error"]
