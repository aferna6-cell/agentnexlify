"""Authentication endpoints — register, login, me."""


import logging
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from jose import JWTError, jwt

from backend.config import settings
from backend.models.database import get_supabase
import stripe

from backend.models.schemas import (
    DashboardResponse,
    FaqCreateRequest,
    FaqEntryResponse,
    LoginRequest,
    LoginResponse,
    MeResponse,
    RegisterRequest,
    RegisterResponse,
    TrialStatusResponse,
    WidgetConfigDetail,
    WidgetConfigUpdateRequest,
)
from backend.services.stripe_service import PLAN_LIMITS, PLAN_PRICES, get_or_create_customer

logger = logging.getLogger(__name__)

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
    user_id: str | None = None,
    role: str = "owner",
    is_team_member: bool = False,
    name: str | None = None,
) -> str:
    payload = {
        "tenant_id": tenant_id,
        "sub": tenant_id,
        "email": email,
        "plan": plan,
        "business_name": business_name,
        "role": role,
        "is_team_member": is_team_member,
        "exp": datetime.now(timezone.utc) + timedelta(days=_JWT_EXPIRE_DAYS),
    }
    if user_id:
        payload["user_id"] = user_id
    if name:
        payload["name"] = name
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


def require_role(*allowed_roles):
    """FastAPI dependency factory: restrict endpoint to specific roles."""
    def checker(claims: dict = Depends(_get_current_tenant)):
        role = claims.get("role", "owner")
        if role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return claims
    return checker


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
        "free_trial_started_at": datetime.now(timezone.utc).isoformat(),
    }
    result = db.table("tenants").insert(tenant_data).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create account")

    tenant = result.data[0]
    tenant_id = str(tenant["id"])

    # Create widget config with prefixed api_key and defaults
    api_key = f"anx_{secrets.token_urlsafe(32)}"
    db.table("widget_configs").insert({
        "tenant_id": tenant_id,
        "api_key": api_key,
        "bot_name": f"{req.business_name} Assistant",
        "primary_color": "#00BFFF",
        "greeting_message": "Hi! How can I help you today?",
        "position": "bottom-right",
        "show_watermark": True,
    }).execute()

    token = _create_token(tenant_id, req.email, "free", req.business_name)

    return RegisterResponse(tenant_id=tenant_id, api_key=api_key, token=token)


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    db = get_supabase()
    email = req.email.lower().strip()

    # 1. Check tenants table (owner login)
    result = (
        db.table("tenants")
        .select("id, password_hash, business_name, plan")
        .eq("owner_email", email)
        .limit(1)
        .execute()
    )
    if result.data:
        tenant = result.data[0]
        if not tenant.get("password_hash"):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        if not _verify_password(req.password, tenant["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        tenant_id = str(tenant["id"])
        token = _create_token(
            tenant_id,
            email,
            tenant.get("plan", "free"),
            tenant.get("business_name", ""),
        )
        return LoginResponse(
            tenant_id=tenant_id,
            token=token,
            business_name=tenant.get("business_name", ""),
            plan=tenant.get("plan", "free"),
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
            raise HTTPException(status_code=401, detail="Invalid email or password")
        if not _verify_password(req.password, member["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        # Fetch tenant info
        tenant_result = (
            db.table("tenants")
            .select("business_name, plan")
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
            plan=t.get("plan", "free"),
            business_name=t.get("business_name", ""),
            user_id=str(member["id"]),
            role=member["role"],
            is_team_member=True,
            name=member.get("name"),
        )
        return LoginResponse(
            tenant_id=tenant_id,
            token=token,
            business_name=t.get("business_name", ""),
            plan=t.get("plan", "free"),
        )

    raise HTTPException(status_code=401, detail="Invalid email or password")


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


@router.get("/dashboard/{tenant_id}", response_model=DashboardResponse)
async def dashboard(tenant_id: str, claims: dict = Depends(_get_current_tenant)):
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db = get_supabase()

    # Tenant row
    tenant_result = (
        db.table("tenants")
        .select("business_name, plan, plan_status, conversations_used_this_month, monthly_conversation_limit, free_trial_started_at")
        .eq("id", tenant_id)
        .limit(1)
        .execute()
    )
    if not tenant_result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")
    t = tenant_result.data[0]
    logger.info("Dashboard tenant row for %s: %s", tenant_id, t)

    # Widget config — full details for onboarding
    widget_result = (
        db.table("widget_configs")
        .select("api_key, bot_name, primary_color, greeting_message, position, branding")
        .eq("tenant_id", tenant_id)
        .limit(1)
        .execute()
    )
    logger.info("Dashboard widget_configs query for tenant_id=%s: data=%s", tenant_id, widget_result.data)

    if widget_result.data:
        w = widget_result.data[0]
        api_key = w["api_key"]
        widget_config = WidgetConfigDetail(
            bot_name=w.get("bot_name", ""),
            primary_color=w.get("primary_color", "#00BFFF"),
            greeting_message=w.get("greeting_message", "Hi! How can I help you today?"),
            position=w.get("position", "bottom-right"),
            branding=w.get("branding") or None,
        )
    else:
        # Auto-create widget_config if missing
        api_key = f"anx_{secrets.token_urlsafe(32)}"
        logger.info("Dashboard auto-creating widget_config for %s with api_key=%s", tenant_id, api_key)
        db.table("widget_configs").insert({
            "tenant_id": tenant_id,
            "api_key": api_key,
            "bot_name": f"{t.get('business_name', 'AI')} Assistant",
            "primary_color": "#00BFFF",
            "greeting_message": "Hi! How can I help you today?",
            "position": "bottom-right",
            "show_watermark": True,
        }).execute()
        widget_config = WidgetConfigDetail(
            bot_name=f"{t.get('business_name', 'AI')} Assistant",
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
        logger.warning("Leads count query failed for tenant %s", tenant_id, exc_info=True)
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
        logger.warning("Hot leads count query failed for tenant %s", tenant_id, exc_info=True)
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
    # and deduplicate in Python.  Limit to 500 rows for safety.
    conversations_used = t.get("conversations_used_this_month", 0)
    try:
        chat_sessions = (
            db.table("chat_messages")
            .select("session_id")
            .eq("tenant_id", tenant_id)
            .limit(500)
            .execute()
        )
        if chat_sessions.data:
            unique_sessions = len({r["session_id"] for r in chat_sessions.data})
            conversations_used = max(conversations_used, unique_sessions)
    except Exception:
        logger.debug("chat_messages count failed for tenant %s", tenant_id)

    trial = _compute_trial_status(t)

    response = DashboardResponse(
        business_name=t.get("business_name", ""),
        plan=t.get("plan", "free"),
        plan_status=t.get("plan_status", "active"),
        conversations_used_this_month=conversations_used,
        monthly_conversation_limit=t.get("monthly_conversation_limit", 50),
        widget_api_key=api_key,
        leads_count=leads_count,
        widget_config=widget_config,
        faq_count=faq_count,
        has_conversations=conversations_used > 0,
        hot_leads_count=hot_leads_count,
        trial_days_remaining=trial["trial_days_remaining"],
        trial_expired=trial["trial_expired"],
    )
    logger.info("Dashboard response for %s: %s", tenant_id, response.model_dump())
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

    db = get_supabase()

    # Get tenant plan for branding filtering
    tenant_result = db.table("tenants").select("plan").eq("id", tenant_id).limit(1).execute()
    plan = tenant_result.data[0].get("plan", "free") if tenant_result.data else "free"

    updates = {k: v for k, v in req.model_dump(exclude={"branding"}).items() if v is not None}

    # Handle branding separately: sanitize CSS + strip plan-disallowed fields
    if req.branding is not None:
        from backend.routers.widget import _filter_branding_for_plan, _sanitize_css
        branding_dict = req.branding.model_dump(exclude_none=True)
        if "custom_css" in branding_dict:
            branding_dict["custom_css"] = _sanitize_css(branding_dict["custom_css"])
        branding_dict = _filter_branding_for_plan(branding_dict, plan)
        # Merge with existing branding to avoid overwriting other fields
        existing = db.table("widget_configs").select("branding").eq("tenant_id", tenant_id).limit(1).execute()
        existing_branding = (existing.data[0].get("branding") or {}) if existing.data else {}
        existing_branding.update(branding_dict)
        updates["branding"] = existing_branding

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    result = (
        db.table("widget_configs")
        .update(updates)
        .eq("tenant_id", tenant_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Widget config not found")

    w = result.data[0]
    return WidgetConfigDetail(
        bot_name=w.get("bot_name", ""),
        primary_color=w.get("primary_color", "#00BFFF"),
        greeting_message=w.get("greeting_message", ""),
        position=w.get("position", "bottom-right"),
        branding=w.get("branding") or None,
    )


# ── FAQ CRUD ─────────────────────────────────────────────────


@router.get("/faq/{tenant_id}", response_model=list[FaqEntryResponse])
async def list_faq(tenant_id: str, claims: dict = Depends(_get_current_tenant)):
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db = get_supabase()
    result = (
        db.table("faq_entries")
        .select("id, question, answer, category, is_active")
        .eq("tenant_id", tenant_id)
        .eq("is_active", True)
        .order("created_at", desc=False)
        .execute()
    )
    return [FaqEntryResponse(**row) for row in (result.data or [])]


@router.post("/faq/{tenant_id}", response_model=FaqEntryResponse, status_code=201)
async def create_faq(
    tenant_id: str,
    req: FaqCreateRequest,
    claims: dict = Depends(_get_current_tenant),
):
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db = get_supabase()
    result = (
        db.table("faq_entries")
        .insert({
            "tenant_id": tenant_id,
            "question": req.question,
            "answer": req.answer,
            "category": req.category,
            "is_active": True,
        })
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create FAQ entry")

    row = result.data[0]
    return FaqEntryResponse(
        id=str(row["id"]),
        question=row["question"],
        answer=row["answer"],
        category=row.get("category"),
        is_active=row.get("is_active", True),
    )


@router.delete("/faq/{tenant_id}/{faq_id}", status_code=204)
async def delete_faq(
    tenant_id: str,
    faq_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db = get_supabase()
    # Soft delete — mark inactive
    db.table("faq_entries").update({"is_active": False}).eq("id", faq_id).eq("tenant_id", tenant_id).execute()


# ── Conversations ────────────────────────────────────────────


@router.get("/conversations/{tenant_id}")
async def list_conversations(tenant_id: str, claims: dict = Depends(_get_current_tenant)):
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db = get_supabase()
    # Fetch recent chat messages grouped by session
    result = (
        db.table("chat_messages")
        .select("session_id, role, content, created_at")
        .eq("tenant_id", tenant_id)
        .order("created_at", desc=True)
        .limit(500)
        .execute()
    )

    sessions: dict = {}
    for msg in (result.data or []):
        sid = msg["session_id"]
        if sid not in sessions:
            sessions[sid] = {
                "session_id": sid,
                "message_count": 0,
                "last_message": "",
                "last_message_at": msg["created_at"],
                "preview": "",
            }
        sessions[sid]["message_count"] += 1
        # First user message as preview
        if msg["role"] == "user" and not sessions[sid]["preview"]:
            sessions[sid]["preview"] = (msg["content"] or "")[:120]
        # Last message content
        if msg["created_at"] >= sessions[sid]["last_message_at"]:
            sessions[sid]["last_message_at"] = msg["created_at"]
            sessions[sid]["last_message"] = (msg["content"] or "")[:120]

    # Try to attach lead names to sessions
    lead_map = {}
    try:
        leads_result = (
            db.table("leads")
            .select("conversation_id, name, email")
            .eq("client_id", tenant_id)
            .execute()
        )
        for lead in (leads_result.data or []):
            cid = lead.get("conversation_id")
            if cid:
                lead_map[cid] = lead.get("name") or lead.get("email") or ""
    except Exception:
        pass

    conv_list = sorted(sessions.values(), key=lambda s: s["last_message_at"], reverse=True)
    for c in conv_list:
        c["lead_name"] = lead_map.get(c["session_id"], "")

    return {"conversations": conv_list}


@router.get("/conversations/{tenant_id}/{session_id}")
async def get_conversation_messages(
    tenant_id: str,
    session_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db = get_supabase()
    result = (
        db.table("chat_messages")
        .select("id, role, content, created_at")
        .eq("tenant_id", tenant_id)
        .eq("session_id", session_id)
        .order("created_at", desc=False)
        .execute()
    )
    return {"messages": result.data or []}


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
    allowed = {"business_name", "business_type", "city", "owner_name", "notification_phone", "sms_notifications_enabled", "google_review_link"}
    updates = {k: v for k, v in body.items() if k in allowed and v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update")

    db = get_supabase()
    logger.info("update_settings tenant_id=%s updates=%s", tenant_id, updates)
    try:
        result = db.table("tenants").update(updates).eq("id", tenant_id).execute()
    except Exception as e:
        logger.exception("update_settings failed for tenant_id=%s", tenant_id)
        raise HTTPException(status_code=500, detail=str(e))
    if not result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return result.data[0]


@router.get("/tenant/{tenant_id}")
async def get_tenant(tenant_id: str, claims: dict = Depends(_get_current_tenant)):
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db = get_supabase()
    result = (
        db.table("tenants")
        .select("id, business_name, business_type, city, owner_email, owner_name, plan, plan_status, notification_phone, sms_notifications_enabled, google_review_link")
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
        raise HTTPException(status_code=400, detail=f"Invalid plan. Must be one of: {', '.join(PLAN_PRICES)}")

    db = get_supabase()
    result = db.table("tenants").select("*").eq("id", tenant_id).limit(1).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")
    tenant = result.data[0]

    customer = get_or_create_customer(
        email=tenant.get("owner_email", ""),
        tenant_id=tenant_id,
        business_name=tenant.get("business_name"),
    )

    prices = PLAN_PRICES[plan]
    line_items = []
    if "setup" in prices:
        line_items.append({"price": prices["setup"], "quantity": 1})
    line_items.append({"price": prices["monthly"], "quantity": 1})

    session_params: dict = {
        "mode": "subscription",
        "customer": customer.id,
        "line_items": line_items,
        "success_url": f"{settings.frontend_url}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
        "cancel_url": f"{settings.frontend_url}/billing/cancel",
        "metadata": {"tenant_id": tenant_id, "plan": plan},
        "subscription_data": {"metadata": {"tenant_id": tenant_id, "plan": plan}},
    }

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

    db = get_supabase()
    result = db.table("tenants").select("stripe_customer_id").eq("id", tenant_id).limit(1).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")

    customer_id = result.data[0].get("stripe_customer_id")
    if not customer_id:
        raise HTTPException(status_code=400, detail="No billing account. Upgrade to a paid plan first.")

    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=f"{settings.frontend_url}/billing",
    )
    return {"portal_url": session.url}


# ── Free Trial ────────────────────────────────────────────────

FREE_TRIAL_DAYS = 30


def _compute_trial_status(tenant: dict) -> dict:
    """Compute trial status for a tenant. Returns dict with trial fields."""
    plan = tenant.get("plan", "free")
    if plan != "free":
        return {"trial_days_remaining": None, "trial_expired": False}

    trial_started = tenant.get("free_trial_started_at")
    if not trial_started:
        # Legacy tenant without trial start — not expired (grandfather)
        return {"trial_days_remaining": None, "trial_expired": False}

    from datetime import datetime, timezone
    if isinstance(trial_started, str):
        # Parse ISO format
        trial_started = datetime.fromisoformat(trial_started.replace("Z", "+00:00"))
    if trial_started.tzinfo is None:
        trial_started = trial_started.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    elapsed = (now - trial_started).days
    remaining = max(0, FREE_TRIAL_DAYS - elapsed)
    expired = remaining <= 0

    return {"trial_days_remaining": remaining, "trial_expired": expired}


@router.get("/trial-status/{tenant_id}", response_model=TrialStatusResponse)
async def trial_status(tenant_id: str, claims: dict = Depends(_get_current_tenant)):
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db = get_supabase()
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

    # Compute expiry date
    trial_expires = None
    if trial_started:
        from datetime import datetime, timezone, timedelta
        if isinstance(trial_started, str):
            ts = datetime.fromisoformat(trial_started.replace("Z", "+00:00"))
        else:
            ts = trial_started
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        trial_expires = (ts + timedelta(days=FREE_TRIAL_DAYS)).isoformat()

    return TrialStatusResponse(
        plan=tenant.get("plan", "free"),
        trial_started=trial_started if isinstance(trial_started, str) else (trial_started.isoformat() if trial_started else None),
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

    db = get_supabase()
    items: list[dict] = []

    # 1. Try activity_log table first
    try:
        result = (
            db.table("activity_log")
            .select("id, activity_type, description, lead_id, metadata, created_at")
            .eq("tenant_id", tenant_id)
            .order("created_at", desc=True)
            .limit(20)
            .execute()
        )
        if result.data:
            for row in result.data:
                items.append({
                    "id": row["id"],
                    "type": row["activity_type"],
                    "message": row["description"],
                    "created_at": row["created_at"],
                })
    except Exception:
        logger.debug("activity_log query failed, falling back to other tables", exc_info=True)

    # 2. If activity_log is empty, synthesize from other tables
    if not items:
        # Recent leads
        try:
            leads_result = (
                db.table("leads")
                .select("id, name, email, created_at")
                .eq("client_id", tenant_id)
                .order("created_at", desc=True)
                .limit(5)
                .execute()
            )
            for row in (leads_result.data or []):
                name = row.get("name") or row.get("email") or "Unknown"
                items.append({
                    "id": f"lead_{row['id']}",
                    "type": "new_lead",
                    "message": f"New lead captured: {name}",
                    "created_at": row["created_at"],
                })
        except Exception:
            logger.debug("leads fallback query failed", exc_info=True)

        # Recent chat sessions (distinct sessions)
        try:
            chats_result = (
                db.table("chat_messages")
                .select("session_id, created_at")
                .eq("tenant_id", tenant_id)
                .eq("role", "user")
                .order("created_at", desc=True)
                .limit(20)
                .execute()
            )
            seen_sessions: set[str] = set()
            for row in (chats_result.data or []):
                sid = row["session_id"]
                if sid not in seen_sessions and len(seen_sessions) < 5:
                    seen_sessions.add(sid)
                    items.append({
                        "id": f"chat_{sid}",
                        "type": "conversation_summary",
                        "message": f"New conversation: {sid[:12]}...",
                        "created_at": row["created_at"],
                    })
        except Exception:
            logger.debug("chat_messages fallback query failed", exc_info=True)

        # Recent appointments
        try:
            appt_result = (
                db.table("appointments")
                .select("id, customer_name, start_time, created_at")
                .eq("tenant_id", tenant_id)
                .order("created_at", desc=True)
                .limit(5)
                .execute()
            )
            for row in (appt_result.data or []):
                name = row.get("customer_name") or "Customer"
                items.append({
                    "id": f"appt_{row['id']}",
                    "type": "appointment",
                    "message": f"Appointment booked: {name}",
                    "created_at": row["created_at"],
                })
        except Exception:
            logger.debug("appointments fallback query failed", exc_info=True)

        # Sort combined results by created_at descending
        items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        items = items[:20]

    return {"activity": items}
