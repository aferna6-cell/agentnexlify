"""Regressions for the 2026-06-16 security-audit fixes on the money path.

- billing.py /api/v1/billing/webhook now dispatches invoice.payment_succeeded
  (CRITICAL-1: dunning recovery previously never fired on this endpoint).
- That endpoint is now idempotent: a duplicate Stripe event is skipped
  (CRITICAL-2: retries previously reprocessed + double-fired the owner alert).
- RegisterRequest rejects passwords over bcrypt's 72-byte limit (MEDIUM-2).
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
os.environ.setdefault("TESTING", "1")

from backend.routers import billing


def _request():
    req = MagicMock()

    async def _body():
        return b"{}"

    req.body = _body
    req.headers.get.return_value = "sig"
    return req


def _event(event_type, obj=None):
    return {"type": event_type, "id": "evt_x", "data": {"object": obj or {}}}


@pytest.mark.asyncio
async def test_billing_webhook_dispatches_payment_succeeded():
    """CRITICAL-1: invoice.payment_succeeded reaches _handle_payment_succeeded."""
    recover = AsyncMock()
    with (
        patch.object(billing.stripe.Webhook, "construct_event",
                     return_value=_event("invoice.payment_succeeded", {"customer": "cus_1"})),
        patch.object(billing, "get_service_supabase", return_value=MagicMock()),
        patch.object(billing, "check_and_record", AsyncMock(return_value=(True, None))),
        patch.object(billing, "record_response", AsyncMock()),
        patch.object(billing, "_handle_payment_succeeded", recover),
    ):
        result = await billing.stripe_webhook(_request())

    assert result == {"status": "ok"}
    recover.assert_awaited_once()


@pytest.mark.asyncio
async def test_billing_webhook_skips_duplicate_event():
    """CRITICAL-2: a duplicate event is not reprocessed (no activation handler call)."""
    handler = MagicMock()
    with (
        patch.object(billing.stripe.Webhook, "construct_event",
                     return_value=_event("checkout.session.completed", {"metadata": {}})),
        patch.object(billing, "get_service_supabase", return_value=MagicMock()),
        patch.object(billing, "check_and_record",
                     AsyncMock(return_value=(False, {"response_body": {"status": "ok"}}))),
        patch.object(billing, "_handle_checkout_completed", handler),
    ):
        result = await billing.stripe_webhook(_request())

    assert result == {"status": "ok"}
    handler.assert_not_called()


@pytest.mark.asyncio
async def test_billing_webhook_releases_idempotency_row_on_handler_failure():
    """GH #308: if the handler raises, the in-flight idempotency row is deleted
    so Stripe's retry reprocesses instead of being acked as a duplicate.

    Without the fix, the NULL-response row written before the handler persists,
    every retry short-circuits, and the event is permanently dropped."""
    from fastapi import HTTPException

    released = AsyncMock()
    with (
        patch.object(billing.stripe.Webhook, "construct_event",
                     return_value=_event("invoice.payment_succeeded", {"customer": "cus_1"})),
        patch.object(billing, "get_service_supabase", return_value=MagicMock()),
        patch.object(billing, "check_and_record", AsyncMock(return_value=(True, None))),
        patch.object(billing, "record_response", AsyncMock()),
        patch.object(billing, "delete_key", released),
        patch.object(billing, "_handle_payment_succeeded",
                     AsyncMock(side_effect=RuntimeError("db down"))),
    ):
        with pytest.raises(HTTPException) as exc:
            await billing.stripe_webhook(_request())

    assert exc.value.status_code == 500
    # The in-flight row for this event was released so the retry reprocesses.
    released.assert_awaited_once()
    assert released.await_args.args[1] == "stripe:evt_x"


def test_register_rejects_overlong_password():
    """MEDIUM-2: passwords beyond bcrypt's 72-byte limit are rejected, not truncated."""
    import pydantic
    from backend.models.schemas import RegisterRequest

    base = {"email": "a@b.com", "business_name": "Acme", "owner_name": "Sam"}
    long_pw = "Aa1" + "x" * 80  # > 72 bytes
    with pytest.raises(pydantic.ValidationError, match=r"72 bytes"):
        RegisterRequest(password=long_pw, **base)

    # A compliant <=72-byte password still validates.
    ok = RegisterRequest(password="Aa1" + "x" * 60, **base)
    assert ok.password.startswith("Aa1")
