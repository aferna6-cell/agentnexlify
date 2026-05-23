"""Unit tests for backend.services.email_sequence_processor.

Covers ``_process_one_send`` outcomes (sent / skipped-step-missing /
skipped-lead-missing / skipped-unsubscribed / skipped-no-email / failed-send),
``process_due_sends`` batch counting, ``_maybe_complete_enrollment``, and
``increment_runs_total``.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services.email_sequence_processor import (
    _maybe_complete_enrollment,
    _process_one_send,
    increment_runs_total,
    process_due_sends,
)


def _chain(data=None, *, count=None):
    ch = MagicMock()
    for m in (
        "select",
        "insert",
        "upsert",
        "update",
        "eq",
        "lte",
        "limit",
        "order",
    ):
        getattr(ch, m).return_value = ch
    res = MagicMock()
    res.data = data
    res.count = count
    ch.execute.return_value = res
    return ch


def _chain_raises(exc):
    ch = MagicMock()
    for m in (
        "select",
        "insert",
        "upsert",
        "update",
        "eq",
        "lte",
        "limit",
        "order",
    ):
        getattr(ch, m).return_value = ch
    ch.execute.side_effect = exc
    return ch


_SEND_ROW = {
    "id": "send1",
    "step_id": "step1",
    "lead_id": "lead1",
    "tenant_id": "t1",
    "enrollment_id": "enr1",
}

_STEP_ROW = {
    "subject": "Hello {{name}}",
    "body": "Hi {{name}} from {{business_name}}",
    "email_type": "email",
    "step_order": 1,
    "sequence_id": "seq1",
}


# ---------------------------------------------------------------------------
# _process_one_send
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_one_send_happy_path_marks_sent_and_increments_runs():
    step_chain = _chain([_STEP_ROW])
    lead_chain = _chain([{"id": "lead1", "name": "Ada", "email": "ada@x.com"}])
    tenant_chain = _chain([{"business_name": "Acme"}])
    update_sent_chain = _chain([{"id": "send1"}])
    complete_remaining_chain = _chain([], count=0)
    complete_update_chain = _chain([{"id": "enr1"}])

    db = MagicMock()
    db.table.side_effect = [
        step_chain,
        lead_chain,
        tenant_chain,
        update_sent_chain,
        complete_remaining_chain,
        complete_update_chain,
    ]

    with patch(
        "backend.services.email_sequence_processor.send_email",
        AsyncMock(return_value={"success": True}),
    ), patch(
        "backend.services.email_sequence_processor.render_template",
        side_effect=lambda tpl, ctx: tpl,
    ), patch(
        "backend.services.email_sequence_processor.build_unsubscribe_url",
        return_value="https://unsub",
    ), patch(
        "backend.services.email_sequence_processor.log_activity"
    ) as log_activity_mock, patch(
        "backend.services.email_sequence_processor.increment_runs_total"
    ) as inc_runs_mock:
        outcome = await _process_one_send(db, _SEND_ROW)

    assert outcome == "sent"
    log_activity_mock.assert_called_once()
    inc_runs_mock.assert_called_once_with("t1", "email_sequence")


@pytest.mark.asyncio
async def test_process_one_send_step_not_found_returns_skipped():
    step_chain = _chain([])  # empty -> step missing
    update_chain = _chain([{"id": "send1"}])
    db = MagicMock()
    db.table.side_effect = [step_chain, update_chain]

    outcome = await _process_one_send(db, _SEND_ROW)
    assert outcome == "skipped"


@pytest.mark.asyncio
async def test_process_one_send_step_query_raises_returns_failed():
    bad_step = _chain_raises(RuntimeError("step query failed"))
    update_chain = _chain([{"id": "send1"}])
    db = MagicMock()
    db.table.side_effect = [bad_step, update_chain]

    outcome = await _process_one_send(db, _SEND_ROW)
    assert outcome == "failed"


@pytest.mark.asyncio
async def test_process_one_send_lead_not_found_returns_skipped():
    step_chain = _chain([_STEP_ROW])
    lead_chain = _chain([])
    update_chain = _chain([{"id": "send1"}])
    db = MagicMock()
    db.table.side_effect = [step_chain, lead_chain, update_chain]

    outcome = await _process_one_send(db, _SEND_ROW)
    assert outcome == "skipped"


@pytest.mark.asyncio
async def test_process_one_send_unsubscribed_lead_skipped():
    step_chain = _chain([_STEP_ROW])
    lead_chain = _chain(
        [{"id": "lead1", "name": "Ada", "email": "a@x.com", "unsubscribed": True}]
    )
    update_chain = _chain([{"id": "send1"}])
    db = MagicMock()
    db.table.side_effect = [step_chain, lead_chain, update_chain]

    outcome = await _process_one_send(db, _SEND_ROW)
    assert outcome == "skipped"


@pytest.mark.asyncio
async def test_process_one_send_no_email_address_skipped():
    step_chain = _chain([_STEP_ROW])
    lead_chain = _chain([{"id": "lead1", "name": "Ada", "email": ""}])
    update_chain = _chain([{"id": "send1"}])
    db = MagicMock()
    db.table.side_effect = [step_chain, lead_chain, update_chain]

    outcome = await _process_one_send(db, _SEND_ROW)
    assert outcome == "skipped"


@pytest.mark.asyncio
async def test_process_one_send_send_failure_returns_failed():
    step_chain = _chain([_STEP_ROW])
    lead_chain = _chain([{"id": "lead1", "name": "Ada", "email": "a@x.com"}])
    tenant_chain = _chain([{"business_name": "Acme"}])
    update_chain = _chain([{"id": "send1"}])
    db = MagicMock()
    db.table.side_effect = [step_chain, lead_chain, tenant_chain, update_chain]

    with patch(
        "backend.services.email_sequence_processor.send_email",
        AsyncMock(return_value={"success": False, "detail": "smtp down"}),
    ), patch(
        "backend.services.email_sequence_processor.render_template",
        side_effect=lambda tpl, ctx: tpl,
    ), patch(
        "backend.services.email_sequence_processor.build_unsubscribe_url",
        return_value="https://unsub",
    ):
        outcome = await _process_one_send(db, _SEND_ROW)

    assert outcome == "failed"


@pytest.mark.asyncio
async def test_process_one_send_send_exception_returns_failed():
    step_chain = _chain([_STEP_ROW])
    lead_chain = _chain([{"id": "lead1", "name": "Ada", "email": "a@x.com"}])
    tenant_chain = _chain([{"business_name": "Acme"}])
    update_chain = _chain([{"id": "send1"}])
    db = MagicMock()
    db.table.side_effect = [step_chain, lead_chain, tenant_chain, update_chain]

    with patch(
        "backend.services.email_sequence_processor.send_email",
        AsyncMock(side_effect=RuntimeError("blew up")),
    ), patch(
        "backend.services.email_sequence_processor.render_template",
        side_effect=lambda tpl, ctx: tpl,
    ), patch(
        "backend.services.email_sequence_processor.build_unsubscribe_url",
        return_value="https://unsub",
    ):
        outcome = await _process_one_send(db, _SEND_ROW)

    assert outcome == "failed"


# ---------------------------------------------------------------------------
# process_due_sends
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_due_sends_no_due_returns_zero_counts():
    due_chain = _chain([])
    db = MagicMock()
    db.table.return_value = due_chain

    counts = await process_due_sends(db)
    assert counts == {"processed": 0, "sent": 0, "failed": 0, "skipped": 0}


@pytest.mark.asyncio
async def test_process_due_sends_aggregates_outcomes():
    rows = [dict(_SEND_ROW, id=f"send{i}") for i in range(3)]
    due_chain = _chain(rows)
    db = MagicMock()
    db.table.return_value = due_chain

    outcomes = iter(["sent", "failed", "skipped"])

    async def fake_process(_db, _row):
        return next(outcomes)

    with patch(
        "backend.services.email_sequence_processor._process_one_send",
        side_effect=fake_process,
    ):
        counts = await process_due_sends(db)

    assert counts == {"processed": 3, "sent": 1, "failed": 1, "skipped": 1}


@pytest.mark.asyncio
async def test_process_due_sends_query_error_propagates():
    bad_chain = _chain_raises(RuntimeError("supabase down"))
    db = MagicMock()
    db.table.return_value = bad_chain

    with pytest.raises(RuntimeError):
        await process_due_sends(db)


# ---------------------------------------------------------------------------
# _maybe_complete_enrollment
# ---------------------------------------------------------------------------


def test_maybe_complete_marks_completed_when_no_pending():
    remaining_chain = _chain([], count=0)
    update_chain = _chain([{"id": "enr1"}])
    db = MagicMock()
    db.table.side_effect = [remaining_chain, update_chain]

    _maybe_complete_enrollment(db, "enr1", "seq1")

    update_chain.update.assert_called_once()
    payload = update_chain.update.call_args[0][0]
    assert payload["status"] == "completed"
    assert "completed_at" in payload


def test_maybe_complete_does_nothing_when_pending_remain():
    remaining_chain = _chain([], count=3)
    tables_called: list[str] = []
    db = MagicMock()
    db.table.side_effect = lambda name: (tables_called.append(name) or remaining_chain)

    _maybe_complete_enrollment(db, "enr1", "seq1")
    # Observable: only the pending-count table was queried, no update branch reached
    assert tables_called == ["email_sequence_sends"]


def test_maybe_complete_swallows_errors():
    bad_chain = _chain_raises(RuntimeError("count failed"))
    db = MagicMock()
    db.table.return_value = bad_chain

    # Must not raise
    _maybe_complete_enrollment(db, "enr1", "seq1")


# ---------------------------------------------------------------------------
# increment_runs_total
# ---------------------------------------------------------------------------


def test_increment_runs_total_happy_path():
    select_chain = _chain([{"id": "a1", "runs_total": 5}])
    update_payloads: list[dict] = []
    update_chain = MagicMock()
    update_chain.update = lambda payload: (update_payloads.append(payload) or update_chain)
    update_chain.eq.return_value = update_chain
    update_chain.execute.return_value = MagicMock(data=[{"id": "a1"}])
    fake_db = MagicMock()
    fake_db.table.side_effect = [select_chain, update_chain]

    with patch(
        "backend.services.email_sequence_processor.get_service_supabase",
        return_value=fake_db,
    ):
        increment_runs_total("t1", "email_sequence")

    # Observable: runs_total bumped from 5 to 6
    assert update_payloads == [{"runs_total": 6}]


def test_increment_runs_total_no_matching_row_is_noop():
    select_chain = _chain([])  # no automation row
    tables_called: list[str] = []
    fake_db = MagicMock()
    fake_db.table.side_effect = lambda name: (tables_called.append(name) or select_chain)

    with patch(
        "backend.services.email_sequence_processor.get_service_supabase",
        return_value=fake_db,
    ):
        increment_runs_total("t1", "email_sequence")

    # Observable: only the lookup query ran, no update branch reached
    assert tables_called == ["automations"]


def test_increment_runs_total_swallows_errors():
    bad_chain = _chain_raises(RuntimeError("db down"))
    fake_db = MagicMock()
    fake_db.table.return_value = bad_chain

    with patch(
        "backend.services.email_sequence_processor.get_service_supabase",
        return_value=fake_db,
    ):
        # Should not raise
        increment_runs_total("t1", "email_sequence")
