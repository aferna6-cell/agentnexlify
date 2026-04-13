"""Form & Survey Builder — create embeddable forms, collect submissions, auto-create leads."""

import html
import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from backend.dependencies import verify_tenant
from backend.limiter import limiter
from backend.models.database import get_service_supabase
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
    data_json: dict = Field(default_factory=dict, max_length=100)
    source_url: str | None = Field(None, max_length=2000)

    def model_post_init(self, __context):
        """Validate data_json size to prevent DoS via oversized payloads."""
        import json
        serialized = json.dumps(self.data_json)
        if len(serialized) > 50_000:  # 50KB max
            raise ValueError("Form submission data too large (max 50KB)")
        if len(self.data_json) > 100:
            raise ValueError("Form submission has too many fields (max 100)")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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
            .select("id, name, description, fields_json, settings_json, is_active, public_token")
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

    fields = form.get("fields_json") or []
    settings = form.get("settings_json") or {}
    theme_color = html.escape(settings.get("theme_color", "#7c3aed"))
    submit_text = html.escape(settings.get("submit_button_text", "Submit"))
    form_name = html.escape(form.get("name", "Form"))
    form_desc = html.escape(form.get("description") or "")

    # Build field HTML
    field_html_parts = []
    for f in fields:
        fid = html.escape(f.get("id", ""))
        flabel = html.escape(f.get("label", ""))
        ftype = f.get("type", "text")
        freq = f.get("required", False)
        fplaceholder = html.escape(f.get("placeholder") or "")
        req_attr = "required" if freq else ""
        req_mark = ' <span style="color:#ef4444">*</span>' if freq else ""

        if ftype in ("text", "email", "phone", "number", "date"):
            input_type = {"phone": "tel"}.get(ftype, ftype)
            field_html_parts.append(
                f'<div class="field"><label>{flabel}{req_mark}</label>'
                f'<input type="{input_type}" name="{fid}" placeholder="{fplaceholder}" {req_attr}/></div>'
            )
        elif ftype == "textarea":
            field_html_parts.append(
                f'<div class="field"><label>{flabel}{req_mark}</label>'
                f'<textarea name="{fid}" placeholder="{fplaceholder}" rows="4" {req_attr}></textarea></div>'
            )
        elif ftype in ("select", "radio"):
            options = f.get("options") or []
            if ftype == "select":
                opts_html = '<option value="">Select...</option>'
                for o in options:
                    ov = html.escape(str(o))
                    opts_html += f'<option value="{ov}">{ov}</option>'
                field_html_parts.append(
                    f'<div class="field"><label>{flabel}{req_mark}</label>'
                    f'<select name="{fid}" {req_attr}>{opts_html}</select></div>'
                )
            else:
                radios = ""
                for o in options:
                    ov = html.escape(str(o))
                    radios += f'<label class="radio"><input type="radio" name="{fid}" value="{ov}" {req_attr}/> {ov}</label>'
                field_html_parts.append(f'<div class="field"><label>{flabel}{req_mark}</label><div class="radio-group">{radios}</div></div>')
        elif ftype == "checkbox":
            field_html_parts.append(
                f'<div class="field checkbox"><label><input type="checkbox" name="{fid}" value="true" {req_attr}/> {flabel}</label></div>'
            )

    fields_html = "\n".join(field_html_parts)

    page_html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{form_name}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f8fafc;color:#1e293b;padding:24px}}
.form-container{{max-width:560px;margin:0 auto;background:#fff;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,.1);padding:32px}}
h1{{font-size:1.5rem;margin-bottom:4px}}
.desc{{color:#64748b;margin-bottom:24px;font-size:.9rem}}
.field{{margin-bottom:16px}}
.field label{{display:block;font-weight:600;font-size:.85rem;margin-bottom:6px;color:#334155}}
.field input,.field textarea,.field select{{width:100%;padding:10px 12px;border:1px solid #e2e8f0;border-radius:8px;font-size:.9rem;transition:border .15s}}
.field input:focus,.field textarea:focus,.field select:focus{{outline:none;border-color:{theme_color};box-shadow:0 0 0 3px {theme_color}22}}
.checkbox label{{font-weight:normal;display:flex;align-items:center;gap:8px;cursor:pointer}}
.radio-group{{display:flex;flex-direction:column;gap:6px}}
.radio label{{font-weight:normal;display:flex;align-items:center;gap:6px;cursor:pointer}}
.submit-btn{{width:100%;padding:12px;border:none;border-radius:8px;background:{theme_color};color:#fff;font-size:1rem;font-weight:600;cursor:pointer;margin-top:8px;transition:opacity .15s}}
.submit-btn:hover{{opacity:.9}}
.submit-btn:disabled{{opacity:.5;cursor:wait}}
.success{{text-align:center;padding:40px 20px;color:#16a34a;font-size:1.1rem}}
.error{{color:#ef4444;font-size:.85rem;margin-top:8px}}
.powered{{text-align:center;margin-top:16px;font-size:.75rem;color:#94a3b8}}
.powered a{{color:#94a3b8;text-decoration:none}}
</style></head><body>
<div class="form-container">
<h1>{form_name}</h1>
{"<p class='desc'>" + form_desc + "</p>" if form_desc else ""}
<form id="publicForm">
{fields_html}
<button type="submit" class="submit-btn" id="submitBtn">{submit_text}</button>
<div id="errorMsg" class="error" style="display:none"></div>
</form>
<div id="successMsg" class="success" style="display:none"></div>
</div>
<div class="powered">Powered by <a href="https://agentnexlify.com" target="_blank">AgentNexLiFy</a></div>
<script>
document.getElementById("publicForm").addEventListener("submit",async function(e){{
e.preventDefault();
const btn=document.getElementById("submitBtn");
const err=document.getElementById("errorMsg");
btn.disabled=true;err.style.display="none";
const fd=new FormData(this);
const data={{}};
fd.forEach((v,k)=>{{if(data[k]){{if(!Array.isArray(data[k]))data[k]=[data[k]];data[k].push(v)}}else data[k]=v}});
try{{
const r=await fetch(window.location.href.replace("/embed","/submit"),{{
method:"POST",headers:{{"Content-Type":"application/json"}},body:JSON.stringify({{data:data}})
}});
if(!r.ok)throw new Error((await r.json().catch(()=>({{}}))).detail||"Submission failed");
document.getElementById("publicForm").style.display="none";
document.getElementById("successMsg").style.display="block";
document.getElementById("successMsg").textContent={repr(form.get("success_message") or "Thank you for your submission!")};
}}catch(ex){{err.textContent=ex.message;err.style.display="block"}}
finally{{btn.disabled=false}}
}});
</script></body></html>"""

    return HTMLResponse(page_html)


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
    public_token = _generate_public_token()

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


# ---------------------------------------------------------------------------
# Form Presets — pre-built forms for specific business types
# ---------------------------------------------------------------------------

_FORM_PRESETS: dict[str, dict] = {
    "dental_intake": {
        "name": "New Patient Health History",
        "description": "Collect essential health information from new dental patients before their first visit.",
        "fields": [
            {"id": "full_name", "type": "text", "label": "Full Name", "required": True, "placeholder": "First and Last Name"},
            {"id": "dob", "type": "date", "label": "Date of Birth", "required": True},
            {"id": "email", "type": "email", "label": "Email", "required": True, "placeholder": "your@email.com"},
            {"id": "phone", "type": "phone", "label": "Phone Number", "required": True, "placeholder": "(555) 123-4567"},
            {"id": "insurance_carrier", "type": "text", "label": "Insurance Carrier", "required": False, "placeholder": "e.g. Delta Dental, Cigna"},
            {"id": "insurance_member_id", "type": "text", "label": "Insurance Member ID", "required": False},
            {"id": "allergies", "type": "textarea", "label": "Allergies (medications, latex, etc.)", "required": False, "placeholder": "List any known allergies"},
            {"id": "medications", "type": "textarea", "label": "Current Medications", "required": False, "placeholder": "List all current medications"},
            {"id": "conditions", "type": "select", "label": "Do you have any of the following?", "required": False, "options": ["None", "Diabetes", "Heart Disease", "High Blood Pressure", "Bleeding Disorder", "Asthma", "Other"]},
            {"id": "pregnant", "type": "radio", "label": "Are you currently pregnant?", "required": False, "options": ["No", "Yes", "Not Applicable"]},
            {"id": "last_dental_visit", "type": "select", "label": "When was your last dental visit?", "required": False, "options": ["Less than 6 months", "6-12 months", "1-2 years", "More than 2 years", "Never"]},
            {"id": "concerns", "type": "textarea", "label": "What brings you in today?", "required": False, "placeholder": "Describe any dental concerns or symptoms"},
            {"id": "consent", "type": "checkbox", "label": "I consent to treatment and acknowledge that the information provided is accurate", "required": True},
        ],
        "success_message": "Thank you! Your health history has been received. We look forward to seeing you at your appointment.",
    },
    "medical_intake": {
        "name": "Patient Registration Form",
        "description": "New patient registration and medical history for healthcare practices.",
        "fields": [
            {"id": "full_name", "type": "text", "label": "Full Name", "required": True},
            {"id": "dob", "type": "date", "label": "Date of Birth", "required": True},
            {"id": "email", "type": "email", "label": "Email", "required": True},
            {"id": "phone", "type": "phone", "label": "Phone Number", "required": True},
            {"id": "insurance_carrier", "type": "text", "label": "Insurance Provider", "required": False},
            {"id": "insurance_id", "type": "text", "label": "Insurance ID / Policy Number", "required": False},
            {"id": "allergies", "type": "textarea", "label": "Known Allergies", "required": False},
            {"id": "medications", "type": "textarea", "label": "Current Medications", "required": False},
            {"id": "medical_history", "type": "textarea", "label": "Relevant Medical History", "required": False},
            {"id": "reason_for_visit", "type": "textarea", "label": "Reason for Visit", "required": True},
            {"id": "consent", "type": "checkbox", "label": "I consent to treatment and acknowledge the privacy notice", "required": True},
        ],
        "success_message": "Thank you for completing your registration. We'll see you at your appointment.",
    },
    "contractor_estimate": {
        "name": "Request a Free Estimate",
        "description": "Collect project details for a free estimate.",
        "fields": [
            {"id": "name", "type": "text", "label": "Your Name", "required": True},
            {"id": "email", "type": "email", "label": "Email", "required": True},
            {"id": "phone", "type": "phone", "label": "Phone", "required": True},
            {"id": "address", "type": "text", "label": "Property Address", "required": True},
            {"id": "service_type", "type": "select", "label": "Type of Service", "required": True, "options": ["Repair", "Installation", "Replacement", "Inspection", "Emergency", "Other"]},
            {"id": "description", "type": "textarea", "label": "Describe the Project", "required": True, "placeholder": "What do you need done?"},
            {"id": "timeline", "type": "select", "label": "When do you need this done?", "required": False, "options": ["ASAP", "This week", "This month", "Flexible"]},
            {"id": "photos", "type": "text", "label": "Link to Photos (optional)", "required": False, "placeholder": "Google Drive or Dropbox link"},
        ],
        "success_message": "Thanks! We'll review your request and get back to you with an estimate within 24 hours.",
    },
    "legal_intake": {
        "name": "New Client Intake Form",
        "description": "Collect case details and client information for initial consultation.",
        "fields": [
            {"id": "full_name", "type": "text", "label": "Full Name", "required": True},
            {"id": "email", "type": "email", "label": "Email", "required": True},
            {"id": "phone", "type": "phone", "label": "Phone Number", "required": True},
            {"id": "case_type", "type": "select", "label": "Type of Legal Matter", "required": True, "options": ["Family Law", "Estate Planning", "Personal Injury", "Criminal Defense", "Business/Corporate", "Real Estate", "Immigration", "Employment", "Other"]},
            {"id": "description", "type": "textarea", "label": "Brief Description of Your Situation", "required": True, "placeholder": "Please describe your legal matter in a few sentences"},
            {"id": "opposing_party", "type": "text", "label": "Opposing Party Name (if applicable)", "required": False},
            {"id": "deadline", "type": "date", "label": "Any Upcoming Court Dates or Deadlines?", "required": False},
            {"id": "prior_attorney", "type": "radio", "label": "Have you worked with another attorney on this matter?", "required": False, "options": ["No", "Yes"]},
            {"id": "preferred_contact", "type": "select", "label": "Preferred Contact Method", "required": False, "options": ["Phone", "Email", "Text"]},
            {"id": "consent", "type": "checkbox", "label": "I understand that submitting this form does not create an attorney-client relationship", "required": True},
        ],
        "success_message": "Thank you. We'll review your information and contact you within 1 business day to schedule a consultation.",
    },
    "fitness_waiver": {
        "name": "Fitness Liability Waiver",
        "description": "Liability waiver and health screening for new gym members and trial participants.",
        "fields": [
            {"id": "full_name", "type": "text", "label": "Full Name", "required": True},
            {"id": "email", "type": "email", "label": "Email", "required": True},
            {"id": "phone", "type": "phone", "label": "Phone Number", "required": True},
            {"id": "dob", "type": "date", "label": "Date of Birth", "required": True},
            {"id": "emergency_contact", "type": "text", "label": "Emergency Contact Name & Phone", "required": True, "placeholder": "Name: (555) 123-4567"},
            {"id": "health_conditions", "type": "select", "label": "Do you have any medical conditions?", "required": True, "options": ["None", "Heart Condition", "High Blood Pressure", "Diabetes", "Asthma", "Joint Issues", "Other"]},
            {"id": "medications", "type": "textarea", "label": "Current Medications (if any)", "required": False},
            {"id": "fitness_goals", "type": "select", "label": "What are your fitness goals?", "required": False, "options": ["Weight Loss", "Muscle Building", "Endurance", "Flexibility", "General Health", "Sports Performance"]},
            {"id": "experience", "type": "select", "label": "Fitness Experience Level", "required": False, "options": ["Beginner", "Intermediate", "Advanced"]},
            {"id": "waiver", "type": "checkbox", "label": "I acknowledge that physical exercise carries inherent risks. I voluntarily assume all risks and release this facility from liability for injuries sustained during exercise.", "required": True},
        ],
        "success_message": "Thank you! Your waiver is on file. Welcome to the team — we're excited to help you reach your goals!",
    },
    "catering_inquiry": {
        "name": "Catering & Event Inquiry",
        "description": "Collect event details for catering quotes and private dining requests.",
        "fields": [
            {"id": "name", "type": "text", "label": "Your Name", "required": True},
            {"id": "email", "type": "email", "label": "Email", "required": True},
            {"id": "phone", "type": "phone", "label": "Phone", "required": True},
            {"id": "event_date", "type": "date", "label": "Event Date", "required": True},
            {"id": "guest_count", "type": "number", "label": "Number of Guests", "required": True},
            {"id": "event_type", "type": "select", "label": "Type of Event", "required": True, "options": ["Birthday Party", "Corporate Event", "Wedding", "Anniversary", "Holiday Party", "Private Dining", "Other"]},
            {"id": "budget", "type": "select", "label": "Budget Range (per person)", "required": False, "options": ["Under $25", "$25-$50", "$50-$75", "$75-$100", "Over $100"]},
            {"id": "dietary", "type": "textarea", "label": "Dietary Restrictions or Special Requests", "required": False, "placeholder": "Allergies, vegetarian, gluten-free, etc."},
        ],
        "success_message": "Thank you for your inquiry! We'll reach out within 24 hours with a custom catering proposal.",
    },
}
