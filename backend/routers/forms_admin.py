"""Authenticated (dashboard) form CRUD endpoints.

Extracted from forms.py (god class split 2026-05-24).
Registered AFTER public routes in forms.py — see forms_public.py for ordering.

Route ordering note: `/stats` and `/presets` are registered BEFORE the
dynamic `/{form_id}` routes so FastAPI does not treat them as form IDs.

WARNING: PEP 563 deferred annotations are incompatible with FastAPI — do not
add a future-annotations import here.
"""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.dependencies import _get_current_tenant, require_role, verify_tenant
from backend.models.database import get_service_supabase
from backend.routers.forms_models import FormCreate, FormUpdate
from backend.services.form_defaults import _FORM_PRESETS
from backend.services.form_rendering import generate_public_token

logger = logging.getLogger(__name__)

router = APIRouter(tags=["forms"])


@router.get("/{tenant_id}/stats")
async def form_stats(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Form analytics: total forms, total submissions, conversion rate."""
    verify_tenant(claims, tenant_id)

    db = get_service_supabase()

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
    verify_tenant(claims, tenant_id)

    db = get_service_supabase()
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
    verify_tenant(claims, tenant_id)

    public_token = generate_public_token()
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

    db = get_service_supabase()
    try:
        result = db.table("forms").insert(data).execute()
    except Exception:
        logger.exception("Failed to create form for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to create form")

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create form")
    return result.data[0]


# Presets must come before /{tenant_id}/{form_id} to avoid route shadowing
@router.get("/{tenant_id}/presets")
async def list_form_presets(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """List available form presets for one-click creation."""
    verify_tenant(claims, tenant_id)
    return [
        {"key": key, "name": preset["name"], "description": preset["description"], "field_count": len(preset["fields"])}
        for key, preset in _FORM_PRESETS.items()
    ]


@router.post("/{tenant_id}/presets/{preset_key}")
async def create_form_from_preset(
    tenant_id: str,
    preset_key: str,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Create a form from a preset template."""
    verify_tenant(claims, tenant_id)

    if preset_key not in _FORM_PRESETS:
        raise HTTPException(status_code=404, detail=f"Preset '{preset_key}' not found")

    preset = _FORM_PRESETS[preset_key]
    public_token = generate_public_token()

    data = {
        "tenant_id": tenant_id,
        "name": preset["name"],
        "description": preset.get("description"),
        "fields_json": preset["fields"],
        "settings_json": {},
        "is_active": True,
        "public_token": public_token,
        "submission_count": 0,
        "success_message": preset.get("success_message"),
    }

    db = get_service_supabase()
    try:
        result = db.table("forms").insert(data).execute()
    except Exception:
        logger.exception("Failed to create form from preset %s for tenant %s", preset_key, tenant_id)
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
    verify_tenant(claims, tenant_id)

    db = get_service_supabase()
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
    verify_tenant(claims, tenant_id)

    db = get_service_supabase()

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
    verify_tenant(claims, tenant_id)

    db = get_service_supabase()

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
    verify_tenant(claims, tenant_id)

    db = get_service_supabase()

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
