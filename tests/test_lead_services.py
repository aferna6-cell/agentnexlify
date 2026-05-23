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


# ---------------------------------------------------------------------------
# lead_contact.fetch_lead_with_channel
# ---------------------------------------------------------------------------


def test_fetch_lead_with_channel_email_returns_lead():
    from backend.services.lead_contact import fetch_lead_with_channel

    db = _make_db_returning(
        [{"id": "lead-1", "email": "a@x.com", "name": "Alice"}]
    )
    lead = fetch_lead_with_channel(db, "t1", "lead-1", "email")
    assert lead["email"] == "a@x.com"
    assert lead["name"] == "Alice"


def test_fetch_lead_with_channel_phone_returns_lead():
    from backend.services.lead_contact import fetch_lead_with_channel

    db = _make_db_returning(
        [{"id": "lead-2", "phone": "+15551234567", "name": "Bob"}]
    )
    lead = fetch_lead_with_channel(db, "t1", "lead-2", "phone")
    assert lead["phone"] == "+15551234567"


def test_fetch_lead_with_channel_unknown_channel_raises_value_error():
    from backend.services.lead_contact import fetch_lead_with_channel

    db = MagicMock()
    with pytest.raises(ValueError) as exc:
        fetch_lead_with_channel(db, "t1", "lead-1", "fax")
    assert "fax" in str(exc.value)


def test_fetch_lead_with_channel_missing_lead_raises_not_found():
    from backend.services.lead_contact import fetch_lead_with_channel

    db = _make_db_returning([])
    with pytest.raises(LookupError) as exc:
        fetch_lead_with_channel(db, "t1", "missing", "email")
    assert str(exc.value) == "not_found"


def test_fetch_lead_with_channel_empty_email_raises_no_channel():
    from backend.services.lead_contact import fetch_lead_with_channel

    db = _make_db_returning(
        [{"id": "lead-1", "email": None, "name": "Alice"}]
    )
    with pytest.raises(LookupError) as exc:
        fetch_lead_with_channel(db, "t1", "lead-1", "email")
    assert str(exc.value) == "no_channel"


def test_fetch_lead_with_channel_empty_phone_raises_no_channel():
    from backend.services.lead_contact import fetch_lead_with_channel

    db = _make_db_returning(
        [{"id": "lead-1", "phone": "", "name": "Bob"}]
    )
    with pytest.raises(LookupError) as exc:
        fetch_lead_with_channel(db, "t1", "lead-1", "phone")
    assert str(exc.value) == "no_channel"


# ---------------------------------------------------------------------------
# lead_contact.fetch_business_name
# ---------------------------------------------------------------------------


def test_fetch_business_name_returns_tenant_value():
    from backend.services.lead_contact import fetch_business_name

    db = _make_db_returning([{"business_name": "Acme Plumbing"}])
    assert fetch_business_name(db, "t1") == "Acme Plumbing"


def test_fetch_business_name_returns_default_when_missing():
    from backend.services.lead_contact import fetch_business_name

    db = _make_db_returning([])
    assert fetch_business_name(db, "t1") == "Our Team"


def test_fetch_business_name_respects_custom_default():
    from backend.services.lead_contact import fetch_business_name

    db = _make_db_returning([])
    assert fetch_business_name(db, "t1", default="The Team") == "The Team"


# ---------------------------------------------------------------------------
# lead_contact.build_followup_email_html
# ---------------------------------------------------------------------------


def test_build_followup_email_html_escapes_message_html():
    from backend.services.lead_contact import build_followup_email_html

    html = build_followup_email_html("<script>x</script>", "Acme")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "— Acme" in html


def test_build_followup_email_html_replaces_newlines_with_br():
    from backend.services.lead_contact import build_followup_email_html

    html = build_followup_email_html("line1\nline2", "Acme")
    assert "line1<br>line2" in html


def test_build_followup_email_html_escapes_business_name():
    from backend.services.lead_contact import build_followup_email_html

    html = build_followup_email_html("hello", "<b>Acme</b>")
    assert "<b>Acme</b>" not in html
    assert "&lt;b&gt;Acme&lt;/b&gt;" in html


# ---------------------------------------------------------------------------
# lead_contact.auto_promote_new_to_contacted
# ---------------------------------------------------------------------------


def test_auto_promote_new_to_contacted_promotes_when_status_new():
    from backend.services.lead_contact import auto_promote_new_to_contacted

    # First db.table call -> status read; second -> update
    db = _make_db_returning([{"status": "new"}], [])
    auto_promote_new_to_contacted(db, "t1", "lead-1")
    # Two db.table calls expected: select + update
    assert db.table.call_count == 2


def test_auto_promote_new_to_contacted_skips_when_status_not_new():
    from backend.services.lead_contact import auto_promote_new_to_contacted

    db = _make_db_returning([{"status": "contacted"}])
    auto_promote_new_to_contacted(db, "t1", "lead-1")
    # Only the status read; no update issued
    assert db.table.call_count == 1


def test_auto_promote_new_to_contacted_skips_when_no_data():
    from backend.services.lead_contact import auto_promote_new_to_contacted

    db = _make_db_returning([])
    auto_promote_new_to_contacted(db, "t1", "missing")
    assert db.table.call_count == 1


def test_auto_promote_new_to_contacted_swallows_exception():
    from backend.services.lead_contact import auto_promote_new_to_contacted

    db = MagicMock()
    db.table.side_effect = RuntimeError("db down")
    # Should not raise
    auto_promote_new_to_contacted(db, "t1", "lead-1")


# ---------------------------------------------------------------------------
# lead_ai_summary.fetch_lead_summary_inputs
# ---------------------------------------------------------------------------


def test_fetch_lead_summary_inputs_returns_messages_on_happy_path():
    from backend.services.lead_ai_summary import fetch_lead_summary_inputs

    messages = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
        {"role": "user", "content": "need help"},
    ]
    db = _make_db_returning(
        [{"conversation_id": "conv-1", "name": "Alice"}],
        [{"messages": messages}],
    )
    assert fetch_lead_summary_inputs(db, "t1", "lead-1") == messages


def test_fetch_lead_summary_inputs_raises_not_found_when_lead_missing():
    from backend.services.lead_ai_summary import fetch_lead_summary_inputs

    db = _make_db_returning([])
    with pytest.raises(LookupError) as exc:
        fetch_lead_summary_inputs(db, "t1", "missing")
    assert str(exc.value) == "not_found"


def test_fetch_lead_summary_inputs_raises_no_conversation_when_link_missing():
    from backend.services.lead_ai_summary import fetch_lead_summary_inputs

    db = _make_db_returning(
        [{"conversation_id": None, "name": "Alice"}],
    )
    with pytest.raises(LookupError) as exc:
        fetch_lead_summary_inputs(db, "t1", "lead-1")
    assert str(exc.value) == "no_conversation"


def test_fetch_lead_summary_inputs_raises_no_messages_when_conv_empty():
    from backend.services.lead_ai_summary import fetch_lead_summary_inputs

    db = _make_db_returning(
        [{"conversation_id": "conv-1", "name": "A"}],
        [],
    )
    with pytest.raises(LookupError) as exc:
        fetch_lead_summary_inputs(db, "t1", "lead-1")
    assert str(exc.value) == "no_messages"


def test_fetch_lead_summary_inputs_raises_no_messages_when_messages_key_empty():
    from backend.services.lead_ai_summary import fetch_lead_summary_inputs

    db = _make_db_returning(
        [{"conversation_id": "conv-1", "name": "A"}],
        [{"messages": []}],
    )
    with pytest.raises(LookupError) as exc:
        fetch_lead_summary_inputs(db, "t1", "lead-1")
    assert str(exc.value) == "no_messages"


def test_fetch_lead_summary_inputs_raises_too_short_when_single_message():
    from backend.services.lead_ai_summary import fetch_lead_summary_inputs

    db = _make_db_returning(
        [{"conversation_id": "conv-1", "name": "A"}],
        [{"messages": [{"role": "user", "content": "hi"}]}],
    )
    with pytest.raises(LookupError) as exc:
        fetch_lead_summary_inputs(db, "t1", "lead-1")
    assert str(exc.value) == "too_short"


# ---------------------------------------------------------------------------
# lead_ai_summary.build_lead_transcript
# ---------------------------------------------------------------------------


def test_build_lead_transcript_renders_visitor_and_agent_roles():
    from backend.services.lead_ai_summary import build_lead_transcript

    messages = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ]
    transcript = build_lead_transcript(messages)
    assert "Visitor: hi" in transcript
    assert "Agent: hello" in transcript


def test_build_lead_transcript_keeps_only_last_n_messages():
    from backend.services.lead_ai_summary import build_lead_transcript

    messages = [
        {"role": "user", "content": f"msg-{i}"} for i in range(50)
    ]
    transcript = build_lead_transcript(messages, limit=5)
    assert "msg-49" in transcript
    assert "msg-44" not in transcript  # outside last-5 window
    assert transcript.count("Visitor:") == 5


def test_build_lead_transcript_truncates_to_char_limit():
    from backend.services.lead_ai_summary import build_lead_transcript

    messages = [{"role": "user", "content": "x" * 5000}]
    transcript = build_lead_transcript(messages, char_limit=100)
    assert len(transcript) == 100


# ---------------------------------------------------------------------------
# lead_ai_summary.save_lead_summary
# ---------------------------------------------------------------------------


def test_save_lead_summary_writes_summary_to_lead():
    from backend.services.lead_ai_summary import save_lead_summary

    db = _make_db_returning([])
    save_lead_summary(db, "t1", "lead-1", "Customer wants quote.")
    # tenant_update issues one db.table call
    assert db.table.call_count == 1


# ---------------------------------------------------------------------------
# lead_bulk_ops.apply_bulk_lead_updates
# ---------------------------------------------------------------------------


def test_apply_bulk_lead_updates_returns_updated_count_on_success():
    from backend.services.lead_bulk_ops import apply_bulk_lead_updates

    # Each lead-id update: one db.table call returning data=[{...}]
    db = _make_db_returning([{"id": "lead-1"}], [{"id": "lead-2"}])
    updated, failed = apply_bulk_lead_updates(
        db, "t1",
        lead_ids=["lead-1", "lead-2"],
        status="contacted",
    )
    assert updated == 2
    assert failed == []


def test_apply_bulk_lead_updates_marks_lead_failed_when_no_data_returned():
    from backend.services.lead_bulk_ops import apply_bulk_lead_updates

    db = _make_db_returning([])  # update returns empty data
    updated, failed = apply_bulk_lead_updates(
        db, "t1",
        lead_ids=["lead-1"],
        status="contacted",
    )
    assert updated == 0
    assert failed == ["lead-1"]


def test_apply_bulk_lead_updates_skips_when_payload_empty():
    from backend.services.lead_bulk_ops import apply_bulk_lead_updates

    db = MagicMock()
    updated, failed = apply_bulk_lead_updates(
        db, "t1",
        lead_ids=["lead-1"],
        # No status / assigned_to / tags_add provided -> empty payload skip
    )
    assert updated == 0
    assert failed == []
    db.table.assert_not_called()


def test_apply_bulk_lead_updates_normalizes_empty_assigned_to_to_null():
    from backend.services.lead_bulk_ops import apply_bulk_lead_updates

    captured: list[dict] = []
    db = MagicMock()

    def _table(_name):
        chain = MagicMock()
        chain.update.return_value = chain
        chain.eq.return_value = chain
        chain.execute.return_value = _result([{"id": "lead-1"}])

        def _capture_update(payload):
            captured.append(payload)
            return chain
        chain.update.side_effect = _capture_update
        return chain

    db.table.side_effect = _table

    apply_bulk_lead_updates(
        db, "t1",
        lead_ids=["lead-1"],
        assigned_to="",  # empty -> should be normalized to None in payload
    )
    assert captured == [{"assigned_to": None}]


def test_apply_bulk_lead_updates_merges_existing_tags_with_new_tags():
    from backend.services.lead_bulk_ops import apply_bulk_lead_updates

    # Sequence: tag-read returns existing -> update returns success
    db = _make_db_returning(
        [{"tags": ["a"]}],
        [{"id": "lead-1"}],
    )
    updated, failed = apply_bulk_lead_updates(
        db, "t1",
        lead_ids=["lead-1"],
        tags_add=["b"],
    )
    assert updated == 1
    assert failed == []


def test_apply_bulk_lead_updates_skips_tag_update_when_lead_missing():
    from backend.services.lead_bulk_ops import apply_bulk_lead_updates

    # tag-read returns empty -> no update issued, no failure either since
    # payload becomes empty after tag-merge skipped
    db = _make_db_returning([])
    updated, failed = apply_bulk_lead_updates(
        db, "t1",
        lead_ids=["lead-1"],
        tags_add=["b"],
    )
    assert updated == 0
    assert failed == []


def test_apply_bulk_lead_updates_records_failure_when_exception_raised():
    from backend.services.lead_bulk_ops import apply_bulk_lead_updates

    db = MagicMock()
    db.table.side_effect = RuntimeError("db down")
    updated, failed = apply_bulk_lead_updates(
        db, "t1",
        lead_ids=["lead-1", "lead-2"],
        status="contacted",
    )
    assert updated == 0
    assert failed == ["lead-1", "lead-2"]


def test_apply_bulk_lead_updates_partial_failure_continues_processing():
    from backend.services.lead_bulk_ops import apply_bulk_lead_updates

    call_count = {"n": 0}

    def _table(_name):
        chain = MagicMock()
        chain.update.return_value = chain
        chain.eq.return_value = chain
        call_count["n"] += 1
        if call_count["n"] == 1:
            chain.execute.side_effect = RuntimeError("boom")
        else:
            chain.execute.return_value = _result([{"id": "lead-2"}])
        return chain

    db = MagicMock()
    db.table.side_effect = _table

    updated, failed = apply_bulk_lead_updates(
        db, "t1",
        lead_ids=["lead-1", "lead-2"],
        status="contacted",
    )
    assert updated == 1
    assert failed == ["lead-1"]


def test_apply_bulk_lead_updates_handles_lead_with_no_existing_tags():
    from backend.services.lead_bulk_ops import apply_bulk_lead_updates

    db = _make_db_returning(
        [{"tags": None}],  # existing tags is null
        [{"id": "lead-1"}],
    )
    updated, _failed = apply_bulk_lead_updates(
        db, "t1",
        lead_ids=["lead-1"],
        tags_add=["new-tag"],
    )
    assert updated == 1


# ---------------------------------------------------------------------------
# lead_assignment.assign_lead_to_member
# ---------------------------------------------------------------------------


def test_assign_lead_to_member_assigns_when_member_exists(monkeypatch):
    from backend.services import lead_assignment

    db = _make_db_returning(
        [{"id": "mem-1", "name": "Alice", "email": "a@x.com"}],  # member lookup
        [{"id": "lead-1", "assigned_to": "mem-1"}],  # lead update
    )
    log_calls = []
    monkeypatch.setattr(
        lead_assignment, "log_activity",
        lambda **kw: log_calls.append(kw),
    )
    result = lead_assignment.assign_lead_to_member(
        db, "t1", "lead-1",
        assigned_to="mem-1",
        performer_id="owner-1",
        performer_name="Owner",
    )
    assert result == {"id": "lead-1", "assigned_to": "mem-1"}
    assert len(log_calls) == 1
    assert log_calls[0]["description"] == "Lead assigned to Alice"
    assert log_calls[0]["metadata"]["assigned_to"] == "mem-1"
    assert log_calls[0]["metadata"]["assigned_to_name"] == "Alice"
    assert log_calls[0]["metadata"]["performed_by"] == "owner-1"


def test_assign_lead_to_member_raises_member_when_team_member_missing():
    from backend.services.lead_assignment import assign_lead_to_member

    db = _make_db_returning([])  # member lookup empty
    with pytest.raises(LookupError) as exc:
        assign_lead_to_member(
            db, "t1", "lead-1",
            assigned_to="bogus-mem",
            performer_id="owner-1",
            performer_name="Owner",
        )
    assert str(exc.value) == "member"


def test_assign_lead_to_member_raises_lead_when_lead_missing(monkeypatch):
    from backend.services import lead_assignment

    db = _make_db_returning(
        [{"id": "mem-1", "name": "Alice", "email": "a@x.com"}],  # member ok
        [],  # lead update empty -> lead missing
    )
    monkeypatch.setattr(lead_assignment, "log_activity", lambda **_: None)
    with pytest.raises(LookupError) as exc:
        lead_assignment.assign_lead_to_member(
            db, "t1", "missing-lead",
            assigned_to="mem-1",
            performer_id="owner-1",
            performer_name="Owner",
        )
    assert str(exc.value) == "lead"


def test_assign_lead_to_member_unassigns_when_assigned_to_none(monkeypatch):
    from backend.services import lead_assignment

    db = _make_db_returning([{"id": "lead-1", "assigned_to": None}])
    log_calls = []
    monkeypatch.setattr(
        lead_assignment, "log_activity",
        lambda **kw: log_calls.append(kw),
    )
    result = lead_assignment.assign_lead_to_member(
        db, "t1", "lead-1",
        assigned_to=None,
        performer_id="owner-1",
        performer_name="Owner",
    )
    assert result == {"id": "lead-1", "assigned_to": None}
    assert log_calls[0]["description"] == "Lead assigned to nobody"
    assert log_calls[0]["metadata"]["assigned_to"] is None
    assert log_calls[0]["metadata"]["assigned_to_name"] == "nobody"


def test_assign_lead_to_member_swallows_log_activity_exception(monkeypatch):
    from backend.services import lead_assignment

    db = _make_db_returning(
        [{"id": "mem-1", "name": "Alice", "email": "a@x.com"}],
        [{"id": "lead-1", "assigned_to": "mem-1"}],
    )

    def _boom(**_):
        raise RuntimeError("log down")

    monkeypatch.setattr(lead_assignment, "log_activity", _boom)
    # Should NOT raise; logging failure is best-effort
    result = lead_assignment.assign_lead_to_member(
        db, "t1", "lead-1",
        assigned_to="mem-1",
        performer_id="owner-1",
        performer_name="Owner",
    )
    assert result == {"id": "lead-1", "assigned_to": "mem-1"}


# ---------------------------------------------------------------------------
# lead_suggestions.apply_or_dismiss_suggestion
# ---------------------------------------------------------------------------


def test_apply_or_dismiss_suggestion_rejects_unknown_action():
    from backend.services.lead_suggestions import apply_or_dismiss_suggestion

    db = MagicMock()
    with pytest.raises(ValueError):
        apply_or_dismiss_suggestion(db, "t1", "sugg-1", "garbage")


def test_apply_or_dismiss_suggestion_raises_not_found_when_missing():
    from backend.services.lead_suggestions import apply_or_dismiss_suggestion

    db = _make_db_returning([])  # suggestion lookup empty
    with pytest.raises(LookupError) as exc:
        apply_or_dismiss_suggestion(db, "t1", "sugg-1", "approve")
    assert str(exc.value) == "not_found"


def test_apply_or_dismiss_suggestion_dismiss_deletes_without_lead_update():
    from backend.services.lead_suggestions import apply_or_dismiss_suggestion

    # suggestion fetch returns one row; dismiss path only deletes -> 2 calls total
    db = _make_db_returning(
        [{"id": "sugg-1", "lead_id": "lead-1", "metadata": {"suggestions": {"status": {"new": "qualified"}}}}],
        None,  # delete response
    )
    result = apply_or_dismiss_suggestion(db, "t1", "sugg-1", "dismiss")
    assert result == {"success": True, "action": "dismiss"}


def test_apply_or_dismiss_suggestion_approve_applies_updates_and_deletes():
    from backend.services.lead_suggestions import apply_or_dismiss_suggestion

    # 3 table calls: suggestion-fetch, lead-update, suggestion-delete
    db = _make_db_returning(
        [{
            "id": "sugg-1",
            "lead_id": "lead-1",
            "metadata": {"suggestions": {"status": {"new": "qualified"}, "name": {"new": "Bob"}}},
        }],
        [{"id": "lead-1"}],  # update response
        None,  # delete response
    )
    result = apply_or_dismiss_suggestion(db, "t1", "sugg-1", "approve")
    assert result == {"success": True, "action": "approve"}


def test_apply_or_dismiss_suggestion_approve_skips_update_when_no_lead_id():
    from backend.services.lead_suggestions import apply_or_dismiss_suggestion

    # suggestion with no lead_id -> approve path skips update, only deletes
    db = _make_db_returning(
        [{"id": "sugg-1", "lead_id": None, "metadata": {"suggestions": {"status": {"new": "qualified"}}}}],
        None,  # delete response
    )
    result = apply_or_dismiss_suggestion(db, "t1", "sugg-1", "approve")
    assert result == {"success": True, "action": "approve"}


def test_apply_or_dismiss_suggestion_approve_skips_update_when_no_suggestions():
    from backend.services.lead_suggestions import apply_or_dismiss_suggestion

    # suggestion with empty/missing suggestions -> approve path skips update
    db = _make_db_returning(
        [{"id": "sugg-1", "lead_id": "lead-1", "metadata": {}}],
        None,  # delete response
    )
    result = apply_or_dismiss_suggestion(db, "t1", "sugg-1", "approve")
    assert result == {"success": True, "action": "approve"}


def test_apply_or_dismiss_suggestion_approve_handles_null_metadata():
    from backend.services.lead_suggestions import apply_or_dismiss_suggestion

    db = _make_db_returning(
        [{"id": "sugg-1", "lead_id": "lead-1", "metadata": None}],
        None,  # delete response
    )
    result = apply_or_dismiss_suggestion(db, "t1", "sugg-1", "approve")
    assert result == {"success": True, "action": "approve"}


# ---------------------------------------------------------------------------
# lead_suggestions.list_pending_suggestions
# ---------------------------------------------------------------------------


def test_list_pending_suggestions_returns_rows():
    from backend.services.lead_suggestions import list_pending_suggestions

    rows = [
        {"id": "s1", "lead_id": "l1", "description": "x", "metadata": {}, "created_at": "2026-05-23"},
        {"id": "s2", "lead_id": "l2", "description": "y", "metadata": {}, "created_at": "2026-05-22"},
    ]
    db = _make_db_returning(rows)
    assert list_pending_suggestions(db, "t1") == rows


def test_list_pending_suggestions_returns_empty_when_no_rows():
    from backend.services.lead_suggestions import list_pending_suggestions

    db = _make_db_returning(None)
    assert list_pending_suggestions(db, "t1") == []


def test_list_pending_suggestions_respects_custom_limit():
    from backend.services.lead_suggestions import list_pending_suggestions

    db = _make_db_returning([])
    list_pending_suggestions(db, "t1", limit=5)
    # No assertion on limit value; coverage on the branch is enough.


# ---------------------------------------------------------------------------
# lead_create.build_manual_lead_payload
# ---------------------------------------------------------------------------


def test_build_manual_lead_payload_drops_none_values():
    from backend.services.lead_create import build_manual_lead_payload

    p = build_manual_lead_payload(
        "t1",
        name="Alice",
        email=None,
        phone=None,
        status=None,
        lead_temperature=None,
        areas_of_interest=None,
        deal_value=None,
        expected_close_date=None,
    )
    assert p == {
        "client_id": "t1",
        "name": "Alice",
        "status": "new",
        "source": "manual",
    }


def test_build_manual_lead_payload_includes_deal_value_and_close_date():
    from backend.services.lead_create import build_manual_lead_payload

    p = build_manual_lead_payload(
        "t1",
        name="A", email=None, phone=None, status="qualified",
        lead_temperature="hot", areas_of_interest="plumbing",
        deal_value=1000.0, expected_close_date="2026-06-01",
    )
    assert p["deal_value"] == 1000.0
    assert p["expected_close_date"] == "2026-06-01"
    assert p["status"] == "qualified"
    assert p["lead_temperature"] == "hot"


def test_build_manual_lead_payload_treats_zero_deal_value_as_present():
    from backend.services.lead_create import build_manual_lead_payload

    p = build_manual_lead_payload(
        "t1", name="A", email=None, phone=None, status=None,
        lead_temperature=None, areas_of_interest=None,
        deal_value=0.0, expected_close_date=None,
    )
    # 0.0 is not None, so it stays
    assert p["deal_value"] == 0.0


def test_build_manual_lead_payload_skips_empty_close_date_string():
    from backend.services.lead_create import build_manual_lead_payload

    p = build_manual_lead_payload(
        "t1", name="A", email=None, phone=None, status=None,
        lead_temperature=None, areas_of_interest=None,
        deal_value=None, expected_close_date="",
    )
    assert "expected_close_date" not in p


# ---------------------------------------------------------------------------
# lead_create.insert_manual_lead
# ---------------------------------------------------------------------------


def test_insert_manual_lead_raises_runtimeerror_when_insert_returns_empty(monkeypatch):
    from backend.services import lead_create

    monkeypatch.setattr(lead_create, "log_activity", lambda **_: None)
    db = _make_db_returning([])  # insert returns no row
    with pytest.raises(RuntimeError) as exc:
        lead_create.insert_manual_lead(
            db, "t1", {"client_id": "t1", "name": "A", "status": "new", "source": "manual"},
            performer_id="owner", performer_name="Owner",
        )
    assert str(exc.value) == "insert_failed"


def test_insert_manual_lead_returns_inserted_row_and_logs_and_fires(monkeypatch):
    from backend.services import lead_create

    log_calls = []
    fire_calls = []
    monkeypatch.setattr(
        lead_create, "log_activity",
        lambda **kw: log_calls.append(kw),
    )
    db = _make_db_returning([{"id": "lead-1", "name": "Alice"}])
    result = lead_create.insert_manual_lead(
        db, "t1",
        {"client_id": "t1", "name": "Alice", "status": "new", "source": "manual"},
        performer_id="owner-1", performer_name="Owner",
        fire_event=lambda *a: fire_calls.append(a),
    )
    assert result == {"id": "lead-1", "name": "Alice"}
    assert len(log_calls) == 1
    assert log_calls[0]["activity_type"] == "lead_created"
    assert "Alice" in log_calls[0]["description"]
    assert log_calls[0]["metadata"]["performed_by"] == "owner-1"
    assert len(fire_calls) == 1
    assert fire_calls[0][0] == "t1"
    assert fire_calls[0][1] == "lead.created"
    assert fire_calls[0][2]["lead_id"] == "lead-1"


def test_insert_manual_lead_works_without_fire_event_callback(monkeypatch):
    from backend.services import lead_create

    monkeypatch.setattr(lead_create, "log_activity", lambda **_: None)
    db = _make_db_returning([{"id": "lead-1"}])
    result = lead_create.insert_manual_lead(
        db, "t1",
        {"client_id": "t1", "name": "Bob", "status": "new", "source": "manual"},
        performer_id="owner", performer_name="Owner",
        fire_event=None,
    )
    assert result == {"id": "lead-1"}


def test_insert_manual_lead_descriptor_falls_back_through_email_phone(monkeypatch):
    from backend.services import lead_create

    log_calls = []
    monkeypatch.setattr(
        lead_create, "log_activity",
        lambda **kw: log_calls.append(kw),
    )
    db = _make_db_returning([{"id": "lead-1"}])
    # payload without name, with email -> descriptor should be email
    lead_create.insert_manual_lead(
        db, "t1",
        {"client_id": "t1", "email": "alice@x.com", "status": "new", "source": "manual"},
        performer_id="owner", performer_name="Owner",
    )
    assert "alice@x.com" in log_calls[-1]["description"]

    # payload without name/email, with phone -> descriptor should be phone
    log_calls.clear()
    db = _make_db_returning([{"id": "lead-2"}])
    lead_create.insert_manual_lead(
        db, "t1",
        {"client_id": "t1", "phone": "+15551234567", "status": "new", "source": "manual"},
        performer_id="owner", performer_name="Owner",
    )
    assert "+15551234567" in log_calls[-1]["description"]


# ---------------------------------------------------------------------------
# lead_diagnostics.collect_lead_capture_diagnostics
# ---------------------------------------------------------------------------


def _diag_result(data=None, count=None):
    return SimpleNamespace(data=data, count=count)


def _diag_chainable(response):
    m = MagicMock()
    m.eq.return_value = m
    m.gte.return_value = m
    m.order.return_value = m
    m.limit.return_value = m
    m.select.return_value = m
    m.execute.return_value = response
    return m


def _make_diag_db(*responses):
    iter_responses = iter(responses)
    db = MagicMock()

    def _table(_name):
        try:
            r = next(iter_responses)
        except StopIteration:
            r = _diag_result(data=[], count=0)
        return _diag_chainable(r)

    db.table.side_effect = _table
    return db


def test_collect_lead_capture_diagnostics_happy_path():
    from backend.services.lead_diagnostics import collect_lead_capture_diagnostics

    db = _make_diag_db(
        _diag_result(data=[{"id": "l1"}], count=42),  # total
        _diag_result(data=[{"id": "l1"}], count=5),   # recent 7d
        _diag_result(  # sample
            data=[
                {"id": "l1", "created_at": "2026-05-22T10:00:00Z", "email": "a@b.com", "phone": None},
                {"id": "l2", "created_at": "2026-05-21T10:00:00Z", "email": None, "phone": "+1555"},
            ],
            count=None,
        ),
    )

    out = collect_lead_capture_diagnostics(db, "tenant-1")

    assert out["total_leads"] == 42
    assert out["leads_last_7_days"] == 5
    assert out["last_lead_created_at"] == "2026-05-22T10:00:00Z"
    assert out["sample_lead_ids"] == ["l1", "l2"]
    assert out["has_email_leads"] is True


def test_collect_lead_capture_diagnostics_empty_sample_means_no_last_created():
    from backend.services.lead_diagnostics import collect_lead_capture_diagnostics

    db = _make_diag_db(
        _diag_result(data=[], count=0),
        _diag_result(data=[], count=0),
        _diag_result(data=[], count=None),
    )

    out = collect_lead_capture_diagnostics(db, "tenant-1")

    assert out["total_leads"] == 0
    assert out["leads_last_7_days"] == 0
    assert out["last_lead_created_at"] is None
    assert out["sample_lead_ids"] == []
    assert out["has_email_leads"] is False


def test_collect_lead_capture_diagnostics_total_count_failure_returns_minus_one():
    from backend.services.lead_diagnostics import collect_lead_capture_diagnostics

    # First .table() call raises (total count). Other two succeed.
    db = MagicMock()
    call_n = {"i": 0}

    def _table(_name):
        call_n["i"] += 1
        if call_n["i"] == 1:
            m = MagicMock()
            m.select.return_value = m
            m.eq.return_value = m
            m.execute.side_effect = RuntimeError("db down")
            return m
        return _diag_chainable(
            _diag_result(data=[], count=0) if call_n["i"] == 2
            else _diag_result(data=[], count=None)
        )

    db.table.side_effect = _table

    out = collect_lead_capture_diagnostics(db, "tenant-1")

    assert out["total_leads"] == -1
    assert out["leads_last_7_days"] == 0
    assert out["last_lead_created_at"] is None


def test_collect_lead_capture_diagnostics_recent_failure_returns_minus_one():
    from backend.services.lead_diagnostics import collect_lead_capture_diagnostics

    db = MagicMock()
    call_n = {"i": 0}

    def _table(_name):
        call_n["i"] += 1
        if call_n["i"] == 2:  # recent count
            m = MagicMock()
            m.select.return_value = m
            m.eq.return_value = m
            m.gte.return_value = m
            m.execute.side_effect = RuntimeError("timeout")
            return m
        return _diag_chainable(
            _diag_result(data=[], count=7) if call_n["i"] == 1
            else _diag_result(data=[], count=None)
        )

    db.table.side_effect = _table

    out = collect_lead_capture_diagnostics(db, "tenant-1")

    assert out["total_leads"] == 7
    assert out["leads_last_7_days"] == -1


def test_collect_lead_capture_diagnostics_sample_failure_returns_defaults():
    from backend.services.lead_diagnostics import collect_lead_capture_diagnostics

    db = MagicMock()
    call_n = {"i": 0}

    def _table(_name):
        call_n["i"] += 1
        if call_n["i"] == 3:  # sample query
            m = MagicMock()
            m.select.return_value = m
            m.eq.return_value = m
            m.order.return_value = m
            m.limit.return_value = m
            m.execute.side_effect = RuntimeError("query blew up")
            return m
        return _diag_chainable(
            _diag_result(data=[], count=10)
        )

    db.table.side_effect = _table

    out = collect_lead_capture_diagnostics(db, "tenant-1")

    assert out["total_leads"] == 10
    assert out["leads_last_7_days"] == 10
    assert out["last_lead_created_at"] is None
    assert out["sample_lead_ids"] == []
    assert out["has_email_leads"] is False


# ---------------------------------------------------------------------------
# lead_listing.list_leads_paginated
# ---------------------------------------------------------------------------


class _ListingChainable:
    """Records every filter/sort/range/exec call for assertion."""

    def __init__(self, response):
        self.calls = []
        self._response = response
        self.select = self._noop("select")
        self.eq = self._record("eq")
        self.is_ = self._record("is_")
        self.or_ = self._record("or_")
        self.order = self._record("order")
        self.range = self._record("range")

    def _record(self, name):
        def _fn(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            return self
        return _fn

    def _noop(self, name):
        def _fn(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            return self
        return _fn

    def execute(self):
        return self._response


def _make_listing_db(response):
    chainable = _ListingChainable(response)
    db = MagicMock()
    db.table.return_value = chainable
    return db, chainable


def test_list_leads_paginated_returns_data_total_and_pagination():
    from backend.services.lead_listing import list_leads_paginated

    db, _ = _make_listing_db(
        SimpleNamespace(data=[{"id": "l1"}, {"id": "l2"}], count=42)
    )
    out = list_leads_paginated(
        db, "tenant-1", page=2, per_page=10,
    )
    assert out["leads"] == [{"id": "l1"}, {"id": "l2"}]
    assert out["total"] == 42
    assert out["page"] == 2
    assert out["per_page"] == 10
    assert out["total_pages"] == 5  # ceil(42 / 10)


def test_list_leads_paginated_filters_by_stage():
    from backend.services.lead_listing import list_leads_paginated

    db, chain = _make_listing_db(SimpleNamespace(data=[], count=0))
    list_leads_paginated(db, "tenant-1", stage="contacted")

    eq_calls = [c for c in chain.calls if c[0] == "eq"]
    assert any(call[1] == ("status", "contacted") for call in eq_calls)


def test_list_leads_paginated_filters_unassigned_uses_is_null():
    from backend.services.lead_listing import list_leads_paginated

    db, chain = _make_listing_db(SimpleNamespace(data=[], count=0))
    list_leads_paginated(db, "tenant-1", assigned_to="unassigned")

    is_calls = [c for c in chain.calls if c[0] == "is_"]
    assert is_calls == [("is_", ("assigned_to", "null"), {})]


def test_list_leads_paginated_filters_by_assignee():
    from backend.services.lead_listing import list_leads_paginated

    db, chain = _make_listing_db(SimpleNamespace(data=[], count=0))
    list_leads_paginated(db, "tenant-1", assigned_to="member-99")

    eq_calls = [c for c in chain.calls if c[0] == "eq"]
    assert any(call[1] == ("assigned_to", "member-99") for call in eq_calls)


def test_list_leads_paginated_sanitizes_search_strips_special_chars():
    from backend.services.lead_listing import list_leads_paginated

    db, chain = _make_listing_db(SimpleNamespace(data=[], count=0))
    list_leads_paginated(db, "tenant-1", search="alice'; DROP TABLE--")

    or_calls = [c for c in chain.calls if c[0] == "or_"]
    assert len(or_calls) == 1
    arg = or_calls[0][1][0]
    assert "'" not in arg
    assert "DROP" in arg  # letters survive sanitization
    assert "%" in arg  # ilike pattern syntax


def test_list_leads_paginated_skips_search_when_sanitized_empty():
    from backend.services.lead_listing import list_leads_paginated

    db, chain = _make_listing_db(SimpleNamespace(data=[], count=0))
    list_leads_paginated(db, "tenant-1", search="'';;")  # all stripped

    or_calls = [c for c in chain.calls if c[0] == "or_"]
    assert or_calls == []


def test_list_leads_paginated_unsafe_sort_falls_back_to_default():
    from backend.services.lead_listing import list_leads_paginated

    db, chain = _make_listing_db(SimpleNamespace(data=[], count=0))
    list_leads_paginated(db, "tenant-1", sort="; DROP TABLE leads;")

    order_calls = [c for c in chain.calls if c[0] == "order"]
    assert order_calls[0][1] == ("lead_score",)


def test_list_leads_paginated_order_asc_when_specified():
    from backend.services.lead_listing import list_leads_paginated

    db, chain = _make_listing_db(SimpleNamespace(data=[], count=0))
    list_leads_paginated(db, "tenant-1", sort="created_at", order="asc")

    order_calls = [c for c in chain.calls if c[0] == "order"]
    assert order_calls[0][2] == {"desc": False}


def test_list_leads_paginated_page_offset_math():
    from backend.services.lead_listing import list_leads_paginated

    db, chain = _make_listing_db(SimpleNamespace(data=[], count=0))
    list_leads_paginated(db, "tenant-1", page=3, per_page=25)

    range_calls = [c for c in chain.calls if c[0] == "range"]
    # page 3, per_page 25 => offset 50, end 74
    assert range_calls[0][1] == (50, 74)


def test_list_leads_paginated_total_falls_back_to_len_when_count_none():
    from backend.services.lead_listing import list_leads_paginated

    db, _ = _make_listing_db(
        SimpleNamespace(data=[{"id": "x"}, {"id": "y"}], count=None)
    )
    out = list_leads_paginated(db, "tenant-1")
    assert out["total"] == 2


def test_list_leads_paginated_query_failure_raises_runtimeerror():
    from backend.services.lead_listing import list_leads_paginated

    chain = _ListingChainable(SimpleNamespace(data=[], count=0))
    def _exec_fail():
        raise RuntimeError("supabase 503")
    chain.execute = _exec_fail
    db = MagicMock()
    db.table.return_value = chain

    with pytest.raises(RuntimeError, match="query_failed"):
        list_leads_paginated(db, "tenant-1")


def test_list_leads_paginated_empty_total_returns_one_total_page():
    from backend.services.lead_listing import list_leads_paginated

    db, _ = _make_listing_db(SimpleNamespace(data=[], count=0))
    out = list_leads_paginated(db, "tenant-1")
    assert out["total"] == 0
    assert out["total_pages"] == 1


def test_collect_lead_capture_diagnostics_count_none_normalizes_to_zero():
    from backend.services.lead_diagnostics import collect_lead_capture_diagnostics

    db = _make_diag_db(
        _diag_result(data=None, count=None),  # total returns None
        _diag_result(data=None, count=None),  # recent returns None
        _diag_result(data=None, count=None),  # sample returns None
    )

    out = collect_lead_capture_diagnostics(db, "tenant-1")

    assert out["total_leads"] == 0
    assert out["leads_last_7_days"] == 0
    assert out["last_lead_created_at"] is None
    assert out["sample_lead_ids"] == []
    assert out["has_email_leads"] is False


# ---------------------------------------------------------------------------
# lead_updates.apply_lead_update
# ---------------------------------------------------------------------------


def test_apply_lead_update_raises_value_error_when_updates_empty():
    from backend.services.lead_updates import apply_lead_update

    db = MagicMock()
    with pytest.raises(ValueError, match="no_updates"):
        apply_lead_update(db, "tenant-1", "lead-1", {})


def test_apply_lead_update_raises_lookup_error_when_no_rows_affected():
    from backend.services.lead_updates import apply_lead_update

    db = _make_db_returning([])  # update returns no data
    with pytest.raises(LookupError, match="not_found"):
        apply_lead_update(db, "tenant-1", "lead-1", {"name": "Alice"})


def test_apply_lead_update_returns_updated_row_on_happy_path():
    from backend.services.lead_updates import apply_lead_update

    row = {"id": "lead-1", "name": "Alice", "status": "contacted"}
    db = _make_db_returning([row])
    out = apply_lead_update(db, "tenant-1", "lead-1", {"name": "Alice"})
    assert out == row


def test_apply_lead_update_works_without_fire_event_callback():
    from backend.services.lead_updates import apply_lead_update

    row = {"id": "lead-1", "status": "won"}
    db = _make_db_returning([row])
    # fire_event=None — should not raise
    out = apply_lead_update(db, "tenant-1", "lead-1", {"status": "won"})
    assert out == row


def test_apply_lead_update_fires_lead_updated_event_with_payload():
    from backend.services.lead_updates import apply_lead_update

    row = {"id": "lead-1", "name": "Alice"}
    db = _make_db_returning([row])
    events = []
    apply_lead_update(
        db, "tenant-1", "lead-1", {"name": "Alice", "phone": "555"},
        fire_event=lambda t, e, p: events.append((t, e, p)),
    )

    updated = [e for e in events if e[1] == "lead.updated"]
    assert len(updated) == 1
    assert updated[0][0] == "tenant-1"
    payload = updated[0][2]
    assert payload["lead_id"] == "lead-1"
    assert set(payload["updated_fields"]) == {"name", "phone"}
    assert payload["name"] == "Alice"
    assert payload["phone"] == "555"


def test_apply_lead_update_fires_status_changed_event_when_status_in_updates():
    from backend.services.lead_updates import apply_lead_update

    row = {"id": "lead-1", "status": "won"}
    db = _make_db_returning([row])
    events = []
    apply_lead_update(
        db, "tenant-1", "lead-1", {"status": "won"},
        fire_event=lambda t, e, p: events.append((t, e, p)),
    )

    status_events = [e for e in events if e[1] == "lead.status_changed"]
    assert len(status_events) == 1
    assert status_events[0][2] == {
        "lead_id": "lead-1",
        "new_status": "won",
        "source": "leads_update",
    }


def test_apply_lead_update_skips_status_changed_event_when_status_not_in_updates():
    from backend.services.lead_updates import apply_lead_update

    row = {"id": "lead-1", "name": "Alice"}
    db = _make_db_returning([row])
    events = []
    apply_lead_update(
        db, "tenant-1", "lead-1", {"name": "Alice"},
        fire_event=lambda t, e, p: events.append((t, e, p)),
    )

    status_events = [e for e in events if e[1] == "lead.status_changed"]
    assert status_events == []


# ---------- lead_messaging.record_followup_sent ----------

def test_record_followup_sent_email_logs_with_subject(monkeypatch):
    from backend.services import lead_messaging

    activity_calls = []
    promote_calls = []
    monkeypatch.setattr(
        lead_messaging,
        "log_activity",
        lambda **kwargs: activity_calls.append(kwargs),
    )
    monkeypatch.setattr(
        lead_messaging,
        "auto_promote_new_to_contacted",
        lambda db, tenant_id, lead_id: promote_calls.append((tenant_id, lead_id)),
    )

    db = object()
    lead = {"name": "Alice", "email": "a@example.com"}
    lead_messaging.record_followup_sent(
        db, "tenant-1", "lead-1",
        lead=lead, channel="email", subject="Re: quote",
    )

    assert len(activity_calls) == 1
    call = activity_calls[0]
    assert call["tenant_id"] == "tenant-1"
    assert call["activity_type"] == "email_sent"
    assert call["lead_id"] == "lead-1"
    assert "Alice" in call["description"]
    assert "Re: quote" in call["description"]
    assert promote_calls == [("tenant-1", "lead-1")]


def test_record_followup_sent_email_without_subject(monkeypatch):
    from backend.services import lead_messaging

    activity_calls = []
    monkeypatch.setattr(
        lead_messaging,
        "log_activity",
        lambda **kwargs: activity_calls.append(kwargs),
    )
    monkeypatch.setattr(
        lead_messaging,
        "auto_promote_new_to_contacted",
        lambda *_args, **_kw: None,
    )

    lead = {"name": "Bob", "email": "b@example.com"}
    lead_messaging.record_followup_sent(
        object(), "tenant-1", "lead-1",
        lead=lead, channel="email",
    )

    assert len(activity_calls) == 1
    description = activity_calls[0]["description"]
    assert "Bob" in description
    assert ":" not in description


def test_record_followup_sent_email_falls_back_to_email_then_lead_id(monkeypatch):
    from backend.services import lead_messaging

    captured = []
    monkeypatch.setattr(
        lead_messaging,
        "log_activity",
        lambda **kwargs: captured.append(kwargs),
    )
    monkeypatch.setattr(
        lead_messaging,
        "auto_promote_new_to_contacted",
        lambda *_a, **_k: None,
    )

    # No name -> use email
    lead_messaging.record_followup_sent(
        object(), "tenant-1", "lead-1",
        lead={"email": "noname@example.com"}, channel="email",
    )
    assert "noname@example.com" in captured[0]["description"]

    # No name, no email -> fall back to lead_id
    lead_messaging.record_followup_sent(
        object(), "tenant-1", "lead-zzz",
        lead={}, channel="email",
    )
    assert "lead-zzz" in captured[1]["description"]


def test_record_followup_sent_sms_logs_and_promotes(monkeypatch):
    from backend.services import lead_messaging

    activity_calls = []
    promote_calls = []
    monkeypatch.setattr(
        lead_messaging,
        "log_activity",
        lambda **kwargs: activity_calls.append(kwargs),
    )
    monkeypatch.setattr(
        lead_messaging,
        "auto_promote_new_to_contacted",
        lambda db, tenant_id, lead_id: promote_calls.append((tenant_id, lead_id)),
    )

    lead = {"name": "Carol", "phone": "+15551234567"}
    lead_messaging.record_followup_sent(
        object(), "tenant-2", "lead-2",
        lead=lead, channel="sms",
    )

    assert len(activity_calls) == 1
    call = activity_calls[0]
    assert call["activity_type"] == "sms_sent"
    assert call["tenant_id"] == "tenant-2"
    assert call["lead_id"] == "lead-2"
    assert "Carol" in call["description"]
    assert promote_calls == [("tenant-2", "lead-2")]


def test_record_followup_sent_sms_falls_back_to_phone(monkeypatch):
    from backend.services import lead_messaging

    captured = []
    monkeypatch.setattr(
        lead_messaging,
        "log_activity",
        lambda **kwargs: captured.append(kwargs),
    )
    monkeypatch.setattr(
        lead_messaging,
        "auto_promote_new_to_contacted",
        lambda *_a, **_k: None,
    )

    lead_messaging.record_followup_sent(
        object(), "tenant-1", "lead-1",
        lead={"phone": "+15550000000"}, channel="sms",
    )
    assert "+15550000000" in captured[0]["description"]


def test_record_followup_sent_unknown_channel_raises():
    from backend.services import lead_messaging
    import pytest

    with pytest.raises(ValueError, match="unknown channel"):
        lead_messaging.record_followup_sent(
            object(), "tenant-1", "lead-1",
            lead={"name": "X"}, channel="voice",
        )
