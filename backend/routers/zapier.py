"""Zapier CRM export endpoints — API key management + leads polling."""

import logging
import secrets
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from passlib.context import CryptContext
from pydantic import BaseModel

from backend.models.database import get_service_supabase
from backend.services.auth_service import get_current_tenant

logger = logging.getLogger(__name__)

router = APIRouter(tags=["zapier"])

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

_GROWTH_PLUS_PLANS = {"growth", "professional", "autopilot", "enterprise"}

# In-memory rate limiter: key_prefix -> list of request timestamps
_rate_buckets: dict[str, list[float]] = defaultdict(list)
_RATE_LIMIT = 100
_RATE_WINDOW = 60.0  # seconds


# ── Helpers ──────────────────────────────────────────────────────────────────


def _check_rate_limit(key_prefix: str) -> None:
    now = time.monotonic()
    bucket = _rate_buckets[key_prefix]
    cutoff = now - _RATE_WINDOW
    # Evict stale timestamps
    _rate_buckets[key_prefix] = [t for t in bucket if t > cutoff]
    if len(_rate_buckets[key_prefix]) >= _RATE_LIMIT:
        raise HTTPException(
            status_code=429, detail="Rate limit exceeded — max 100 requests/min"
        )
    _rate_buckets[key_prefix].append(now)


async def _resolve_api_key(
    x_api_key: str = Header(default=None), api_key: str = Query(default=None)
) -> dict:
    """Dependency: validate X-API-Key or ?api_key, return tenant dict."""
    raw_key = x_api_key or api_key
    if not raw_key:
        raise HTTPException(
            status_code=401,
            detail="API key required (X-API-Key header or api_key param)",
        )

    key_prefix = raw_key[:12]

    db = get_service_supabase()
    result = (
        db.table("tenant_api_keys")
        .select("id, client_id, key_hash, key_prefix, revoked_at")
        .eq("key_prefix", key_prefix)
        .is_("revoked_at", "null")
        .limit(5)
        .execute()
    )
    rows = result.data or []

    matched = None
    for row in rows:
        if _pwd_ctx.verify(raw_key, row["key_hash"]):
            matched = row
            break

    if not matched:
        raise HTTPException(status_code=401, detail="Invalid API key")

    _check_rate_limit(key_prefix)

    tenant_result = (
        db.table("tenants")
        .select("id, plan")
        .eq("id", matched["client_id"])
        .limit(1)
        .execute()
    )
    if not tenant_result.data:
        raise HTTPException(status_code=401, detail="Tenant not found")

    tenant = tenant_result.data[0]
    if tenant.get("plan") not in _GROWTH_PLUS_PLANS:
        raise HTTPException(
            status_code=402, detail="Zapier integration requires Growth plan or higher"
        )

    # Update last_used_at
    try:
        db.table("tenant_api_keys").update(
            {"last_used_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", matched["id"]).execute()
    except Exception as exc:
        logger.warning(
            "Failed to update last_used_at for key %s", matched["id"], exc_info=exc
        )

    return tenant


# ── Leads endpoint (API key auth) ────────────────────────────────────────────


@router.get("/leads/new")
async def get_new_leads(
    since: str = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    tenant: dict = Depends(_resolve_api_key),
) -> dict:
    """Poll for new leads. Auth: X-API-Key."""
    client_id = tenant["id"]

    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=400, detail="Invalid 'since' datetime format — use ISO 8601"
            )
    else:
        since_dt = datetime.now(timezone.utc) - timedelta(hours=24)

    since_iso = since_dt.isoformat()

    db = get_service_supabase()
    try:
        result = (
            db.table("leads")
            .select(
                "id, client_id, name, email, phone, areas_of_interest, status, created_at"
            )
            .eq("client_id", client_id)
            .gt("created_at", since_iso)
            .order("created_at", desc=True)
            .limit(limit + 1)
            .execute()
        )
    except Exception as exc:
        logger.warning(
            "Zapier leads query failed for tenant %s", client_id, exc_info=exc
        )
        raise HTTPException(status_code=503, detail="Leads query failed — please retry")

    rows = result.data or []
    has_more = len(rows) > limit
    leads = rows[:limit]

    serialized = []
    for lead in leads:
        aoi = lead.get("areas_of_interest")
        if isinstance(aoi, list):
            aoi = ";".join(aoi)
        serialized.append(
            {
                "id": lead.get("id"),
                "client_id": lead.get("client_id"),
                "name": lead.get("name"),
                "email": lead.get("email"),
                "phone": lead.get("phone"),
                "areas_of_interest": aoi,
                "status": lead.get("status"),
                "created_at": lead.get("created_at"),
            }
        )

    return {"results": serialized, "count": len(serialized), "has_more": has_more}


# ── Key management (JWT auth) ─────────────────────────────────────────────────


class GenerateKeyRequest(BaseModel):
    name: str


@router.post("/keys", status_code=201)
async def generate_api_key(
    req: GenerateKeyRequest,
    claims: dict = Depends(get_current_tenant),
) -> dict:
    """Generate a new API key. Returns the full key ONCE."""
    tenant_id = claims.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant ID missing from token")

    if not req.name.strip():
        raise HTTPException(status_code=400, detail="Key name is required")

    raw_key = "anz_" + secrets.token_urlsafe(32)
    key_prefix = raw_key[:12]
    key_hash = _pwd_ctx.hash(raw_key)

    db = get_service_supabase()
    result = (
        db.table("tenant_api_keys")
        .insert(
            {
                "client_id": tenant_id,
                "key_hash": key_hash,
                "key_prefix": key_prefix,
                "name": req.name.strip(),
            }
        )
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create API key")

    row = result.data[0]
    return {"key": raw_key, "key_prefix": key_prefix, "id": row["id"]}


@router.get("/keys")
async def list_api_keys(claims: dict = Depends(get_current_tenant)) -> dict:
    """List API keys for this tenant. Never returns key_hash."""
    tenant_id = claims.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant ID missing from token")

    db = get_service_supabase()
    result = (
        db.table("tenant_api_keys")
        .select("id, key_prefix, name, last_used_at, created_at, revoked_at")
        .eq("client_id", tenant_id)
        .order("created_at", desc=True)
        .execute()
    )

    return {"keys": result.data or []}


@router.delete("/keys/{key_id}", status_code=204)
async def revoke_api_key(
    key_id: str,
    claims: dict = Depends(get_current_tenant),
) -> None:
    """Revoke (soft-delete) an API key."""
    tenant_id = claims.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant ID missing from token")

    db = get_service_supabase()
    result = (
        db.table("tenant_api_keys")
        .update({"revoked_at": datetime.now(timezone.utc).isoformat()})
        .eq("id", key_id)
        .eq("client_id", tenant_id)
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="API key not found")
