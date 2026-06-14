"""Review requester (Agent OS review-request draft) — unit tests.

Contracts:
  - compose_review_sms builds a friendly SMS with business_name + customer first name
  - compose_review_sms includes review_link when provided; omits it when None
  - create_review_request_draft is a no-op when customer_phone is empty
  - pending_approval status -> draft filed, dispatch NOT called
  - approved status -> draft filed, dispatch called
  - dedupe: if run already exists for appointment_id, returns existing run id
  - DB failures never raise; function returns None on fatal errors
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, call, patch

from backend.services.review_requester import (
    compose_review_sms,
    create_review_request_draft,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tenant_table_mock(run_id="run-rr-1", dedupe_hit=False):
    """Chainable tenant_table mock.

    .execute() returns a row with id=run_id for insert calls.
    For the dedupe select, returns data=[{"id": run_id}] when dedupe_hit=True,
    else returns data=[].
    """
    chain = MagicMock()
    for m in ["insert", "select", "eq", "filter", "limit", "update", "order"]:
        getattr(chain, m).return_value = chain

    if dedupe_hit:
        chain.execute.return_value = MagicMock(data=[{"id": run_id}])
    else:
        # First call is dedupe select (returns empty), subsequent calls return run_id
        _calls = [0]

        def _execute():
            _calls[0] += 1
            if _calls[0] == 1:
                # dedupe select
                return MagicMock(data=[])
            return MagicMock(data=[{"id": run_id}])

        chain.execute.side_effect = _execute

    return chain


# ---------------------------------------------------------------------------
# compose_review_sms
# ---------------------------------------------------------------------------


def test_compose_review_sms_with_link():
    text = compose_review_sms("Acme Plumbing", "Jane", "https://g.co/review/acme")
    assert "Jane" in text
    assert "Acme Plumbing" in text
    assert "https://g.co/review/acme" in text


def test_compose_review_sms_without_link():
    text = compose_review_sms("Acme Plumbing", "Jane", None)
    assert "Jane" in text
    assert "Acme Plumbing" in text
    assert "http" not in text


def test_compose_review_sms_no_name_graceful():
    text = compose_review_sms("Acme", "", "https://g.co/review")
    # No crash, still contains business name and link
    assert "Acme" in text
    assert "https://g.co/review" in text


def test_compose_review_sms_three_sentences_max():
    text = compose_review_sms("Acme", "Bob", "https://g.co/review")
    # Simple length guard — SMS should stay reasonable
    assert len(text) <= 400


# ---------------------------------------------------------------------------
# no phone -> no-op
# ---------------------------------------------------------------------------


def test_no_phone_is_noop():
    result = asyncio.run(
        create_review_request_draft(
            MagicMock(),
            tenant_id="t1",
            appointment_id="appt-1",
            lead_id="lead-1",
            customer_name="Jane Doe",
            customer_phone="",
            business_name="Acme",
            google_review_link="https://g.co/review",
        )
    )
    assert result is None


# ---------------------------------------------------------------------------
# pending_approval -> draft filed, dispatch NOT called
# ---------------------------------------------------------------------------


@patch("backend.services.review_requester.queue_action_for_run", new_callable=AsyncMock)
@patch(
    "backend.services.review_requester.resolve_deliverable_status",
    return_value="pending_approval",
)
@patch("backend.services.review_requester.tenant_table")
def test_pending_draft_filed_without_dispatch(mock_tt, mock_resolve, mock_queue):
    mock_tt.return_value = _tenant_table_mock()

    run_id = asyncio.run(
        create_review_request_draft(
            MagicMock(),
            tenant_id="t1",
            appointment_id="appt-42",
            lead_id="lead-5",
            customer_name="Jane Doe",
            customer_phone="+15551112222",
            business_name="Acme Plumbing",
            google_review_link="https://g.co/review/acme",
        )
    )

    assert run_id == "run-rr-1"
    mock_queue.assert_not_awaited()

    # Confirm the inserted run row has correct shape
    inserted_rows = [c.args[0] for c in mock_tt.return_value.insert.call_args_list]
    run_rows = [r for r in inserted_rows if r.get("action_type") == "sms.send"]
    assert len(run_rows) == 1
    run = run_rows[0]
    assert run["agent_name"] == "review_requester"
    assert run["deliverable_status"] == "pending_approval"
    assert run["deliverable"]["channel"] == "sms"
    assert "+15551112222" in run["deliverable"]["body"]
    assert run["deliverable"]["metadata"]["recipient"] == "+15551112222"
    assert run["deliverable"]["metadata"]["appointment_id"] == "appt-42"
    assert run["deliverable"]["metadata"]["source"] == "review_request"
    mock_resolve.assert_called_once()


# ---------------------------------------------------------------------------
# approved -> draft filed AND dispatch called
# ---------------------------------------------------------------------------


@patch("backend.services.review_requester.queue_action_for_run", new_callable=AsyncMock)
@patch(
    "backend.services.review_requester.resolve_deliverable_status",
    return_value="approved",
)
@patch("backend.services.review_requester.tenant_table")
def test_auto_approved_draft_dispatches(mock_tt, mock_resolve, mock_queue):
    mock_tt.return_value = _tenant_table_mock(run_id="run-rr-2")

    run_id = asyncio.run(
        create_review_request_draft(
            MagicMock(),
            tenant_id="t1",
            appointment_id="appt-99",
            lead_id=None,
            customer_name="Bob Smith",
            customer_phone="+15559998888",
            business_name="Bob's HVAC",
            google_review_link=None,
        )
    )

    assert run_id == "run-rr-2"
    mock_queue.assert_awaited_once()
    # Confirm no-review-link note in metadata
    inserted_rows = [c.args[0] for c in mock_tt.return_value.insert.call_args_list]
    run_rows = [r for r in inserted_rows if r.get("action_type") == "sms.send"]
    assert run_rows[0]["deliverable"]["metadata"].get("note") == "no review link configured"


# ---------------------------------------------------------------------------
# dedupe: existing run for same appointment -> return existing id, no new insert
# ---------------------------------------------------------------------------


@patch("backend.services.review_requester.queue_action_for_run", new_callable=AsyncMock)
@patch(
    "backend.services.review_requester.resolve_deliverable_status",
    return_value="pending_approval",
)
@patch("backend.services.review_requester.tenant_table")
def test_dedupe_returns_existing_run_id(mock_tt, mock_resolve, mock_queue):
    mock_tt.return_value = _tenant_table_mock(run_id="run-existing", dedupe_hit=True)

    run_id = asyncio.run(
        create_review_request_draft(
            MagicMock(),
            tenant_id="t1",
            appointment_id="appt-dupe",
            lead_id="lead-1",
            customer_name="Jane",
            customer_phone="+15551234567",
            business_name="Acme",
            google_review_link=None,
        )
    )

    assert run_id == "run-existing"
    # resolve and queue should not have been called since we short-circuited
    mock_resolve.assert_not_called()
    mock_queue.assert_not_awaited()
    # No sms.send insert should have happened
    inserted_rows = [c.args[0] for c in mock_tt.return_value.insert.call_args_list]
    run_rows = [r for r in inserted_rows if r.get("action_type") == "sms.send"]
    assert len(run_rows) == 0


# ---------------------------------------------------------------------------
# DB failure never raises
# ---------------------------------------------------------------------------


@patch("backend.services.review_requester.queue_action_for_run", new_callable=AsyncMock)
@patch(
    "backend.services.review_requester.resolve_deliverable_status",
    return_value="pending_approval",
)
@patch("backend.services.review_requester.tenant_table")
def test_db_failure_never_raises(mock_tt, mock_resolve, mock_queue):
    mock_tt.side_effect = RuntimeError("db down")

    result = asyncio.run(
        create_review_request_draft(
            MagicMock(),
            tenant_id="t1",
            appointment_id="appt-fail",
            lead_id=None,
            customer_name="Jane",
            customer_phone="+15550001111",
            business_name="Acme",
            google_review_link=None,
        )
    )

    assert result is None
