"""Attribution flows through the LIVE widget lead-capture path (#T2).

The live widget never POSTs to /api/v1/widget/lead — it POSTs to
/api/v1/widget/chat, and the backend extracts a lead from the conversation via
`_capture_leads_from_session`. This test proves the first-touch attribution
the widget sends on the chat request lands (sanitized) on the newly-created
lead row, so attribution is real end-to-end and not stored only on a
never-called endpoint.
"""

import os

os.environ["TESTING"] = "1"

import asyncio
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import backend.routers.widget_lead_helpers as helpers

TENANT = "tenant-attr-001"


def _run_capture(attribution):
    """Drive _capture_leads_from_session down the new-lead insert path and
    return the lead_fields payload passed to tenant_insert."""
    captured = {}

    # One user message carrying an email → triggers the new-lead insert path.
    history = [{"role": "user", "content": "hi, reach me at buyer@example.com"}]

    db = MagicMock()

    dedup = MagicMock()
    dedup.eq.return_value = dedup
    dedup.limit.return_value = dedup
    dedup.execute.return_value = MagicMock(data=[])  # no existing lead → insert

    def _fake_insert(_db, _table, _tenant_id, fields):
        captured["fields"] = fields
        chain = MagicMock()
        chain.execute.return_value = MagicMock(data=[{"id": "lead-attr-xyz"}])
        return chain

    with patch("backend.routers.widget_chat_helpers._load_chat_history", return_value=history), \
         patch.object(helpers, "get_service_supabase", return_value=db), \
         patch.object(helpers, "tenant_select", return_value=dedup), \
         patch.object(helpers, "tenant_insert", side_effect=_fake_insert):
        asyncio.run(
            helpers._capture_leads_from_session(TENANT, "sess-attr", "not-a-uuid", attribution)
        )
    return captured.get("fields")


def test_attribution_lands_sanitized_on_new_lead():
    fields = _run_capture({
        "utm_source": "google",
        "utm_medium": "cpc",
        "utm_campaign": "spring",
        "referrer": "https://google.com/",
        "landing_path": "/plumbers",
        "source": "google",
        "evil_key": "dropped",   # unknown key must be stripped by the sanitizer
    })
    assert fields is not None, "expected a new-lead insert"
    assert fields["client_id"] == TENANT  # live schema: client_id, not tenant_id
    attr = fields.get("attribution")
    assert attr is not None
    assert attr["utm_source"] == "google"
    assert attr["landing_path"] == "/plumbers"
    assert "evil_key" not in attr  # sanitizer keeps only the known keys


def test_no_attribution_omits_the_field():
    fields = _run_capture(None)
    assert fields is not None
    assert "attribution" not in fields  # nothing to store → key absent


def test_garbage_attribution_is_dropped_not_crash():
    fields = _run_capture("not-a-dict")
    assert fields is not None
    assert "attribution" not in fields  # sanitizer returns None → key absent, no raise
