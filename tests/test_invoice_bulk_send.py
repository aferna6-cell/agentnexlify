"""Unit tests for invoice_bulk_send — batch dispatch semantics + error handling."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services.invoice_bulk_send import (
    MAX_ERRORS_RETURNED,
    bulk_send_invoices_for_tenant,
)


def _chain(data):
    """Build a chainable mock whose .execute() returns a result with .data = data."""
    ch = MagicMock()
    for m in ("select", "update", "eq", "limit"):
        getattr(ch, m).return_value = ch
    res = MagicMock()
    res.data = data
    ch.execute.return_value = res
    return ch


def _patch_bulk(*, tenant_table_side_effect, dispatch=None, payment_link=None):
    """Apply the three patches every bulk_send test needs."""
    if dispatch is None:
        dispatch = AsyncMock(return_value=(True, True, []))
    if payment_link is None:
        payment_link = AsyncMock(return_value="https://pay.stripe/x")
    return (
        patch(
            "backend.services.invoice_bulk_send.tenant_table",
            side_effect=tenant_table_side_effect,
        ),
        patch(
            "backend.services.invoice_bulk_send.dispatch_invoice_channels",
            dispatch,
        ),
        patch(
            "backend.services.invoice_bulk_send.get_or_create_stripe_payment_link",
            payment_link,
        ),
    )


# --- batch shape ---


@pytest.mark.asyncio
async def test_empty_batch_returns_zero_counts():
    biz_chain = _chain([{"business_name": "Acme"}])
    p1, p2, p3 = _patch_bulk(tenant_table_side_effect=[biz_chain])
    with p1, p2, p3:
        out = await bulk_send_invoices_for_tenant(MagicMock(), "t1", [], "email")
    assert out == {"sent": 0, "failed": 0, "errors": []}


@pytest.mark.asyncio
async def test_happy_path_single_invoice_marks_sent():
    biz_chain = _chain([{"business_name": "Acme"}])
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
    lead_chain = _chain([{"name": "Jane", "email": "j@x.com", "phone": None}])
    update_chain = _chain([{"id": "inv1"}])

    p1, p2, p3 = _patch_bulk(
        tenant_table_side_effect=[biz_chain, inv_chain, lead_chain, update_chain]
    )
    with p1, p2, p3 as link_mock:
        out = await bulk_send_invoices_for_tenant(
            MagicMock(), "t1", ["inv1"], "email"
        )

    assert out["sent"] == 1
    assert out["failed"] == 0
    assert out["errors"] == []
    update_call = update_chain.update.call_args[0][0]
    assert update_call["status"] == "sent"
    assert update_call["sent_via"] == "email"
    assert "sent_at" in update_call
    link_mock.assert_awaited_once()


# --- per-invoice failure modes ---


@pytest.mark.asyncio
async def test_invoice_not_found():
    biz_chain = _chain([{"business_name": "Acme"}])
    inv_chain = _chain([])

    p1, p2, p3 = _patch_bulk(tenant_table_side_effect=[biz_chain, inv_chain])
    with p1, p2, p3:
        out = await bulk_send_invoices_for_tenant(
            MagicMock(), "t1", ["missing"], "email"
        )

    assert out["sent"] == 0
    assert out["failed"] == 1
    assert out["errors"] == ["missing: not found"]


@pytest.mark.asyncio
async def test_invoice_already_paid_is_failed():
    biz_chain = _chain([{"business_name": "Acme"}])
    inv_chain = _chain(
        [
            {
                "id": "inv1",
                "invoice_number": "INV-001",
                "status": "paid",
                "lead_id": "lead1",
                "total": 100.0,
            }
        ]
    )

    p1, p2, p3 = _patch_bulk(tenant_table_side_effect=[biz_chain, inv_chain])
    with p1, p2, p3:
        out = await bulk_send_invoices_for_tenant(
            MagicMock(), "t1", ["inv1"], "email"
        )

    assert out["sent"] == 0
    assert out["failed"] == 1
    assert "already paid" in out["errors"][0]
    assert "INV-001" in out["errors"][0]


@pytest.mark.asyncio
async def test_invoice_cancelled_is_failed():
    biz_chain = _chain([{"business_name": "Acme"}])
    inv_chain = _chain(
        [
            {
                "id": "inv1",
                "invoice_number": "INV-002",
                "status": "cancelled",
                "lead_id": "lead1",
                "total": 100.0,
            }
        ]
    )

    p1, p2, p3 = _patch_bulk(tenant_table_side_effect=[biz_chain, inv_chain])
    with p1, p2, p3:
        out = await bulk_send_invoices_for_tenant(
            MagicMock(), "t1", ["inv1"], "email"
        )

    assert out["failed"] == 1
    assert "already cancelled" in out["errors"][0]


@pytest.mark.asyncio
async def test_no_lead_is_failed_no_contact_info():
    biz_chain = _chain([{"business_name": "Acme"}])
    inv_chain = _chain(
        [
            {
                "id": "inv1",
                "invoice_number": "INV-003",
                "status": "draft",
                "lead_id": "lead-missing",
                "total": 100.0,
            }
        ]
    )
    lead_chain = _chain([])

    p1, p2, p3 = _patch_bulk(
        tenant_table_side_effect=[biz_chain, inv_chain, lead_chain]
    )
    with p1, p2, p3:
        out = await bulk_send_invoices_for_tenant(
            MagicMock(), "t1", ["inv1"], "email"
        )

    assert out["failed"] == 1
    assert "no contact info" in out["errors"][0]
    assert "INV-003" in out["errors"][0]


@pytest.mark.asyncio
async def test_lead_with_no_email_and_no_phone_is_failed():
    biz_chain = _chain([{"business_name": "Acme"}])
    inv_chain = _chain(
        [
            {
                "id": "inv1",
                "invoice_number": "INV-004",
                "status": "draft",
                "lead_id": "lead1",
                "total": 100.0,
            }
        ]
    )
    lead_chain = _chain([{"name": "Jane", "email": None, "phone": None}])

    p1, p2, p3 = _patch_bulk(
        tenant_table_side_effect=[biz_chain, inv_chain, lead_chain]
    )
    with p1, p2, p3:
        out = await bulk_send_invoices_for_tenant(
            MagicMock(), "t1", ["inv1"], "email"
        )

    assert out["failed"] == 1
    assert "no contact info" in out["errors"][0]


@pytest.mark.asyncio
async def test_lead_with_only_phone_succeeds():
    biz_chain = _chain([{"business_name": "Acme"}])
    inv_chain = _chain(
        [
            {
                "id": "inv1",
                "invoice_number": "INV-005",
                "status": "draft",
                "lead_id": "lead1",
                "total": 50.0,
            }
        ]
    )
    lead_chain = _chain([{"name": "Jane", "email": None, "phone": "+1555"}])
    update_chain = _chain([{"id": "inv1"}])

    p1, p2, p3 = _patch_bulk(
        tenant_table_side_effect=[biz_chain, inv_chain, lead_chain, update_chain]
    )
    with p1, p2, p3:
        out = await bulk_send_invoices_for_tenant(
            MagicMock(), "t1", ["inv1"], "sms"
        )

    assert out["sent"] == 1
    assert out["failed"] == 0


# --- payment link resolution ---


@pytest.mark.asyncio
async def test_existing_payment_link_reused():
    biz_chain = _chain([{"business_name": "Acme"}])
    inv_chain = _chain(
        [
            {
                "id": "inv1",
                "invoice_number": "INV-006",
                "status": "draft",
                "lead_id": "lead1",
                "total": 75.0,
                "stripe_payment_link": "https://existing.link",
            }
        ]
    )
    lead_chain = _chain([{"name": "Jane", "email": "j@x.com", "phone": None}])
    update_chain = _chain([{"id": "inv1"}])
    link_mock = AsyncMock(return_value="https://new.link")
    dispatch_mock = AsyncMock(return_value=(True, True, []))

    p1, p2, p3 = _patch_bulk(
        tenant_table_side_effect=[biz_chain, inv_chain, lead_chain, update_chain],
        dispatch=dispatch_mock,
        payment_link=link_mock,
    )
    with p1, p2, p3:
        await bulk_send_invoices_for_tenant(MagicMock(), "t1", ["inv1"], "email")

    link_mock.assert_not_called()
    kwargs = dispatch_mock.call_args.kwargs
    assert kwargs["payment_link_url"] == "https://existing.link"


@pytest.mark.asyncio
async def test_payment_link_creation_failure_proceeds_with_empty_url():
    biz_chain = _chain([{"business_name": "Acme"}])
    inv_chain = _chain(
        [
            {
                "id": "inv1",
                "invoice_number": "INV-007",
                "status": "draft",
                "lead_id": "lead1",
                "total": 200.0,
                "stripe_payment_link": "",
            }
        ]
    )
    lead_chain = _chain([{"name": "Jane", "email": "j@x.com"}])
    update_chain = _chain([{"id": "inv1"}])

    link_mock = AsyncMock(side_effect=RuntimeError("stripe down"))
    dispatch_mock = AsyncMock(return_value=(True, True, []))

    p1, p2, p3 = _patch_bulk(
        tenant_table_side_effect=[biz_chain, inv_chain, lead_chain, update_chain],
        dispatch=dispatch_mock,
        payment_link=link_mock,
    )
    with p1, p2, p3:
        out = await bulk_send_invoices_for_tenant(
            MagicMock(), "t1", ["inv1"], "email"
        )

    assert out["sent"] == 1
    assert dispatch_mock.call_args.kwargs["payment_link_url"] == ""


@pytest.mark.asyncio
async def test_zero_total_skips_payment_link_creation():
    biz_chain = _chain([{"business_name": "Acme"}])
    inv_chain = _chain(
        [
            {
                "id": "inv1",
                "invoice_number": "INV-008",
                "status": "draft",
                "lead_id": "lead1",
                "total": 0.0,
                "stripe_payment_link": "",
            }
        ]
    )
    lead_chain = _chain([{"name": "Jane", "email": "j@x.com"}])
    update_chain = _chain([{"id": "inv1"}])
    link_mock = AsyncMock(return_value="should-not-be-called")

    p1, p2, p3 = _patch_bulk(
        tenant_table_side_effect=[biz_chain, inv_chain, lead_chain, update_chain],
        payment_link=link_mock,
    )
    with p1, p2, p3:
        out = await bulk_send_invoices_for_tenant(
            MagicMock(), "t1", ["inv1"], "email"
        )

    link_mock.assert_not_called()
    assert out["sent"] == 1
    assert out["failed"] == 0


# --- resilience ---


@pytest.mark.asyncio
async def test_mark_sent_failure_still_counts_as_sent():
    biz_chain = _chain([{"business_name": "Acme"}])
    inv_chain = _chain(
        [
            {
                "id": "inv1",
                "invoice_number": "INV-009",
                "status": "draft",
                "lead_id": "lead1",
                "total": 30.0,
            }
        ]
    )
    lead_chain = _chain([{"name": "Jane", "email": "j@x.com"}])
    update_chain = _chain([])
    update_chain.execute.side_effect = RuntimeError("db down")

    p1, p2, p3 = _patch_bulk(
        tenant_table_side_effect=[biz_chain, inv_chain, lead_chain, update_chain]
    )
    with p1, p2, p3:
        out = await bulk_send_invoices_for_tenant(
            MagicMock(), "t1", ["inv1"], "email"
        )

    assert out["sent"] == 1
    assert out["failed"] == 0


@pytest.mark.asyncio
async def test_dispatch_exception_marks_invoice_failed():
    biz_chain = _chain([{"business_name": "Acme"}])
    inv_chain = _chain(
        [
            {
                "id": "inv1",
                "invoice_number": "INV-010",
                "status": "draft",
                "lead_id": "lead1",
                "total": 40.0,
            }
        ]
    )
    lead_chain = _chain([{"name": "Jane", "email": "j@x.com"}])
    dispatch_mock = AsyncMock(side_effect=RuntimeError("smtp down"))

    p1, p2, p3 = _patch_bulk(
        tenant_table_side_effect=[biz_chain, inv_chain, lead_chain],
        dispatch=dispatch_mock,
    )
    with p1, p2, p3:
        out = await bulk_send_invoices_for_tenant(
            MagicMock(), "t1", ["inv1"], "email"
        )

    assert out["failed"] == 1
    assert "inv1: unexpected error" in out["errors"]


@pytest.mark.asyncio
async def test_business_fetch_failure_does_not_abort_batch():
    biz_chain = _chain([])
    biz_chain.execute.side_effect = RuntimeError("tenants table down")
    inv_chain = _chain(
        [
            {
                "id": "inv1",
                "invoice_number": "INV-011",
                "status": "draft",
                "lead_id": "lead1",
                "total": 60.0,
            }
        ]
    )
    lead_chain = _chain([{"name": "Jane", "email": "j@x.com"}])
    update_chain = _chain([{"id": "inv1"}])

    p1, p2, p3 = _patch_bulk(
        tenant_table_side_effect=[biz_chain, inv_chain, lead_chain, update_chain]
    )
    with p1, p2, p3:
        out = await bulk_send_invoices_for_tenant(
            MagicMock(), "t1", ["inv1"], "email"
        )

    assert out["sent"] == 1


# --- error truncation ---


@pytest.mark.asyncio
async def test_errors_truncated_to_max_returned():
    biz_chain = _chain([{"business_name": "Acme"}])
    n = MAX_ERRORS_RETURNED + 5
    invoice_ids = [f"inv{i}" for i in range(n)]
    inv_chains = [_chain([]) for _ in range(n)]

    p1, p2, p3 = _patch_bulk(tenant_table_side_effect=[biz_chain, *inv_chains])
    with p1, p2, p3:
        out = await bulk_send_invoices_for_tenant(
            MagicMock(), "t1", invoice_ids, "email"
        )

    assert out["sent"] == 0
    assert out["failed"] == n
    assert len(out["errors"]) == MAX_ERRORS_RETURNED
