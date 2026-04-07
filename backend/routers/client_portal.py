"""Client Portal endpoints — service records, portal tokens, photo upload, public portal view, and client login."""

import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, UploadFile
from jose import JWTError, jwt
from pydantic import BaseModel, Field

from backend.config import settings
from backend.limiter import limiter
from backend.models.database import get_supabase
from backend.routers.auth import _get_current_tenant
from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/portal", tags=["client-portal"])

_PORTAL_BASE_URL = "https://agentnexlify.vercel.app/client"
_JWT_ALGORITHM = "HS256"
_CLIENT_JWT_EXPIRE_DAYS = 30


def _jwt_secret() -> str:
    jwt_secret = getattr(settings, "jwt_secret_key", "")
    if isinstance(jwt_secret, str) and jwt_secret:
        return jwt_secret
    api_secret = getattr(settings, "api_secret_key", "")
    return api_secret if isinstance(api_secret, str) else ""


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

    db = get_supabase()
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

    db = get_supabase()
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

    db = get_supabase()
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
            tenant_table(db, "service_records", tenant_id)
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
            tenant_table(db, "service_records", tenant_id)
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
        return {"token": token, "url": f"{_PORTAL_BASE_URL}/{token}"}

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

    # Fetch business info
    try:
        tenant_result = (
            tenant_table(db, "tenants", tenant_id)
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
            tenant_table(db, "leads", tenant_id)
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

    # Fetch service records for this lead + tenant (only public-safe columns)
    try:
        records_result = (
            tenant_table(db, "service_records", tenant_id)
            .select("id, title, description, service_date, photos_json, documents_json, invoice_amount, created_at")
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
            tenant_table(db, "widget_configs", tenant_id)
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

    # Check if client login is enabled for this tenant
    client_login_enabled = False
    try:
        tenant_full = (
            tenant_table(db, "tenants", tenant_id)
            .select("client_login_enabled")
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
        if tenant_full.data:
            client_login_enabled = bool(tenant_full.data[0].get("client_login_enabled"))
    except Exception:
        logger.warning("Failed to check client_login_enabled for tenant %s", tenant_id)

    return {
        "business": business,
        "customer": customer,
        "service_records": service_records,
        "rebook_enabled": rebook_enabled,
        "widget_api_key": widget_api_key,
        "api_base": settings.api_url,
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


def _hash_client_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def _verify_client_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def _create_client_token(tenant_id: str, lead_id: str, email: str) -> str:
    payload = {
        "tenant_id": tenant_id,
        "lead_id": lead_id,
        "email": email,
        "scope": "client",
        "exp": datetime.now(timezone.utc) + timedelta(days=_CLIENT_JWT_EXPIRE_DAYS),
    }
    return jwt.encode(payload, _jwt_secret(), algorithm=_JWT_ALGORITHM)


def _get_current_client(authorization: str = Header(...)) -> dict:
    """Decode and validate a client JWT token."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = authorization[7:]
    try:
        payload = jwt.decode(token, _jwt_secret(), algorithms=[_JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    if payload.get("scope") != "client":
        raise HTTPException(status_code=403, detail="Not a client token")
    return payload


@router.post("/client/register")
@limiter.limit("10/minute")
async def client_register(req: ClientRegisterRequest, request: Request):
    """Register a client account using a portal token as proof of identity.

    The portal token validates the client is a real lead for a real business.
    After registration, the client can log in with email + password.
    """
    db = get_supabase()

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
    db = get_supabase()

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
    db = get_supabase()
    tenant_id = claims["tenant_id"]
    lead_id = claims["lead_id"]

    # Fetch business info
    try:
        tenant_result = (
            tenant_table(db, "tenants", tenant_id)
            .select("id, business_name, owner_email, industry, city, business_slug")
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception("Failed to fetch tenant %s for client portal", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to load portal")

    business = tenant_result.data[0] if tenant_result.data else {}

    # Fetch customer (lead) info — leads table uses client_id
    try:
        lead_result = (
            tenant_table(db, "leads", tenant_id)
            .select("id, name, email, phone")
            .eq("id", lead_id)
            .eq("client_id", tenant_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception("Failed to fetch lead %s for client portal", lead_id)
        raise HTTPException(status_code=500, detail="Failed to load portal")

    customer = lead_result.data[0] if lead_result.data else {}

    # Fetch service records (client-facing columns only)
    try:
        records_result = (
            tenant_table(db, "service_records", tenant_id)
            .select("id, title, description, service_date, photos_json, documents_json, invoice_amount, created_at")
            .eq("tenant_id", tenant_id)
            .eq("lead_id", lead_id)
            .order("service_date", desc=True)
            .execute()
        )
    except Exception:
        logger.exception("Failed to fetch service records for client %s", lead_id)
        raise HTTPException(status_code=500, detail="Failed to load portal")

    # Fetch appointments
    try:
        appt_result = (
            tenant_table(db, "appointments", tenant_id)
            .select("id, customer_name, start_time, end_time, status, notes")
            .eq("tenant_id", tenant_id)
            .eq("lead_id", lead_id)
            .order("start_time", desc=True)
            .limit(20)
            .execute()
        )
    except Exception:
        logger.warning("Failed to fetch appointments for client %s", lead_id)
        appt_result = type("R", (), {"data": []})()

    # Fetch invoices
    try:
        inv_result = (
            tenant_table(db, "invoices", tenant_id)
            .select("id, invoice_number, items_json, subtotal, tax, total, status, created_at, due_date")
            .eq("tenant_id", tenant_id)
            .eq("lead_id", lead_id)
            .order("created_at", desc=True)
            .limit(20)
            .execute()
        )
    except Exception:
        logger.warning("Failed to fetch invoices for client %s", lead_id)
        inv_result = type("R", (), {"data": []})()

    # Fetch documents
    try:
        doc_result = (
            tenant_table(db, "documents", tenant_id)
            .select("id, title, status, created_at, signed_at")
            .eq("tenant_id", tenant_id)
            .eq("lead_id", lead_id)
            .order("created_at", desc=True)
            .limit(20)
            .execute()
        )
    except Exception:
        logger.warning("Failed to fetch documents for client %s", lead_id)
        doc_result = type("R", (), {"data": []})()

    # Check rebook status
    rebook_enabled = False
    widget_api_key = None
    try:
        wc_result = (
            tenant_table(db, "widget_configs", tenant_id)
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
        "service_records": records_result.data or [],
        "appointments": appt_result.data or [],
        "invoices": inv_result.data or [],
        "documents": doc_result.data or [],
        "rebook_enabled": rebook_enabled,
        "widget_api_key": widget_api_key,
        "api_base": settings.api_url,
    }


@router.put("/{tenant_id}/client-login")
async def toggle_client_login(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Enable or disable client login for a tenant (toggle)."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()
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
        raise HTTPException(status_code=500, detail="Failed to update setting")
