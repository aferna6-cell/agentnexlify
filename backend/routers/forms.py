"""Form & Survey Builder — create embeddable forms, collect submissions, auto-create leads."""

import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from backend.limiter import limiter
from backend.models.database import get_supabase
from backend.routers.auth import _get_current_tenant, require_role
from backend.services.webhook_dispatcher import fire_event_background

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/forms", tags=["forms"])


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------

class FormFieldModel(BaseModel):
    id: str = Field(..., max_length=100)
    type: str = Field(..., pattern="^(text|email|phone|textarea|select|radio|checkbox|number|date)$")
    label: str = Field(..., max_length=200)
    required: bool = False
    placeholder: str | None = Field(None, max_length=300)
    options: list[str] | None = None


class FormSettingsModel(BaseModel):
    theme_color: str | None = Field(None, max_length=20)
    submit_button_text: str | None = Field(None, max_length=100)
    show_branding: bool = True


class FormCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(None, max_length=2000)
    fields_json: list[FormFieldModel] = Field(default_factory=list)
    settings_json: FormSettingsModel | None = None
    redirect_url: str | None = Field(None, max_length=2000)
    success_message: str | None = Field(None, max_length=1000)
    is_active: bool = True


class FormUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, max_length=2000)
    fields_json: list[FormFieldModel] | None = None
    settings_json: FormSettingsModel | None = None
    redirect_url: str | None = Field(None, max_length=2000)
    success_message: str | None = Field(None, max_length=1000)
    is_active: bool | None = None


class PublicFormSubmission(BaseModel):
    data_json: dict = Field(default_factory=dict)
    source_url: str | None = Field(None, max_length=2000)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _verify_tenant(claims: dict, tenant_id: str) -> None:
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")


def _generate_public_token() -> str:
    """Generate a short, URL-safe public token for form embedding."""
    return f"frm_{secrets.token_urlsafe(24)}"


# ---------------------------------------------------------------------------
# ROUTE ORDERING: Public endpoints and static sub-paths (/public/*, /stats)
# are registered BEFORE dynamic /{tenant_id}/{form_id} routes so FastAPI
# does not mistake the literal path segments for path parameters.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Public Endpoints (No auth — for embedded forms)
# ---------------------------------------------------------------------------

@router.get("/public/{token}")
@limiter.limit("30/minute")
async def get_public_form(request: Request, token: str):
    """Get form definition by public token for rendering. No auth required."""
    db = get_supabase()
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
    db = get_supabase()

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

    # Validate required fields
    missing_fields = []
    for field_def in fields_spec:
        if field_def.get("required"):
            field_id = field_def.get("id", "")
            value = submitted_data.get(field_id)
            if value is None or (isinstance(value, str) and not value.strip()):
                missing_fields.append(field_def.get("label") or field_id)

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

    # Auto-create lead if name/email/phone fields are present
    lead_id = None
    lead_name = None
    lead_email = None
    lead_phone = None

    # Build a map of field IDs to field types for smart extraction
    field_type_map = {f.get("id", ""): f.get("type", "text") for f in fields_spec}

    for field_id, value in submitted_data.items():
        if not value or not isinstance(value, str):
            continue
        value = value.strip()
        if not value:
            continue

        ftype = field_type_map.get(field_id, "text")
        field_lower = field_id.lower()

        if ftype == "email" or field_lower in ("email", "email_address", "e-mail"):
            lead_email = value
        elif ftype == "phone" or field_lower in ("phone", "phone_number", "mobile", "tel"):
            lead_phone = value
        elif field_lower in ("name", "full_name", "fullname", "your_name", "customer_name"):
            lead_name = value

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


# ---------------------------------------------------------------------------
# Authenticated Endpoints (Dashboard)
# IMPORTANT: /{tenant_id}/stats is registered BEFORE /{tenant_id}/{form_id}
# so FastAPI doesn't match "stats" as a form_id.
# ---------------------------------------------------------------------------

@router.get("/{tenant_id}/stats")
async def form_stats(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Form analytics: total forms, total submissions, conversion rate."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()

    try:
        forms_result = (
            db.table("forms")
            .select("id, submission_count, is_active, created_at")
            .eq("tenant_id", tenant_id)
            .execute()
        )
    except Exception:
        logger.exception("Failed to fetch form stats for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to fetch form stats")

    forms = forms_result.data or []
    total_forms = len(forms)
    active_forms = sum(1 for f in forms if f.get("is_active"))
    total_submissions = sum(f.get("submission_count", 0) for f in forms)

    # Conversion rate: submissions that resulted in leads / total submissions
    leads_from_forms = 0
    try:
        leads_result = (
            db.table("leads")
            .select("id", count="exact")
            .eq("client_id", tenant_id)
            .eq("source", "form")
            .execute()
        )
        leads_from_forms = leads_result.count or 0
    except Exception:
        logger.warning("Could not count form-sourced leads for tenant %s", tenant_id, exc_info=True)

    conversion_rate = round(
        (leads_from_forms / total_submissions * 100) if total_submissions > 0 else 0.0,
        1,
    )

    return {
        "total_forms": total_forms,
        "active_forms": active_forms,
        "total_submissions": total_submissions,
        "leads_from_forms": leads_from_forms,
        "conversion_rate": conversion_rate,
    }


@router.get("/{tenant_id}")
async def list_forms(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """List all forms for a tenant."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()
    try:
        result = (
            db.table("forms")
            .select("*", count="exact")
            .eq("tenant_id", tenant_id)
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
    except Exception:
        logger.exception("Failed to list forms for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to list forms")

    return {
        "forms": result.data or [],
        "count": result.count or len(result.data or []),
        "offset": offset,
        "limit": limit,
    }


@router.post("/{tenant_id}", status_code=201)
async def create_form(
    tenant_id: str,
    req: FormCreate,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Create a new form with fields and settings."""
    _verify_tenant(claims, tenant_id)

    public_token = _generate_public_token()
    fields = [field.model_dump() for field in req.fields_json]
    settings_data = req.settings_json.model_dump() if req.settings_json else {}

    data: dict = {
        "tenant_id": tenant_id,
        "name": req.name,
        "fields_json": fields,
        "settings_json": settings_data,
        "is_active": req.is_active,
        "public_token": public_token,
        "submission_count": 0,
    }
    if req.description is not None:
        data["description"] = req.description
    if req.redirect_url is not None:
        data["redirect_url"] = req.redirect_url
    if req.success_message is not None:
        data["success_message"] = req.success_message

    db = get_supabase()
    try:
        result = db.table("forms").insert(data).execute()
    except Exception:
        logger.exception("Failed to create form for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to create form")

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create form")
    return result.data[0]


@router.get("/{tenant_id}/{form_id}")
async def get_form(
    tenant_id: str,
    form_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Get a single form with submission stats."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()
    try:
        result = (
            db.table("forms")
            .select("*")
            .eq("id", form_id)
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception("Failed to fetch form %s for tenant %s", form_id, tenant_id)
        raise HTTPException(status_code=500, detail="Failed to fetch form")

    if not result.data:
        raise HTTPException(status_code=404, detail="Form not found")

    form = result.data[0]

    # Enrich with recent submission count (last 7 days)
    try:
        week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        recent_result = (
            db.table("form_submissions")
            .select("id", count="exact")
            .eq("form_id", form_id)
            .eq("tenant_id", tenant_id)
            .gte("created_at", week_ago)
            .execute()
        )
        form["submissions_last_7_days"] = recent_result.count or 0
    except Exception:
        logger.warning("Could not fetch recent submissions for form %s", form_id, exc_info=True)
        form["submissions_last_7_days"] = 0

    return form


@router.put("/{tenant_id}/{form_id}")
async def update_form(
    tenant_id: str,
    form_id: str,
    req: FormUpdate,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Update form name, fields, settings, or active status."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()

    # Verify form exists
    try:
        existing_result = (
            db.table("forms")
            .select("id")
            .eq("id", form_id)
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception("Failed to fetch form %s for update", form_id)
        raise HTTPException(status_code=500, detail="Failed to fetch form")

    if not existing_result.data:
        raise HTTPException(status_code=404, detail="Form not found")

    updates: dict = {"updated_at": datetime.now(timezone.utc).isoformat()}

    if req.name is not None:
        updates["name"] = req.name
    if req.description is not None:
        updates["description"] = req.description
    if req.fields_json is not None:
        updates["fields_json"] = [field.model_dump() for field in req.fields_json]
    if req.settings_json is not None:
        updates["settings_json"] = req.settings_json.model_dump()
    if req.redirect_url is not None:
        updates["redirect_url"] = req.redirect_url
    if req.success_message is not None:
        updates["success_message"] = req.success_message
    if req.is_active is not None:
        updates["is_active"] = req.is_active

    if len(updates) == 1:  # only updated_at was set
        raise HTTPException(status_code=400, detail="No fields to update")

    try:
        result = (
            db.table("forms")
            .update(updates)
            .eq("id", form_id)
            .eq("tenant_id", tenant_id)
            .execute()
        )
    except Exception:
        logger.exception("Failed to update form %s for tenant %s", form_id, tenant_id)
        raise HTTPException(status_code=500, detail="Failed to update form")

    if not result.data:
        raise HTTPException(status_code=404, detail="Form not found")
    return result.data[0]


@router.delete("/{tenant_id}/{form_id}")
async def delete_form(
    tenant_id: str,
    form_id: str,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Delete a form and its submissions."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()

    # Verify form exists
    try:
        existing_result = (
            db.table("forms")
            .select("id")
            .eq("id", form_id)
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception("Failed to fetch form %s before delete", form_id)
        raise HTTPException(status_code=500, detail="Failed to fetch form")

    if not existing_result.data:
        raise HTTPException(status_code=404, detail="Form not found")

    # Delete submissions first (if no FK cascade)
    try:
        db.table("form_submissions").delete().eq("form_id", form_id).eq("tenant_id", tenant_id).execute()
    except Exception:
        logger.warning("Could not delete submissions for form %s", form_id, exc_info=True)

    # Delete the form
    try:
        db.table("forms").delete().eq("id", form_id).eq("tenant_id", tenant_id).execute()
    except Exception:
        logger.exception("Failed to delete form %s for tenant %s", form_id, tenant_id)
        raise HTTPException(status_code=500, detail="Failed to delete form")

    return {"deleted": True}


@router.get("/{tenant_id}/{form_id}/submissions")
async def list_submissions(
    tenant_id: str,
    form_id: str,
    claims: dict = Depends(_get_current_tenant),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """List form submissions with optional lead enrichment."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()

    # Verify form exists
    try:
        form_check = (
            db.table("forms")
            .select("id")
            .eq("id", form_id)
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception("Failed to verify form %s for submissions list", form_id)
        raise HTTPException(status_code=500, detail="Failed to verify form")

    if not form_check.data:
        raise HTTPException(status_code=404, detail="Form not found")

    try:
        result = (
            db.table("form_submissions")
            .select("*", count="exact")
            .eq("form_id", form_id)
            .eq("tenant_id", tenant_id)
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
    except Exception:
        logger.exception("Failed to list submissions for form %s", form_id)
        raise HTTPException(status_code=500, detail="Failed to list submissions")

    submissions = result.data or []

    # Enrich with lead names
    lead_ids = list({s["lead_id"] for s in submissions if s.get("lead_id")})
    lead_names: dict[str, str] = {}
    if lead_ids:
        try:
            leads_result = (
                db.table("leads")
                .select("id, name, email")
                .in_("id", lead_ids)
                .eq("client_id", tenant_id)
                .execute()
            )
            for lead in (leads_result.data or []):
                lead_names[lead["id"]] = lead.get("name") or lead.get("email") or ""
        except Exception:
            logger.warning("Could not batch-fetch lead names for form submissions", exc_info=True)

    for sub in submissions:
        sub["lead_name"] = lead_names.get(sub.get("lead_id", ""), "")

    return {
        "submissions": submissions,
        "count": result.count or len(submissions),
        "offset": offset,
        "limit": limit,
    }
