"""Missed-call recovery (G3 Phase 1) — voicemail -> Agent OS callback draft.

Contracts:
  - compose_callback_text builds an SMS-sized draft from summary/follow_up
  - create_missed_call_followup files an os_agent_runs deliverable
    (channel sms, action sms.send) gated by resolve_deliverable_status
  - auto-approved drafts dispatch through queue_action_for_run
  - no caller phone -> no-op; DB failures never raise
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from backend.services.voice_recovery import (
    compose_callback_text,
    create_missed_call_followup,
)


def _tenant_table_mock(run_id="run-1"):
    """Chainable tenant_table mock whose insert().execute() returns a row."""
    chain = MagicMock()
    for m in ["insert", "select", "eq", "limit", "update", "order"]:
        getattr(chain, m).return_value = chain
    chain.execute.return_value = MagicMock(data=[{"id": run_id}])
    return chain


def test_compose_callback_text_uses_follow_up():
    text = compose_callback_text("Acme Plumbing", "Caller needs a quote", "We can quote your water heater tomorrow.")
    assert "Acme Plumbing" in text
    assert "water heater" in text
    assert "Reply here" in text


def test_compose_callback_text_falls_back_gracefully():
    text = compose_callback_text("Acme", "", "")
    assert "Acme" in text
    assert "How can we help" in text


def test_no_caller_is_noop():
    result = asyncio.run(
        create_missed_call_followup(
            MagicMock(),
            tenant_id="t1",
            business_name="Acme",
            caller="",
            call_id="c1",
            lead_id=None,
            summary="s",
            follow_up="f",
        )
    )
    assert result is None


@patch("backend.services.voice_recovery.queue_action_for_run", new_callable=AsyncMock)
@patch("backend.services.voice_recovery.resolve_deliverable_status", return_value="pending_approval")
@patch("backend.services.voice_recovery.tenant_table")
def test_pending_draft_filed_without_dispatch(mock_tt, mock_resolve, mock_queue):
    mock_tt.return_value = _tenant_table_mock()

    run_id = asyncio.run(
        create_missed_call_followup(
            MagicMock(),
            tenant_id="t1",
            business_name="Acme",
            caller="+15551112222",
            call_id="call-9",
            lead_id="lead-3",
            summary="Needs a Tuesday appointment",
            follow_up="Offer Tuesday 2pm or 4pm",
            transcript_excerpt="Hi, calling about booking Tuesday",
        )
    )

    assert run_id == "run-1"
    mock_queue.assert_not_awaited()
    # The run insert carried the sms deliverable, gated by lead_nurture rules
    inserted_rows = [c.args[0] for c in mock_tt.return_value.insert.call_args_list]
    run_rows = [r for r in inserted_rows if r.get("action_type") == "sms.send"]
    assert len(run_rows) == 1
    run = run_rows[0]
    assert run["agent_name"] == "lead_nurture"
    assert run["deliverable_status"] == "pending_approval"
    assert run["deliverable"]["channel"] == "sms"
    assert "+15551112222" in run["deliverable"]["body"]
    assert run["deliverable"]["metadata"]["recipient"] == "+15551112222"
    mock_resolve.assert_called_once()


@patch("backend.services.voice_recovery.queue_action_for_run", new_callable=AsyncMock)
@patch("backend.services.voice_recovery.resolve_deliverable_status", return_value="approved")
@patch("backend.services.voice_recovery.tenant_table")
def test_auto_approved_draft_dispatches(mock_tt, mock_resolve, mock_queue):
    mock_tt.return_value = _tenant_table_mock(run_id="run-2")

    run_id = asyncio.run(
        create_missed_call_followup(
            MagicMock(),
            tenant_id="t1",
            business_name="Acme",
            caller="+15551112222",
            call_id="call-9",
            lead_id=None,
            summary="s",
            follow_up="f",
        )
    )

    assert run_id == "run-2"
    mock_queue.assert_awaited_once()


@patch("backend.services.voice_recovery.queue_action_for_run", new_callable=AsyncMock)
@patch("backend.services.voice_recovery.resolve_deliverable_status", return_value="pending_approval")
@patch("backend.services.voice_recovery.tenant_table")
def test_db_failure_never_raises(mock_tt, mock_resolve, mock_queue):
    mock_tt.side_effect = RuntimeError("db down")
    result = asyncio.run(
        create_missed_call_followup(
            MagicMock(),
            tenant_id="t1",
            business_name="Acme",
            caller="+15551112222",
            call_id=None,
            lead_id=None,
            summary="s",
            follow_up="f",
        )
    )
    assert result is None
