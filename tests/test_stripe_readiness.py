from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException


def _db_with_tenant(row: dict):
    table = MagicMock()
    for method in ("select", "eq", "limit"):
        getattr(table, method).return_value = table
    table.execute.return_value = MagicMock(data=[row])

    db = MagicMock()
    db.table.return_value = table
    return db


@pytest.mark.asyncio
async def test_marketing_addon_checkout_returns_503_when_stripe_missing(monkeypatch):
    from backend.routers import billing

    db = _db_with_tenant(
        {
            "id": "tenant-1",
            "owner_email": "owner@example.com",
            "business_name": "Test Biz",
            "marketing_addon_active": False,
            "marketing_addon_stripe_sub_id": None,
        }
    )
    get_customer = MagicMock()
    create_session = MagicMock()

    monkeypatch.setattr(billing, "get_service_supabase", lambda: db)
    monkeypatch.setattr(
        billing,
        "ensure_stripe_configured",
        MagicMock(side_effect=RuntimeError("STRIPE_SECRET_KEY is not configured.")),
    )
    monkeypatch.setattr(billing, "get_or_create_customer", get_customer)
    monkeypatch.setattr(billing, "create_marketing_addon_checkout_session", create_session)

    with pytest.raises(HTTPException) as exc_info:
        await billing.marketing_addon_checkout({"tenant_id": "tenant-1"})

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "STRIPE_SECRET_KEY is not configured."
    get_customer.assert_not_called()
    create_session.assert_not_called()


@pytest.mark.asyncio
async def test_marketing_addon_cancel_returns_503_when_stripe_missing(monkeypatch):
    from backend.routers import billing

    db = _db_with_tenant(
        {
            "marketing_addon_stripe_sub_id": "sub_marketing",
            "marketing_addon_grandfathered": False,
        }
    )
    cancel_subscription = MagicMock()

    monkeypatch.setattr(billing, "get_service_supabase", lambda: db)
    monkeypatch.setattr(
        billing,
        "ensure_stripe_configured",
        MagicMock(side_effect=RuntimeError("STRIPE_SECRET_KEY is not configured.")),
    )
    monkeypatch.setattr(billing, "cancel_marketing_addon_subscription", cancel_subscription)

    with pytest.raises(HTTPException) as exc_info:
        await billing.marketing_addon_cancel({"tenant_id": "tenant-1"})

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "STRIPE_SECRET_KEY is not configured."
    cancel_subscription.assert_not_called()


def test_stripe_helpers_raise_actionable_error_when_secret_missing(monkeypatch):
    from backend.services import stripe_service

    ensure_configured = MagicMock(
        side_effect=RuntimeError("STRIPE_SECRET_KEY is not configured.")
    )
    monkeypatch.setattr(stripe_service, "ensure_stripe_configured", ensure_configured)

    with pytest.raises(RuntimeError, match="STRIPE_SECRET_KEY is not configured"):
        stripe_service.get_or_create_customer(
            email="owner@example.com",
            tenant_id="tenant-1",
            business_name="Test Biz",
        )

    with pytest.raises(RuntimeError, match="STRIPE_SECRET_KEY is not configured"):
        stripe_service.create_marketing_addon_checkout_session(
            tenant_id="tenant-1",
            customer_id="cus_123",
            success_url="https://example.com/success",
            cancel_url="https://example.com/cancel",
        )

    with pytest.raises(RuntimeError, match="STRIPE_SECRET_KEY is not configured"):
        stripe_service.cancel_marketing_addon_subscription("sub_123")

    assert ensure_configured.call_count == 3
