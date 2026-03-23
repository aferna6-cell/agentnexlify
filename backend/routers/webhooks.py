"""Webhook management endpoints — CRUD for webhook configurations and delivery logs."""

import hashlib
import hmac
import json
import logging
import secrets
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from backend.limiter import limiter
from backend.models.database import get_supabase
from backend.models.schemas import (
    WebhookCreateRequest,
    WebhookListResponse,
    WebhookResponse,
    WebhookTestResponse,
    WebhookUpdateRequest,
    WebhookLogResponse,
)
from backend.routers.auth import _get_current_tenant, require_role
from backend.services.webhook_dispatcher import SUPPORTED_EVENTS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])


def _verify_tenant(claims: dict, tenant_id: str) -> None:
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")


# ---------------------------------------------------------------------------
# Static paths — MUST be defined before /{tenant_id} to prevent route shadow
# ---------------------------------------------------------------------------

@router.get("/schema/events")
async def webhook_events_schema():
    """Public endpoint: returns all webhook events with sample payloads for Zapier/integration setup."""
    now = datetime.now(timezone.utc)
    tomorrow = now + timedelta(days=1)
    tomorrow_end = tomorrow + timedelta(hours=1)

    schema = {}
    for event in sorted(SUPPORTED_EVENTS):
        sample = _build_sample_payload(event)
        schema[event] = {
            "description": {
                "lead.created": "Fired when a new lead is captured (from widget, CSV import, or offline form)",
                "lead.updated": "Fired when a lead's details or stage change",
                "appointment.booked": "Fired when a new appointment is booked",
                "appointment.cancelled": "Fired when an appointment is cancelled",
                "conversation.started": "Fired when a new chat conversation begins",
                "conversation.message": "Fired on each message exchange in a conversation",
                "automation.email_sent": "Fired when an automated email is sent via a sequence",
                "automation.sms_sent": "Fired when an automated SMS is sent via a sequence",
                "lead.status_changed": "Fired when a lead's status changes (e.g. new → contacted)",
                "order.created": "Fired when a new order is placed through the chat widget",
                "call.completed": "Fired when an AI-answered phone call completes",
                "invoice.created": "Fired when a new invoice is created",
                "invoice.paid": "Fired when an invoice is marked as paid",
                "form.submitted": "Fired when a public form receives a submission",
                "review.received": "Fired when a new customer review is added",
            }.get(event, event),
            "sample_payload": {
                "event": event,
                "timestamp": now.isoformat(),
                "data": sample,
            },
        }
    return {"events": schema}


# ---------------------------------------------------------------------------
# Tenant-scoped CRUD
# ---------------------------------------------------------------------------

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
    claims: dict = Depends(require_role("owner", "admin")),
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
    claims: dict = Depends(require_role("owner", "admin")),
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
    claims: dict = Depends(require_role("owner", "admin")),
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
    claims: dict = Depends(require_role("owner", "admin")),
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


def _build_sample_payload(event: str) -> dict:
    """Generate realistic sample data for a given webhook event type."""
    now = datetime.now(timezone.utc)
    tomorrow = now + timedelta(days=1)
    tomorrow_end = tomorrow + timedelta(hours=1)

    samples = {
        "lead.created": {
            "lead_id": "test-uuid",
            "name": "Test Lead",
            "email": "test@example.com",
            "phone": "+1 555-0100",
            "source": "widget",
        },
        "lead.updated": {
            "lead_id": "test-uuid",
            "updated_fields": ["status", "name"],
            "status": "contacted",
            "source": "widget",
        },
        "appointment.booked": {
            "appointment_id": "test-uuid",
            "customer_name": "Test Customer",
            "customer_email": "test@example.com",
            "start_time": tomorrow.isoformat(),
            "end_time": tomorrow_end.isoformat(),
        },
        "appointment.cancelled": {
            "appointment_id": "test-uuid",
            "customer_name": "Test Customer",
            "customer_email": "test@example.com",
            "start_time": tomorrow.isoformat(),
            "end_time": tomorrow_end.isoformat(),
        },
        "conversation.started": {
            "session_id": "test-session",
            "conversation_id": "test-conv-uuid",
        },
        "conversation.message": {
            "session_id": "test-session",
            "user_message": "Hello, I need help!",
            "assistant_message": "Hi! I'd be happy to help. What can I assist you with today?",
        },
        "automation.email_sent": {
            "lead_id": "test-uuid",
            "lead_email": "test@example.com",
            "subject": "Following up on your inquiry",
            "sequence_id": "test-seq-uuid",
            "step_order": 1,
        },
        "automation.sms_sent": {
            "lead_id": "test-uuid",
            "lead_phone": "+1 555-0100",
            "sequence_id": "test-seq-uuid",
            "step_order": 1,
        },
        "lead.status_changed": {
            "lead_id": "test-uuid",
            "old_status": "new",
            "new_status": "contacted",
        },
        "order.created": {
            "order_id": "test-uuid",
            "customer_name": "Test Customer",
            "items": [{"name": "Item 1", "quantity": 2, "price": 9.99}],
            "total": 19.98,
            "order_type": "delivery",
        },
        "call.completed": {
            "call_id": "test-uuid",
            "caller_phone": "+1 555-0100",
            "duration_seconds": 120,
            "summary": "Caller asked about pricing for a repair.",
        },
        "invoice.created": {
            "invoice_id": "test-uuid",
            "invoice_number": "INV-001",
            "total": 500.00,
            "lead_id": "test-uuid",
        },
        "invoice.paid": {
            "invoice_id": "test-uuid",
            "invoice_number": "INV-001",
            "total": 500.00,
            "payment_method": "stripe",
        },
        "form.submitted": {
            "form_id": "test-uuid",
            "submission_id": "test-uuid",
            "lead_id": "test-uuid",
            "data": {"name": "Test User", "email": "test@example.com", "message": "I'm interested"},
        },
        "review.received": {
            "review_id": "test-uuid",
            "platform": "google",
            "author_name": "Test Reviewer",
            "rating": 5,
            "review_text": "Great service!",
        },
    }
    return samples.get(event, {"message": "Test event", "event_type": event})


@router.post(
    "/{tenant_id}/{webhook_id}/test",
    response_model=WebhookTestResponse,
)
@limiter.limit("10/minute")
async def test_webhook(
    request: Request,
    tenant_id: str,
    webhook_id: str,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Send a sample event to a webhook URL to verify it is working."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()

    # Fetch webhook and verify ownership
    try:
        result = (
            db.table("webhooks")
            .select("id, url, events, secret")
            .eq("id", webhook_id)
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception("Failed to fetch webhook %s for tenant %s", webhook_id, tenant_id)
        raise HTTPException(status_code=500, detail="Failed to fetch webhook")

    if not result.data:
        raise HTTPException(status_code=404, detail="Webhook not found")

    webhook = result.data[0]

    # Pick event type: first from webhook's events list, or default
    events_list = webhook.get("events") or []
    event = events_list[0] if events_list else "lead.created"

    # Build the envelope
    sample_data = _build_sample_payload(event)
    payload = {
        "event": event,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": sample_data,
        "test": True,
    }

    payload_bytes = json.dumps(payload, default=str).encode()

    # Sign with HMAC-SHA256 if webhook has a secret
    headers = {"Content-Type": "application/json"}
    secret = webhook.get("secret")
    if secret:
        signature = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()
        headers["X-Webhook-Signature"] = signature

    # Deliver
    success = False
    status_code = None
    response_body = None

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(webhook["url"], content=payload_bytes, headers=headers)
            status_code = resp.status_code
            response_body = resp.text[:2000]
            success = 200 <= resp.status_code < 300
    except httpx.TimeoutException:
        response_body = "Timeout after 10 seconds"
        logger.warning("Webhook test timed out for webhook %s", webhook_id)
    except Exception as exc:
        response_body = str(exc)[:2000]
        logger.warning("Webhook test delivery failed for webhook %s: %s", webhook_id, exc)

    # Log result in webhook_logs
    try:
        db.table("webhook_logs").insert({
            "webhook_id": webhook_id,
            "event": event,
            "payload": payload,
            "response_status": status_code,
            "response_body": response_body,
            "success": success,
        }).execute()
    except Exception:
        logger.exception("Failed to log webhook test result for webhook %s", webhook_id)

    return WebhookTestResponse(
        success=success,
        status_code=status_code,
        response_body=response_body,
        event=event,
    )
