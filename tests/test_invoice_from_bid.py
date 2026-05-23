"""Unit tests for invoice_from_bid — bid-to-invoice conversion semantics."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from backend.services.invoice_from_bid import create_invoice_from_bid_for_tenant


def _chain(data):
    """Build a chainable mock whose .execute() returns a result with .data = data."""
    ch = MagicMock()
    for m in ("select", "insert", "eq", "limit"):
        getattr(ch, m).return_value = ch
    res = MagicMock()
    res.data = data
    ch.execute.return_value = res
    return ch


def _chain_raises(exc):
    """Chainable mock whose .execute() raises."""
    ch = MagicMock()
    for m in ("select", "insert", "eq", "limit"):
        getattr(ch, m).return_value = ch
    ch.execute.side_effect = exc
    return ch


def _patch_service(*, tenant_table_side_effect, totals=(100.0, 0.0, 100.0), invoice_number="INV-0001"):
    return (
        patch(
            "backend.services.invoice_from_bid.tenant_table",
            side_effect=tenant_table_side_effect,
        ),
        patch(
            "backend.services.invoice_from_bid.compute_invoice_totals",
            return_value=totals,
        ),
        patch(
            "backend.services.invoice_from_bid.get_next_invoice_number",
            AsyncMock(return_value=invoice_number),
        ),
    )


@pytest.mark.asyncio
async def test_happy_path_returns_created_invoice():
    bid_row = {
        "id": "bid1",
        "status": "accepted",
        "lead_id": "lead1",
        "title": "Roof repair",
        "items_json": [
            {"description": "Labor", "quantity": 2, "unit_price": 50},
        ],
    }
    bid_chain = _chain([bid_row])
    existing_chain = _chain([])
    inserted_invoice = {
        "id": "inv1",
        "invoice_number": "INV-0001",
        "total": 100.0,
        "status": "draft",
    }
    insert_chain = _chain([inserted_invoice])

    p1, p2, p3 = _patch_service(
        tenant_table_side_effect=[bid_chain, existing_chain, insert_chain]
    )
    with p1, p2, p3:
        out = await create_invoice_from_bid_for_tenant(MagicMock(), "t1", "bid1")

    assert out == inserted_invoice
    # Verify insert payload shape
    insert_chain.insert.assert_called_once()
    payload = insert_chain.insert.call_args[0][0]
    assert payload["tenant_id"] == "t1"
    assert payload["bid_id"] == "bid1"
    assert payload["lead_id"] == "lead1"
    assert payload["invoice_number"] == "INV-0001"
    assert payload["subtotal"] == 100.0
    assert payload["total"] == 100.0
    assert payload["tax_rate"] == 0.0
    assert payload["status"] == "draft"
    assert "Roof repair" in payload["notes"]
    assert payload["items_json"] == [
        {"description": "Labor", "quantity": 2, "unit_price": 50}
    ]


@pytest.mark.asyncio
async def test_404_when_bid_missing():
    bid_chain = _chain([])
    p1, p2, p3 = _patch_service(tenant_table_side_effect=[bid_chain])
    with p1, p2, p3:
        with pytest.raises(HTTPException) as exc_info:
            await create_invoice_from_bid_for_tenant(MagicMock(), "t1", "missing")
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_500_when_bid_fetch_raises():
    bid_chain = _chain_raises(RuntimeError("db blew up"))
    p1, p2, p3 = _patch_service(tenant_table_side_effect=[bid_chain])
    with p1, p2, p3:
        with pytest.raises(HTTPException) as exc_info:
            await create_invoice_from_bid_for_tenant(MagicMock(), "t1", "bid1")
    assert exc_info.value.status_code == 500


@pytest.mark.asyncio
async def test_400_when_bid_not_accepted():
    bid_chain = _chain([{"id": "bid1", "status": "pending"}])
    p1, p2, p3 = _patch_service(tenant_table_side_effect=[bid_chain])
    with p1, p2, p3:
        with pytest.raises(HTTPException) as exc_info:
            await create_invoice_from_bid_for_tenant(MagicMock(), "t1", "bid1")
    assert exc_info.value.status_code == 400
    assert "pending" in exc_info.value.detail


@pytest.mark.asyncio
async def test_409_when_invoice_already_exists_for_bid():
    bid_chain = _chain([{"id": "bid1", "status": "accepted", "items_json": []}])
    existing_chain = _chain([{"id": "inv-old", "invoice_number": "INV-9999"}])
    p1, p2, p3 = _patch_service(
        tenant_table_side_effect=[bid_chain, existing_chain]
    )
    with p1, p2, p3:
        with pytest.raises(HTTPException) as exc_info:
            await create_invoice_from_bid_for_tenant(MagicMock(), "t1", "bid1")
    assert exc_info.value.status_code == 409
    assert "INV-9999" in exc_info.value.detail


@pytest.mark.asyncio
async def test_duplicate_check_failure_is_best_effort_and_proceeds():
    """If the duplicate check query raises, log + proceed (no false 409)."""
    bid_row = {"id": "bid1", "status": "accepted", "items_json": []}
    bid_chain = _chain([bid_row])
    existing_chain = _chain_raises(RuntimeError("transient db error"))
    insert_chain = _chain([{"id": "inv1", "invoice_number": "INV-0001"}])

    p1, p2, p3 = _patch_service(
        tenant_table_side_effect=[bid_chain, existing_chain, insert_chain]
    )
    with p1, p2, p3:
        out = await create_invoice_from_bid_for_tenant(MagicMock(), "t1", "bid1")
    assert out["id"] == "inv1"


@pytest.mark.asyncio
async def test_500_when_insert_raises():
    bid_chain = _chain([{"id": "bid1", "status": "accepted", "items_json": []}])
    existing_chain = _chain([])
    insert_chain = _chain_raises(RuntimeError("insert failed"))

    p1, p2, p3 = _patch_service(
        tenant_table_side_effect=[bid_chain, existing_chain, insert_chain]
    )
    with p1, p2, p3:
        with pytest.raises(HTTPException) as exc_info:
            await create_invoice_from_bid_for_tenant(MagicMock(), "t1", "bid1")
    assert exc_info.value.status_code == 500


@pytest.mark.asyncio
async def test_500_when_insert_returns_empty():
    bid_chain = _chain([{"id": "bid1", "status": "accepted", "items_json": []}])
    existing_chain = _chain([])
    insert_chain = _chain([])  # no data returned

    p1, p2, p3 = _patch_service(
        tenant_table_side_effect=[bid_chain, existing_chain, insert_chain]
    )
    with p1, p2, p3:
        with pytest.raises(HTTPException) as exc_info:
            await create_invoice_from_bid_for_tenant(MagicMock(), "t1", "bid1")
    assert exc_info.value.status_code == 500


@pytest.mark.asyncio
async def test_items_normalized_with_defaults_when_fields_missing():
    """Items missing fields should fall back to defaults (description='', quantity=1, unit_price=0)."""
    bid_row = {
        "id": "bid1",
        "status": "accepted",
        "items_json": [{}, {"description": "Just a desc"}],
    }
    bid_chain = _chain([bid_row])
    existing_chain = _chain([])
    insert_chain = _chain([{"id": "inv1", "invoice_number": "INV-0001"}])

    p1, p2, p3 = _patch_service(
        tenant_table_side_effect=[bid_chain, existing_chain, insert_chain]
    )
    with p1, p2, p3:
        out = await create_invoice_from_bid_for_tenant(MagicMock(), "t1", "bid1")
    assert out["id"] == "inv1"

    payload = insert_chain.insert.call_args[0][0]
    assert payload["items_json"] == [
        {"description": "", "quantity": 1, "unit_price": 0},
        {"description": "Just a desc", "quantity": 1, "unit_price": 0},
    ]
