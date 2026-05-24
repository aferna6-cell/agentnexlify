"""Client Portal endpoints — service records, portal tokens, photo upload, public portal view, and client login."""

import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel, Field

from backend.config import settings
from backend.limiter import limiter
from backend.models.database import get_service_supabase as _get_service_supabase
from backend.dependencies import _get_current_tenant
from backend.services.tenant_scope import tenant_table
from backend.services.client_portal.urls import (
    _PUBLIC_API_BASE_URL,
    _PUBLIC_PORTAL_FRONTEND_URL,
    _STALE_FRONTEND_HOSTS,
    _STALE_FRONTEND_HOST_SUFFIXES,
    _api_base_url,
    _jwt_secret,
    _portal_base_url,
)
from backend.services.client_portal.auth import (
    _CLIENT_JWT_EXPIRE_DAYS,
    _JWT_ALGORITHM,
    _create_client_token,
    _get_current_client,
    _hash_client_password,
    _verify_client_password,
)
from backend.services.client_portal.photos import (
    append_photo_url,
    fetch_record_for_upload,
    upload_photo_to_storage,
    validate_and_read_photo,
)
from backend.services.client_portal.portal_data import (
    fetch_appointments,
    fetch_business,
    fetch_client_login_enabled,
    fetch_customer,
    fetch_documents,
    fetch_invoices,
    fetch_service_records,
    fetch_widget_config,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/portal", tags=["client-portal"])

__all__ = [
    "router",
    "settings",
    "get_supabase",
    "get_service_supabase",
    "_portal_base_url",
    "_api_base_url",
    "_jwt_secret",
    "_PUBLIC_PORTAL_FRONTEND_URL",
    "_PUBLIC_API_BASE_URL",
    "_STALE_FRONTEND_HOSTS",
    "_STALE_FRONTEND_HOST_SUFFIXES",
    "_JWT_ALGORITHM",
    "_CLIENT_JWT_EXPIRE_DAYS",
    "_hash_client_password",
    "_verify_client_password",
    "_create_client_token",
    "_get_current_client",
]


def get_supabase():
    """Backward-compatible test seam for modules that still patch client_portal.get_supabase."""
    return _get_service_supabase()


def get_service_supabase():
    """Preserve existing call sites while allowing get_supabase() patches to intercept."""
    return get_supabase()


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

    db = get_service_supabase()
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
        result = tenant_table(db, "service_records", tenant_id).insert(row).execute()
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

    db = get_service_supabase()
    try:
        query = (
            tenant_table(db, "service_records", tenant_id)
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

    db = get_service_supabase()
    try:
        result = (
            tenant_table(db, "service_records", tenant_id)
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

    db = get_service_supabase()
    try:
        result = (
            tenant_table(db, "service_records", tenant_id)
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

    data, content_type = await validate_and_read_photo(file)
    db = get_service_supabase()
    record = fetch_record_for_upload(db, tenant_id, record_id)
    current_photos = record.get("photos_json") or []
    public_url = upload_photo_to_storage(db, tenant_id, record_id, file.filename, data, content_type)
    return append_photo_url(db, tenant_id, record_id, current_photos, public_url)


@router.post("/{tenant_id}/portal-link/{lead_id}")
async def generate_portal_link(
    tenant_id: str,
    lead_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Generate (or return existing) a portal token for a lead and return the public URL."""
    _verify_tenant(claims, tenant_id)

    db = get_service_supabase()

    # Check if a token already exists for this tenant + lead
    try:
        existing = (
            tenant_table(db, "portal_tokens", tenant_id)
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
        return {"token": token, "url": f"{_portal_base_url()}/{token}"}

    # Generate a new token
    token = secrets.token_urlsafe(32)
    try:
        tenant_table(db, "portal_tokens", tenant_id).insert({
            "tenant_id": tenant_id,
            "lead_id": lead_id,
            "token": token,
        }).execute()
    except Exception:
        logger.exception("Failed to insert portal token for lead %s", lead_id)
        raise HTTPException(status_code=500, detail="Failed to generate portal link")

    return {"token": token, "url": f"{_portal_base_url()}/{token}"}


# ── Public (no auth) endpoints ────────────────────────────────


@router.get("/portal/{token}")
@limiter.limit("60/minute")
async def get_portal_data(token: str, request: Request):
    """Public portal page: business info, customer info, service records, and rebook flag.

    Rate limited to 60 requests per minute per IP.
    """
    db = get_service_supabase()

    # Look up the token
    try:
        tok_result = (
            db.table("portal_tokens")
            .select("tenant_id, lead_id")
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

    business = fetch_business(db, tenant_id)
    customer = fetch_customer(db, tenant_id, lead_id)
    service_records = fetch_service_records(db, tenant_id, lead_id)
    rebook_enabled, widget_api_key = fetch_widget_config(db, tenant_id)
    client_login_enabled = fetch_client_login_enabled(db, tenant_id)

    return {
        "business": business,
        "customer": customer,
        "service_records": service_records,
        "rebook_enabled": rebook_enabled,
        "widget_api_key": widget_api_key,
        "api_base": _api_base_url(),
        "client_login_enabled": client_login_enabled,
    }


# ── Client Login System ──────────────────────────────────────


class ClientRegisterRequest(BaseModel):
    portal_token: str = Field(..., description="Portal token proving client identity")
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=6, max_length=128)


class ClientLoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)
    business_slug: str = Field(..., min_length=1, max_length=100)


@router.post("/client/register")
@limiter.limit("10/minute")
async def client_register(req: ClientRegisterRequest, request: Request):
    """Register a client account using a portal token as proof of identity.

    The portal token validates the client is a real lead for a real business.
    After registration, the client can log in with email + password.
    """
    db = get_service_supabase()

    # Validate the portal token
    try:
        tok_result = (
            db.table("portal_tokens")
            .select("tenant_id, lead_id")
            .eq("token", req.portal_token)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception("Failed to look up portal token during client registration")
        raise HTTPException(status_code=500, detail="Registration failed")

    if not tok_result.data:
        raise HTTPException(status_code=404, detail="Invalid portal token")

    tenant_id = tok_result.data[0]["tenant_id"]
    lead_id = tok_result.data[0]["lead_id"]

    # Check if client login is enabled for this tenant
    try:
        tenant_result = (
            tenant_table(db, "tenants", tenant_id)
            .select("client_login_enabled")
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
        if not tenant_result.data or not tenant_result.data[0].get("client_login_enabled"):
            raise HTTPException(status_code=403, detail="Client login is not enabled for this business")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to check client_login_enabled for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Registration failed")

    # Check if account already exists
    try:
        existing = (
            tenant_table(db, "client_accounts", tenant_id)
            .select("id")
            .eq("tenant_id", tenant_id)
            .eq("lead_id", lead_id)
            .limit(1)
            .execute()
        )
        if existing.data:
            raise HTTPException(status_code=409, detail="Account already exists for this client")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to check existing client account")
        raise HTTPException(status_code=500, detail="Registration failed")

    # Create the account
    password_hash = _hash_client_password(req.password)
    try:
        tenant_table(db, "client_accounts", tenant_id).insert({
            "tenant_id": tenant_id,
            "lead_id": lead_id,
            "email": req.email,
            "password_hash": password_hash,
        }).execute()
    except Exception:
        logger.exception("Failed to create client account for lead %s", lead_id)
        raise HTTPException(status_code=500, detail="Registration failed")

    token = _create_client_token(tenant_id, lead_id, req.email)
    return {"token": token, "message": "Account created successfully"}


@router.post("/client/login")
@limiter.limit("10/minute")
async def client_login(req: ClientLoginRequest, request: Request):
    """Log in as a client using email + password, scoped to a business by slug."""
    db = get_service_supabase()

    # Find the tenant by business_slug
    try:
        tenant_result = (
            db.table("tenants")
            .select("id, client_login_enabled")
            .eq("business_slug", req.business_slug)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception("Failed to look up tenant by slug %s", req.business_slug)
        raise HTTPException(status_code=500, detail="Login failed")

    if not tenant_result.data:
        raise HTTPException(status_code=404, detail="Business not found")

    tenant = tenant_result.data[0]
    if not tenant.get("client_login_enabled"):
        raise HTTPException(status_code=403, detail="Client login is not enabled for this business")

    tenant_id = tenant["id"]

    # Find the client account
    try:
        account_result = (
            tenant_table(db, "client_accounts", tenant_id)
            .select("id, lead_id, email, password_hash")
            .eq("tenant_id", tenant_id)
            .eq("email", req.email)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception("Failed to look up client account for %s", req.email)
        raise HTTPException(status_code=500, detail="Login failed")

    if not account_result.data:
        # Constant-time: always hash to prevent timing-based email enumeration
        _hash_client_password(req.password)
        raise HTTPException(status_code=401, detail="Invalid email or password")

    account = account_result.data[0]
    if not _verify_client_password(req.password, account["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = _create_client_token(tenant_id, account["lead_id"], account["email"])
    return {"token": token}


@router.get("/client/me")
async def client_me(claims: dict = Depends(_get_current_client)):
    """Get the authenticated client's portal data — same as the public portal but via JWT."""
    db = get_service_supabase()
    tenant_id = claims["tenant_id"]
    lead_id = claims["lead_id"]

    business = fetch_business(db, tenant_id, with_slug=True)
    if not business:
        raise HTTPException(status_code=500, detail="Failed to load portal")

    customer = fetch_customer(db, tenant_id, lead_id)
    service_records = fetch_service_records(db, tenant_id, lead_id)
    appointments = fetch_appointments(db, tenant_id, lead_id)
    invoices = fetch_invoices(db, tenant_id, lead_id)
    documents = fetch_documents(db, tenant_id, lead_id)
    rebook_enabled, widget_api_key = fetch_widget_config(db, tenant_id)

    return {
        "business": business,
        "customer": customer,
        "service_records": service_records,
        "appointments": appointments,
        "invoices": invoices,
        "documents": documents,
        "rebook_enabled": rebook_enabled,
        "widget_api_key": widget_api_key,
        "api_base": _api_base_url(),
    }


@router.put("/{tenant_id}/client-login")
async def toggle_client_login(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Enable or disable client login for a tenant (toggle)."""
    _verify_tenant(claims, tenant_id)

    db = get_service_supabase()
    try:
        # Get current state
        current = (
            tenant_table(db, "tenants", tenant_id)
            .select("client_login_enabled")
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
        if not current.data:
            raise HTTPException(status_code=404, detail="Tenant not found")

        new_value = not bool(current.data[0].get("client_login_enabled"))
        tenant_table(db, "tenants", tenant_id).update({"client_login_enabled": new_value}).eq("id", tenant_id).execute()
        return {"client_login_enabled": new_value}
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to toggle client login for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to toggle client login")
