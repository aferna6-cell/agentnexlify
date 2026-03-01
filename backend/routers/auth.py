"""Authentication endpoints — register, login, me."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Header
from jose import JWTError, jwt

from backend.config import settings
from backend.models.database import get_supabase
from backend.models.schemas import (
    LoginRequest,
    LoginResponse,
    MeResponse,
    RegisterRequest,
    RegisterResponse,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

_JWT_ALGORITHM = "HS256"
_JWT_EXPIRE_DAYS = 7


# ── Helpers ──────────────────────────────────────────────────


def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def _verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def _create_token(
    tenant_id: str,
    email: str,
    plan: str,
    business_name: str,
) -> str:
    payload = {
        "tenant_id": tenant_id,
        "sub": tenant_id,
        "email": email,
        "plan": plan,
        "business_name": business_name,
        "exp": datetime.now(timezone.utc) + timedelta(days=_JWT_EXPIRE_DAYS),
    }
    return jwt.encode(payload, settings.api_secret_key, algorithm=_JWT_ALGORITHM)


def _decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.api_secret_key, algorithms=[_JWT_ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc


def _get_current_tenant(authorization: str = Header(...)) -> dict:
    """FastAPI dependency: extract tenant claims from Bearer token."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    return _decode_token(authorization.removeprefix("Bearer ").strip())


# ── Endpoints ────────────────────────────────────────────────


@router.post("/register", response_model=RegisterResponse)
async def register(req: RegisterRequest):
    db = get_supabase()

    # Check duplicate email
    existing = (
        db.table("tenants")
        .select("id")
        .eq("owner_email", req.email)
        .limit(1)
        .execute()
    )
    if existing.data:
        raise HTTPException(status_code=409, detail="Email already registered")

    # Insert tenant
    tenant_data = {
        "business_name": req.business_name,
        "business_type": req.industry,
        "owner_email": req.email,
        "owner_name": req.owner_name,
        "password_hash": _hash_password(req.password),
        "city": req.city,
        "plan": "free",
    }
    result = db.table("tenants").insert(tenant_data).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create account")

    tenant = result.data[0]
    tenant_id = str(tenant["id"])

    # Create widget config with prefixed api_key
    api_key = f"anx_{secrets.token_urlsafe(32)}"
    db.table("widget_configs").insert({
        "tenant_id": tenant_id,
        "api_key": api_key,
    }).execute()

    token = _create_token(tenant_id, req.email, "free", req.business_name)

    return RegisterResponse(tenant_id=tenant_id, api_key=api_key, token=token)


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    db = get_supabase()

    result = (
        db.table("tenants")
        .select("id, password_hash, business_name, plan")
        .eq("owner_email", req.email.lower().strip())
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    tenant = result.data[0]
    if not tenant.get("password_hash"):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not _verify_password(req.password, tenant["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    tenant_id = str(tenant["id"])
    token = _create_token(
        tenant_id,
        req.email,
        tenant.get("plan", "free"),
        tenant.get("business_name", ""),
    )

    return LoginResponse(
        tenant_id=tenant_id,
        token=token,
        business_name=tenant.get("business_name", ""),
        plan=tenant.get("plan", "free"),
    )


@router.get("/me", response_model=MeResponse)
async def me(claims: dict = Depends(_get_current_tenant)):
    db = get_supabase()

    result = (
        db.table("tenants")
        .select("id, owner_email, business_name, plan, city, owner_name")
        .eq("id", claims["tenant_id"])
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")

    t = result.data[0]
    return MeResponse(
        tenant_id=str(t["id"]),
        email=t["owner_email"],
        business_name=t["business_name"],
        plan=t.get("plan", "free"),
        city=t.get("city"),
        owner_name=t.get("owner_name"),
    )
