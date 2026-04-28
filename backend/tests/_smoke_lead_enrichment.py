"""Standalone smoke runner for `_enrich_lead_from_message`.

Exists because backend/tests/conftest.py drags in `from backend.main import app`
which transitively imports every router (and every router's deps). On
constrained dev environments those deps may not be installable. This script
imports ONLY backend.routers.widget_helpers and exercises the new helper
through the same mock patterns the real test file uses.

Run with:
    TESTING=1 python backend/tests/_smoke_lead_enrichment.py

NOT a replacement for the pytest suite — that runs in CI. This script
provides a fast local confidence signal that the helper logic is sound
when the real test environment isn't available.
"""

import asyncio
import os
import sys
import traceback
from unittest.mock import MagicMock, patch

os.environ.setdefault("TESTING", "1")

# Force-import widget_helpers without going through conftest
from backend.routers import widget_lead_helpers as widget_helpers  # noqa: E402


TENANT = "11111111-1111-1111-1111-111111111111"
SESSION = "sess-smoke"


def _run(coro):
    return asyncio.run(coro)


def _fake_db_with_lead(lead):
    db = MagicMock()
    tables = {}

    def _build_leads_tbl():
        tbl = MagicMock()
        select_chain = MagicMock()
        select_chain.data = [lead] if lead else []
        tbl.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = select_chain
        tbl.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[lead] if lead else [])
        return tbl

    def _build_activity_tbl():
        tbl = MagicMock()
        tbl.insert.return_value.execute.return_value = MagicMock(data=[])
        return tbl

    def table_side_effect(name):
        if name not in tables:
            if name == "leads":
                tables[name] = _build_leads_tbl()
            elif name == "activity_log":
                tables[name] = _build_activity_tbl()
            else:
                tables[name] = MagicMock()
        return tables[name]

    db.table.side_effect = table_side_effect
    return db


# ---------------------------------------------------------------------------
# Test cases (mirror backend/tests/test_lead_enrichment.py)
# ---------------------------------------------------------------------------


def test_helper_is_importable():
    assert hasattr(widget_helpers, "_enrich_lead_from_message")


def test_extractor_returns_nothing_new():
    regex = {"name": "Sara", "email": "sara@example.com", "phone": "555-1234"}
    existing_lead = {
        "id": "lead_1", "client_id": TENANT,
        "name": "Sara", "email": "sara@example.com", "phone": "555-1234",
    }
    db = _fake_db_with_lead(existing_lead)
    with (
        patch("backend.services.structured_extractor.extract_structured",
              return_value={"name": "Sara", "email": "sara@example.com",
                            "phone": "555-1234", "interest": None,
                            "timeline": None, "budget": None, "source": None}),
        patch("backend.routers.widget_lead_helpers.get_service_supabase", return_value=db),
        patch("backend.routers.widget_lead_helpers.log_activity") as mock_log,
    ):
        _run(widget_helpers._enrich_lead_from_message(
            tenant_id=TENANT, session_id=SESSION,
            raw_text="x", regex_extracted=regex,
        ))
    leads_tbl = db.table("leads")
    assert not leads_tbl.update.called, "expected no update"
    assert not mock_log.called, "expected no activity log"


def test_no_email_or_phone_skips_with_no_db_call():
    regex = {}
    db = _fake_db_with_lead(None)
    with (
        patch("backend.services.structured_extractor.extract_structured",
              return_value={"interest": "haircut", "timeline": "next week",
                            "budget": None, "name": None, "email": None,
                            "phone": None, "source": None}),
        patch("backend.routers.widget_lead_helpers.get_service_supabase", return_value=db),
        patch("backend.routers.widget_lead_helpers.log_activity") as mock_log,
    ):
        _run(widget_helpers._enrich_lead_from_message(
            tenant_id=TENANT, session_id=SESSION,
            raw_text="x", regex_extracted=regex,
        ))
    assert not db.table.called, "no email/phone → no db lookup"
    assert not mock_log.called


def test_lead_not_found_skips_update():
    regex = {"email": "ghost@example.com"}
    db = _fake_db_with_lead(None)
    with (
        patch("backend.services.structured_extractor.extract_structured",
              return_value={"name": "Ghost", "interest": "consultation",
                            "email": None, "phone": None, "timeline": None,
                            "budget": None, "source": None}),
        patch("backend.routers.widget_lead_helpers.get_service_supabase", return_value=db),
        patch("backend.routers.widget_lead_helpers.log_activity") as mock_log,
    ):
        _run(widget_helpers._enrich_lead_from_message(
            tenant_id=TENANT, session_id=SESSION,
            raw_text="x", regex_extracted=regex,
        ))
    leads_tbl = db.table("leads")
    assert not leads_tbl.update.called
    assert not mock_log.called


def test_fills_missing_fields():
    regex = {"email": "sara@example.com"}
    existing_lead = {
        "id": "lead_1", "client_id": TENANT,
        "name": None, "email": "sara@example.com", "phone": None,
    }
    db = _fake_db_with_lead(existing_lead)
    with (
        patch("backend.services.structured_extractor.extract_structured",
              return_value={"name": "Sara Kim", "email": "sara@example.com",
                            "phone": "(555) 867-5309",
                            "interest": "autopilot plan",
                            "timeline": "by June",
                            "budget": None, "source": None}),
        patch("backend.routers.widget_lead_helpers.get_service_supabase", return_value=db),
        patch("backend.routers.widget_lead_helpers.log_activity"),
    ):
        _run(widget_helpers._enrich_lead_from_message(
            tenant_id=TENANT, session_id=SESSION,
            raw_text="x", regex_extracted=regex,
        ))
    leads_tbl = db.table("leads")
    assert leads_tbl.update.called, "expected leads.update() call"
    payload = leads_tbl.update.call_args.args[0]
    assert payload.get("name") == "Sara Kim", payload
    assert payload.get("phone") == "(555) 867-5309", payload
    assert payload.get("areas_of_interest") == "autopilot plan", payload
    assert payload.get("timeline") == "by June", payload


def test_respects_regex_wins_policy():
    regex = {"name": "Bob", "email": "bob@example.com"}
    existing_lead = {"id": "lead_1", "client_id": TENANT,
                     "name": "Bob", "email": "bob@example.com", "phone": None}
    db = _fake_db_with_lead(existing_lead)
    with (
        patch("backend.services.structured_extractor.extract_structured",
              return_value={"name": "Robert Smith", "email": "bob@example.com",
                            "phone": "555-1212", "interest": None,
                            "timeline": None, "budget": None, "source": None}),
        patch("backend.routers.widget_lead_helpers.get_service_supabase", return_value=db),
        patch("backend.routers.widget_lead_helpers.log_activity"),
    ):
        _run(widget_helpers._enrich_lead_from_message(
            tenant_id=TENANT, session_id=SESSION,
            raw_text="x", regex_extracted=regex,
        ))
    leads_tbl = db.table("leads")
    payload = leads_tbl.update.call_args.args[0]
    assert payload.get("name") != "Robert Smith", payload
    assert payload.get("phone") == "555-1212", payload


def test_activity_log_written_with_fields_added():
    regex = {"email": "sara@example.com"}
    existing_lead = {"id": "lead_1", "client_id": TENANT,
                     "name": None, "email": "sara@example.com"}
    db = _fake_db_with_lead(existing_lead)
    with (
        patch("backend.services.structured_extractor.extract_structured",
              return_value={"name": "Sara Kim", "email": "sara@example.com",
                            "phone": None, "interest": "autopilot",
                            "timeline": None, "budget": None, "source": None}),
        patch("backend.routers.widget_lead_helpers.get_service_supabase", return_value=db),
        patch("backend.routers.widget_lead_helpers.log_activity") as mock_log,
    ):
        _run(widget_helpers._enrich_lead_from_message(
            tenant_id=TENANT, session_id=SESSION,
            raw_text="x", regex_extracted=regex,
        ))
    assert mock_log.called, "expected log_activity() call"
    kw = mock_log.call_args.kwargs
    assert kw.get("activity_type") == "lead_enriched", kw
    assert kw.get("tenant_id") == TENANT
    assert kw.get("lead_id") == "lead_1"
    meta = kw.get("metadata") or {}
    assert "fields_added" in meta
    assert "name" in set(meta["fields_added"])
    assert meta.get("session_id") == SESSION


def test_extractor_value_error_does_not_crash():
    regex = {"email": "sara@example.com"}
    db = _fake_db_with_lead(None)
    with (
        patch("backend.services.structured_extractor.extract_structured",
              side_effect=ValueError("invalid JSON")),
        patch("backend.routers.widget_lead_helpers.get_service_supabase", return_value=db),
        patch("backend.routers.widget_lead_helpers.log_activity") as mock_log,
    ):
        _run(widget_helpers._enrich_lead_from_message(
            tenant_id=TENANT, session_id=SESSION,
            raw_text="x", regex_extracted=regex,
        ))
    leads_tbl = db.table("leads")
    assert not leads_tbl.update.called
    assert not mock_log.called


def test_extractor_unexpected_exception_does_not_crash():
    regex = {"email": "sara@example.com"}
    db = _fake_db_with_lead(None)
    with (
        patch("backend.services.structured_extractor.extract_structured",
              side_effect=RuntimeError("anthropic timeout")),
        patch("backend.routers.widget_lead_helpers.get_service_supabase", return_value=db),
        patch("backend.routers.widget_lead_helpers.log_activity") as mock_log,
    ):
        _run(widget_helpers._enrich_lead_from_message(
            tenant_id=TENANT, session_id=SESSION,
            raw_text="x", regex_extracted=regex,
        ))
    leads_tbl = db.table("leads")
    assert not leads_tbl.update.called
    assert not mock_log.called


def test_handles_clean_dict_from_extractor():
    regex = {"email": "sara@example.com"}
    existing_lead = {"id": "lead_1", "client_id": TENANT,
                     "name": None, "email": "sara@example.com"}
    db = _fake_db_with_lead(existing_lead)
    with (
        patch("backend.services.structured_extractor.extract_structured",
              return_value={"name": "Sara", "email": "sara@example.com",
                            "phone": None, "interest": None,
                            "timeline": None, "budget": None, "source": None}),
        patch("backend.routers.widget_lead_helpers.get_service_supabase", return_value=db),
        patch("backend.routers.widget_lead_helpers.log_activity"),
    ):
        _run(widget_helpers._enrich_lead_from_message(
            tenant_id=TENANT, session_id=SESSION,
            raw_text="x", regex_extracted=regex,
        ))
    leads_tbl = db.table("leads")
    payload = leads_tbl.update.call_args.args[0]
    assert payload.get("name") == "Sara", payload


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def main() -> int:
    tests = [
        test_helper_is_importable,
        test_extractor_returns_nothing_new,
        test_no_email_or_phone_skips_with_no_db_call,
        test_lead_not_found_skips_update,
        test_fills_missing_fields,
        test_respects_regex_wins_policy,
        test_activity_log_written_with_fields_added,
        test_extractor_value_error_does_not_crash,
        test_extractor_unexpected_exception_does_not_crash,
        test_handles_clean_dict_from_extractor,
    ]
    passed = 0
    failed = 0
    for fn in tests:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
            passed += 1
        except Exception:
            print(f"FAIL  {fn.__name__}")
            traceback.print_exc()
            failed += 1
    print(f"\n{passed}/{len(tests)} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
