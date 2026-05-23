"""Unit tests for invoice_dispatch — email + SMS channel dispatch."""

from unittest.mock import AsyncMock, patch

import pytest

from backend.services.invoice_dispatch import (
    build_invoice_sms_body,
    dispatch_invoice_channels,
)


# --- build_invoice_sms_body ---


def test_sms_body_with_payment_link():
    body = build_invoice_sms_body(
        invoice={"invoice_number": "INV-001", "total": 150.5},
        business={"business_name": "Acme"},
        lead={"name": "Jane"},
        payment_link_url="https://buy.stripe.com/xyz",
    )
    assert "INV-001" in body
    assert "$150.50" in body
    assert "Acme" in body
    assert "Jane" in body
    assert "https://buy.stripe.com/xyz" in body


def test_sms_body_without_payment_link_falls_back_to_contact():
    body = build_invoice_sms_body(
        invoice={"invoice_number": "INV-002", "total": 99.0},
        business={"business_name": "Biz"},
        lead={"name": "Bob"},
        payment_link_url="",
    )
    assert "INV-002" in body
    assert "$99.00" in body
    assert "Please contact us" in body
    assert "stripe" not in body.lower()


def test_sms_body_defaults_when_fields_missing():
    body = build_invoice_sms_body(
        invoice={"total": 10},
        business={},
        lead={},
        payment_link_url="",
    )
    assert "there" in body  # default name
    assert "Your Service Provider" in body  # default biz


# --- dispatch_invoice_channels ---


@pytest.mark.asyncio
async def test_dispatch_email_only_success():
    with patch(
        "backend.services.invoice_dispatch.send_email",
        new=AsyncMock(return_value={"success": True}),
    ):
        email_sent, sms_sent, errors = await dispatch_invoice_channels(
            invoice={"invoice_number": "INV-1", "total": 100},
            business={"business_name": "B"},
            lead={"email": "x@example.com", "name": "X"},
            method="email",
            payment_link_url="",
            tenant_id="t1",
            invoice_id="inv1",
        )
    assert email_sent is True
    assert sms_sent is False
    assert errors == []


@pytest.mark.asyncio
async def test_dispatch_email_no_address_returns_error():
    email_sent, sms_sent, errors = await dispatch_invoice_channels(
        invoice={"invoice_number": "INV-1", "total": 100},
        business={},
        lead={"email": "", "name": "X"},
        method="email",
        payment_link_url="",
        tenant_id="t1",
        invoice_id="inv1",
    )
    assert email_sent is False
    assert any("No email" in e for e in errors)


@pytest.mark.asyncio
async def test_dispatch_email_failure_reports_detail():
    with patch(
        "backend.services.invoice_dispatch.send_email",
        new=AsyncMock(return_value={"success": False, "detail": "smtp down"}),
    ):
        email_sent, sms_sent, errors = await dispatch_invoice_channels(
            invoice={"invoice_number": "INV-1", "total": 100},
            business={},
            lead={"email": "x@example.com"},
            method="email",
            payment_link_url="",
            tenant_id="t1",
            invoice_id="inv1",
        )
    assert email_sent is False
    assert any("smtp down" in e for e in errors)


@pytest.mark.asyncio
async def test_dispatch_email_exception_caught():
    with patch(
        "backend.services.invoice_dispatch.send_email",
        new=AsyncMock(side_effect=RuntimeError("boom")),
    ):
        email_sent, _sms_sent, errors = await dispatch_invoice_channels(
            invoice={"invoice_number": "INV-1", "total": 100},
            business={},
            lead={"email": "x@example.com"},
            method="email",
            payment_link_url="",
            tenant_id="t1",
            invoice_id="inv1",
        )
    assert email_sent is False
    assert any("unexpectedly" in e for e in errors)


@pytest.mark.asyncio
async def test_dispatch_sms_only_success():
    with patch(
        "backend.services.invoice_dispatch.send_sms",
        new=AsyncMock(return_value=True),
    ):
        email_sent, sms_sent, errors = await dispatch_invoice_channels(
            invoice={"invoice_number": "INV-1", "total": 100},
            business={"business_name": "B"},
            lead={"phone": "+15551234567", "name": "X"},
            method="sms",
            payment_link_url="https://pay/x",
            tenant_id="t1",
            invoice_id="inv1",
        )
    assert email_sent is False
    assert sms_sent is True
    assert errors == []


@pytest.mark.asyncio
async def test_dispatch_sms_no_phone_returns_error():
    email_sent, sms_sent, errors = await dispatch_invoice_channels(
        invoice={"invoice_number": "INV-1", "total": 100},
        business={},
        lead={"phone": "", "name": "X"},
        method="sms",
        payment_link_url="",
        tenant_id="t1",
        invoice_id="inv1",
    )
    assert sms_sent is False
    assert any("No phone" in e for e in errors)


@pytest.mark.asyncio
async def test_dispatch_sms_send_returns_false():
    with patch(
        "backend.services.invoice_dispatch.send_sms",
        new=AsyncMock(return_value=False),
    ):
        _email_sent, sms_sent, errors = await dispatch_invoice_channels(
            invoice={"invoice_number": "INV-1", "total": 100},
            business={},
            lead={"phone": "+15551234567"},
            method="sms",
            payment_link_url="",
            tenant_id="t1",
            invoice_id="inv1",
        )
    assert sms_sent is False
    assert any("SMS delivery failed" in e for e in errors)


@pytest.mark.asyncio
async def test_dispatch_sms_exception_caught():
    with patch(
        "backend.services.invoice_dispatch.send_sms",
        new=AsyncMock(side_effect=RuntimeError("twilio down")),
    ):
        _email_sent, sms_sent, errors = await dispatch_invoice_channels(
            invoice={"invoice_number": "INV-1", "total": 100},
            business={},
            lead={"phone": "+15551234567"},
            method="sms",
            payment_link_url="",
            tenant_id="t1",
            invoice_id="inv1",
        )
    assert sms_sent is False
    assert any("unexpectedly" in e for e in errors)


@pytest.mark.asyncio
async def test_dispatch_both_channels_success():
    with patch(
        "backend.services.invoice_dispatch.send_email",
        new=AsyncMock(return_value={"success": True}),
    ), patch(
        "backend.services.invoice_dispatch.send_sms",
        new=AsyncMock(return_value=True),
    ):
        email_sent, sms_sent, errors = await dispatch_invoice_channels(
            invoice={"invoice_number": "INV-1", "total": 100},
            business={"business_name": "B"},
            lead={"email": "x@example.com", "phone": "+15551234567"},
            method="both",
            payment_link_url="https://pay/x",
            tenant_id="t1",
            invoice_id="inv1",
        )
    assert email_sent is True
    assert sms_sent is True
    assert errors == []
