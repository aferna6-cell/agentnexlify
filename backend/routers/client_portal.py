"""Client Portal endpoints — service records, portal tokens, photo upload, and public portal view."""

import logging
import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel, Field

from backend.config import settings
from backend.limiter import limiter
from backend.models.database import get_supabase
from backend.routers.auth import _get_current_tenant

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/portal", tags=["client-portal"])

_PORTAL_BASE_URL = "https://agentnexlify.vercel.app/client"


# ── Pydantic models ──────────────────────────────────────────


class ServiceRecordCreate(BaseModel):
    title: str
    description: str | None = None
    service_date: str | None = None
    photos_json: list | None = Field(default_factory=list)
    documents_json: list | None = Field(default_factory=list)
    notes: str | None = None
    invoice_amount: float | None = None
    lead_id: str | None = None


class ServiceRecordUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    service_date: str | None = None
    photos_json: list | None = None
    documents_json: list | None = None
    notes: str | None = None
    invoice_amount: float | None = None
    lead_id: str | None = None


# ── Helpers ───────────────────────────────────────────────────


def _verify_tenant(claims: dict, tenant_id: str) -> None:
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")


# ── Dashboard (authenticated) endpoints ──────────────────────


@router.post("/{tenant_id}/service-records", status_code=201)
async def create_service_record(
    tenant_id: str,
    body: ServiceRecordCreate,
    claims: dict = Depends(_get_current_tenant),
):
    """Create a service record for a tenant."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()
    row = {
        "tenant_id": tenant_id,
        "title": body.title,
        "description": body.description,
        "service_date": body.service_date,
        "photos_json": body.photos_json or [],
        "documents_json": body.documents_json or [],
        "notes": body.notes,
        "invoice_amount": body.invoice_amount,
        "lead_id": body.lead_id,
    }

    try:
        result = db.table("service_records").insert(row).execute()
    except Exception:
        logger.exception("Failed to create service record for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to create service record")

    if not result.data:
        logger.error("Insert returned empty data for service record, tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to create service record")

    return result.data[0]


@router.get("/{tenant_id}/service-records")
async def list_service_records(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
    lead_id: str | None = Query(None),
):
    """List service records for a tenant, optionally filtered by lead_id."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()
    try:
        query = (
            db.table("service_records")
            .select("*")
            .eq("tenant_id", tenant_id)
            .order("service_date", desc=True)
        )
        if lead_id:
            query = query.eq("lead_id", lead_id)
        result = query.execute()
    except Exception:
        logger.exception("Failed to list service records for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to list service records")

    return {"service_records": result.data or []}


@router.put("/{tenant_id}/service-records/{record_id}")
async def update_service_record(
    tenant_id: str,
    record_id: str,
    body: ServiceRecordUpdate,
    claims: dict = Depends(_get_current_tenant),
):
    """Update a service record."""
    _verify_tenant(claims, tenant_id)

    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    db = get_supabase()
    try:
        result = (
            db.table("service_records")
            .update(updates)
            .eq("id", record_id)
            .eq("tenant_id", tenant_id)
            .execute()
        )
    except Exception:
        logger.exception("Failed to update service record %s for tenant %s", record_id, tenant_id)
        raise HTTPException(status_code=500, detail="Failed to update service record")

    if not result.data:
        raise HTTPException(status_code=404, detail="Service record not found")

    return result.data[0]


@router.delete("/{tenant_id}/service-records/{record_id}", status_code=204)
async def delete_service_record(
    tenant_id: str,
    record_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Delete a service record."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()
    try:
        result = (
            db.table("service_records")
            .delete()
            .eq("id", record_id)
            .eq("tenant_id", tenant_id)
            .execute()
        )
    except Exception:
        logger.exception("Failed to delete service record %s for tenant %s", record_id, tenant_id)
        raise HTTPException(status_code=500, detail="Failed to delete service record")

    if not result.data:
        raise HTTPException(status_code=404, detail="Service record not found")


# ── Photo upload for service records ─────────────────────────

_ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
_MAX_PHOTO_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post("/{tenant_id}/service-records/{record_id}/upload")
async def upload_service_photo(
    tenant_id: str,
    record_id: str,
    file: UploadFile,
    claims: dict = Depends(_get_current_tenant),
):
    """Upload a photo for a service record.

    Accepts image/jpeg, image/png, image/webp up to 10 MB.
    Stores in Supabase Storage bucket 'service-photos'.
    Appends the public URL to the service record's photos_json array.
    """
    _verify_tenant(claims, tenant_id)

    # Validate file type
    content_type = file.content_type or ""
    if content_type not in _ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed: {content_type}. Accepted: JPEG, PNG, WebP.",
        )

    # Read file with size check
    data = await file.read()
    if len(data) > _MAX_PHOTO_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 10 MB)")

    db = get_supabase()

    # Verify the service record exists and belongs to this tenant
    try:
        existing = (
            db.table("service_records")
            .select("id, photos_json")
            .eq("id", record_id)
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception("Failed to fetch service record %s for photo upload", record_id)
        raise HTTPException(status_code=500, detail="Failed to fetch service record")

    if not existing.data:
        raise HTTPException(status_code=404, detail="Service record not found")

    record = existing.data[0]
    current_photos = record.get("photos_json") or []

    # Generate unique path in Supabase Storage
    ext = (file.filename or "photo.jpg").rsplit(".", 1)[-1][:10]
    unique_name = f"{uuid.uuid4().hex[:12]}.{ext}"
    path = f"{tenant_id}/{record_id}/{unique_name}"

    try:
        db.storage.from_("service-photos").upload(
            path,
            data,
            file_options={"content-type": content_type},
        )
    except Exception:
        logger.exception("Photo upload to storage failed for record %s", record_id)
        raise HTTPException(status_code=500, detail="Photo upload failed")

    # Build public URL
    public_url = f"{settings.supabase_url}/storage/v1/object/public/service-photos/{path}"

    # Append URL to photos_json array
    updated_photos = current_photos + [public_url]
    try:
        result = (
            db.table("service_records")
            .update({"photos_json": updated_photos})
            .eq("id", record_id)
            .eq("tenant_id", tenant_id)
            .execute()
        )
    except Exception:
        logger.exception("Failed to update photos_json for record %s", record_id)
        raise HTTPException(status_code=500, detail="Failed to update service record")

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to update service record")

    return result.data[0]


@router.post("/{tenant_id}/portal-link/{lead_id}")
async def generate_portal_link(
    tenant_id: str,
    lead_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Generate (or return existing) a portal token for a lead and return the public URL."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()

    # Check if a token already exists for this tenant + lead
    try:
        existing = (
            db.table("portal_tokens")
            .select("token")
            .eq("tenant_id", tenant_id)
            .eq("lead_id", lead_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception("Failed to check existing portal token for lead %s", lead_id)
        raise HTTPException(status_code=500, detail="Failed to generate portal link")

    if existing.data:
        token = existing.data[0]["token"]
        return {"token": token, "url": f"{_PORTAL_BASE_URL}/{token}"}

    # Generate a new token
    token = secrets.token_urlsafe(32)
    try:
        db.table("portal_tokens").insert({
            "tenant_id": tenant_id,
            "lead_id": lead_id,
            "token": token,
        }).execute()
    except Exception:
        logger.exception("Failed to insert portal token for lead %s", lead_id)
        raise HTTPException(status_code=500, detail="Failed to generate portal link")

    return {"token": token, "url": f"{_PORTAL_BASE_URL}/{token}"}


# ── Public (no auth) endpoints ────────────────────────────────


@router.get("/portal/{token}")
@limiter.limit("60/minute")
async def get_portal_data(token: str, request: Request):
    """Public portal page: business info, customer info, service records, and rebook flag.

    Rate limited to 60 requests per minute per IP.
    """
    db = get_supabase()

    # Look up the token
    try:
        tok_result = (
            db.table("portal_tokens")
            .select("*")
            .eq("token", token)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception("Failed to look up portal token")
        raise HTTPException(status_code=500, detail="Internal error")

    if not tok_result.data:
        raise HTTPException(status_code=404, detail="Portal link not found or expired")

    tok = tok_result.data[0]
    tenant_id = tok["tenant_id"]
    lead_id = tok["lead_id"]

    # Fetch business info
    try:
        tenant_result = (
            db.table("tenants")
            .select("id, business_name, owner_email, industry, city")
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception("Failed to fetch tenant %s for portal", tenant_id)
        raise HTTPException(status_code=500, detail="Internal error")

    business = tenant_result.data[0] if tenant_result.data else {}

    # Fetch customer (lead) info — leads table uses client_id
    try:
        lead_result = (
            db.table("leads")
            .select("id, name, email, phone")
            .eq("id", lead_id)
            .eq("client_id", tenant_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception("Failed to fetch lead %s for portal", lead_id)
        raise HTTPException(status_code=500, detail="Internal error")

    customer = lead_result.data[0] if lead_result.data else {}

    # Fetch service records for this lead + tenant
    try:
        records_result = (
            db.table("service_records")
            .select("*")
            .eq("tenant_id", tenant_id)
            .eq("lead_id", lead_id)
            .order("service_date", desc=True)
            .execute()
        )
    except Exception:
        logger.exception("Failed to fetch service records for portal, lead %s", lead_id)
        raise HTTPException(status_code=500, detail="Internal error")

    service_records = records_result.data or []

    # Check if booking is enabled and fetch widget API key for rebook button
    rebook_enabled = False
    widget_api_key = None
    try:
        wc_result = (
            db.table("widget_configs")
            .select("booking_enabled, api_key")
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
        if wc_result.data:
            rebook_enabled = bool(wc_result.data[0].get("booking_enabled"))
            widget_api_key = wc_result.data[0].get("api_key")
    except Exception:
        logger.warning("Failed to check widget config for tenant %s", tenant_id)

    return {
        "business": business,
        "customer": customer,
        "service_records": service_records,
        "rebook_enabled": rebook_enabled,
        "widget_api_key": widget_api_key,
        "api_base": "https://agentnexlify-production.up.railway.app",
    }
