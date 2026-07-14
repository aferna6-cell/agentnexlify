"""Reviews AI (review_responder) — unit tests.

Contracts:
  - draft_response drafts via llm_runtime and inserts status='draft'
  - tone instruction is apologetic for low ratings, gracious for high ratings
  - draft_response is a no-op (returns None) on missing/invalid input
  - draft_response never raises: LLM failure or DB failure -> None
  - approve_response flips draft -> approved, records approver + approved_at
  - approve_response is blocked (no-op) unless current status is 'draft'
  - reject_response flips draft -> rejected, records approver
  - reject_response is blocked (no-op) unless current status is 'draft'
  - there is NO code path that posts a response without approval:
      * post_response_stub always raises NotImplementedError
      * post_response_stub is never called from anywhere else in the module
      * no code path ever sets status='posted'
"""

import asyncio
import inspect
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import backend.services.review_responder as review_responder
from backend.services.review_responder import (
    approve_response,
    draft_response,
    post_response_stub,
    reject_response,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _db_mock(business_name="Acme Plumbing", business_type="plumbing"):
    """Mock for the raw `db` argument — used only for the tenants lookup."""
    db = MagicMock()
    tenant_chain = MagicMock()
    for m in ["select", "eq", "limit"]:
        getattr(tenant_chain, m).return_value = tenant_chain
    tenant_chain.execute.return_value = MagicMock(
        data=[{"business_name": business_name, "business_type": business_type}]
    )
    db.table.return_value = tenant_chain
    return db


def _insert_chain(inserted_row):
    """Mock for tenant_table(...).insert(row).execute() used by draft_response."""
    chain = MagicMock()
    chain.insert.return_value = chain
    chain.execute.return_value = MagicMock(data=[inserted_row])
    return chain


def _lookup_update_chain(existing_row, updated_row=None, found=True):
    """Mock for the select-then-update sequence used by approve/reject.

    First .execute() (the select lookup) returns `existing_row` (or none when
    found=False). Second .execute() (the update) returns `updated_row`.
    """
    chain = MagicMock()
    for m in ["select", "eq", "limit", "update"]:
        getattr(chain, m).return_value = chain

    calls = {"n": 0}

    def _execute():
        calls["n"] += 1
        if calls["n"] == 1:
            return MagicMock(data=[existing_row] if found else [])
        return MagicMock(data=[updated_row or existing_row])

    chain.execute.side_effect = _execute
    return chain


# ---------------------------------------------------------------------------
# draft_response — happy path
# ---------------------------------------------------------------------------


@patch("backend.services.review_responder.tenant_table")
@patch("backend.services.review_responder.call_claude_messages", new_callable=AsyncMock)
def test_draft_response_stores_status_draft(mock_llm, mock_tt):
    mock_llm.return_value = MagicMock(text="Thanks for the kind words!")
    inserted_row = {
        "id": "resp-1",
        "tenant_id": "t1",
        "review_text": "Great service!",
        "review_rating": 5,
        "draft_reply": "Thanks for the kind words!",
        "status": "draft",
    }
    mock_tt.return_value = _insert_chain(inserted_row)
    db = _db_mock()

    result = asyncio.run(
        draft_response(
            db,
            tenant_id="t1",
            review={"review_text": "Great service!", "review_rating": 5},
        )
    )

    assert result["status"] == "draft"
    assert result["draft_reply"] == "Thanks for the kind words!"
    mock_tt.assert_called_once_with(db, "review_responses", "t1")
    inserted_arg = mock_tt.return_value.insert.call_args.args[0]
    assert inserted_arg["status"] == "draft"
    assert inserted_arg["review_rating"] == 5


@patch("backend.services.review_responder.tenant_table")
@patch("backend.services.review_responder.call_claude_messages", new_callable=AsyncMock)
def test_draft_response_passes_optional_review_id_and_external_ref(mock_llm, mock_tt):
    mock_llm.return_value = MagicMock(text="Thanks!")
    mock_tt.return_value = _insert_chain({"id": "resp-1", "status": "draft"})
    db = _db_mock()

    asyncio.run(
        draft_response(
            db,
            tenant_id="t1",
            review={
                "review_text": "Great service!",
                "review_rating": 5,
                "review_id": "review-uuid-1",
                "external_ref": "google-ext-1",
            },
        )
    )

    inserted_arg = mock_tt.return_value.insert.call_args.args[0]
    assert inserted_arg["review_id"] == "review-uuid-1"
    assert inserted_arg["external_ref"] == "google-ext-1"


# ---------------------------------------------------------------------------
# draft_response — tone matches rating
# ---------------------------------------------------------------------------


@patch("backend.services.review_responder.tenant_table")
@patch("backend.services.review_responder.call_claude_messages", new_callable=AsyncMock)
def test_draft_response_low_rating_uses_apologetic_tone(mock_llm, mock_tt):
    mock_llm.return_value = MagicMock(text="We're sorry to hear this.")
    mock_tt.return_value = _insert_chain({"id": "resp-2", "status": "draft"})
    db = _db_mock()

    asyncio.run(
        draft_response(
            db,
            tenant_id="t1",
            review={"review_text": "Terrible experience.", "review_rating": 1},
        )
    )

    _, kwargs = mock_llm.call_args
    assert "apolog" in kwargs["system"].lower()


@patch("backend.services.review_responder.tenant_table")
@patch("backend.services.review_responder.call_claude_messages", new_callable=AsyncMock)
def test_draft_response_high_rating_uses_gracious_tone(mock_llm, mock_tt):
    mock_llm.return_value = MagicMock(text="Thank you so much!")
    mock_tt.return_value = _insert_chain({"id": "resp-3", "status": "draft"})
    db = _db_mock()

    asyncio.run(
        draft_response(
            db,
            tenant_id="t1",
            review={"review_text": "Loved it, five stars!", "review_rating": 5},
        )
    )

    _, kwargs = mock_llm.call_args
    assert "gracious" in kwargs["system"].lower()


# ---------------------------------------------------------------------------
# draft_response — invalid input, no LLM call, no insert
# ---------------------------------------------------------------------------


@patch("backend.services.review_responder.tenant_table")
@patch("backend.services.review_responder.call_claude_messages", new_callable=AsyncMock)
def test_draft_response_missing_text_returns_none(mock_llm, mock_tt):
    db = _db_mock()
    result = asyncio.run(
        draft_response(db, tenant_id="t1", review={"review_text": "", "review_rating": 5})
    )
    assert result is None
    mock_llm.assert_not_awaited()
    mock_tt.assert_not_called()


@patch("backend.services.review_responder.tenant_table")
@patch("backend.services.review_responder.call_claude_messages", new_callable=AsyncMock)
def test_draft_response_invalid_rating_returns_none(mock_llm, mock_tt):
    db = _db_mock()
    result = asyncio.run(
        draft_response(db, tenant_id="t1", review={"review_text": "ok", "review_rating": 7})
    )
    assert result is None
    mock_llm.assert_not_awaited()
    mock_tt.assert_not_called()


# ---------------------------------------------------------------------------
# draft_response — never raises on failure
# ---------------------------------------------------------------------------


@patch("backend.services.review_responder.tenant_table")
@patch("backend.services.review_responder.call_claude_messages", new_callable=AsyncMock)
def test_draft_response_llm_failure_returns_none(mock_llm, mock_tt):
    mock_llm.side_effect = RuntimeError("anthropic down")
    db = _db_mock()
    result = asyncio.run(
        draft_response(db, tenant_id="t1", review={"review_text": "ok", "review_rating": 5})
    )
    assert result is None
    mock_tt.assert_not_called()


@patch("backend.services.review_responder.tenant_table")
@patch("backend.services.review_responder.call_claude_messages", new_callable=AsyncMock)
def test_draft_response_db_insert_failure_returns_none(mock_llm, mock_tt):
    mock_llm.return_value = MagicMock(text="Thanks!")
    mock_tt.side_effect = RuntimeError("db down")
    db = _db_mock()
    result = asyncio.run(
        draft_response(db, tenant_id="t1", review={"review_text": "ok", "review_rating": 5})
    )
    assert result is None


# ---------------------------------------------------------------------------
# approve_response
# ---------------------------------------------------------------------------


@patch("backend.services.review_responder.tenant_table")
def test_approve_response_flips_draft_to_approved(mock_tt):
    existing = {
        "id": "resp-1",
        "tenant_id": "t1",
        "status": "draft",
        "review_text": "x",
        "review_rating": 5,
        "draft_reply": "y",
    }
    updated = {**existing, "status": "approved", "approved_by": "owner@acme.com"}
    mock_tt.return_value = _lookup_update_chain(existing, updated)
    db = MagicMock()

    result = asyncio.run(
        approve_response(db, tenant_id="t1", response_id="resp-1", approver="owner@acme.com")
    )

    assert result["status"] == "approved"
    update_arg = mock_tt.return_value.update.call_args.args[0]
    assert update_arg["status"] == "approved"
    assert update_arg["approved_by"] == "owner@acme.com"
    assert "approved_at" in update_arg


@patch("backend.services.review_responder.tenant_table")
def test_approve_response_blocked_when_not_draft(mock_tt):
    existing = {"id": "resp-1", "status": "approved"}
    mock_tt.return_value = _lookup_update_chain(existing)
    db = MagicMock()

    result = asyncio.run(
        approve_response(db, tenant_id="t1", response_id="resp-1", approver="owner@acme.com")
    )

    assert result is None
    mock_tt.return_value.update.assert_not_called()


@patch("backend.services.review_responder.tenant_table")
def test_approve_response_not_found_returns_none(mock_tt):
    mock_tt.return_value = _lookup_update_chain({}, found=False)
    db = MagicMock()

    result = asyncio.run(
        approve_response(db, tenant_id="t1", response_id="missing", approver="owner@acme.com")
    )

    assert result is None


# ---------------------------------------------------------------------------
# reject_response
# ---------------------------------------------------------------------------


@patch("backend.services.review_responder.tenant_table")
def test_reject_response_flips_draft_to_rejected(mock_tt):
    existing = {"id": "resp-1", "tenant_id": "t1", "status": "draft"}
    updated = {**existing, "status": "rejected", "approved_by": "owner@acme.com"}
    mock_tt.return_value = _lookup_update_chain(existing, updated)
    db = MagicMock()

    result = asyncio.run(
        reject_response(db, tenant_id="t1", response_id="resp-1", approver="owner@acme.com")
    )

    assert result["status"] == "rejected"
    update_arg = mock_tt.return_value.update.call_args.args[0]
    assert update_arg["status"] == "rejected"
    assert update_arg["approved_by"] == "owner@acme.com"
    # approved_at is only set on the approve path, never on reject
    assert "approved_at" not in update_arg


@patch("backend.services.review_responder.tenant_table")
def test_reject_response_blocked_when_not_draft(mock_tt):
    existing = {"id": "resp-1", "status": "rejected"}
    mock_tt.return_value = _lookup_update_chain(existing)
    db = MagicMock()

    result = asyncio.run(
        reject_response(db, tenant_id="t1", response_id="resp-1", approver="owner@acme.com")
    )

    assert result is None
    mock_tt.return_value.update.assert_not_called()


# ---------------------------------------------------------------------------
# Invariant: no code path posts without approval
# ---------------------------------------------------------------------------


def test_post_response_stub_always_raises_not_implemented():
    with pytest.raises(NotImplementedError):
        post_response_stub()


def test_post_response_stub_never_called_internally():
    """post_response_stub must only ever be invoked by a human-triggered,
    not-yet-built posting step. No function in this module (draft_response,
    approve_response, reject_response, _flip_status) may call it."""
    source = inspect.getsource(review_responder)
    # The only occurrence of the call-shaped substring must be the def line
    # itself — proves no internal caller invokes it.
    assert source.count("post_response_stub(") == 1
    assert "def post_response_stub(" in source


def test_no_code_path_ever_sets_status_posted():
    """Static guarantee: 'posted' is never assigned as a status value anywhere
    in the module (only referenced in _VALID_STATUSES and docs, matching the
    CHECK constraint in migrations/166_review_responses.sql) — only
    'draft' -> 'approved' / 'rejected' transitions actually happen. Posting
    requires a future, separate implementation."""
    source = inspect.getsource(review_responder)
    # No dict/kwarg assignment ever sets a status field to "posted".
    assert 'status": "posted"' not in source
    assert "status='posted'" not in source
    assert 'new_status="posted"' not in source
    assert "new_status='posted'" not in source


def test_approve_and_reject_are_the_only_status_transitions_from_draft():
    """_flip_status is the single place status changes after creation, and
    it is only ever called with 'approved' or 'rejected'."""
    import backend.services.review_responder as module

    approve_src = inspect.getsource(module.approve_response)
    reject_src = inspect.getsource(module.reject_response)
    assert 'new_status="approved"' in approve_src
    assert 'new_status="rejected"' in reject_src
