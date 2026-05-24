"""Billing helpers — auth deps, dict converters, refund audit helpers, AdminRefundRequest."""


import hashlib
import hmac as _hmac
import logging
from typing import Any

from fastapi import Header, HTTPException
from pydantic import BaseModel, Field, field_validator

from backend.config import settings

logger = logging.getLogger(__name__)


class AdminRefundRequest(BaseModel):
    tenant_id: str = Field(..., min_length=1)
    refund_request_id: str = Field(..., min_length=8, max_length=120)
    payment_intent: str | None = None
    charge: str | None = None
    amount_cents: int | None = Field(default=None, gt=0)
    stripe_reason: str | None = None
    internal_reason: str = Field(..., min_length=3, max_length=500)
    requested_by: str = Field(..., min_length=2, max_length=200)

    @field_validator("refund_request_id")
    @classmethod
    def _strip_refund_request_id(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("refund_request_id is required")
        return cleaned


def _verify_secret(x_api_secret: str = Header(...)):
    secret = settings.billing_secret or settings.api_secret_key
    if not secret or not _hmac.compare_digest(x_api_secret, secret):
        raise HTTPException(status_code=403, detail="Invalid API secret")


def _admin_secret() -> str:
    admin_secret = getattr(settings, "admin_api_secret_key", "")
    if isinstance(admin_secret, str) and admin_secret:
        return admin_secret
    api_secret = getattr(settings, "api_secret_key", "")
    return api_secret if isinstance(api_secret, str) else ""


def _verify_admin_secret(x_api_secret: str | None) -> None:
    secret = _admin_secret()
    if not secret or not x_api_secret or not _hmac.compare_digest(x_api_secret, secret):
        raise HTTPException(status_code=401, detail="Invalid admin secret")


def _stripe_obj_to_dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "to_dict_recursive"):
        return value.to_dict_recursive()
    if isinstance(value, dict):
        return dict(value)
    result: dict[str, Any] = {}
    for key in ("id", "amount", "currency", "status", "payment_intent", "charge", "reason"):
        if hasattr(value, key):
            result[key] = getattr(value, key)
    return result


def _refund_idempotency_key(req: AdminRefundRequest) -> str:
    key = f"agentnexlify-refund:{req.tenant_id}:{req.refund_request_id}"
    if len(key) <= 255:
        return key
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return f"agentnexlify-refund:{digest}"


def _refund_response_from_audit(row: dict[str, Any], *, idempotent_replay: bool) -> dict[str, Any]:
    return {
        "status": "refunded",
        "stripe_refund_id": row.get("stripe_refund_id"),
        "amount_cents": row.get("amount_cents"),
        "currency": row.get("currency") or "usd",
        "refund_status": row.get("status") or "pending",
        "idempotent_replay": idempotent_replay,
    }


def _find_refund_audit(
    db,
    *,
    tenant_id: str,
    refund_request_id: str | None = None,
    stripe_refund_id: str | None = None,
) -> dict[str, Any] | None:
    query = (
        db.table("billing_refunds")
        .select("stripe_refund_id, amount_cents, currency, status, refund_request_id")
        .eq("tenant_id", tenant_id)
    )
    if refund_request_id:
        query = query.eq("refund_request_id", refund_request_id)
    if stripe_refund_id:
        query = query.eq("stripe_refund_id", stripe_refund_id)
    result = query.limit(1).execute()
    return result.data[0] if result.data else None
