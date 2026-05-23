"""Unit tests for invoice_payment_links — Stripe Payment Link creation."""

from unittest.mock import MagicMock, patch

import pytest
import stripe

from backend.services.invoice_payment_links import get_or_create_stripe_payment_link


@pytest.mark.asyncio
async def test_returns_none_when_stripe_not_configured():
    with patch(
        "backend.services.invoice_payment_links.ensure_stripe_configured",
        side_effect=RuntimeError("not configured"),
    ):
        url = await get_or_create_stripe_payment_link("inv1", "t1", "INV-001", 100.0)
    assert url is None


@pytest.mark.asyncio
async def test_success_returns_payment_link_url():
    price = MagicMock()
    price.id = "price_123"
    payment_link = MagicMock()
    payment_link.url = "https://buy.stripe.com/test_xyz"

    with patch(
        "backend.services.invoice_payment_links.ensure_stripe_configured"
    ), patch(
        "backend.services.invoice_payment_links.stripe.Price.create",
        return_value=price,
    ), patch(
        "backend.services.invoice_payment_links.stripe.PaymentLink.create",
        return_value=payment_link,
    ):
        url = await get_or_create_stripe_payment_link("inv1", "t1", "INV-001", 250.50)
    assert url == "https://buy.stripe.com/test_xyz"


@pytest.mark.asyncio
async def test_stripe_error_returns_none():
    with patch(
        "backend.services.invoice_payment_links.ensure_stripe_configured"
    ), patch(
        "backend.services.invoice_payment_links.stripe.Price.create",
        side_effect=stripe.StripeError("rate limit"),
    ):
        url = await get_or_create_stripe_payment_link("inv1", "t1", "INV-001", 100.0)
    assert url is None


@pytest.mark.asyncio
async def test_unexpected_error_returns_none():
    with patch(
        "backend.services.invoice_payment_links.ensure_stripe_configured"
    ), patch(
        "backend.services.invoice_payment_links.stripe.Price.create",
        side_effect=ValueError("boom"),
    ):
        url = await get_or_create_stripe_payment_link("inv1", "t1", "INV-001", 100.0)
    assert url is None
