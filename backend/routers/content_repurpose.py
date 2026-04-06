"""Content Repurpose endpoints — create, list, edit, connect repurpose jobs."""

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from backend.limiter import limiter
from backend.models.database import get_supabase
from backend.routers.auth import _get_current_tenant
from backend.services.content_repurposer import extract_source, repurpose, connect_outputs

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/repurpose", tags=["content-repurpose"])

ALLOWED_PLANS = ("professional", "enterprise")
VALID_TONES = ("professional", "engaging", "casual", "indie_hacker")
VALID_FORMATS = ("x_thread", "linkedin_carousel", "email_sequence", "tiktok_scripts", "social_posts")
VALID_SOURCE_TYPES = ("text", "url", "youtube", "podcast")


class RepurposeCreate(BaseModel):
    source_type: str = Field(..., description="text, url, youtube, or podcast")
    source_input: str = Field(..., min_length=1, max_length=100000)
    tone: str = Field(default="professional")
    formats: list[str] = Field(default=["x_thread", "linkedin_carousel", "email_sequence", "tiktok_scripts", "social_posts"])


class RepurposeUpdate(BaseModel):
    outputs: dict | None = None
    source_title: str | None = None


class ConnectRequest(BaseModel):
    targets: list[str] = Field(..., min_length=1)


def _verify_tenant(claims: dict, tenant_id: str) -> None:
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")


def _verify_plan(claims: dict) -> None:
    db = get_supabase()
    tenant = db.table("tenants").select("plan").eq("id", claims["tenant_id"]).single().execute()
    if not tenant.data or tenant.data.get("plan") not in ALLOWED_PLANS:
        raise HTTPException(
            status_code=403,
            detail="Content Repurposer requires Professional or Enterprise plan. Upgrade to access this feature.",
        )


async def _run_repurpose_job(
    job_id: str, tenant_id: str, source_type: str, source_input: str, tone: str, formats: list[str]
):
    """Background task: extract source, generate content, update job."""
    db = get_supabase()
    try:
        source = await extract_source(source_type, source_input)
        outputs = await repurpose(
            source_content=source["content"],
            title=source["title"],
            tenant_id=tenant_id,
            tone=tone,
            formats=formats,
        )
        db.table("repurpose_jobs").update({
            "source_content": source["content"],
            "source_title": source["title"],
            "outputs": outputs,
            "status": "completed",
        }).eq("id", job_id).execute()
    except Exception as e:
        logger.error("Repurpose job %s failed: %s", job_id, e)
        db.table("repurpose_jobs").update({"status": "failed"}).eq("id", job_id).execute()


@router.post("/{tenant_id}")
@limiter.limit("5/minute")
async def create_repurpose_job(
    request: Request,
    tenant_id: str,
    req: RepurposeCreate,
    background_tasks: BackgroundTasks,
    claims: dict = Depends(_get_current_tenant),
):
    """Create a new repurpose job. Extraction + AI generation runs in background."""
    _verify_tenant(claims, tenant_id)
    _verify_plan(claims)

    if req.source_type not in VALID_SOURCE_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid source_type. Must be one of: {VALID_SOURCE_TYPES}")
    if req.tone not in VALID_TONES:
        raise HTTPException(status_code=400, detail=f"Invalid tone. Must be one of: {VALID_TONES}")
    for fmt in req.formats:
        if fmt not in VALID_FORMATS:
            raise HTTPException(status_code=400, detail=f"Invalid format: {fmt}. Must be one of: {VALID_FORMATS}")

    db = get_supabase()
    job = db.table("repurpose_jobs").insert({
        "tenant_id": tenant_id,
        "source_type": req.source_type,
        "source_url": req.source_input if req.source_type in ("url", "youtube") else None,
        "source_content": req.source_input,
        "tone": req.tone,
        "status": "processing",
        "created_via": "dashboard",
    }).execute()

    job_id = job.data[0]["id"]
    background_tasks.add_task(
        _run_repurpose_job, job_id, tenant_id, req.source_type, req.source_input, req.tone, req.formats
    )
    return {"id": job_id, "status": "processing"}


@router.get("/{tenant_id}")
async def list_repurpose_jobs(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
):
    """List repurpose jobs for a tenant."""
    _verify_tenant(claims, tenant_id)
    _verify_plan(claims)

    db = get_supabase()
    resp = (
        db.table("repurpose_jobs")
        .select("id, source_type, source_title, tone, status, created_via, created_at")
        .eq("tenant_id", tenant_id)
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return {"jobs": resp.data or [], "total": len(resp.data or [])}


@router.get("/{tenant_id}/{job_id}")
async def get_repurpose_job(
    tenant_id: str,
    job_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Get a single repurpose job with full outputs."""
    _verify_tenant(claims, tenant_id)
    _verify_plan(claims)

    db = get_supabase()
    resp = db.table("repurpose_jobs").select("*").eq("id", job_id).eq("tenant_id", tenant_id).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Job not found")
    return resp.data[0]


@router.put("/{tenant_id}/{job_id}")
async def update_repurpose_job(
    tenant_id: str,
    job_id: str,
    req: RepurposeUpdate,
    claims: dict = Depends(_get_current_tenant),
):
    """Update a repurpose job (edit outputs or title)."""
    _verify_tenant(claims, tenant_id)
    _verify_plan(claims)

    update_data = {}
    if req.outputs is not None:
        update_data["outputs"] = req.outputs
    if req.source_title is not None:
        update_data["source_title"] = req.source_title
    if not update_data:
        raise HTTPException(status_code=400, detail="Nothing to update")

    db = get_supabase()
    resp = db.table("repurpose_jobs").update(update_data).eq("id", job_id).eq("tenant_id", tenant_id).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Job not found")
    return resp.data[0]


@router.post("/{tenant_id}/{job_id}/connect")
async def connect_repurpose_outputs(
    tenant_id: str,
    job_id: str,
    req: ConnectRequest,
    claims: dict = Depends(_get_current_tenant),
):
    """Push repurpose outputs to social posts, email sequences, X, or TikTok."""
    _verify_tenant(claims, tenant_id)
    _verify_plan(claims)

    valid_targets = {"social_posts", "email_sequence", "x_thread", "tiktok"}
    for t in req.targets:
        if t not in valid_targets:
            raise HTTPException(status_code=400, detail=f"Invalid target: {t}. Must be one of: {valid_targets}")

    db = get_supabase()
    job = db.table("repurpose_jobs").select("outputs, status").eq("id", job_id).eq("tenant_id", tenant_id).execute()
    if not job.data:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.data[0]["status"] != "completed":
        raise HTTPException(status_code=400, detail="Job is not completed yet")
    if not job.data[0]["outputs"]:
        raise HTTPException(status_code=400, detail="Job has no outputs")

    result = await connect_outputs(job_id, tenant_id, job.data[0]["outputs"], req.targets, db)
    return result


@router.delete("/{tenant_id}/{job_id}")
async def delete_repurpose_job(
    tenant_id: str,
    job_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Delete a repurpose job."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()
    resp = db.table("repurpose_jobs").delete().eq("id", job_id).eq("tenant_id", tenant_id).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"deleted": True}
