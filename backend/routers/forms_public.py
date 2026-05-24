"""Public (unauthenticated) form endpoints.

Extracted from forms.py (god class split 2026-05-24).
These routes are registered BEFORE admin routes in forms.py so FastAPI does
not match the literal `/public/{token}` against the dynamic
`/{tenant_id}/{form_id}` route pattern.

WARNING: PEP 563 deferred annotations are incompatible with FastAPI — do not
add a future-annotations import here.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from backend.limiter import limiter
from backend.models.database import get_service_supabase
from backend.routers.forms_models import PublicFormSubmission
from backend.services.form_rendering import (
    extract_lead_fields,
    render_form_embed_html,
    validate_required_fields,
)
from backend.services.webhook_dispatcher import fire_event_background

logger = logging.getLogger(__name__)

router = APIRouter(tags=["forms"])


@router.get("/public/{token}")
@limiter.limit("30/minute")
async def get_public_form(request: Request, token: str):
    """Get form definition by public token for rendering. No auth required."""
    db = get_service_supabase()
    try:
        result = (
            db.table("forms")
            .select("id, name, description, fields_json, settings_json, success_message, redirect_url, is_active")
            .eq("public_token", token)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception("Failed to fetch public form by token")
        raise HTTPException(status_code=500, detail="Failed to fetch form")

    if not result.data:
        raise HTTPException(status_code=404, detail="Form not found")

    form = result.data[0]

    if not form.get("is_active"):
        raise HTTPException(status_code=410, detail="This form is no longer accepting submissions")

    # Strip internal fields — only return what the public needs
    return {
        "id": form["id"],
        "name": form["name"],
        "description": form.get("description"),
        "fields": form.get("fields_json", []),
        "settings": form.get("settings_json", {}),
        "success_message": form.get("success_message", "Thank you for your submission!"),
        "redirect_url": form.get("redirect_url"),
    }


@router.get("/public/{token}/embed", response_class=HTMLResponse)
@limiter.limit("30/minute")
async def get_public_form_embed(request: Request, token: str):
    """Render the form as a self-contained HTML page for iframe embedding."""
    db = get_service_supabase()
    try:
        result = (
            db.table("forms")
            .select(
                "id, name, description, fields_json, settings_json, "
                "is_active, public_token, success_message"
            )
            .eq("public_token", token)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception("Failed to fetch public form for embed")
        return HTMLResponse("<h2>Something went wrong. Please try again later.</h2>", status_code=500)

    if not result.data:
        return HTMLResponse("<h2>Form not found</h2>", status_code=404)

    form = result.data[0]
    if not form.get("is_active"):
        return HTMLResponse("<h2>This form is no longer accepting submissions.</h2>", status_code=410)

    return HTMLResponse(render_form_embed_html(form))


@router.post("/public/{token}/submit")
@limiter.limit("10/minute")
async def submit_public_form(
    token: str,
    req: PublicFormSubmission,
    request: Request,
):
    """Submit form data publicly. Auto-creates lead if name/email/phone present.

    No auth required — this is the public submission endpoint for embedded forms.
    """
    db = get_service_supabase()

    # Fetch the form by token
    try:
        form_result = (
            db.table("forms")
            .select("id, tenant_id, fields_json, success_message, is_active, submission_count")
            .eq("public_token", token)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception("Failed to fetch form for public submission")
        raise HTTPException(status_code=500, detail="Failed to process submission")

    if not form_result.data:
        raise HTTPException(status_code=404, detail="Form not found")

    form = form_result.data[0]

    if not form.get("is_active"):
        raise HTTPException(status_code=410, detail="This form is no longer accepting submissions")

    form_id = form["id"]
    tenant_id = form["tenant_id"]
    fields_spec = form.get("fields_json") or []
    submitted_data = req.data_json

    missing_fields = validate_required_fields(fields_spec, submitted_data)
    if missing_fields:
        raise HTTPException(
            status_code=422,
            detail=f"Missing required fields: {', '.join(missing_fields)}",
        )

    # Extract IP address
    ip_address = None
    if request.client:
        ip_address = request.client.host

    # Insert the submission
    submission_data: dict = {
        "form_id": form_id,
        "tenant_id": tenant_id,
        "data_json": submitted_data,
        "source_url": req.source_url,
        "ip_address": ip_address,
    }

    lead_id = None
    lead_fields = extract_lead_fields(submitted_data, fields_spec)
    lead_name = lead_fields["name"]
    lead_email = lead_fields["email"]
    lead_phone = lead_fields["phone"]

    if lead_email or lead_phone:
        # Try to find existing lead first (dedup by email or phone)
        try:
            dedup_query = db.table("leads").select("id").eq("client_id", tenant_id)
            if lead_email:
                dedup_query = dedup_query.eq("email", lead_email)
            elif lead_phone:
                dedup_query = dedup_query.eq("phone", lead_phone)
            dedup_result = dedup_query.limit(1).execute()

            if dedup_result.data:
                lead_id = dedup_result.data[0]["id"]
                logger.info("Form submission matched existing lead %s for tenant %s", lead_id, tenant_id)
            else:
                # Create new lead — uses client_id (NOT tenant_id) per schema
                lead_insert: dict = {
                    "client_id": tenant_id,
                    "source": "form",
                    "status": "new",
                }
                if lead_name:
                    lead_insert["name"] = lead_name
                if lead_email:
                    lead_insert["email"] = lead_email
                if lead_phone:
                    lead_insert["phone"] = lead_phone

                lead_result = db.table("leads").insert(lead_insert).execute()
                if lead_result.data:
                    lead_id = lead_result.data[0]["id"]
                    logger.info("Form submission created new lead %s for tenant %s", lead_id, tenant_id)
        except Exception:
            logger.exception("Failed to create/find lead from form submission for tenant %s", tenant_id)
            # Continue with submission even if lead creation fails

    if lead_id:
        submission_data["lead_id"] = lead_id

    try:
        sub_result = db.table("form_submissions").insert(submission_data).execute()
    except Exception:
        logger.exception("Failed to insert form submission for form %s", form_id)
        raise HTTPException(status_code=500, detail="Failed to save submission")

    if not sub_result.data:
        raise HTTPException(status_code=500, detail="Failed to save submission")

    # Increment submission_count on the form
    try:
        current_count = form.get("submission_count", 0) or 0
        db.table("forms").update(
            {"submission_count": current_count + 1, "updated_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", form_id).execute()
    except Exception:
        logger.warning("Failed to increment submission_count for form %s", form_id, exc_info=True)

    # Fire webhook event
    try:
        fire_event_background(
            tenant_id=tenant_id,
            event="form.submitted",
            data={
                "form_id": form_id,
                "submission_id": sub_result.data[0].get("id"),
                "lead_id": lead_id,
                "data": submitted_data,
            },
        )
    except Exception:
        logger.warning("Failed to fire form.submitted webhook for form %s", form_id, exc_info=True)

    success_message = form.get("success_message") or "Thank you for your submission!"
    return {
        "success": True,
        "message": success_message,
        "submission_id": sub_result.data[0].get("id"),
        "lead_id": lead_id,
    }
