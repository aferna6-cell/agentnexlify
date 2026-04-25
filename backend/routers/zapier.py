"""Zapier CRM export — API key management and lead feed endpoints.

Spec: specs/zapier-crm-export_spec.md
Issue: #58

Endpoints:
  POST   /api/zapier/keys          — generate a new API key (JWT auth)
  GET    /api/zapier/keys          — list keys for the tenant (JWT auth)
  DELETE /api/zapier/keys/{key_id} — revoke a key (JWT auth)
  GET    /api/zapier/leads/new     — fetch new leads (API key auth, tier-gated)

Tier gating: Growth, Autopilot, Professional, Enterprise allowed.
             Free tier blocked (HTTP 402).
Legacy Growth tenants at $199/mo are in 'growth' tier — allowed.

INVARIANTS (CLAUDE.md):
  - client_id (NOT tenant_id) in DB and response bodies
  - bcrypt cost 12 for API key hashes
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel

from backend.models.database import get_service_supabase
from backend.routers.auth import _get_current_tenant
from backend.services.api_key_auth import (
    generate_api_key,
    touch_last_used,
    validate_api_key,
    _ALLOWED_PLANS,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/zapier", tags=["zapier"])


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class CreateKeyRequest(BaseModel):
    name: str


class ApiKeyResponse(BaseModel):
    id: str
    client_id: str
    name: str
    key_prefix: str
    last_used_at: str | None
    created_at: str
    revoked_at: str | None


class CreateKeyResponse(BaseModel):
    id: str
    client_id: str
    name: str
    raw_key: str  # shown ONCE — store securely
    key_prefix: str
    created_at: str


class LeadRow(BaseModel):
    id: str
    client_id: str
    name: str | None
    email: str | None
    phone: str | None
    areas_of_interest: str | None  # semicolon-joined
    status: str | None
    created_at: str


# ---------------------------------------------------------------------------
# API-key auth dependency (for Zapier polling endpoint)
# ---------------------------------------------------------------------------


def _get_api_key_client(x_api_key: str = Header(...)) -> dict:
    """FastAPI dependency: validate X-Api-Key header, return tenant row.

    Returns a dict with at minimum: client_id, plan, plan_status, key_row.
    Raises 401 on invalid/revoked key, 402 on Free tier.
    """
    key_row = validate_api_key(x_api_key)
    if key_row is None:
        raise HTTPException(status_code=401, detail="Invalid or revoked API key")

    client_id = key_row["client_id"]
    db = get_service_supabase()

    tenant_result = (
        db.table("tenants")
        .select("id, plan, plan_status")
        .eq("id", client_id)
        .limit(1)
        .execute()
    )
    if not tenant_result.data:
        raise HTTPException(status_code=401, detail="Tenant not found for this API key")

    tenant = tenant_result.data[0]
    plan = tenant.get("plan") or "free"

    if plan not in _ALLOWED_PLANS:
        raise HTTPException(
            status_code=402,
            detail=(
                "Zapier integration requires a Growth, Autopilot, Professional, or "
                "Enterprise plan. Upgrade to use this feature."
            ),
        )

    # best-effort touch — never fail the request
    touch_last_used(key_row["id"])

    return {"client_id": client_id, "plan": plan, "key_row": key_row}


# ---------------------------------------------------------------------------
# Dashboard endpoints (JWT auth — tenant managing their own keys)
# ---------------------------------------------------------------------------


@router.post("/keys", response_model=CreateKeyResponse, status_code=201)
async def create_api_key(
    req: CreateKeyRequest,
    claims: dict = Depends(_get_current_tenant),
):
    """Generate a new Zapier API key for the current tenant.

    The raw key is returned ONCE — the caller must store it securely.
    """
    client_id: str = claims["tenant_id"]
    db = get_service_supabase()

    # Tier gate — dashboard check
    tenant_result = (
        db.table("tenants")
        .select("plan")
        .eq("id", client_id)
        .limit(1)
        .execute()
    )
    if not tenant_result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")

    plan = tenant_result.data[0].get("plan") or "free"
    if plan not in _ALLOWED_PLANS:
        raise HTTPException(
            status_code=402,
            detail="Zapier API keys require Growth plan or higher.",
        )

    raw_key, key_hash, key_prefix = generate_api_key()
    now = datetime.now(timezone.utc).isoformat()

    insert_result = (
        db.table("tenant_api_keys")
        .insert(
            {
                "client_id": client_id,
                "key_hash": key_hash,
                "key_prefix": key_prefix,
                "name": req.name.strip(),
                "created_at": now,
            }
        )
        .execute()
    )

    if not insert_result.data:
        raise HTTPException(status_code=500, detail="Failed to persist API key")

    row = insert_result.data[0]
    return CreateKeyResponse(
        id=row["id"],
        client_id=client_id,
        name=row["name"],
        raw_key=raw_key,
        key_prefix=key_prefix,
        created_at=row.get("created_at") or now,
    )


@router.get("/keys", response_model=list[ApiKeyResponse])
async def list_api_keys(
    claims: dict = Depends(_get_current_tenant),
):
    """List all non-revoked API keys for the current tenant."""
    client_id: str = claims["tenant_id"]
    db = get_service_supabase()

    result = (
        db.table("tenant_api_keys")
        .select("id, client_id, name, key_prefix, last_used_at, created_at, revoked_at")
        .eq("client_id", client_id)
        .order("created_at", desc=True)
        .execute()
    )

    return [
        ApiKeyResponse(
            id=row["id"],
            client_id=row["client_id"],
            name=row["name"],
            key_prefix=row["key_prefix"],
            last_used_at=row.get("last_used_at"),
            created_at=row["created_at"],
            revoked_at=row.get("revoked_at"),
        )
        for row in (result.data or [])
    ]


@router.delete("/keys/{key_id}", status_code=204)
async def revoke_api_key(
    key_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Revoke (soft-delete) an API key. Sets revoked_at to now."""
    client_id: str = claims["tenant_id"]
    db = get_service_supabase()

    # Verify ownership before revoking
    existing = (
        db.table("tenant_api_keys")
        .select("id, client_id, revoked_at")
        .eq("id", key_id)
        .eq("client_id", client_id)
        .limit(1)
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="API key not found")

    if existing.data[0].get("revoked_at"):
        # Already revoked — idempotent 204
        return

    db.table("tenant_api_keys").update(
        {"revoked_at": datetime.now(timezone.utc).isoformat()}
    ).eq("id", key_id).execute()


# ---------------------------------------------------------------------------
# Zapier polling endpoint (API key auth — called by Zapier, not the dashboard)
# ---------------------------------------------------------------------------


@router.get("/leads/new", response_model=list[LeadRow])
async def get_new_leads(
    since: str = Query(..., description="ISO 8601 datetime — return leads created after this"),
    limit: int = Query(default=100, ge=1, le=500),
    api_key_ctx: dict = Depends(_get_api_key_client),
):
    """Zapier trigger endpoint: returns leads created after `since`.

    Authentication: X-Api-Key header (API key, not Bearer JWT).
    Tier gating:    Growth, Autopilot, Professional, Enterprise.
    Returns:        Flat lead rows with semicolon-joined areas_of_interest.
    """
    client_id: str = api_key_ctx["client_id"]

    # Validate `since` is a parseable datetime
    try:
        datetime.fromisoformat(since.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid 'since' parameter — must be ISO 8601 datetime",
        )

    db = get_service_supabase()

    result = (
        db.table("leads")
        .select("id, client_id, name, email, phone, areas_of_interest, status, created_at")
        .eq("client_id", client_id)
        .gt("created_at", since)
        .order("created_at", desc=False)
        .limit(limit)
        .execute()
    )

    rows = []
    for row in result.data or []:
        aoi = row.get("areas_of_interest")
        if isinstance(aoi, list):
            aoi = ";".join(str(x) for x in aoi)
        rows.append(
            LeadRow(
                id=str(row["id"]),
                client_id=str(row["client_id"]),
                name=row.get("name"),
                email=row.get("email"),
                phone=row.get("phone"),
                areas_of_interest=aoi,
                status=row.get("status"),
                created_at=str(row["created_at"]),
            )
        )

    return rows
