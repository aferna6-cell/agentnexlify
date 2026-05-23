"""Unit tests for invoice_numbering — sequential invoice number generation."""

from unittest.mock import MagicMock

import pytest

from backend.services.invoice_numbering import get_next_invoice_number


def _mock_db_returning(data):
    db = MagicMock()
    table = MagicMock()
    for m in ["select", "eq", "order", "limit"]:
        getattr(table, m).return_value = table
    result = MagicMock()
    result.data = data
    table.execute.return_value = result
    db.table.return_value = table
    return db


@pytest.mark.asyncio
async def test_first_invoice_uses_seq_1():
    db = _mock_db_returning([])
    num = await get_next_invoice_number(db, "tenant-abc")
    assert num == "INV-TENA-001"


@pytest.mark.asyncio
async def test_increments_from_last():
    db = _mock_db_returning([{"invoice_number": "INV-TENA-007"}])
    num = await get_next_invoice_number(db, "tenant-abc")
    assert num == "INV-TENA-008"


@pytest.mark.asyncio
async def test_attempt_offsets_sequence():
    db = _mock_db_returning([{"invoice_number": "INV-TENA-007"}])
    num = await get_next_invoice_number(db, "tenant-abc", attempt=2)
    assert num == "INV-TENA-010"


@pytest.mark.asyncio
async def test_unparseable_last_number_resets_to_one():
    db = _mock_db_returning([{"invoice_number": "BOGUS"}])
    num = await get_next_invoice_number(db, "tenant-abc")
    assert num == "INV-TENA-001"


@pytest.mark.asyncio
async def test_db_exception_falls_back_to_one():
    db = MagicMock()
    db.table.side_effect = RuntimeError("db down")
    num = await get_next_invoice_number(db, "tenant-abc")
    assert num == "INV-TENA-001"


@pytest.mark.asyncio
async def test_short_tenant_id_padded_prefix():
    db = _mock_db_returning([])
    num = await get_next_invoice_number(db, "ab")
    assert num.startswith("INV-AB-")
