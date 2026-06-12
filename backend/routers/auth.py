"""Authentication endpoints — register, login, me."""

import html
import logging
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import bcrypt
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt

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
from backend.services.email_sender import send_email, mask_email
from backend.services.activity import log_activity
from backend.services.business_profiles import (
    get_dashboard_business_profile,
    get_widget_defaults,
)
from backend.services.fraud_guard import (
    check_registration_velocity,
    is_disposable_email,
    _record_signup_attempt,
)
from backend.services import dashboard_service as _dash_svc
from backend.services import widget_config_service as _widget_svc
from backend.services.referral import apply_referral_attribution

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


# ── Google OAuth helpers + endpoints moved to auth_google.py;
# password reset moved to auth_password_reset.py (2026-06-11, audit H1
# god-file split slices 2+3). Same /api/v1/auth/* URLs.



def _provision_tenant_account(
    *,
    business_name: str,
    owner_name: str,
    email: str,
    password_hash: str,
    industry: str,
    city: str,
    phone: str | None = None,
    website_url: str | None = None,
) -> tuple[str, str]:
    db = get_service_supabase()
    normalized_email = email.lower().strip()

    existing = (
        db.table("tenants")
        .select("id")
        .eq("owner_email", normalized_email)
        .limit(1)
        .execute()
    )
    if existing.data:
        raise HTTPException(status_code=409, detail="Email already registered")

    tenant_data = {
        "business_name": business_name,
        "business_type": industry,
        "owner_email": normalized_email,
        "owner_name": owner_name,
        "password_hash": password_hash,
        "city": city,
        "plan": "free",
        "referral_code": secrets.token_hex(4),  # 8-char unique code for the new tenant
    }
    result = db.table("tenants").insert(tenant_data).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create account")

    tenant_id = str(result.data[0]["id"])

    extra_fields = {}
    if website_url:
        extra_fields["website_url"] = website_url
    if phone:
        extra_fields["notification_phone"] = phone
        extra_fields["sms_notifications_enabled"] = True
    if extra_fields:
        try:
            db.table("tenants").update(extra_fields).eq("id", tenant_id).execute()
        except Exception:
            logger.warning(
                "Failed to save signup fields for new tenant %s",
                tenant_id,
                exc_info=True,
            )

    api_key = f"anx_{secrets.token_urlsafe(32)}"
    widget_defaults = get_widget_defaults(industry, business_name)
    try:
        wc_result = (
            db.table("widget_configs")
            .insert(
                {
                    "tenant_id": tenant_id,
                    "api_key": api_key,
                    "bot_name": widget_defaults["bot_name"],
                    "primary_color": widget_defaults["primary_color"],
                    "greeting_message": widget_defaults["greeting_message"],
                    "position": widget_defaults["position"],
                    "show_watermark": True,
                }
            )
            .execute()
        )
        if not wc_result.data:
            raise RuntimeError("widget_configs insert returned no data")
    except Exception:
        logger.error(
            "Failed to create widget_configs for tenant %s — rolling back",
            tenant_id,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail="Failed to initialize widget configuration"
        )

    _seed_industry_faqs(tenant_id, industry, business_name, city)
    return tenant_id, api_key


async def _run_signup_side_effects(
    *,
    email: str,
    owner_name: str,
    tenant_id: str,
    business_name: str,
    industry: str,
    city: str,
    website_url: str | None = None,
) -> None:
    try:
        await send_email(
            to=email,
            subject="Welcome to AgentNexLiFy!",
            body_html=(
                f"<h2>Welcome to AgentNexLiFy, {owner_name or 'there'}!</h2>"
                "<p>Your AI staff is ready. Ask them to send invoices, follow up "
                "with leads, draft posts, and book appointments &mdash; just by typing.</p>"
                "<p><strong>Try this first:</strong></p>"
                "<ol>"
                "<li>Open the Agent OS and say hi to your AI staff</li>"
                "<li>Ask: &quot;What can you do for my business?&quot;</li>"
                "<li>Optional: add the chat widget to your website to capture leads 24/7</li>"
                "</ol>"
                f"<p><a href='{settings.frontend_url}/dashboard/agent-os' style='background:#6366f1;color:#fff;"
                "padding:10px 20px;border-radius:6px;text-decoration:none;font-weight:600;'>"
                "Meet your AI staff &rarr;</a></p>"
                "<p>&mdash; The AgentNexLiFy Team</p>"
            ),
            tenant_id=tenant_id,
        )
    except Exception:
        logger.warning(
            "Welcome email failed for new tenant %s", tenant_id, exc_info=True
        )

    if website_url:
        try:
            from backend.services.website_crawler import start_crawl

            await start_crawl(tenant_id, website_url)
        except Exception:
            logger.warning(
                "Signup crawl failed for new tenant %s url=%s",
                tenant_id,
                website_url,
                exc_info=True,
            )

    try:
        from backend.services.welcome_thread import create_welcome_thread

        db = get_service_supabase()
        await create_welcome_thread(
            db,
            tenant_id=tenant_id,
            business_name=business_name,
            business_type=industry,
            website_url=website_url,
        )
    except Exception:
        logger.warning(
            "Welcome thread creation failed for new tenant %s",
            tenant_id,
            exc_info=True,
        )


# ── Industry FAQ Seeds ───────────────────────────────────────
# Moved to backend/services/industry_faqs.py
# Re-exported here for backward compatibility with any direct imports.
from backend.services.industry_faqs import (
    _seed_industry_faqs,
)  # noqa: F401

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

    # Referral attribution (?ref=CODE) — never blocks signup, invalid codes ignored.
    apply_referral_attribution(
        get_service_supabase(), new_tenant_id=tenant_id, ref_code=req.ref_code
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


@router.get("/me", response_model=MeResponse)
async def me(claims: dict = Depends(_get_current_tenant)):
    db = get_service_supabase()

    result = (
        db.table("tenants")
        .select(
            "id, owner_email, business_name, plan, city, owner_name, "
            "business_type, referral_code"
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
        referral_code=t.get("referral_code"),
    )


@router.get("/dashboard/{tenant_id}", response_model=DashboardResponse)
async def dashboard(tenant_id: str, claims: dict = Depends(_get_current_tenant)):
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db = get_service_supabase()

    # Tenant row
    tenant_result = (
        db.table("tenants")
        .select(
            "business_name, business_type, plan, plan_status, conversations_used_this_month, monthly_conversation_limit, free_trial_started_at"
        )
        .eq("id", tenant_id)
        .limit(1)
        .execute()
    )
    if not tenant_result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")
    t = tenant_result.data[0]
    logger.info("Dashboard tenant row loaded for %s", tenant_id)

    # Widget config — full details for onboarding
    widget_result = (
        db.table("widget_configs")
        .select(
            "api_key, bot_name, primary_color, greeting_message, position, branding, is_online, offline_message, teaser_message, teaser_delay_seconds, teaser_enabled"
        )
        .eq("tenant_id", tenant_id)
        .limit(1)
        .execute()
    )
    logger.info(
        "Dashboard widget_configs query for tenant_id=%s found=%s",
        tenant_id,
        bool(widget_result.data),
    )

    if widget_result.data:
        w = widget_result.data[0]
        api_key = w["api_key"]
        widget_config = WidgetConfigDetail(
            bot_name=w.get("bot_name", ""),
            primary_color=w.get("primary_color", "#00BFFF"),
            greeting_message=w.get("greeting_message", "Hi! How can I help you today?"),
            position=w.get("position", "bottom-right"),
            branding=w.get("branding") or None,
            is_online=w.get("is_online", True),
            offline_message=w.get("offline_message"),
            teaser_message=w.get("teaser_message"),
            teaser_delay_seconds=w.get("teaser_delay_seconds") or 3,
            teaser_enabled=w.get("teaser_enabled", True),
            enable_ai_fallback=w.get("enable_ai_fallback", False),
            enable_structured_lead_parser=w.get("enable_structured_lead_parser", False),
        )
    else:
        # Auto-create widget_config if missing
        api_key = f"anx_{secrets.token_urlsafe(32)}"
        widget_defaults = get_widget_defaults(
            t.get("business_type"), t.get("business_name")
        )
        logger.info("Dashboard auto-creating widget_config for %s", tenant_id)
        db.table("widget_configs").insert(
            {
                "tenant_id": tenant_id,
                "api_key": api_key,
                "bot_name": widget_defaults["bot_name"],
                "primary_color": widget_defaults["primary_color"],
                "greeting_message": widget_defaults["greeting_message"],
                "position": widget_defaults["position"],
                "show_watermark": True,
            }
        ).execute()
        widget_config = WidgetConfigDetail(
            bot_name=widget_defaults["bot_name"],
            primary_color=widget_defaults["primary_color"],
            greeting_message=widget_defaults["greeting_message"],
            position=widget_defaults["position"],
        )

    # Leads count (live schema uses client_id, not tenant_id)
    try:
        leads_result = (
            db.table("leads")
            .select("id", count="exact")
            .eq("client_id", tenant_id)
            .execute()
        )
        leads_count = leads_result.count or 0
    except Exception:
        logger.warning(
            "Leads count query failed for tenant %s", tenant_id, exc_info=True
        )
        leads_count = 0

    # Hot leads count (live schema: lead_score is 1-10, hot = 8+)
    try:
        hot_result = (
            db.table("leads")
            .select("id", count="exact")
            .eq("client_id", tenant_id)
            .gte("lead_score", 8)
            .execute()
        )
        hot_leads_count = hot_result.count or 0
    except Exception:
        logger.warning(
            "Hot leads count query failed for tenant %s", tenant_id, exc_info=True
        )
        hot_leads_count = 0

    # FAQ count
    try:
        faq_result = (
            db.table("faq_entries")
            .select("id", count="exact")
            .eq("tenant_id", tenant_id)
            .eq("is_active", True)
            .execute()
        )
        faq_count = faq_result.count or 0
    except Exception:
        logger.warning("FAQ count query failed for tenant %s", tenant_id, exc_info=True)
        faq_count = 0

    # Count actual conversations from chat_messages (distinct session_ids).
    # Supabase REST doesn't support COUNT(DISTINCT), so we fetch session_ids
    # and deduplicate in Python.  Limit raised to 5000 to avoid under-counting
    # tenants with many messages per session (88 sessions × ~6 msgs = ~528 rows).
    conversations_used = t.get("conversations_used_this_month") or 0
    try:
        chat_sessions = (
            db.table("chat_messages")
            .select("session_id")
            .eq("tenant_id", tenant_id)
            .limit(5000)
            .execute()
        )
        if chat_sessions.data:
            unique_sessions = len({r["session_id"] for r in chat_sessions.data})
            conversations_used = max(conversations_used, unique_sessions)
    except Exception:
        logger.warning(
            "chat_messages count failed for tenant %s", tenant_id, exc_info=True
        )

    # Missed calls this week
    missed_calls = 0
    try:
        from datetime import datetime, timedelta, timezone as tz

        week_ago = (datetime.now(tz.utc) - timedelta(days=7)).isoformat()
        mc_result = (
            db.table("activity_log")
            .select("id", count="exact")
            .eq("tenant_id", tenant_id)
            .eq("activity_type", "missed_call_textback")
            .gte("created_at", week_ago)
            .execute()
        )
        missed_calls = mc_result.count or 0
    except Exception:
        logger.debug("Missed calls count failed for tenant %s", tenant_id)

    trial = _compute_trial_status(t)
    business_profile = get_dashboard_business_profile(
        t.get("business_type"), t.get("business_name")
    )

    response = DashboardResponse(
        business_name=t.get("business_name") or "",
        business_type=t.get("business_type"),
        plan=t.get("plan") or "free",
        plan_status=t.get("plan_status", "active"),
        conversations_used_this_month=conversations_used,
        monthly_conversation_limit=None,
        widget_api_key=api_key,
        leads_count=leads_count,
        widget_config=widget_config,
        business_profile=business_profile,
        faq_count=faq_count,
        has_conversations=conversations_used > 0,
        hot_leads_count=hot_leads_count,
        trial_days_remaining=trial["trial_days_remaining"],
        trial_expired=trial["trial_expired"],
        missed_calls_this_week=missed_calls,
    )
    logger.info(
        "Dashboard response assembled for %s leads=%s conversations=%s",
        tenant_id,
        leads_count,
        conversations_used,
    )
    return response


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
        "os_auto_send_enabled",
        "os_auto_send_rules",
        "voice_ai_enabled",
    }
    updates = {k: v for k, v in body.items() if k in allowed and v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update")

    # os_auto_send_rules is a JSONB dict of agent_name -> bool; reject any
    # other shape before it reaches the auto-send gate.
    if "os_auto_send_rules" in updates:
        rules = updates["os_auto_send_rules"]
        if (
            not isinstance(rules, dict)
            or len(rules) > 30
            or not all(
                isinstance(k, str) and len(k) <= 50 and isinstance(v, bool)
                for k, v in rules.items()
            )
        ):
            raise HTTPException(
                status_code=422,
                detail="os_auto_send_rules must map agent names to booleans",
            )

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
            "id, business_name, business_type, city, owner_email, owner_name, plan, plan_status, notification_phone, sms_notifications_enabled, google_review_link, review_request_config, website_url, business_slug, business_page_enabled, textback_enabled, textback_message, textback_quiet_start, textback_quiet_end, client_login_enabled, daily_briefing_enabled, noshow_recovery_enabled, os_auto_send_enabled, os_auto_send_rules, voice_ai_enabled"
        )
        .eq("id", tenant_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return result.data[0]


# ── Billing endpoints moved to backend/routers/auth_billing.py (2026-06-11,
# audit H1 god-file split). Same /api/v1/auth/billing/* URLs.


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
