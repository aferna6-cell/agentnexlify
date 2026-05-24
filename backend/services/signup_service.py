"""Register + login handler bodies extracted from auth.py.

Two service functions:
- `register(request, req)` — new tenant signup with disposable-email + velocity guards.
- `login(request, req)` — tenant-owner or team-member login with timing-attack
  protected dummy hash on miss.

Both use `from backend.routers import auth as _auth` lazy lookup so test
patches on `backend.routers.auth.<symbol>` continue to intercept.
"""

import logging
from datetime import datetime, timezone

import bcrypt
from fastapi import HTTPException, Request

from backend.models.schemas import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
)

logger = logging.getLogger(__name__)

_BCRYPT_ROUNDS = 14  # OWASP 2024+ minimum


async def register(*, request: Request, req: RegisterRequest) -> RegisterResponse:
    from backend.routers import auth as _auth

    email = req.email.lower().strip()
    if _auth.is_disposable_email(email):
        raise HTTPException(
            status_code=400, detail="Disposable email addresses are not allowed."
        )
    _auth.check_registration_velocity(request, email)
    tenant_id, api_key = _auth._provision_tenant_account(
        business_name=req.business_name,
        owner_name=req.owner_name,
        email=req.email,
        password_hash=_auth._hash_password(req.password),
        industry=req.industry,
        city=req.city,
        phone=req.phone,
        website_url=req.website_url,
    )

    token = _auth._create_token(
        tenant_id, req.email, "free", req.business_name, business_type=req.industry
    )

    await _auth._run_signup_side_effects(
        email=req.email,
        owner_name=req.owner_name,
        tenant_id=tenant_id,
        business_name=req.business_name,
        industry=req.industry,
        city=req.city,
        website_url=req.website_url,
    )

    _auth._record_signup_attempt(
        _auth._get_client_ip_for_fraud(request), email, tenant_id
    )
    return RegisterResponse(tenant_id=tenant_id, api_key=api_key, token=token)


async def login(*, request: Request, req: LoginRequest) -> LoginResponse:
    from backend.routers import auth as _auth

    db = _auth.get_service_supabase()
    email = req.email.lower().strip()

    # 1. Check tenants table (owner login)
    result = (
        db.table("tenants")
        .select("id, password_hash, business_name, plan, business_type")
        .eq("owner_email", email)
        .limit(1)
        .execute()
    )
    if result.data:
        tenant = result.data[0]
        if not tenant.get("password_hash"):
            _auth._verify_password(
                req.password,
                bcrypt.hashpw(b"dummy", bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)).decode(),
            )
            raise HTTPException(status_code=401, detail="Invalid email or password")
        if not _auth._verify_password(req.password, tenant["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        tenant_id = str(tenant["id"])
        token = _auth._create_token(
            tenant_id,
            email,
            tenant.get("plan") or "free",
            tenant.get("business_name") or "",
            business_type=tenant.get("business_type"),
        )
        return LoginResponse(
            tenant_id=tenant_id,
            token=token,
            business_name=tenant.get("business_name") or "",
            plan=tenant.get("plan") or "free",
        )

    # 2. Check team_members table (team member login)
    tm_result = (
        db.table("team_members")
        .select("id, tenant_id, email, name, role, password_hash, invite_accepted")
        .eq("email", email)
        .eq("invite_accepted", True)
        .limit(1)
        .execute()
    )
    if tm_result.data:
        member = tm_result.data[0]
        if not member.get("password_hash"):
            _auth._verify_password(
                req.password,
                bcrypt.hashpw(b"dummy", bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)).decode(),
            )
            raise HTTPException(status_code=401, detail="Invalid email or password")
        if not _auth._verify_password(req.password, member["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        tenant_result = (
            db.table("tenants")
            .select("business_name, plan, business_type")
            .eq("id", member["tenant_id"])
            .limit(1)
            .execute()
        )
        t = tenant_result.data[0] if tenant_result.data else {}
        tenant_id = str(member["tenant_id"])

        db.table("team_members").update(
            {"last_login": datetime.now(timezone.utc).isoformat()}
        ).eq("id", member["id"]).execute()

        token = _auth._create_token(
            tenant_id=tenant_id,
            email=email,
            plan=t.get("plan") or "free",
            business_name=t.get("business_name") or "",
            user_id=str(member["id"]),
            role=member["role"],
            is_team_member=True,
            name=member.get("name"),
            business_type=t.get("business_type"),
        )
        return LoginResponse(
            tenant_id=tenant_id,
            token=token,
            business_name=t.get("business_name") or "",
            plan=t.get("plan") or "free",
        )

    # No user found — dummy hash for timing parity
    _auth._verify_password(
        req.password,
        bcrypt.hashpw(b"dummy", bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)).decode(),
    )
    raise HTTPException(status_code=401, detail="Invalid email or password")
