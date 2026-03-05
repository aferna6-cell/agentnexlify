"""Authentication endpoints — register, login, me."""


import logging
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Header
from jose import JWTError, jwt

from backend.config import settings
from backend.models.database import get_supabase
from backend.models.schemas import (
    DashboardResponse,
    FaqCreateRequest,
    FaqEntryResponse,
    LoginRequest,
    LoginResponse,
    MeResponse,
    RegisterRequest,
    RegisterResponse,
    WidgetConfigDetail,
    WidgetConfigUpdateRequest,
)

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


@router.get("/dashboard/{tenant_id}", response_model=DashboardResponse)
async def dashboard(tenant_id: str, claims: dict = Depends(_get_current_tenant)):
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db = get_supabase()

    # Tenant row
    tenant_result = (
        db.table("tenants")
        .select("business_name, plan, plan_status, conversations_used_this_month, monthly_conversation_limit")
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
        .select("api_key, bot_name, primary_color, greeting_message, position")
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

    # Leads count (tenant_id is the correct FK — confirmed from schema)
    try:
        leads_result = (
            db.table("leads")
            .select("id", count="exact")
            .eq("tenant_id", tenant_id)
            .execute()
        )
        leads_count = leads_result.count or 0
    except Exception:
        logger.warning("Leads count query failed for tenant %s", tenant_id, exc_info=True)
        leads_count = 0

    # Hot leads count (score >= 80)
    try:
        hot_result = (
            db.table("leads")
            .select("id", count="exact")
            .eq("tenant_id", tenant_id)
            .gte("lead_score", 80)
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
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
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
