"""Authentication endpoints — register, login, me."""

import logging
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import bcrypt
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from jose import jwt

from backend.config import settings
from backend.limiter import limiter
from backend.models.database import get_service_supabase as _get_service_supabase
import stripe

from backend.models.schemas import (
    DashboardResponse,
    GoogleRegisterRequest,
    LoginRequest,
    LoginResponse,
    MeResponse,
    RegisterRequest,
    RegisterResponse,
    TrialStatusResponse,
    WidgetConfigDetail,
    WidgetConfigUpdateRequest,
)
from backend.services.auth_service import _jwt_secret
from backend.services.stripe_service import (
    PLAN_PRICES,
    ensure_plan_prices_configured,
    ensure_stripe_configured,
    get_or_create_customer,
)
from backend.services.email_sender import send_email
from backend.services.activity import log_activity
from backend.services.fraud_guard import (
    check_registration_velocity,
    is_disposable_email,
    _record_signup_attempt,
)
from backend.services import dashboard_service as _dash_svc
from backend.services import widget_config_service as _widget_svc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

_JWT_ALGORITHM = "HS256"
_JWT_EXPIRE_HOURS = 24  # Short-lived to prevent stale plan claims after downgrade
_GOOGLE_STATE_EXPIRY_MINUTES = 10
_GOOGLE_SETUP_EXPIRY_HOURS = 1
_GOOGLE_OAUTH_SCOPE = "openid email profile"


def get_supabase():
    """Backward-compatible test seam for modules that still patch auth.get_supabase."""
    return _get_service_supabase()


def get_service_supabase():
    """Preserve existing call sites while allowing get_supabase() patches to intercept."""
    return get_supabase()


# _jwt_secret, _decode_token, and get_current_tenant live in auth_service to
# avoid service→router import violations. Imported above; defined here only
# as aliases so existing call sites in this file continue to work unchanged.


# ── Helpers ──────────────────────────────────────────────────

_BCRYPT_ROUNDS = 14  # OWASP recommended minimum for 2024+


def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)).decode()


def _verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def _create_token(
    tenant_id: str,
    email: str,
    plan: str,
    business_name: str,
    user_id: str | None = None,
    role: str = "owner",
    is_team_member: bool = False,
    name: str | None = None,
    business_type: str | None = None,
) -> str:
    payload = {
        "tenant_id": tenant_id,
        "sub": tenant_id,
        "email": email,
        "plan": plan,
        "business_name": business_name,
        "role": role,
        "is_team_member": is_team_member,
        "exp": datetime.now(timezone.utc) + timedelta(hours=_JWT_EXPIRE_HOURS),
    }
    if user_id:
        payload["user_id"] = user_id
    if name:
        payload["name"] = name
    if business_type:
        payload["business_type"] = business_type
    return jwt.encode(payload, _jwt_secret(), algorithm=_JWT_ALGORITHM)


# _get_current_tenant and require_role live in backend.dependencies — import for own use.
from backend.dependencies import _get_current_tenant, require_role  # noqa: E402


# Google OAuth + paid-plan helpers extracted to auth_google_helpers.py.
# Re-imported here so existing call sites + test patch points keep working.
from backend.routers.auth_google_helpers import (  # noqa: E402, F401
    _decode_google_setup_token,
    _decode_google_state,
    _encode_google_setup_token,
    _encode_google_state,
    _frontend_redirect,
    _google_auth_callback_url,
    _normalize_paid_plan,
)

# Tenant provisioning + signup side effects extracted to auth_provisioning.py.
from backend.routers.auth_provisioning import (  # noqa: E402, F401
    _provision_tenant_account,
    _run_signup_side_effects,
)


# ── Industry FAQ Seeds ───────────────────────────────────────
# Moved to backend/services/industry_faqs.py
# Re-exported here for backward compatibility with any direct imports.

# ── Endpoints ────────────────────────────────────────────────


@router.post("/register", response_model=RegisterResponse)
@limiter.limit("5/minute")
async def register(request: Request, req: RegisterRequest):
    email = req.email.lower().strip()
    if is_disposable_email(email):
        raise HTTPException(
            status_code=400, detail="Disposable email addresses are not allowed."
        )
    check_registration_velocity(request, email)
    tenant_id, api_key = _provision_tenant_account(
        business_name=req.business_name,
        owner_name=req.owner_name,
        email=req.email,
        password_hash=_hash_password(req.password),
        industry=req.industry,
        city=req.city,
        phone=req.phone,
        website_url=req.website_url,
    )

    token = _create_token(
        tenant_id, req.email, "free", req.business_name, business_type=req.industry
    )

    await _run_signup_side_effects(
        email=req.email,
        owner_name=req.owner_name,
        tenant_id=tenant_id,
        business_name=req.business_name,
        industry=req.industry,
        city=req.city,
        website_url=req.website_url,
    )

    _record_signup_attempt(_get_client_ip_for_fraud(request), email, tenant_id)
    return RegisterResponse(tenant_id=tenant_id, api_key=api_key, token=token)


def _get_client_ip_for_fraud(request: Request) -> str:
    """Extract real client IP for fraud tracking."""
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        ips = [ip.strip() for ip in forwarded.split(",") if ip.strip()]
        if ips:
            return ips[-1]
    return request.client.host if request.client else "127.0.0.1"


@router.post("/login", response_model=LoginResponse)
@limiter.limit("5/minute")
async def login(request: Request, req: LoginRequest):
    db = get_service_supabase()
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
            # Use dummy hash to prevent timing attacks
            _verify_password(
                req.password,
                bcrypt.hashpw(b"dummy", bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)).decode(),
            )
            raise HTTPException(status_code=401, detail="Invalid email or password")
        if not _verify_password(req.password, tenant["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        tenant_id = str(tenant["id"])
        token = _create_token(
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
            # Use dummy hash to prevent timing attacks
            _verify_password(
                req.password,
                bcrypt.hashpw(b"dummy", bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)).decode(),
            )
            raise HTTPException(status_code=401, detail="Invalid email or password")
        if not _verify_password(req.password, member["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        # Fetch tenant info
        tenant_result = (
            db.table("tenants")
            .select("business_name, plan, business_type")
            .eq("id", member["tenant_id"])
            .limit(1)
            .execute()
        )
        t = tenant_result.data[0] if tenant_result.data else {}
        tenant_id = str(member["tenant_id"])

        # Update last_login
        db.table("team_members").update(
            {"last_login": datetime.now(timezone.utc).isoformat()}
        ).eq("id", member["id"]).execute()

        token = _create_token(
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

    # No user found — perform dummy hash to prevent timing attacks
    # This ensures the response time is similar whether user exists or not
    _verify_password(
        req.password,
        bcrypt.hashpw(b"dummy", bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)).decode(),
    )
    raise HTTPException(status_code=401, detail="Invalid email or password")


@router.get("/google/url")
async def google_auth_url(
    mode: str = Query("signup", pattern="^(login|signup)$"),
    plan: str | None = Query(None),
):
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(status_code=503, detail="Google OAuth is not configured")

    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(
        {
            "client_id": settings.google_client_id,
            "redirect_uri": _google_auth_callback_url(),
            "response_type": "code",
            "scope": _GOOGLE_OAUTH_SCOPE,
            "state": _encode_google_state(mode, plan),
            "prompt": "select_account",
        }
    )
    return {"auth_url": auth_url}


@router.get("/google/callback")
async def google_auth_callback(
    code: str | None = Query(None, description="Authorization code returned by Google"),
    state: str = Query(..., description="Signed OAuth state token"),
    error: str | None = Query(None, description="OAuth error returned by Google"),
):
    oauth_state = _decode_google_state(state)
    mode = oauth_state["mode"]
    plan = oauth_state["plan"]

    if error:
        target = "/login" if mode == "login" else "/signup"
        return RedirectResponse(
            url=_frontend_redirect(target, {"google_error": error, "plan": plan})
        )

    if not code:
        raise HTTPException(status_code=400, detail="Missing Google authorization code")
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(status_code=503, detail="Google OAuth is not configured")

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            token_resp = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "redirect_uri": _google_auth_callback_url(),
                    "grant_type": "authorization_code",
                },
            )
            token_resp.raise_for_status()
            token_data = token_resp.json()

            access_token = token_data.get("access_token")
            if not access_token:
                raise HTTPException(
                    status_code=502, detail="Google did not return an access token"
                )

            userinfo_resp = await client.get(
                "https://openidconnect.googleapis.com/v1/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            userinfo_resp.raise_for_status()
            profile = userinfo_resp.json()
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Google OAuth exchange failed")
        raise HTTPException(
            status_code=502, detail="Failed to complete Google sign-in"
        ) from exc

    email = (profile.get("email") or "").lower().strip()
    owner_name = (profile.get("name") or "").strip() or email.split("@")[0]
    if not email:
        raise HTTPException(
            status_code=400, detail="Google account did not provide an email address"
        )
    if profile.get("email_verified") is False:
        raise HTTPException(
            status_code=400, detail="Google account email must be verified"
        )

    db = get_service_supabase()
    existing = (
        db.table("tenants")
        .select("id, business_name, plan, business_type")
        .eq("owner_email", email)
        .limit(1)
        .execute()
    )
    if existing.data:
        tenant = existing.data[0]
        tenant_id = str(tenant["id"])
        token = _create_token(
            tenant_id=tenant_id,
            email=email,
            plan=tenant.get("plan") or "free",
            business_name=tenant.get("business_name") or "",
            business_type=tenant.get("business_type"),
            name=owner_name,
        )
        return RedirectResponse(
            url=_frontend_redirect(
                "/auth/callback",
                {"token": token, "tenant_id": tenant_id},
                use_fragment=True,
            )
        )

    setup_token = _encode_google_setup_token(
        email=email, owner_name=owner_name, plan=plan
    )
    return RedirectResponse(
        url=_frontend_redirect(
            "/signup",
            {
                "google_setup": setup_token,
                "email": email,
                "name": owner_name,
                "plan": plan,
            },
        )
    )


@router.post("/google-register", response_model=RegisterResponse)
@limiter.limit("5/minute")
async def google_register(request: Request, req: GoogleRegisterRequest):
    setup = _decode_google_setup_token(req.setup_token)
    email = setup["email"].lower().strip()
    if is_disposable_email(email):
        raise HTTPException(
            status_code=400, detail="Disposable email addresses are not allowed."
        )
    check_registration_velocity(request, email)
    generated_password = secrets.token_urlsafe(32)

    tenant_id, api_key = _provision_tenant_account(
        business_name=req.business_name,
        owner_name=setup["owner_name"],
        email=setup["email"],
        password_hash=_hash_password(generated_password),
        industry=req.industry,
        city=req.city,
        phone=req.phone,
        website_url=req.website_url,
    )

    token = _create_token(
        tenant_id=tenant_id,
        email=setup["email"],
        plan="free",
        business_name=req.business_name,
        business_type=req.industry,
        name=setup["owner_name"],
    )

    await _run_signup_side_effects(
        email=setup["email"],
        owner_name=setup["owner_name"],
        tenant_id=tenant_id,
        business_name=req.business_name,
        industry=req.industry,
        city=req.city,
        website_url=req.website_url,
    )

    _record_signup_attempt(_get_client_ip_for_fraud(request), email, tenant_id)
    return RegisterResponse(tenant_id=tenant_id, api_key=api_key, token=token)


@router.post("/forgot-password")
@limiter.limit("3/minute")
async def forgot_password(request: Request):
    """Send password reset email."""
    body = await request.json()
    email = (body.get("email") or "").lower().strip()
    if not email:
        raise HTTPException(status_code=400, detail="Email required")

    db = get_service_supabase()
    # Check tenants table for the email
    try:
        result = (
            db.table("tenants")
            .select("id, owner_email, owner_name, business_name")
            .eq("owner_email", email)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.error(
            "DB error during forgot-password lookup for %s", email, exc_info=True
        )
        raise HTTPException(status_code=500, detail="Internal server error")

    if not result.data:
        # Don't reveal whether email exists
        return {"message": "If that email exists, a reset link has been sent."}

    tenant = result.data[0]
    tenant_id = str(tenant["id"])

    # Generate reset token (expires in 1 hour)
    reset_token = secrets.token_urlsafe(32)
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

    # Store hashed token in tenant record (compare hashes on redemption)
    import hashlib as _hashlib

    hashed_token = _hashlib.sha256(reset_token.encode()).hexdigest()
    try:
        db.table("tenants").update(
            {
                "reset_token": hashed_token,
                "reset_token_expires": expires_at,
            }
        ).eq("id", tenant_id).execute()
    except Exception:
        logger.error(
            "Failed to store reset token for tenant %s", tenant_id, exc_info=True
        )
        raise HTTPException(status_code=500, detail="Internal server error")

    # Send reset email
    reset_url = f"{settings.frontend_url}/reset-password?token={reset_token}"
    try:
        await send_email(
            to=email,
            subject="Reset your AgentNexLiFy password",
            body_html=(
                f"<p>Hi {tenant.get('owner_name', 'there')},</p>"
                "<p>Click the link below to reset your password. This link expires in 1 hour.</p>"
                f'<p><a href="{reset_url}" style="background:#3B82F6;color:white;'
                'padding:12px 24px;border-radius:8px;text-decoration:none;display:inline-block;">'
                "Reset Password</a></p>"
                "<p>If you didn't request this, you can safely ignore this email.</p>"
                "<p>- The AgentNexLiFy Team</p>"
            ),
            tenant_id=tenant_id,
        )
    except Exception:
        logger.warning("Failed to send reset email to %s", email, exc_info=True)

    return {"message": "If that email exists, a reset link has been sent."}


@router.post("/reset-password")
@limiter.limit("5/minute")
async def reset_password(request: Request):
    """Reset password using token."""
    body = await request.json()
    token = (body.get("token") or "").strip()
    new_password = body.get("password", "")

    if not token or not new_password:
        raise HTTPException(status_code=400, detail="Token and password required")
    if len(new_password) < 8:
        raise HTTPException(
            status_code=400, detail="Password must be at least 8 characters"
        )

    db = get_service_supabase()
    # Hash the incoming token to match stored hash
    import hashlib as _hashlib

    hashed_token = _hashlib.sha256(token.encode()).hexdigest()
    try:
        result = (
            db.table("tenants")
            .select("id, reset_token_expires")
            .eq("reset_token", hashed_token)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.error("DB error during reset-password token lookup", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

    if not result.data:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link")

    tenant = result.data[0]
    expires = tenant.get("reset_token_expires")
    if expires:
        exp_dt = datetime.fromisoformat(expires.replace("Z", "+00:00"))
        if datetime.now(timezone.utc) > exp_dt:
            raise HTTPException(status_code=400, detail="Reset link has expired")

    # Update password and clear token
    hashed = _hash_password(new_password)
    try:
        db.table("tenants").update(
            {
                "password_hash": hashed,
                "reset_token": None,
                "reset_token_expires": None,
            }
        ).eq("id", str(tenant["id"])).execute()
    except Exception:
        logger.error(
            "Failed to update password for tenant %s", tenant["id"], exc_info=True
        )
        raise HTTPException(status_code=500, detail="Internal server error")

    logger.info("Password reset completed for tenant %s", tenant["id"])
    return {"message": "Password reset successfully"}


@router.get("/me", response_model=MeResponse)
async def me(claims: dict = Depends(_get_current_tenant)):
    db = get_service_supabase()

    result = (
        db.table("tenants")
        .select(
            "id, owner_email, business_name, plan, city, owner_name, "
            "business_type, marketing_addon_active, marketing_addon_grandfathered"
        )
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
        plan=t.get("plan") or "free",
        city=t.get("city"),
        owner_name=t.get("owner_name"),
        business_type=t.get("business_type"),
        marketing_addon_active=bool(t.get("marketing_addon_active")),
        marketing_addon_grandfathered=bool(t.get("marketing_addon_grandfathered")),
    )


@router.get("/dashboard/{tenant_id}", response_model=DashboardResponse)
async def dashboard(tenant_id: str, claims: dict = Depends(_get_current_tenant)):
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    db = get_service_supabase()
    return _dash_svc.build_dashboard_payload(tenant_id, db)


# ── Widget Config ────────────────────────────────────────────


@router.put("/widget-config/{tenant_id}", response_model=WidgetConfigDetail)
async def update_widget_config(
    tenant_id: str,
    req: WidgetConfigUpdateRequest,
    claims: dict = Depends(_get_current_tenant),
):
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    w = _widget_svc.update_widget_config_service(tenant_id, req)
    return WidgetConfigDetail(
        bot_name=w.get("bot_name", ""),
        primary_color=w.get("primary_color", "#00BFFF"),
        greeting_message=w.get("greeting_message", ""),
        position=w.get("position", "bottom-right"),
        branding=w.get("branding") or None,
        teaser_message=w.get("teaser_message"),
        teaser_delay_seconds=w.get("teaser_delay_seconds") or 3,
        teaser_enabled=w.get("teaser_enabled", True),
        enable_ai_fallback=w.get("enable_ai_fallback", False),
        enable_structured_lead_parser=w.get("enable_structured_lead_parser", False),
    )


# FAQ CRUD moved to backend/routers/faq.py
# Conversations endpoints moved to backend/routers/conversations.py


# ── MCP API Keys ──────────────────────────────────────────


@router.post("/mcp-key/{tenant_id}")
async def generate_mcp_key(
    tenant_id: str, claims: dict = Depends(require_role("owner"))
):
    """Generate or regenerate an MCP API key for the tenant."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    import secrets as sec

    mcp_key = f"mcp_{sec.token_urlsafe(32)}"

    db = get_service_supabase()
    result = (
        db.table("tenants")
        .update({"mcp_api_key": mcp_key, "mcp_enabled": True})
        .eq("id", tenant_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")

    return {"mcp_api_key": mcp_key}


@router.delete("/mcp-key/{tenant_id}")
async def revoke_mcp_key(tenant_id: str, claims: dict = Depends(require_role("owner"))):
    """Revoke the MCP API key."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db = get_service_supabase()
    db.table("tenants").update({"mcp_api_key": None, "mcp_enabled": False}).eq(
        "id", tenant_id
    ).execute()
    return {"success": True}


# ── Tenant Settings ──────────────────────────────────────────


@router.put("/settings/{tenant_id}")
async def update_settings(
    tenant_id: str,
    request: Request,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Update tenant business info."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    body = await request.json()
    allowed = {
        "business_name",
        "business_type",
        "city",
        "owner_name",
        "notification_phone",
        "sms_notifications_enabled",
        "google_review_link",
        "review_request_config",
        "website_url",
        "textback_enabled",
        "textback_message",
        "textback_quiet_start",
        "textback_quiet_end",
        "daily_briefing_enabled",
        "noshow_recovery_enabled",
    }
    updates = {k: v for k, v in body.items() if k in allowed and v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update")

    db = get_service_supabase()
    logger.info("update_settings tenant_id=%s fields=%s", tenant_id, sorted(updates))
    try:
        result = db.table("tenants").update(updates).eq("id", tenant_id).execute()
    except Exception:
        logger.exception("update_settings failed for tenant_id=%s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to update settings")
    if not result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return result.data[0]


@router.get("/tenant/{tenant_id}")
async def get_tenant(tenant_id: str, claims: dict = Depends(_get_current_tenant)):
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db = get_service_supabase()
    result = (
        db.table("tenants")
        .select(
            "id, business_name, business_type, city, owner_email, owner_name, plan, plan_status, notification_phone, sms_notifications_enabled, google_review_link, review_request_config, website_url, business_slug, business_page_enabled, textback_enabled, textback_message, textback_quiet_start, textback_quiet_end, client_login_enabled, daily_briefing_enabled, noshow_recovery_enabled"
        )
        .eq("id", tenant_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return result.data[0]


# ── Billing (JWT-authenticated proxies) ──────────────────────


@router.post("/billing/checkout")
async def billing_checkout(
    request: Request,
    claims: dict = Depends(require_role("owner")),
):
    """Create Stripe checkout session (JWT auth, no API secret needed)."""
    body = await request.json()
    tenant_id = claims["tenant_id"]
    plan = body.get("plan")

    if not plan or plan not in PLAN_PRICES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid plan. Must be one of: {', '.join(PLAN_PRICES)}",
        )
    try:
        prices = ensure_plan_prices_configured(plan)
        ensure_stripe_configured()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    db = get_service_supabase()
    result = (
        db.table("tenants")
        .select("id, owner_email, business_name")
        .eq("id", tenant_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")
    tenant = result.data[0]

    customer = get_or_create_customer(
        email=tenant.get("owner_email") or "",
        tenant_id=tenant_id,
        business_name=tenant.get("business_name"),
    )

    line_items = []
    if "setup" in prices:
        line_items.append({"price": prices["setup"], "quantity": 1})
    line_items.append({"price": prices["monthly"], "quantity": 1})

    source = body.get("source")  # "wizard" | None
    if source == "wizard":
        # Wizard expanded to 7 steps in Onboarding v2 (added auto-KB step at position 2).
        # success → Embed (step 7); cancel → Plan (step 6).
        success_url = f"{settings.frontend_url}/onboarding?step=7&session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{settings.frontend_url}/onboarding?step=6&cancelled=1"
    else:
        success_url = f"{settings.frontend_url}/billing/success?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{settings.frontend_url}/billing/cancel"

    session_params: dict = {
        "mode": "subscription",
        "customer": customer.id,
        "line_items": line_items,
        "success_url": success_url,
        "cancel_url": cancel_url,
        "metadata": {"tenant_id": tenant_id, "plan": plan},
        "subscription_data": {"metadata": {"tenant_id": tenant_id, "plan": plan}},
    }
    if plan == "growth":
        session_params["subscription_data"]["trial_period_days"] = 7

    promo_code = body.get("promo_code")
    if promo_code:
        promos = stripe.PromotionCode.list(code=promo_code, active=True, limit=1)
        if promos.data:
            session_params["discounts"] = [{"promotion_code": promos.data[0].id}]
        else:
            raise HTTPException(status_code=400, detail="Invalid promo code")

    session = stripe.checkout.Session.create(**session_params)
    return {"checkout_url": session.url}


@router.get("/billing/portal/{tenant_id}")
async def billing_portal(tenant_id: str, claims: dict = Depends(require_role("owner"))):
    """Create Stripe customer portal session (JWT auth)."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db = get_service_supabase()
    result = (
        db.table("tenants")
        .select("stripe_customer_id")
        .eq("id", tenant_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")

    customer_id = result.data[0].get("stripe_customer_id")
    if not customer_id:
        raise HTTPException(
            status_code=400, detail="No billing account. Upgrade to a paid plan first."
        )

    try:
        ensure_stripe_configured()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=f"{settings.frontend_url}/billing",
    )
    return {"portal_url": session.url}


@router.post("/billing/change-plan")
async def billing_change_plan(
    request: Request,
    claims: dict = Depends(require_role("owner")),
):
    """Change subscription plan (upgrade/downgrade) with proration."""
    body = await request.json()
    new_plan = body.get("plan")
    tenant_id = claims["tenant_id"]

    if not new_plan or new_plan not in PLAN_PRICES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid plan. Must be one of: {', '.join(PLAN_PRICES)}",
        )
    try:
        new_price_id = ensure_plan_prices_configured(new_plan)["monthly"]
        ensure_stripe_configured()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    db = get_service_supabase()
    result = (
        db.table("tenants")
        .select("stripe_customer_id, plan")
        .eq("id", tenant_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")

    tenant = result.data[0]
    customer_id = tenant.get("stripe_customer_id")
    if not customer_id:
        raise HTTPException(
            status_code=400, detail="No billing account. Subscribe first."
        )

    current_plan = tenant.get("plan") or "free"
    if current_plan == new_plan:
        raise HTTPException(status_code=400, detail="Already on this plan")

    # Find active subscription
    subs = stripe.Subscription.list(customer=customer_id, status="active", limit=1)
    if not subs.data:
        raise HTTPException(
            status_code=400,
            detail="No active subscription found. Use checkout to subscribe.",
        )

    subscription = subs.data[0]
    sub_item_id = subscription["items"]["data"][0]["id"]
    # Modify subscription with proration
    updated = stripe.Subscription.modify(
        subscription.id,
        items=[{"id": sub_item_id, "price": new_price_id}],
        proration_behavior="create_prorations",
        metadata={"tenant_id": tenant_id, "plan": new_plan},
    )

    # Update tenant plan immediately (webhook will also fire)
    db.table("tenants").update({"plan": new_plan}).eq("id", tenant_id).execute()

    logger.info(
        "Plan changed for tenant %s: %s -> %s", tenant_id, current_plan, new_plan
    )
    return {"status": "changed", "old_plan": current_plan, "new_plan": new_plan}


@router.post("/billing/cancel")
async def billing_cancel(
    request: Request,
    claims: dict = Depends(require_role("owner")),
):
    """Cancel subscription at end of billing period."""
    tenant_id = claims["tenant_id"]
    try:
        body = await request.json()
    except Exception:
        body = {}
    allowed_reasons = {
        "too_expensive",
        "missing_feature",
        "not_enough_leads",
        "switching_tools",
        "setup_too_hard",
        "temporary_pause",
        "other",
    }
    reason = str(body.get("reason") or "").strip()
    if reason not in allowed_reasons:
        raise HTTPException(status_code=400, detail="Cancellation reason is required")
    reason_detail = str(body.get("reason_detail") or body.get("detail") or "").strip()[
        :1000
    ]
    feedback = str(body.get("feedback") or "").strip()[:1000]

    db = get_service_supabase()
    result = (
        db.table("tenants")
        .select("stripe_customer_id, plan")
        .eq("id", tenant_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")

    tenant = result.data[0]
    customer_id = tenant.get("stripe_customer_id")
    if not customer_id:
        raise HTTPException(status_code=400, detail="No billing account")

    if tenant.get("plan") == "free":
        raise HTTPException(status_code=400, detail="Already on free plan")

    try:
        ensure_stripe_configured()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    subs = stripe.Subscription.list(customer=customer_id, status="active", limit=1)
    if not subs.data:
        raise HTTPException(status_code=400, detail="No active subscription")

    # Cancel at period end (don't immediately revoke access)
    subscription = subs.data[0]
    subscription_id = getattr(subscription, "id", None)
    if subscription_id is None and isinstance(subscription, dict):
        subscription_id = subscription.get("id")
    stripe.Subscription.modify(
        subscription_id,
        cancel_at_period_end=True,
        metadata={
            "tenant_id": tenant_id,
            "cancellation_reason": reason,
        },
    )

    current_period_end = getattr(subscription, "current_period_end", None)
    if current_period_end is None and isinstance(subscription, dict):
        current_period_end = subscription.get("current_period_end")
    current_period_end_iso = None
    if isinstance(current_period_end, (int, float)):
        current_period_end_iso = datetime.fromtimestamp(
            current_period_end,
            tz=timezone.utc,
        ).isoformat()

    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        db.table("tenants").update(
            {
                "cancellation_requested_at": now_iso,
                "cancellation_reason": reason,
                "cancellation_reason_detail": reason_detail or None,
            }
        ).eq("id", tenant_id).execute()
        db.table("tenant_cancellation_events").insert(
            {
                "tenant_id": tenant_id,
                "stripe_subscription_id": subscription_id,
                "plan": tenant.get("plan"),
                "reason": reason,
                "reason_detail": reason_detail or None,
                "feedback": feedback or None,
                "current_period_end": current_period_end_iso,
            }
        ).execute()
    except Exception:
        logger.warning(
            "Failed to persist cancellation reason for tenant %s",
            tenant_id,
            exc_info=True,
        )

    log_activity(
        tenant_id=tenant_id,
        activity_type="subscription_cancellation_scheduled",
        description="Subscription cancellation scheduled at period end",
        metadata={
            "reason": reason,
            "has_reason_detail": bool(reason_detail),
            "current_period_end": current_period_end_iso,
        },
    )

    logger.info("Subscription cancellation scheduled for tenant %s", tenant_id)
    return {
        "status": "cancellation_scheduled",
        "current_period_end": current_period_end,
    }


# ── Free Trial ────────────────────────────────────────────────
# Logic moved to backend/services/dashboard_service.py; re-exported for
# internal use by the dashboard endpoint in this file.
from backend.services.dashboard_service import (  # noqa: F401
    FREE_TRIAL_DAYS,
    _compute_trial_status,
    compute_trial_status,
)


@router.get("/trial-status/{tenant_id}", response_model=TrialStatusResponse)
async def trial_status(tenant_id: str, claims: dict = Depends(_get_current_tenant)):
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db = get_service_supabase()
    result = (
        db.table("tenants")
        .select("plan, free_trial_started_at, created_at")
        .eq("id", tenant_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")

    tenant = result.data[0]
    trial = _compute_trial_status(tenant)
    trial_started = tenant.get("free_trial_started_at")

    trial_expires = None
    if trial_started and trial["trial_days_remaining"] is not None:
        from datetime import datetime, timezone, timedelta

        if isinstance(trial_started, str):
            ts = datetime.fromisoformat(trial_started.replace("Z", "+00:00"))
        else:
            ts = trial_started
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        trial_expires = (ts + timedelta(days=FREE_TRIAL_DAYS)).isoformat()

    return TrialStatusResponse(
        plan=tenant.get("plan") or "free",
        trial_started=(
            trial_started
            if isinstance(trial_started, str)
            else (trial_started.isoformat() if trial_started else None)
        ),
        trial_expires=trial_expires,
        days_remaining=trial["trial_days_remaining"],
        is_expired=trial["trial_expired"],
    )


# ---------------------------------------------------------------------------
# Activity feed
# ---------------------------------------------------------------------------


@router.get("/activity/{tenant_id}")
async def get_activity(tenant_id: str, claims: dict = Depends(_get_current_tenant)):
    """Return recent activity for the dashboard feed."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return _dash_svc.get_activity(tenant_id)


@router.get("/knowledge-stats/{tenant_id}")
async def get_knowledge_stats(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Return stats about what the AI chatbot knows: FAQs, website pages, feedback corrections."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return _dash_svc.get_knowledge_stats(tenant_id)
