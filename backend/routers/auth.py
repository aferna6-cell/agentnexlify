"""Authentication endpoints — register, login, me."""

import logging
import secrets  # noqa: F401 — re-exported for tests patching backend.routers.auth.secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import httpx  # noqa: F401 — re-exported for tests patching backend.routers.auth.httpx
import stripe  # noqa: F401 — re-exported for tests patching backend.routers.auth.stripe
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse  # noqa: F401 — re-exported for tests
from jose import jwt

from backend.config import settings  # noqa: F401 — re-exported for test patches
from backend.limiter import limiter
from backend.models.database import get_service_supabase as _get_service_supabase

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
from backend.services.activity import log_activity  # noqa: F401 — re-exported for test patches
from backend.services.auth_service import _jwt_secret
from backend.services.email_sender import send_email  # noqa: F401 — re-exported for test patches
from backend.services.fraud_guard import (  # noqa: F401 — re-exported for signup_service + google_oauth_service via _auth.<symbol>
    _record_signup_attempt,
    check_registration_velocity,
    is_disposable_email,
)
from backend.services.stripe_service import (  # noqa: F401 — re-exported for tests patching backend.routers.auth.<symbol>
    PLAN_PRICES,
    ensure_plan_prices_configured,
    ensure_stripe_configured,
    get_or_create_customer,
)
from backend.services import billing_service as _billing_svc
from backend.services import dashboard_service as _dash_svc
from backend.services import google_oauth_service as _google_svc
from backend.services import password_service as _pwd_svc
from backend.services import signup_service as _signup_svc
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
    """New tenant signup."""
    return await _signup_svc.register(request=request, req=req)


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
    """Tenant-owner or team-member login."""
    return await _signup_svc.login(request=request, req=req)


@router.get("/google/url")
async def google_auth_url(
    mode: str = Query("signup", pattern="^(login|signup)$"),
    plan: str | None = Query(None),
):
    """Build Google authorization URL."""
    return await _google_svc.google_auth_url(mode=mode, plan=plan)


@router.get("/google/callback")
async def google_auth_callback(
    code: str | None = Query(None, description="Authorization code returned by Google"),
    state: str = Query(..., description="Signed OAuth state token"),
    error: str | None = Query(None, description="OAuth error returned by Google"),
):
    """Exchange Google authorization code for tenant session."""
    return await _google_svc.google_auth_callback(code=code, state=state, error=error)


@router.post("/google-register", response_model=RegisterResponse)
@limiter.limit("5/minute")
async def google_register(request: Request, req: GoogleRegisterRequest):
    """Finalize signup after Google identifies the user."""
    return await _google_svc.google_register(request=request, req=req)


@router.post("/forgot-password")
@limiter.limit("3/minute")
async def forgot_password(request: Request):
    """Send password reset email."""
    body = await request.json()
    return await _pwd_svc.forgot_password(email=body.get("email") or "")


@router.post("/reset-password")
@limiter.limit("5/minute")
async def reset_password(request: Request):
    """Reset password using token."""
    body = await request.json()
    return _pwd_svc.reset_password(
        token=body.get("token") or "",
        new_password=body.get("password", ""),
    )


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
    return _billing_svc.checkout(
        tenant_id=claims["tenant_id"],
        plan=body.get("plan"),
        source=body.get("source"),
        promo_code=body.get("promo_code"),
    )


@router.get("/billing/portal/{tenant_id}")
async def billing_portal(tenant_id: str, claims: dict = Depends(require_role("owner"))):
    """Create Stripe customer portal session (JWT auth)."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return _billing_svc.portal(tenant_id=tenant_id)


@router.post("/billing/change-plan")
async def billing_change_plan(
    request: Request,
    claims: dict = Depends(require_role("owner")),
):
    """Change subscription plan (upgrade/downgrade) with proration."""
    body = await request.json()
    return _billing_svc.change_plan(
        tenant_id=claims["tenant_id"],
        new_plan=body.get("plan"),
    )


@router.post("/billing/cancel")
async def billing_cancel(
    request: Request,
    claims: dict = Depends(require_role("owner")),
):
    """Cancel subscription at end of billing period."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    return _billing_svc.cancel_subscription(
        tenant_id=claims["tenant_id"],
        reason=str(body.get("reason") or "").strip(),
        reason_detail=str(
            body.get("reason_detail") or body.get("detail") or ""
        ).strip(),
        feedback=str(body.get("feedback") or "").strip(),
    )


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
