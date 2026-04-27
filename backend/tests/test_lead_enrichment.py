"""Tests for `_enrich_lead_from_message` background helper.

The helper lives in backend.routers.widget_lead_helpers. It is a non-blocking
background task that runs the structured_extractor managed agent on a
single user message, merges any new fields into the existing lead row,
and logs an activity entry. It must NEVER raise — FastAPI's
BackgroundTasks would propagate the exception otherwise.

Implementation notes verified against the real codebase (NOT spec):
  - structured_extractor.extract_structured raises ValueError, NOT a
    custom ExtractorError class. The spec at specs/lead-parser-replacement_spec.md
    references ExtractorError but the real symbol does not exist —
    these tests pin the actual contract per Rule 10 (code is right
    until proven wrong).
  - leads table has no session_id column. Dedup uses email + client_id
    matching _capture_leads_from_session (line 1102 of widget_helpers.py).
    If neither regex nor extractor produced an email AND no phone, the
    helper skips because there's no safe key to dedup against.
  - Merge policy: regex wins on fields both populated (regex is literal
    and fast). Extractor only fills fields the regex left blank.
  - All Supabase access goes through tenant_update / tenant_select
    helpers from backend.services.tenant_scope.

Patching strategy mirrors test_widget_chat_fallback.py: patch the imported
names where they're USED, not where they're defined. e.g. the helper's
`get_service_supabase` is imported into widget_helpers, so we patch
`backend.routers.widget_lead_helpers.get_service_supabase`.
"""

from unittest.mock import MagicMock, patch

import pytest

from backend.routers import widget_lead_helpers as widget_helpers


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tenant_id():
    return "11111111-1111-1111-1111-111111111111"


@pytest.fixture
def session_id():
    return "sess-enrich-test"



def _fake_db_with_lead(lead: dict | None):
    """MagicMock Supabase client that returns `lead` for select queries
    and records calls for update assertions.

    Mirrors the pattern in test_lead_qualification._fake_supabase_for
    but keeps a single lead row and a single update sink.
    """
    db = MagicMock()
    tables: dict[str, MagicMock] = {}

    def _build_leads_tbl():
        tbl = MagicMock()
        select_chain = MagicMock()
        select_chain.data = [lead] if lead else []
        # tenant_select(db, "leads", tenant_id, "...").eq(col, val).limit(1).execute()
        tbl.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = select_chain
        # tenant_update(db, "leads", tenant_id, fields).eq("id", lead_id).execute()
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
# Helper presence sanity check (bare-minimum red-phase signal)
# ---------------------------------------------------------------------------


class TestHelperExists:
    def test_helper_is_importable(self):
        """If this fails, Phase 2 implementation hasn't shipped yet."""
        assert hasattr(widget_helpers, "_enrich_lead_from_message"), (
            "Phase 2 incomplete: backend/routers/widget_helpers.py is "
            "missing the `_enrich_lead_from_message` background helper."
        )


# ---------------------------------------------------------------------------
# Skip cases
# ---------------------------------------------------------------------------


class TestEnrichmentSkipPaths:
    """Cases where the helper should make zero DB writes."""

    def test_extractor_returns_nothing_new(self, tenant_id, session_id):
        """Extractor confirms what regex already had → no merge → no update."""
        regex = {"name": "Sara", "email": "sara@example.com", "phone": "555-1234"}
        existing_lead = {
            "id": "lead_1",
            "client_id": tenant_id,
            "name": "Sara",
            "email": "sara@example.com",
            "phone": "555-1234",
        }
        db = _fake_db_with_lead(existing_lead)

        with (
            patch(
                "backend.services.structured_extractor.extract_structured",
                return_value={"name": "Sara", "email": "sara@example.com",
                              "phone": "555-1234", "interest": None,
                              "timeline": None, "budget": None, "source": None},
            ),
            patch("backend.routers.widget_lead_helpers.get_service_supabase", return_value=db),
            patch("backend.routers.widget_lead_helpers.log_activity") as mock_log,
        ):
            result = widget_helpers._enrich_lead_from_message(
                tenant_id=tenant_id,
                session_id=session_id,
                raw_text="Hi I'm Sara at sara@example.com call 555-1234",
                regex_extracted=regex,
            )

        assert result is None
        # No update — fields all match
        leads_tbl = db.table("leads")
        leads_tbl.update.assert_not_called()
        mock_log.assert_not_called()

    def test_no_email_or_phone_skips_with_no_db_call(self, tenant_id, session_id):
        """Without email or phone in either dict, no safe dedup key → skip."""
        regex: dict[str, str] = {}
        db = _fake_db_with_lead(None)

        with (
            patch(
                "backend.services.structured_extractor.extract_structured",
                return_value={"interest": "haircut", "timeline": "next week",
                              "budget": None, "name": None, "email": None,
                              "phone": None, "source": None},
            ),
            patch("backend.routers.widget_lead_helpers.get_service_supabase", return_value=db),
            patch("backend.routers.widget_lead_helpers.log_activity") as mock_log,
        ):
            result = widget_helpers._enrich_lead_from_message(
                tenant_id=tenant_id,
                session_id=session_id,
                raw_text="Looking for a haircut next week",
                regex_extracted=regex,
            )

        assert result is None
        # No lookup, no update, no log
        db.table.assert_not_called()
        mock_log.assert_not_called()

    def test_lead_not_found_skips_update(self, tenant_id, session_id):
        """Race: regex_capture task hasn't created the lead yet. Skip cleanly."""
        regex = {"email": "ghost@example.com"}
        db = _fake_db_with_lead(None)  # select returns no rows

        with (
            patch(
                "backend.services.structured_extractor.extract_structured",
                return_value={"name": "Ghost", "interest": "consultation",
                              "email": None, "phone": None, "timeline": None,
                              "budget": None, "source": None},
            ),
            patch("backend.routers.widget_lead_helpers.get_service_supabase", return_value=db),
            patch("backend.routers.widget_lead_helpers.log_activity") as mock_log,
        ):
            result = widget_helpers._enrich_lead_from_message(
                tenant_id=tenant_id,
                session_id=session_id,
                raw_text="I'm Ghost looking for consultation",
                regex_extracted=regex,
            )

        assert result is None

        leads_tbl = db.table("leads")
        leads_tbl.update.assert_not_called()
        mock_log.assert_not_called()


# ---------------------------------------------------------------------------
# Merge + persist
# ---------------------------------------------------------------------------


class TestEnrichmentPersist:
    """Cases where the helper merges new fields and writes to leads."""

    def test_fills_missing_fields(self, tenant_id, session_id):
        """Regex got email only; extractor adds name + interest + timeline."""
        regex = {"email": "sara@example.com"}
        existing_lead = {
            "id": "lead_1",
            "client_id": tenant_id,
            "name": None,
            "email": "sara@example.com",
            "phone": None,
        }
        db = _fake_db_with_lead(existing_lead)

        with (
            patch(
                "backend.services.structured_extractor.extract_structured",
                return_value={
                    "name": "Sara Kim",
                    "email": "sara@example.com",
                    "phone": "(555) 867-5309",
                    "interest": "autopilot plan",
                    "timeline": "by June",
                    "budget": None,
                    "source": None,
                },
            ),
            patch("backend.routers.widget_lead_helpers.get_service_supabase", return_value=db),
            patch("backend.routers.widget_lead_helpers.log_activity"),
        ):
            widget_helpers._enrich_lead_from_message(
                tenant_id=tenant_id,
                session_id=session_id,
                raw_text=("Hi its Sara Kim, sara@example.com or (555) 867-5309, "
                          "looking for the autopilot plan by June"),
                regex_extracted=regex,
            )

        leads_tbl = db.table("leads")
        # update was called
        assert leads_tbl.update.called, "expected leads.update() call"
        update_payload = leads_tbl.update.call_args.args[0]
        # filled missing name
        assert update_payload.get("name") == "Sara Kim"
        # filled missing phone
        assert update_payload.get("phone") == "(555) 867-5309"
        # interest mapped to areas_of_interest (live schema column name)
        assert update_payload.get("areas_of_interest") == "autopilot plan"
        # timeline written through
        assert update_payload.get("timeline") == "by June"

    def test_respects_regex_wins_policy(self, tenant_id, session_id):
        """Both regex and extractor produced a name. Regex wins."""
        regex = {"name": "Bob", "email": "bob@example.com"}
        existing_lead = {
            "id": "lead_1",
            "client_id": tenant_id,
            "name": "Bob",
            "email": "bob@example.com",
            "phone": None,
        }
        db = _fake_db_with_lead(existing_lead)

        with (
            patch(
                "backend.services.structured_extractor.extract_structured",
                return_value={
                    "name": "Robert Smith",  # extractor disagrees — should be ignored
                    "email": "bob@example.com",
                    "phone": "555-1212",
                    "interest": None,
                    "timeline": None,
                    "budget": None,
                    "source": None,
                },
            ),
            patch("backend.routers.widget_lead_helpers.get_service_supabase", return_value=db),
            patch("backend.routers.widget_lead_helpers.log_activity"),
        ):
            widget_helpers._enrich_lead_from_message(
                tenant_id=tenant_id,
                session_id=session_id,
                raw_text="Hi Bob here at bob@example.com, also 555-1212",
                regex_extracted=regex,
            )

        leads_tbl = db.table("leads")
        update_payload = leads_tbl.update.call_args.args[0]
        # regex name wins — extractor's "Robert Smith" must NOT clobber it
        assert update_payload.get("name") != "Robert Smith"
        # phone was missing from regex AND from existing lead → extractor fills it
        assert update_payload.get("phone") == "555-1212"

    def test_activity_log_written_with_fields_added(self, tenant_id, session_id):
        """When merge produces new data, an activity_log row is emitted."""
        regex = {"email": "sara@example.com"}
        existing_lead = {
            "id": "lead_1",
            "client_id": tenant_id,
            "name": None,
            "email": "sara@example.com",
        }
        db = _fake_db_with_lead(existing_lead)

        with (
            patch(
                "backend.services.structured_extractor.extract_structured",
                return_value={
                    "name": "Sara Kim",
                    "email": "sara@example.com",
                    "phone": None,
                    "interest": "autopilot",
                    "timeline": None,
                    "budget": None,
                    "source": None,
                },
            ),
            patch("backend.routers.widget_lead_helpers.get_service_supabase", return_value=db),
            patch("backend.routers.widget_lead_helpers.log_activity") as mock_log,
        ):
            widget_helpers._enrich_lead_from_message(
                tenant_id=tenant_id,
                session_id=session_id,
                raw_text="Im Sara, sara@example.com, want autopilot",
                regex_extracted=regex,
            )

        assert mock_log.called, "expected log_activity() to be called when fields were added"
        log_kwargs = mock_log.call_args.kwargs
        assert log_kwargs.get("activity_type") == "lead_enriched"
        assert log_kwargs.get("tenant_id") == tenant_id
        assert log_kwargs.get("lead_id") == "lead_1"
        # metadata should record what got added
        meta = log_kwargs.get("metadata") or {}
        assert "fields_added" in meta
        # name and interest were genuinely added
        added = set(meta["fields_added"])
        assert "name" in added
        # session_id traceable for cross-ref to chat history
        assert meta.get("session_id") == session_id


# ---------------------------------------------------------------------------
# Failure modes — must NEVER raise
# ---------------------------------------------------------------------------


class TestEnrichmentNeverCrashes:
    """Background task contract: helper swallows all exceptions."""

    def test_extractor_value_error_does_not_crash(self, tenant_id, session_id):
        """Real extractor raises ValueError on parse failures — handle it."""
        regex = {"email": "sara@example.com"}
        db = _fake_db_with_lead(None)

        with (
            patch(
                "backend.services.structured_extractor.extract_structured",
                side_effect=ValueError("structured_extractor returned invalid JSON"),
            ),
            patch("backend.routers.widget_lead_helpers.get_service_supabase", return_value=db),
            patch("backend.routers.widget_lead_helpers.log_activity") as mock_log,
        ):
            # Must not raise.
            result = widget_helpers._enrich_lead_from_message(
                tenant_id=tenant_id,
                session_id=session_id,
                raw_text="garbage",
                regex_extracted=regex,
            )

        assert result is None
        # Defensive: no leads update, no activity_log
        leads_tbl = db.table("leads")
        leads_tbl.update.assert_not_called()
        mock_log.assert_not_called()

    def test_extractor_unexpected_exception_does_not_crash(self, tenant_id, session_id):
        """Network timeout, ManagedAgentNotConfigured, anything → silent log."""
        regex = {"email": "sara@example.com"}
        db = _fake_db_with_lead(None)

        with (
            patch(
                "backend.services.structured_extractor.extract_structured",
                side_effect=RuntimeError("anthropic upstream timeout"),
            ),
            patch("backend.routers.widget_lead_helpers.get_service_supabase", return_value=db),
            patch("backend.routers.widget_lead_helpers.log_activity") as mock_log,
        ):
            # Must not raise.
            result = widget_helpers._enrich_lead_from_message(
                tenant_id=tenant_id,
                session_id=session_id,
                raw_text="anything",
                regex_extracted=regex,
            )

        assert result is None
        leads_tbl = db.table("leads")
        leads_tbl.update.assert_not_called()
        mock_log.assert_not_called()

    def test_handles_fenced_json_via_extractor_contract(self, tenant_id, session_id):
        """If Haiku wraps JSON in fences, extract_structured already strips
        them (see _extract_json_from_reply in structured_extractor.py).
        From the helper's POV, success is success — pin that we do NOT
        re-parse or care what shape the raw reply was."""
        regex = {"email": "sara@example.com"}
        existing_lead = {
            "id": "lead_1",
            "client_id": tenant_id,
            "name": None,
            "email": "sara@example.com",
        }
        db = _fake_db_with_lead(existing_lead)

        with (
            # Simulate extract_structured already having stripped the fence
            # and returned a clean dict.
            patch(
                "backend.services.structured_extractor.extract_structured",
                return_value={
                    "name": "Sara",
                    "email": "sara@example.com",
                    "phone": None,
                    "interest": None,
                    "timeline": None,
                    "budget": None,
                    "source": None,
                },
            ),
            patch("backend.routers.widget_lead_helpers.get_service_supabase", return_value=db),
            patch("backend.routers.widget_lead_helpers.log_activity"),
        ):
            widget_helpers._enrich_lead_from_message(
                tenant_id=tenant_id,
                session_id=session_id,
                raw_text="anything",
                regex_extracted=regex,
            )

        # Update happened with the cleaned-up name
        leads_tbl = db.table("leads")
        update_payload = leads_tbl.update.call_args.args[0]
        assert update_payload.get("name") == "Sara"
