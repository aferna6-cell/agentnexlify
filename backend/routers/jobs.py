"""Job board endpoints — CRUD for jobs + public listings + SMS-first applications."""

import logging

import anthropic
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from backend.limiter import limiter

from backend.config import settings
from backend.models.database import get_supabase
from backend.routers.auth import _get_current_tenant, require_role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


# --- Models ---

class JobCreate(BaseModel):
    title: str = Field(..., max_length=200)
    description: str | None = Field(None, max_length=5000)
    pay_range: str | None = Field(None, max_length=100)
    schedule: str | None = Field(None, max_length=200)
    location: str | None = Field(None, max_length=200)
    skills: list[str] = Field(default_factory=list)


class JobUpdate(BaseModel):
    title: str | None = Field(None, max_length=200)
    description: str | None = Field(None, max_length=5000)
    pay_range: str | None = Field(None, max_length=100)
    schedule: str | None = Field(None, max_length=200)
    location: str | None = Field(None, max_length=200)
    skills: list[str] | None = None
    is_active: bool | None = None


class AIJobWriteRequest(BaseModel):
    role_description: str = Field(..., max_length=1000)


class JobApplicationCreate(BaseModel):
    applicant_name: str = Field(..., max_length=200)
    applicant_phone: str = Field(..., max_length=30)
    message: str | None = Field(None, max_length=2000)


class ApplicationStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(new|contacted|interviewed|hired|rejected)$")
    notes: str | None = Field(None, max_length=2000)


# --- Helpers ---

def _verify_tenant(claims: dict, tenant_id: str) -> None:
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")


# --- Dashboard endpoints (JWT-auth) ---

@router.get("/{tenant_id}")
async def list_jobs(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
    active_only: bool = Query(False),
):
    """List all jobs for a tenant."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()
    query = (
        db.table("jobs")
        .select("*")
        .eq("tenant_id", tenant_id)
        .order("created_at", desc=True)
    )
    if active_only:
        query = query.eq("is_active", True)

    result = query.execute()
    return {"jobs": result.data or [], "count": len(result.data or [])}


@router.post("/{tenant_id}")
async def create_job(
    tenant_id: str,
    req: JobCreate,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Create a new job posting."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()
    data = {
        "tenant_id": tenant_id,
        "title": req.title,
        "description": req.description,
        "pay_range": req.pay_range,
        "schedule": req.schedule,
        "location": req.location,
        "skills": req.skills,
    }
    result = db.table("jobs").insert(data).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create job")
    return result.data[0]


@router.put("/{tenant_id}/{job_id}")
async def update_job(
    tenant_id: str,
    job_id: str,
    req: JobUpdate,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Update a job posting."""
    _verify_tenant(claims, tenant_id)

    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    db = get_supabase()
    result = (
        db.table("jobs")
        .update(updates)
        .eq("id", job_id)
        .eq("tenant_id", tenant_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Job not found")
    return result.data[0]


@router.delete("/{tenant_id}/{job_id}")
async def delete_job(
    tenant_id: str,
    job_id: str,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Delete a job posting."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()
    result = (
        db.table("jobs")
        .delete()
        .eq("id", job_id)
        .eq("tenant_id", tenant_id)
        .execute()
    )
    return {"deleted": True}


@router.post("/{tenant_id}/ai-write")
async def ai_write_job_description(
    tenant_id: str,
    req: AIJobWriteRequest,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """AI generates a professional job posting from a plain-language description."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()
    tenant_result = (
        db.table("tenants")
        .select("business_name, business_type, city")
        .eq("id", tenant_id)
        .limit(1)
        .execute()
    )
    biz_name = ""
    biz_type = ""
    city = ""
    if tenant_result.data:
        biz_name = tenant_result.data[0].get("business_name") or ""
        biz_type = tenant_result.data[0].get("business_type") or ""
        city = tenant_result.data[0].get("city") or ""

    context = f"Business: {biz_name}" if biz_name else ""
    if biz_type:
        context += f" ({biz_type})"
    if city:
        context += f" in {city}"

    prompt = (
        f"Write a professional job posting based on this description from the business owner:\n\n"
        f'"{req.role_description}"\n\n'
        f"{context}\n\n"
        f"Return ONLY valid JSON with these fields:\n"
        f'{{"title": "Job Title", "description": "Full job description (2-4 paragraphs, include responsibilities, '
        f'qualifications, and what makes this role great)", "pay_range": "Pay range if mentioned or null", '
        f'"schedule": "Schedule type if mentioned or null", "location": "Location if mentioned or null", '
        f'"skills": ["skill1", "skill2"]}}\n\n'
        f"Rules:\n"
        f"- Write for a small business audience — friendly and direct, not corporate\n"
        f"- Include clear responsibilities and what a good candidate looks like\n"
        f"- If pay/schedule/location aren't mentioned, set them to null\n"
        f"- Extract 3-6 relevant skills from the description\n"
        f"- Output ONLY the JSON object, no markdown fences"
    )

    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key, timeout=30.0)
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()

        # Parse JSON — handle markdown code blocks
        import json
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            text = text.rsplit("```", 1)[0].strip()

        result = json.loads(text)
        return result
    except json.JSONDecodeError:
        logger.warning("AI job writer returned invalid JSON: %s", text[:200])
        raise HTTPException(status_code=502, detail="AI returned invalid response — try again")
    except anthropic.APIError as e:
        logger.warning("Anthropic API error in AI job writer: %s", str(e))
        raise HTTPException(status_code=502, detail="AI service error — try again")


# --- Applications management (JWT-auth) ---

@router.get("/{tenant_id}/{job_id}/applications")
async def list_applications(
    tenant_id: str,
    job_id: str,
    claims: dict = Depends(_get_current_tenant),
    status: str | None = Query(None),
):
    """List applications for a specific job."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()
    query = (
        db.table("job_applications")
        .select("*")
        .eq("job_id", job_id)
        .eq("tenant_id", tenant_id)
        .order("created_at", desc=True)
    )
    if status:
        query = query.eq("status", status)

    result = query.execute()
    return {"applications": result.data or [], "count": len(result.data or [])}


@router.put("/{tenant_id}/applications/{app_id}/status")
async def update_application_status(
    tenant_id: str,
    app_id: str,
    req: ApplicationStatusUpdate,
    claims: dict = Depends(require_role("owner", "admin", "member")),
):
    """Update an application's status."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()
    updates = {"status": req.status}
    if req.notes is not None:
        updates["notes"] = req.notes

    result = (
        db.table("job_applications")
        .update(updates)
        .eq("id", app_id)
        .eq("tenant_id", tenant_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Application not found")
    return result.data[0]


# --- Public endpoints (no auth) ---

@router.get("/public/{tenant_id}/listings")
@limiter.limit("120/minute")
async def public_job_listings(request: Request, tenant_id: str):
    """Public endpoint — returns active job listings for a tenant."""
    db = get_supabase()

    # Get tenant info for display
    tenant_result = (
        db.table("tenants")
        .select("business_name, business_phone, city")
        .eq("id", tenant_id)
        .limit(1)
        .execute()
    )
    if not tenant_result.data:
        raise HTTPException(status_code=404, detail="Business not found")

    tenant = tenant_result.data[0]

    # Get active jobs
    jobs_result = (
        db.table("jobs")
        .select("id, title, description, pay_range, schedule, location, skills, created_at")
        .eq("tenant_id", tenant_id)
        .eq("is_active", True)
        .order("created_at", desc=True)
        .execute()
    )

    return {
        "business_name": tenant.get("business_name") or "",
        "business_phone": tenant.get("business_phone", ""),
        "city": tenant.get("city") or "",
        "jobs": jobs_result.data or [],
    }


@router.post("/public/{tenant_id}/{job_id}/apply")
@limiter.limit("10/minute")
async def public_apply(
    request: Request,
    tenant_id: str,
    job_id: str,
    req: JobApplicationCreate,
):
    """Public endpoint — submit a job application (SMS-first, no resume)."""
    db = get_supabase()

    # Verify job exists and is active
    job_result = (
        db.table("jobs")
        .select("id, title, tenant_id")
        .eq("id", job_id)
        .eq("tenant_id", tenant_id)
        .eq("is_active", True)
        .limit(1)
        .execute()
    )
    if not job_result.data:
        raise HTTPException(status_code=404, detail="Job not found or no longer active")

    job = job_result.data[0]

    # Create application
    app_data = {
        "job_id": job_id,
        "tenant_id": tenant_id,
        "applicant_name": req.applicant_name,
        "applicant_phone": req.applicant_phone,
        "message": req.message,
        "status": "new",
    }
    result = db.table("job_applications").insert(app_data).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to submit application")

    # Send SMS notification to business owner
    try:
        tenant_result = (
            db.table("tenants")
            .select("business_phone, business_name")
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
        if tenant_result.data:
            owner_phone = tenant_result.data[0].get("business_phone")
            biz_name = tenant_result.data[0].get("business_name") or "your business"
            if owner_phone:
                from backend.services.twilio_service import send_sms
                sms_body = (
                    f"New applicant for {job['title']}!\n"
                    f"Name: {req.applicant_name}\n"
                    f"Phone: {req.applicant_phone}\n"
                    f"Check your dashboard to review."
                )
                await send_sms(to=owner_phone, body=sms_body)
    except Exception:
        logger.warning("Failed to send application notification SMS to owner", exc_info=True)

    # Send SMS confirmation to applicant (best-effort, don't fail the request)
    sms_warnings = []
    try:
        if req.applicant_phone:
            from backend.services.twilio_service import send_sms
            confirm_body = (
                f"Thanks for applying to {job['title']} at {biz_name}! "
                f"We've received your application and will be in touch."
            )
            await send_sms(to=req.applicant_phone, body=confirm_body)
    except Exception:
        logger.warning("Failed to send application confirmation SMS to %s", req.applicant_phone, exc_info=True)
        sms_warnings.append("Confirmation SMS could not be sent")

    resp = {"success": True, "application_id": result.data[0]["id"]}
    if sms_warnings:
        resp["warnings"] = sms_warnings
    return resp
