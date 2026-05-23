"""Unit tests for invoice_payments_service — mark paid, partial payment flow."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from backend.services.invoice_payments_service import (
    mark_invoice_as_paid,
    record_partial_payment_amount,
)


def _mock_chain(returned_data):
    """Return a (db, chain) pair where chain.execute() yields ``returned_data``."""
    chain = MagicMock()
    for m in ["select", "update", "eq", "limit"]:
        getattr(chain, m).return_value = chain
    result = MagicMock()
    result.data = returned_data
    chain.execute.return_value = result
    return chain


# --- mark_invoice_as_paid ---


@pytest.mark.asyncio
async def test_mark_paid_happy_path_fires_webhook():
    select_chain = _mock_chain([{"status": "sent"}])
    paid_row = {
        "id": "inv1",
        "invoice_number": "INV-001",
        "total": 100.0,
        "lead_id": "lead1",
    }
    update_chain = _mock_chain([paid_row])

    with patch(
        "backend.services.invoice_payments_service.tenant_table",
        side_effect=[select_chain, update_chain],
    ) as tt, patch(
        "backend.services.invoice_payments_service.fire_event_background"
    ) as fire:
        out = await mark_invoice_as_paid(MagicMock(), "t1", "inv1", "card")

    assert out == paid_row
    assert tt.call_count == 2
    fire.assert_called_once()
    args, _ = fire.call_args
    assert args[0] == "t1"
    assert args[1] == "invoice.paid"
    payload = args[2]
    assert payload["invoice_id"] == "inv1"
    assert payload["payment_method"] == "card"
    assert payload["lead_id"] == "lead1"


@pytest.mark.asyncio
async def test_mark_paid_writes_payment_method_when_provided():
    select_chain = _mock_chain([{"status": "draft"}])
    update_chain = _mock_chain([{"id": "inv1", "invoice_number": "X"}])

    with patch(
        "backend.services.invoice_payments_service.tenant_table",
        side_effect=[select_chain, update_chain],
    ), patch("backend.services.invoice_payments_service.fire_event_background"):
        await mark_invoice_as_paid(MagicMock(), "t1", "inv1", "ach")

    update_call = update_chain.update.call_args[0][0]
    assert update_call["status"] == "paid"
    assert update_call["payment_method"] == "ach"
    assert "paid_at" in update_call
    assert "updated_at" in update_call


@pytest.mark.asyncio
async def test_mark_paid_omits_payment_method_when_none():
    select_chain = _mock_chain([{"status": "sent"}])
    update_chain = _mock_chain([{"id": "inv1"}])

    with patch(
        "backend.services.invoice_payments_service.tenant_table",
        side_effect=[select_chain, update_chain],
    ), patch("backend.services.invoice_payments_service.fire_event_background"):
        await mark_invoice_as_paid(MagicMock(), "t1", "inv1", None)

    update_call = update_chain.update.call_args[0][0]
    assert "payment_method" not in update_call


@pytest.mark.asyncio
async def test_mark_paid_404_when_invoice_missing():
    select_chain = _mock_chain([])
    with patch(
        "backend.services.invoice_payments_service.tenant_table",
        return_value=select_chain,
    ):
        with pytest.raises(HTTPException) as exc:
            await mark_invoice_as_paid(MagicMock(), "t1", "missing", None)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_mark_paid_400_when_cancelled():
    select_chain = _mock_chain([{"status": "cancelled"}])
    with patch(
        "backend.services.invoice_payments_service.tenant_table",
        return_value=select_chain,
    ):
        with pytest.raises(HTTPException) as exc:
            await mark_invoice_as_paid(MagicMock(), "t1", "inv1", None)
    assert exc.value.status_code == 400
    assert "cancelled" in exc.value.detail


@pytest.mark.asyncio
async def test_mark_paid_400_when_already_paid():
    select_chain = _mock_chain([{"status": "paid"}])
    with patch(
        "backend.services.invoice_payments_service.tenant_table",
        return_value=select_chain,
    ):
        with pytest.raises(HTTPException) as exc:
            await mark_invoice_as_paid(MagicMock(), "t1", "inv1", None)
    assert exc.value.status_code == 400
    assert "already" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_mark_paid_500_when_select_fails():
    select_chain = _mock_chain([])
    select_chain.execute.side_effect = RuntimeError("db down")
    with patch(
        "backend.services.invoice_payments_service.tenant_table",
        return_value=select_chain,
    ):
        with pytest.raises(HTTPException) as exc:
            await mark_invoice_as_paid(MagicMock(), "t1", "inv1", None)
    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_mark_paid_500_when_update_fails():
    select_chain = _mock_chain([{"status": "sent"}])
    update_chain = _mock_chain([])
    update_chain.execute.side_effect = RuntimeError("write failed")

    with patch(
        "backend.services.invoice_payments_service.tenant_table",
        side_effect=[select_chain, update_chain],
    ):
        with pytest.raises(HTTPException) as exc:
            await mark_invoice_as_paid(MagicMock(), "t1", "inv1", None)
    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_mark_paid_404_when_update_returns_no_rows():
    select_chain = _mock_chain([{"status": "sent"}])
    update_chain = _mock_chain([])

    with patch(
        "backend.services.invoice_payments_service.tenant_table",
        side_effect=[select_chain, update_chain],
    ):
        with pytest.raises(HTTPException) as exc:
            await mark_invoice_as_paid(MagicMock(), "t1", "inv1", None)
    assert exc.value.status_code == 404


# --- record_partial_payment_amount ---


@pytest.mark.asyncio
async def test_partial_payment_updates_amount_paid_only():
    select_chain = _mock_chain(
        [{"total": 100.0, "amount_paid": 25.0, "status": "sent"}]
    )
    update_chain = _mock_chain([{"id": "inv1", "amount_paid": 50.0}])

    with patch(
        "backend.services.invoice_payments_service.tenant_table",
        side_effect=[select_chain, update_chain],
    ):
        out = await record_partial_payment_amount(
            MagicMock(), "t1", "inv1", 25.0, "card"
        )

    assert out["amount_paid"] == 50.0
    update_call = update_chain.update.call_args[0][0]
    assert update_call["amount_paid"] == 50.0
    assert "status" not in update_call


@pytest.mark.asyncio
async def test_partial_payment_auto_promotes_to_paid_when_fully_covered():
    select_chain = _mock_chain(
        [{"total": 100.0, "amount_paid": 75.0, "status": "sent"}]
    )
    update_chain = _mock_chain([{"id": "inv1", "status": "paid"}])

    with patch(
        "backend.services.invoice_payments_service.tenant_table",
        side_effect=[select_chain, update_chain],
    ):
        await record_partial_payment_amount(MagicMock(), "t1", "inv1", 25.0, "card")

    update_call = update_chain.update.call_args[0][0]
    assert update_call["status"] == "paid"
    assert update_call["payment_method"] == "card"
    assert update_call["amount_paid"] == 100.0
    assert "paid_at" in update_call


@pytest.mark.asyncio
async def test_partial_payment_clamps_to_total_when_overpay_within_tolerance():
    select_chain = _mock_chain(
        [{"total": 100.0, "amount_paid": 90.0, "status": "sent"}]
    )
    update_chain = _mock_chain([{"id": "inv1"}])

    with patch(
        "backend.services.invoice_payments_service.tenant_table",
        side_effect=[select_chain, update_chain],
    ):
        await record_partial_payment_amount(MagicMock(), "t1", "inv1", 10.005, None)

    update_call = update_chain.update.call_args[0][0]
    assert update_call["amount_paid"] == 100.0


@pytest.mark.asyncio
async def test_partial_payment_404_when_missing():
    select_chain = _mock_chain([])
    with patch(
        "backend.services.invoice_payments_service.tenant_table",
        return_value=select_chain,
    ):
        with pytest.raises(HTTPException) as exc:
            await record_partial_payment_amount(
                MagicMock(), "t1", "missing", 10.0, None
            )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_partial_payment_400_when_already_paid():
    select_chain = _mock_chain(
        [{"total": 100.0, "amount_paid": 100.0, "status": "paid"}]
    )
    with patch(
        "backend.services.invoice_payments_service.tenant_table",
        return_value=select_chain,
    ):
        with pytest.raises(HTTPException) as exc:
            await record_partial_payment_amount(MagicMock(), "t1", "inv1", 50.0, None)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_partial_payment_400_when_cancelled():
    select_chain = _mock_chain(
        [{"total": 100.0, "amount_paid": 0.0, "status": "cancelled"}]
    )
    with patch(
        "backend.services.invoice_payments_service.tenant_table",
        return_value=select_chain,
    ):
        with pytest.raises(HTTPException) as exc:
            await record_partial_payment_amount(MagicMock(), "t1", "inv1", 50.0, None)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_partial_payment_400_when_exceeds_remaining():
    select_chain = _mock_chain(
        [{"total": 100.0, "amount_paid": 50.0, "status": "sent"}]
    )
    with patch(
        "backend.services.invoice_payments_service.tenant_table",
        return_value=select_chain,
    ):
        with pytest.raises(HTTPException) as exc:
            await record_partial_payment_amount(MagicMock(), "t1", "inv1", 75.0, None)
    assert exc.value.status_code == 400
    assert "remaining balance" in exc.value.detail


@pytest.mark.asyncio
async def test_partial_payment_500_when_update_returns_no_data():
    select_chain = _mock_chain(
        [{"total": 100.0, "amount_paid": 25.0, "status": "sent"}]
    )
    update_chain = _mock_chain([])

    with patch(
        "backend.services.invoice_payments_service.tenant_table",
        side_effect=[select_chain, update_chain],
    ):
        with pytest.raises(HTTPException) as exc:
            await record_partial_payment_amount(MagicMock(), "t1", "inv1", 25.0, None)
    assert exc.value.status_code == 500
