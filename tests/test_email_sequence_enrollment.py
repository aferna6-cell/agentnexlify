"""Unit tests for backend.services.email_sequence_enrollment.

Covers: happy path, conflict path (duplicate enrollment), upsert DB error,
existing-enrollment lookup error, and the async wrapper
``enroll_lead_in_sequences``.
"""

from unittest.mock import MagicMock, patch

import pytest

from backend.services.email_sequence_enrollment import (
    enroll_lead_in_sequence,
    enroll_lead_in_sequences,
)


def _chain(data=None, *, count=None):
    """Chainable mock whose .execute() returns a result with .data + .count."""
    ch = MagicMock()
    for m in ("select", "insert", "upsert", "update", "eq", "lte", "limit", "order"):
        getattr(ch, m).return_value = ch
    res = MagicMock()
    res.data = data
    res.count = count
    ch.execute.return_value = res
    return ch


def _chain_raises(exc):
    ch = MagicMock()
    for m in ("select", "insert", "upsert", "update", "eq", "lte", "limit", "order"):
        getattr(ch, m).return_value = ch
    ch.execute.side_effect = exc
    return ch


def test_happy_path_returns_enrollment_id_and_schedules_steps():
    upsert_chain = _chain([{"id": "enr1"}])
    insert_chain1 = _chain([{"id": "send1"}])
    insert_chain2 = _chain([{"id": "send2"}])
    db = MagicMock()
    db.table.side_effect = [upsert_chain, insert_chain1, insert_chain2]

    steps = [
        {"id": "step1", "delay_days": 0, "delay_hours": 0, "is_active": True},
        {"id": "step2", "delay_days": 1, "delay_hours": 0, "is_active": True},
    ]

    out = enroll_lead_in_sequence(db, "seq1", steps, "lead1", "t1")

    assert out == "enr1"
    upsert_chain.upsert.assert_called_once()
    upsert_payload = upsert_chain.upsert.call_args[0][0]
    assert upsert_payload["sequence_id"] == "seq1"
    assert upsert_payload["lead_id"] == "lead1"
    assert upsert_payload["tenant_id"] == "t1"
    assert upsert_payload["status"] == "active"

    # Both active steps scheduled
    insert_chain1.insert.assert_called_once()
    insert_chain2.insert.assert_called_once()


def test_inactive_steps_are_skipped():
    upsert_chain = _chain([{"id": "enr1"}])
    insert_chain = _chain([{"id": "send1"}])
    db = MagicMock()
    db.table.side_effect = [upsert_chain, insert_chain]

    steps = [
        {"id": "step1", "delay_days": 0, "is_active": True},
        {"id": "step2", "delay_days": 1, "is_active": False},
    ]
    out = enroll_lead_in_sequence(db, "seq1", steps, "lead1", "t1")

    assert out == "enr1"
    # Only one insert call -> only step1 scheduled
    insert_chain.insert.assert_called_once()
    inserted_step = insert_chain.insert.call_args[0][0]
    assert inserted_step["step_id"] == "step1"


def test_conflict_returns_existing_enrollment_id():
    upsert_chain = _chain([])  # ignore_duplicates -> empty data on conflict
    existing_chain = _chain([{"id": "existing-enr"}])
    db = MagicMock()
    db.table.side_effect = [upsert_chain, existing_chain]

    out = enroll_lead_in_sequence(db, "seq1", [], "lead1", "t1")

    assert out == "existing-enr"


def test_conflict_with_no_existing_row_returns_none():
    upsert_chain = _chain([])
    existing_chain = _chain([])
    db = MagicMock()
    db.table.side_effect = [upsert_chain, existing_chain]

    out = enroll_lead_in_sequence(db, "seq1", [], "lead1", "t1")
    assert out is None


def test_upsert_db_error_returns_none():
    upsert_chain = _chain_raises(RuntimeError("db down"))
    db = MagicMock()
    db.table.return_value = upsert_chain

    out = enroll_lead_in_sequence(db, "seq1", [], "lead1", "t1")
    assert out is None


def test_existing_lookup_error_returns_none():
    upsert_chain = _chain([])
    existing_chain = _chain_raises(RuntimeError("select failed"))
    db = MagicMock()
    db.table.side_effect = [upsert_chain, existing_chain]

    out = enroll_lead_in_sequence(db, "seq1", [], "lead1", "t1")
    assert out is None


def test_step_schedule_error_does_not_break_enrollment():
    """If scheduling one step fails, enrollment still returns successfully."""
    upsert_chain = _chain([{"id": "enr1"}])
    bad_insert = _chain_raises(RuntimeError("insert blocked"))
    db = MagicMock()
    db.table.side_effect = [upsert_chain, bad_insert]

    steps = [{"id": "step1", "delay_days": 0, "is_active": True}]
    out = enroll_lead_in_sequence(db, "seq1", steps, "lead1", "t1")
    assert out == "enr1"


@pytest.mark.asyncio
async def test_enroll_lead_in_sequences_no_active_sequences():
    """Should return silently when tenant has no lead_captured sequences."""
    seq_chain = _chain([])
    fake_db = MagicMock()
    fake_db.table.return_value = seq_chain

    enroll_calls: list[tuple] = []

    def track(*args, **kwargs):
        enroll_calls.append((args, kwargs))
        return "enr-x"

    with patch(
        "backend.services.email_sequence_enrollment.get_service_supabase",
        return_value=fake_db,
    ), patch(
        "backend.services.email_sequence_enrollment.enroll_lead_in_sequence",
        side_effect=track,
    ):
        await enroll_lead_in_sequences("t1", "lead1")

    # Observable: zero enrollment work was performed.
    assert enroll_calls == []


@pytest.mark.asyncio
async def test_enroll_lead_in_sequences_enrolls_each_active_sequence():
    seq_chain = _chain([{"id": "seq1"}, {"id": "seq2"}])
    steps_chain_1 = _chain([{"id": "step1", "is_active": True, "delay_days": 0}])
    steps_chain_2 = _chain([{"id": "step2", "is_active": True, "delay_days": 0}])
    fake_db = MagicMock()
    fake_db.table.side_effect = [seq_chain, steps_chain_1, steps_chain_2]

    called_with = []

    def fake_enroll(db, sequence_id, steps, lead_id, tenant_id):
        called_with.append((sequence_id, steps, lead_id, tenant_id))
        return "enr-" + sequence_id

    with patch(
        "backend.services.email_sequence_enrollment.get_service_supabase",
        return_value=fake_db,
    ), patch(
        "backend.services.email_sequence_enrollment.enroll_lead_in_sequence",
        side_effect=fake_enroll,
    ):
        await enroll_lead_in_sequences("t1", "lead1")

    assert {c[0] for c in called_with} == {"seq1", "seq2"}


@pytest.mark.asyncio
async def test_enroll_lead_in_sequences_sequences_query_error_returns_silently():
    bad_chain = _chain_raises(RuntimeError("supabase down"))
    fake_db = MagicMock()
    fake_db.table.return_value = bad_chain

    with patch(
        "backend.services.email_sequence_enrollment.get_service_supabase",
        return_value=fake_db,
    ):
        # Should not raise
        await enroll_lead_in_sequences("t1", "lead1")
