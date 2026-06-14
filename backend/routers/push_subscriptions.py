"""Web Push subscription management for pending-approval notifications.

Free alternative to the SMS alert leg: the dashboard subscribes the owner's
browser, and os_push_notify fans out to stored subscriptions when an Agent OS
deliverable lands in pending_approval.

Degrades gracefully: GET /vapid-public-key 404s when VAPID keys are unset
(pending manual Railway env step), and the frontend hides the settings card.

Critical rules:
  - No from __future__ import annotations (FastAPI router file)
  - Never log full endpoint URLs (capability URLs — truncate)
  - push_subscriptions table uses tenant_id (new OS-adjacent table)
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from backend.dependencies import _get_current_tenant, verify_tenant
from backend.config import settings
from backend.models.database import get_service_supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/push", tags=["push"])


def _truncate_endpoint(endpoint: str) -> str:
    return str(endpoint)[:48] + "..."


class PushSubscribeRequest(BaseModel):
    endpoint: str = Field(..., max_length=2000)
    keys: dict = Field(...)

    @field_validator("endpoint")
    @classmethod
    def validate_endpoint(cls, v: str) -> str:
        # SSRF guard: the server POSTs to this URL via pywebpush — only the
        # major browser push services are acceptable hosts. Re-checked at
        # send time in os_push_notify._send_one for rows that predate this.
        from backend.services.os_push_notify import endpoint_host_allowed

        v = v.strip()
        if not endpoint_host_allowed(v):
            raise ValueError("endpoint must be an https URL on a known push service")
        return v

    @field_validator("keys")
    @classmethod
    def validate_keys(cls, v: dict) -> dict:
        if not v.get("p256dh") or not v.get("auth"):
            raise ValueError("keys must contain p256dh and auth")
        return {"p256dh": str(v["p256dh"]), "auth": str(v["auth"])}


class PushUnsubscribeRequest(BaseModel):
    endpoint: str = Field(..., max_length=2000)


@router.get("/vapid-public-key")
async def get_vapid_public_key():
    """Public VAPID key for PushManager.subscribe. 404 when push unconfigured."""
    if not settings.vapid_public_key:
        raise HTTPException(status_code=404, detail="Push notifications not configured")
    return {"public_key": settings.vapid_public_key}


@router.post("/{tenant_id}/subscribe")
async def subscribe(
    tenant_id: str,
    req: PushSubscribeRequest,
    claims: dict = Depends(_get_current_tenant),
):
    """Store (upsert) a browser push subscription for the tenant."""
    verify_tenant(claims, tenant_id)

    db = get_service_supabase()
    try:
        db.table("push_subscriptions").upsert(
            {
                "tenant_id": tenant_id,
                "endpoint": req.endpoint,
                "keys": req.keys,
            },
            on_conflict="endpoint",
        ).execute()
    except Exception:
        logger.exception(
            "push: subscribe failed for tenant %s (endpoint %s)",
            tenant_id,
            _truncate_endpoint(req.endpoint),
        )
        raise HTTPException(status_code=500, detail="Failed to save subscription")

    logger.info(
        "push: subscribed tenant %s (endpoint %s)",
        tenant_id,
        _truncate_endpoint(req.endpoint),
    )
    return {"success": True}


@router.post("/{tenant_id}/unsubscribe")
async def unsubscribe(
    tenant_id: str,
    req: PushUnsubscribeRequest,
    claims: dict = Depends(_get_current_tenant),
):
    """Remove a browser push subscription for the tenant."""
    verify_tenant(claims, tenant_id)

    db = get_service_supabase()
    try:
        db.table("push_subscriptions").delete().eq("tenant_id", tenant_id).eq(
            "endpoint", req.endpoint
        ).execute()
    except Exception:
        logger.exception(
            "push: unsubscribe failed for tenant %s (endpoint %s)",
            tenant_id,
            _truncate_endpoint(req.endpoint),
        )
        raise HTTPException(status_code=500, detail="Failed to remove subscription")

    return {"success": True}
