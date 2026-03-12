"""Webhook management endpoints — CRUD for webhook configurations and delivery logs."""

import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.models.database import get_supabase
from backend.models.schemas import (
    WebhookCreateRequest,
    WebhookListResponse,
    WebhookResponse,
    WebhookUpdateRequest,
    WebhookLogResponse,
)
from backend.routers.auth import _get_current_tenant
from backend.services.webhook_dispatcher import SUPPORTED_EVENTS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])


def _verify_tenant(claims: dict, tenant_id: str) -> None:
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")


@router.get("/{tenant_id}", response_model=list[WebhookListResponse])
async def list_webhooks(tenant_id: str, claims: dict = Depends(_get_current_tenant)):
    _verify_tenant(claims, tenant_id)
    db = get_supabase()
    result = (
        db.table("webhooks")
        .select("id, tenant_id, name, url, events, is_active, last_triggered_at, failure_count, created_at")
        .eq("tenant_id", tenant_id)
        .order("created_at", desc=True)
        .execute()
    )
    return [WebhookListResponse(**row) for row in (result.data or [])]


@router.post("/{tenant_id}", response_model=WebhookResponse, status_code=201)
async def create_webhook(
    tenant_id: str,
    req: WebhookCreateRequest,
    claims: dict = Depends(_get_current_tenant),
):
    _verify_tenant(claims, tenant_id)

    # Validate events
    invalid = set(req.events) - SUPPORTED_EVENTS
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid events: {invalid}. Valid: {sorted(SUPPORTED_EVENTS)}",
        )

    # Limit webhooks per tenant
    db = get_supabase()
    existing = (
        db.table("webhooks")
        .select("id", count="exact")
        .eq("tenant_id", tenant_id)
        .execute()
    )
    if (existing.count or 0) >= 20:
        raise HTTPException(status_code=400, detail="Maximum 20 webhooks per account")

    webhook_data = {
        "tenant_id": tenant_id,
        "name": req.name,
        "url": req.url,
        "events": req.events,
        "secret": req.secret or secrets.token_urlsafe(32),
        "is_active": True,
    }

    result = db.table("webhooks").insert(webhook_data).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create webhook")

    return WebhookResponse(**result.data[0])


@router.put("/{tenant_id}/{webhook_id}", response_model=WebhookListResponse)
async def update_webhook(
    tenant_id: str,
    webhook_id: str,
    req: WebhookUpdateRequest,
    claims: dict = Depends(_get_current_tenant),
):
    _verify_tenant(claims, tenant_id)

    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    # Validate events if provided
    if "events" in updates:
        invalid = set(updates["events"]) - SUPPORTED_EVENTS
        if invalid:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid events: {invalid}. Valid: {sorted(SUPPORTED_EVENTS)}",
            )

    db = get_supabase()
    result = (
        db.table("webhooks")
        .update(updates)
        .eq("id", webhook_id)
        .eq("tenant_id", tenant_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Webhook not found")

    return WebhookListResponse(**result.data[0])


@router.patch("/{tenant_id}/{webhook_id}/toggle")
async def toggle_webhook(
    tenant_id: str,
    webhook_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    _verify_tenant(claims, tenant_id)
    db = get_supabase()

    current = (
        db.table("webhooks")
        .select("is_active, failure_count")
        .eq("id", webhook_id)
        .eq("tenant_id", tenant_id)
        .limit(1)
        .execute()
    )
    if not current.data:
        raise HTTPException(status_code=404, detail="Webhook not found")

    new_active = not current.data[0]["is_active"]
    update_data = {"is_active": new_active}
    # Reset failure count when re-enabling
    if new_active:
        update_data["failure_count"] = 0

    result = (
        db.table("webhooks")
        .update(update_data)
        .eq("id", webhook_id)
        .eq("tenant_id", tenant_id)
        .execute()
    )

    return {"is_active": new_active, "id": webhook_id}


@router.delete("/{tenant_id}/{webhook_id}", status_code=204)
async def delete_webhook(
    tenant_id: str,
    webhook_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    _verify_tenant(claims, tenant_id)
    db = get_supabase()
    result = (
        db.table("webhooks")
        .delete()
        .eq("id", webhook_id)
        .eq("tenant_id", tenant_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Webhook not found")


@router.get("/{tenant_id}/logs/recent", response_model=list[WebhookLogResponse])
async def recent_logs(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
    limit: int = Query(20, ge=1, le=100),
):
    _verify_tenant(claims, tenant_id)
    db = get_supabase()

    # Get webhook IDs for this tenant
    webhooks = (
        db.table("webhooks")
        .select("id")
        .eq("tenant_id", tenant_id)
        .execute()
    )
    webhook_ids = [w["id"] for w in (webhooks.data or [])]
    if not webhook_ids:
        return []

    result = (
        db.table("webhook_logs")
        .select("*")
        .in_("webhook_id", webhook_ids)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

    return [WebhookLogResponse(**row) for row in (result.data or [])]


@router.get("/{tenant_id}/events")
async def list_events(tenant_id: str, claims: dict = Depends(_get_current_tenant)):
    """Return all supported webhook events."""
    _verify_tenant(claims, tenant_id)
    return {"events": sorted(SUPPORTED_EVENTS)}
