"""Regression test for Phase 5 cleanup: new regex-captured leads must tag
`enrichment_source='regex'` so the LeadsPage dashboard can count regex vs
AI captures accurately.

Migration 105 added `leads.enrichment_source` with documented values
`'regex' | 'ai' | NULL`. Before this fix, only the AI enrichment helper
(`_enrich_lead_from_message` at widget_helpers.py:~1605) set the column
to 'ai'. Regex-captured leads were left NULL, so the dashboard always
showed 0% regex captures — a silent dashboard gap.

The fix is a 1-line addition to the INSERT payload in
`_capture_leads_from_session`. The `_enrich_lead_from_message` helper
still overwrites the column to 'ai' when it adds new fields, so the
correct lifecycle is: insert='regex' → (optional) enrichment='ai'.

Contract pinned by this test:
  1. New leads created via regex capture carry `enrichment_source='regex'`
  2. The value is added to the insert payload BEFORE tenant_insert runs
  3. No other invariants change (client_id, status, source stay as-is)
"""

import asyncio
from unittest.mock import MagicMock, patch

from backend.routers import widget_lead_helpers as widget_helpers


def test_regex_captured_lead_tagged_enrichment_source_regex():
    """New leads inserted by _capture_leads_from_session carry
    enrichment_source='regex'. Regression for migration 105 gap."""
    captured_payload: dict = {}

    def insert_spy(db, table_name, tenant_id, rows):
        assert table_name == "leads", f"expected leads table, got {table_name}"
        captured_payload.update(rows)
        result = MagicMock()
        result.execute.return_value = MagicMock(data=[{"id": "new_lead_id"}])
        return result

    # tenant_select returns empty → no existing lead → insert path
    select_result = MagicMock()
    select_result.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=[])

    fake_messages = [
        {"role": "user", "content": "Hi it's Sara at sara@example.com"}
    ]

    # Patch downstream post-insert hooks (trigger_sequence, enroll_lead_in_sequences,
    # score_lead_background) so they don't try to reach Supabase. These fire from
    # _capture_leads_from_session AFTER the insert and are caught internally, but
    # patching keeps test output clean.
    async def _noop_async(*a, **kw):
        return None

    def _noop_sync(*a, **kw):
        return None

    with (
        patch("backend.routers.widget_lead_helpers.get_service_supabase", return_value=MagicMock()),
        patch("backend.routers.widget_lead_helpers.tenant_insert", side_effect=insert_spy),
        patch("backend.routers.widget_lead_helpers.tenant_select", return_value=select_result),
        patch("backend.routers.widget_lead_helpers.tenant_update"),
        patch("backend.routers.widget_chat_helpers._load_chat_history", return_value=fake_messages),
        patch(
            "backend.routers.widget_lead_helpers._extract_lead_info",
            return_value={"name": "Sara", "email": "sara@example.com"},
        ),
        patch("backend.routers.widget_lead_helpers._extract_service_interest", return_value=None),
        patch("backend.routers.widget_lead_helpers._build_conversation_summary", return_value=""),
        patch("backend.routers.widget_lead_helpers._extract_tags_from_conversation", return_value=[]),
        patch("backend.routers.widget_lead_helpers.log_activity"),
        patch("backend.routers.widget_lead_helpers.fire_event_background"),
        patch("backend.services.automation_engine.trigger_sequence", new=_noop_async),
        patch("backend.routers.email_enrollment.enroll_lead_in_sequences", new=_noop_async),
        # score_lead_background is imported at module top in widget_helpers (line 24)
        # so we patch where it's USED, not where it's defined.
        patch("backend.routers.widget_lead_helpers.score_lead_background", new=_noop_sync),
        patch("backend.routers.widget_lead_helpers._send_new_lead_sms_notification", new=_noop_async),
        patch("backend.routers.widget_lead_helpers._send_new_lead_email_notification", new=_noop_async),
    ):
        asyncio.run(widget_helpers._capture_leads_from_session(
            tenant_id="11111111-1111-1111-1111-111111111111",
            session_id="sess-regex-tag-test",
            conversation_id="22222222-2222-2222-2222-222222222222",
        ))

    assert captured_payload.get("enrichment_source") == "regex", (
        f"Expected new regex-captured lead to be tagged enrichment_source='regex'. "
        f"Got payload: {captured_payload}"
    )
    # Invariants — don't regress the rest of the payload shape
    assert captured_payload.get("client_id") == "11111111-1111-1111-1111-111111111111"
    assert captured_payload.get("status") == "new"
    assert captured_payload.get("source") == "widget"
    assert captured_payload.get("email") == "sara@example.com"
    assert captured_payload.get("name") == "Sara"
