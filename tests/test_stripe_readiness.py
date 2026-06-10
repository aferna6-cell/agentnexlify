from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException


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

    assert ensure_configured.call_count == 1
