"""Unit tests for invoice_send — single-invoice send pipeline."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from backend.services.invoice_send import send_invoice_for_tenant


def _chain(data):
    ch = MagicMock()
    for m in ("select", "update", "eq", "limit"):
        getattr(ch, m).return_value = ch
    res = MagicMock()
    res.data = data
    ch.execute.return_value = res
    return ch


def _patches(*, tenant_table_side_effect, dispatch=None, payment_link=None):
    if dispatch is None:
        dispatch = AsyncMock(return_value=(True, True, []))
    if payment_link is None:
        payment_link = AsyncMock(return_value="https://pay.stripe/x")
    return (
        patch(
            "backend.services.invoice_send.tenant_table",
            side_effect=tenant_table_side_effect,
        ),
        patch(
            "backend.services.invoice_send.dispatch_invoice_channels", dispatch
        ),
        patch(
            "backend.services.invoice_send.get_or_create_stripe_payment_link",
            payment_link,
        ),
    )


@pytest.mark.asyncio
async def test_happy_path_returns_send_summary():
    inv_chain = _chain(
        [
            {
                "id": "inv1",
                "invoice_number": "INV-001",
                "status": "draft",
                "lead_id": "lead1",
                "total": 100.0,
                "stripe_payment_link": "",
            }
        ]
    )
    biz_chain = _chain([{"business_name": "Acme", "owner_email": "o@x.com"}])
    lead_chain = _chain([{"id": "lead1", "name": "Jane", "email": "j@x.com"}])
    update_chain = _chain([{"id": "inv1"}])
    dispatch_mock = AsyncMock(return_value=(True, False, []))

    p1, p2, p3 = _patches(
        tenant_table_side_effect=[inv_chain, biz_chain, lead_chain, update_chain],
        dispatch=dispatch_mock,
    )
    with p1, p2, p3:
        out = await send_invoice_for_tenant(MagicMock(), "t1", "inv1", "email")

    assert out["sent"] is True
    assert out["email_sent"] is True
    assert out["sms_sent"] is False
    assert out["payment_link"] == "https://pay.stripe/x"
    assert out["errors"] == []
    update_call = update_chain.update.call_args[0][0]
    assert update_call["status"] == "sent"
    assert update_call["sent_via"] == "email"
    assert update_call["stripe_payment_link"] == "https://pay.stripe/x"


@pytest.mark.asyncio
async def test_404_when_invoice_missing():
    inv_chain = _chain([])
    p1, p2, p3 = _patches(tenant_table_side_effect=[inv_chain])
    with p1, p2, p3, pytest.raises(HTTPException) as exc:
        await send_invoice_for_tenant(MagicMock(), "t1", "missing", "email")
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_500_when_invoice_fetch_raises():
    inv_chain = _chain([])
    inv_chain.execute.side_effect = RuntimeError("db down")
    p1, p2, p3 = _patches(tenant_table_side_effect=[inv_chain])
    with p1, p2, p3, pytest.raises(HTTPException) as exc:
        await send_invoice_for_tenant(MagicMock(), "t1", "inv1", "email")
    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_400_when_already_paid():
    inv_chain = _chain([{"id": "inv1", "status": "paid", "lead_id": "lead1"}])
    p1, p2, p3 = _patches(tenant_table_side_effect=[inv_chain])
    with p1, p2, p3, pytest.raises(HTTPException) as exc:
        await send_invoice_for_tenant(MagicMock(), "t1", "inv1", "email")
    assert exc.value.status_code == 400
    assert "paid" in exc.value.detail


@pytest.mark.asyncio
async def test_400_when_cancelled():
    inv_chain = _chain([{"id": "inv1", "status": "cancelled", "lead_id": "lead1"}])
    p1, p2, p3 = _patches(tenant_table_side_effect=[inv_chain])
    with p1, p2, p3, pytest.raises(HTTPException) as exc:
        await send_invoice_for_tenant(MagicMock(), "t1", "inv1", "email")
    assert exc.value.status_code == 400
    assert "cancelled" in exc.value.detail


@pytest.mark.asyncio
async def test_no_lead_id_still_dispatches():
    """Single send doesn't require contact; dispatch will record the issue."""
    inv_chain = _chain(
        [
            {
                "id": "inv1",
                "status": "draft",
                "lead_id": None,
                "total": 50.0,
                "stripe_payment_link": "",
            }
        ]
    )
    biz_chain = _chain([{"business_name": "Acme"}])
    update_chain = _chain([{"id": "inv1"}])
    dispatch_mock = AsyncMock(return_value=(False, False, ["no lead"]))

    p1, p2, p3 = _patches(
        tenant_table_side_effect=[inv_chain, biz_chain, update_chain],
        dispatch=dispatch_mock,
    )
    with p1, p2, p3:
        out = await send_invoice_for_tenant(MagicMock(), "t1", "inv1", "email")

    kwargs = dispatch_mock.call_args.kwargs
    assert kwargs["lead"] == {}
    assert out["errors"] == ["no lead"]


@pytest.mark.asyncio
async def test_existing_payment_link_reused_no_new_link_created():
    inv_chain = _chain(
        [
            {
                "id": "inv1",
                "status": "draft",
                "lead_id": "lead1",
                "total": 100.0,
                "stripe_payment_link": "https://existing.link",
            }
        ]
    )
    biz_chain = _chain([{"business_name": "Acme"}])
    lead_chain = _chain([{"id": "lead1", "email": "j@x.com"}])
    update_chain = _chain([{"id": "inv1"}])
    link_mock = AsyncMock(return_value="https://should-not-be-called")
    dispatch_mock = AsyncMock(return_value=(True, False, []))

    p1, p2, p3 = _patches(
        tenant_table_side_effect=[inv_chain, biz_chain, lead_chain, update_chain],
        dispatch=dispatch_mock,
        payment_link=link_mock,
    )
    with p1, p2, p3:
        out = await send_invoice_for_tenant(MagicMock(), "t1", "inv1", "email")

    link_mock.assert_not_called()
    assert out["payment_link"] == "https://existing.link"
    assert (
        dispatch_mock.call_args.kwargs["payment_link_url"]
        == "https://existing.link"
    )


@pytest.mark.asyncio
async def test_zero_total_skips_payment_link():
    inv_chain = _chain(
        [
            {
                "id": "inv1",
                "status": "draft",
                "lead_id": "lead1",
                "total": 0,
                "stripe_payment_link": "",
            }
        ]
    )
    biz_chain = _chain([{"business_name": "Acme"}])
    lead_chain = _chain([{"id": "lead1", "email": "j@x.com"}])
    update_chain = _chain([{"id": "inv1"}])
    link_mock = AsyncMock(return_value="should-not-be-called")

    p1, p2, p3 = _patches(
        tenant_table_side_effect=[inv_chain, biz_chain, lead_chain, update_chain],
        payment_link=link_mock,
    )
    with p1, p2, p3:
        out = await send_invoice_for_tenant(MagicMock(), "t1", "inv1", "email")

    link_mock.assert_not_called()
    assert out["payment_link"] == ""
    # When no payment link, update_data should not include the field
    update_call = update_chain.update.call_args[0][0]
    assert "stripe_payment_link" not in update_call


@pytest.mark.asyncio
async def test_status_update_failure_does_not_raise():
    inv_chain = _chain(
        [
            {
                "id": "inv1",
                "status": "draft",
                "lead_id": "lead1",
                "total": 75.0,
                "stripe_payment_link": "",
            }
        ]
    )
    biz_chain = _chain([{"business_name": "Acme"}])
    lead_chain = _chain([{"id": "lead1", "email": "j@x.com"}])
    update_chain = _chain([])
    update_chain.execute.side_effect = RuntimeError("write failed")
    dispatch_mock = AsyncMock(return_value=(True, False, []))

    p1, p2, p3 = _patches(
        tenant_table_side_effect=[inv_chain, biz_chain, lead_chain, update_chain],
        dispatch=dispatch_mock,
    )
    with p1, p2, p3:
        out = await send_invoice_for_tenant(MagicMock(), "t1", "inv1", "email")

    assert out["sent"] is True
    assert out["email_sent"] is True


@pytest.mark.asyncio
async def test_business_fetch_failure_passes_empty_business():
    inv_chain = _chain(
        [
            {
                "id": "inv1",
                "status": "draft",
                "lead_id": "lead1",
                "total": 50.0,
                "stripe_payment_link": "",
            }
        ]
    )
    biz_chain = _chain([])
    biz_chain.execute.side_effect = RuntimeError("tenants down")
    lead_chain = _chain([{"id": "lead1", "email": "j@x.com"}])
    update_chain = _chain([{"id": "inv1"}])
    dispatch_mock = AsyncMock(return_value=(True, False, []))

    p1, p2, p3 = _patches(
        tenant_table_side_effect=[inv_chain, biz_chain, lead_chain, update_chain],
        dispatch=dispatch_mock,
    )
    with p1, p2, p3:
        out = await send_invoice_for_tenant(MagicMock(), "t1", "inv1", "email")

    assert dispatch_mock.call_args.kwargs["business"] == {}
    assert out["sent"] is True


@pytest.mark.asyncio
async def test_lead_fetch_failure_passes_empty_lead():
    inv_chain = _chain(
        [
            {
                "id": "inv1",
                "status": "draft",
                "lead_id": "lead1",
                "total": 50.0,
                "stripe_payment_link": "",
            }
        ]
    )
    biz_chain = _chain([{"business_name": "Acme"}])
    lead_chain = _chain([])
    lead_chain.execute.side_effect = RuntimeError("leads down")
    update_chain = _chain([{"id": "inv1"}])
    dispatch_mock = AsyncMock(return_value=(False, False, ["lead missing"]))

    p1, p2, p3 = _patches(
        tenant_table_side_effect=[inv_chain, biz_chain, lead_chain, update_chain],
        dispatch=dispatch_mock,
    )
    with p1, p2, p3:
        out = await send_invoice_for_tenant(MagicMock(), "t1", "inv1", "email")

    assert dispatch_mock.call_args.kwargs["lead"] == {}
    assert out["errors"] == ["lead missing"]
