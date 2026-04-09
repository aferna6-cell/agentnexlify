"""Widget lead capture endpoints: POST /lead and POST /offline-contact.

WARNING: PEP 563 deferred annotations are incompatible with FastAPI.
It breaks FastAPI's parameter introspection — Pydantic body models and
BackgroundTasks get treated as query params, causing 422 errors.
"""

import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from backend.limiter import limiter
from backend.models.database import get_service_supabase
from backend.models.schemas import WidgetLeadRequest, WidgetLeadResponse, WidgetOfflineContactRequest
from backend.services.activity import log_activity
from backend.services.lead_qualification import qualify_lead_background
from backend.services.lead_scoring import score_lead_background
from backend.services.webhook_dispatcher import fire_event_background
from backend.routers.widget_helpers import (
    _get_or_create_conversation,
    _get_tenant,
    _get_widget_config,
    _send_new_lead_email_notification,
    _send_new_lead_sms_notification,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/widget", tags=["widget"])


@router.post("/lead", response_model=WidgetLeadResponse)
@limiter.limit("60/minute")
async def submit_lead(request: Request, req: WidgetLeadRequest, background_tasks: BackgroundTasks):
    """Manually submit or update lead information from the widget."""
    widget = _get_widget_config(req.api_key)
    tenant = _get_tenant(widget["tenant_id"])

    # Find or create conversation
    conversation_id, _ = _get_or_create_conversation(tenant["id"], req.session_id)

    # Build fields from request
    fields: dict[str, str] = {}
    if req.name:
        fields["name"] = req.name
    if req.email:
        fields["email"] = req.email
    if req.phone:
        fields["phone"] = req.phone
    if req.service:
        fields["areas_of_interest"] = req.service

    if not fields:
        raise HTTPException(status_code=400, detail="No lead fields provided")

    db = get_service_supabase()
    lead_id = None
    is_new = False

    # Dedup by email + client_id (live schema uses client_id, not tenant_id)
    if fields.get("email"):
        existing = (
            db.table("leads")
            .select("id, name, phone")
            .eq("client_id", tenant["id"])
            .eq("email", fields["email"])
            .limit(1)
            .execute()
        )
        if existing.data:
            lead_id = existing.data[0]["id"]
            updates = {k: v for k, v in fields.items()
                       if k != "email" and not existing.data[0].get(k)}
            if updates:
                db.table("leads").update(updates).eq("id", lead_id).execute()

    if not lead_id:
        lead_fields: dict[str, Any] = {
            "client_id": tenant["id"],
            "status": "new",
            **fields,
        }
        try:
            from uuid import UUID
            UUID(conversation_id)
            lead_fields["conversation_id"] = conversation_id
        except (ValueError, AttributeError):
            logger.debug("lead_submit: conversation_id %r is not a UUID, omitting", conversation_id)
        result = db.table("leads").insert(lead_fields).execute()
        if result.data:
            lead_id = result.data[0]["id"]
            is_new = True

    if lead_id:
        background_tasks.add_task(score_lead_background, lead_id)

    # AI qualification only fires for NEW leads on eligible plans — the
    # service itself gates on plan, so we unconditionally enqueue here
    # and let the service decide whether to spend the API call.
    if lead_id and is_new:
        background_tasks.add_task(qualify_lead_background, lead_id)

    if lead_id and is_new:
        logger.info("SMS_TRIGGER[/lead]: new lead created lead_id=%s, about to trigger automation", lead_id)
        try:
            from backend.services.automation_engine import trigger_sequence
            await trigger_sequence(tenant["id"], lead_id, "new_lead")
            logger.info("SMS_TRIGGER[/lead]: trigger_sequence completed for lead %s", lead_id)
        except Exception:
            logger.warning("Failed to trigger automation for lead %s", lead_id, exc_info=True)

        # SMS notification to owner
        logger.info("SMS_TRIGGER[/lead]: about to call SMS notification for lead %s email=%s", lead_id, fields.get("email"))
        try:
            await _send_new_lead_sms_notification(tenant["id"], fields.get("name", "Unknown"), fields)
        except Exception:
            logger.error("SMS_TRIGGER[/lead]: FAILED for lead %s", lead_id, exc_info=True)

        # Email notification to owner
        try:
            await _send_new_lead_email_notification(tenant["id"], fields.get("name", "Unknown"), fields)
        except Exception:
            logger.error("EMAIL_TRIGGER[/lead]: FAILED for lead %s", lead_id, exc_info=True)

        # Email sequence enrollment trigger
        try:
            from backend.routers.email_sequences import enroll_lead_in_sequences
            await enroll_lead_in_sequences(tenant["id"], lead_id)
        except Exception:
            logger.warning("Failed to enroll lead %s in email sequences", lead_id, exc_info=True)

    return WidgetLeadResponse(
        lead_id=lead_id,
        updated_fields=list(fields.keys()),
    )


@router.post("/offline-contact")
@limiter.limit("30/minute")
async def submit_offline_contact(
    request: Request,
    body: WidgetOfflineContactRequest,
    background_tasks: BackgroundTasks,
):
    """Submit contact form when widget is in offline mode. Creates a lead."""
    try:
        # 1. Validate api_key and get widget config / tenant
        widget = _get_widget_config(body.api_key)
        tenant_id = widget["tenant_id"]
        logger.info(
            "offline_contact: tenant=%s name=%s email=%s",
            tenant_id, body.name, body.email,
        )

        db = get_service_supabase()

        # 2. Dedup by email + client_id (leads table uses client_id)
        lead_id = None
        try:
            existing = (
                db.table("leads")
                .select("id")
                .eq("client_id", tenant_id)
                .eq("email", body.email)
                .limit(1)
                .execute()
            )
            if existing.data:
                lead_id = existing.data[0]["id"]
                # Update existing lead with any new info
                updates: dict[str, Any] = {}
                if body.name:
                    updates["name"] = body.name
                if body.phone:
                    updates["phone"] = body.phone
                if updates:
                    db.table("leads").update(updates).eq("id", lead_id).execute()
                logger.info("offline_contact: updated existing lead %s", lead_id)
        except Exception as dedup_err:
            logger.error(
                "offline_contact: dedup check failed: %s", dedup_err, exc_info=True,
            )

        # 3. Create new lead if no existing one found
        offline_is_new = False
        if not lead_id:
            lead_fields: dict[str, Any] = {
                "client_id": tenant_id,
                "name": body.name,
                "email": body.email,
                "status": "new",
                "source": "widget_offline",
            }
            if body.phone:
                lead_fields["phone"] = body.phone
            try:
                result = db.table("leads").insert(lead_fields).execute()
                if result.data:
                    lead_id = result.data[0]["id"]
                    offline_is_new = True
                    logger.info("offline_contact: created new lead %s", lead_id)
                else:
                    logger.warning("offline_contact: INSERT returned no data")
            except Exception as insert_err:
                logger.error(
                    "offline_contact: lead INSERT failed: %s", insert_err, exc_info=True,
                )

        # 4. Log the message in activity_log
        if lead_id:
            try:
                log_activity(
                    tenant_id=tenant_id,
                    activity_type="offline_message",
                    description=body.message,
                    lead_id=lead_id,
                    metadata={"source": "widget_offline", "email": body.email},
                )
            except Exception:
                logger.warning(
                    "offline_contact: log_activity failed for lead %s",
                    lead_id, exc_info=True,
                )

            # Fire webhook for new offline contact
            try:
                fire_event_background(tenant_id, "lead.created", {
                    "lead_id": lead_id,
                    "name": body.name,
                    "email": body.email,
                    "phone": body.phone,
                    "source": "widget_offline",
                })
            except Exception:
                logger.warning(
                    "offline_contact: fire_event_background failed", exc_info=True,
                )

            # Score the lead (non-blocking via BackgroundTasks)
            background_tasks.add_task(score_lead_background, lead_id)

            # AI qualification for new leads on eligible plans.
            if offline_is_new:
                background_tasks.add_task(qualify_lead_background, lead_id)

        return {"success": True, "message": "Thank you! We'll get back to you soon."}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("offline_contact FAILED: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to submit contact form")
