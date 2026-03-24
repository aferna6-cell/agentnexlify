"""Authentication endpoints — register, login, me."""


import logging
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Header, Query, Request
from jose import JWTError, jwt

from backend.config import settings
from backend.limiter import limiter
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
from backend.services.stripe_service import PLAN_PRICES, get_or_create_customer
from backend.services.email_sender import send_email

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
        "exp": datetime.now(timezone.utc) + timedelta(days=_JWT_EXPIRE_DAYS),
    }
    if user_id:
        payload["user_id"] = user_id
    if name:
        payload["name"] = name
    if business_type:
        payload["business_type"] = business_type
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


# ── Industry FAQ Seeds ───────────────────────────────────────

INDUSTRY_FAQS: dict[str, list[dict]] = {
    "plumbing": [
        {"question": "What services do you offer?", "answer": "We offer a full range of plumbing services including drain cleaning, water heater installation and repair, leak detection, pipe repair, sewer line services, faucet and fixture installation, and emergency plumbing.", "category": "Services"},
        {"question": "Do you offer emergency service?", "answer": "Yes, we offer emergency plumbing services. Contact us and we'll get back to you as quickly as possible.", "category": "Services"},
        {"question": "Are you licensed and insured?", "answer": "Yes, we are fully licensed and insured. We carry all required licenses and liability insurance for your protection.", "category": "About"},
        {"question": "What areas do you serve?", "answer": "We serve the local area. Contact us to confirm we can service your location.", "category": "About"},
        {"question": "Do you give free estimates?", "answer": "Yes, we provide free estimates for most plumbing jobs. Contact us to schedule an estimate.", "category": "Pricing"},
    ],
    "dental": [
        {"question": "What services do you offer?", "answer": "We offer comprehensive dental care including cleanings, exams, fillings, crowns, root canals, teeth whitening, Invisalign, dental implants, and emergency dental care.", "category": "Services"},
        {"question": "Do you accept dental insurance?", "answer": "Yes, we accept most major dental insurance plans. Contact us with your insurance information and we'll verify your coverage.", "category": "Insurance"},
        {"question": "Do you see new patients?", "answer": "Yes! We are always welcoming new patients. You can book an appointment through our chat or call us directly.", "category": "About"},
        {"question": "Do you offer emergency dental care?", "answer": "Yes, we offer same-day emergency appointments for dental emergencies like toothaches, broken teeth, or dental trauma.", "category": "Services"},
        {"question": "What is your cancellation policy?", "answer": "We ask for at least 24 hours notice for cancellations. Late cancellations or no-shows may be subject to a fee.", "category": "Policy"},
        {"question": "Do you offer payment plans?", "answer": "Yes, we offer flexible payment plans for major procedures. We also accept CareCredit and other dental financing options.", "category": "Insurance"},
        {"question": "What should I bring to my first visit?", "answer": "Please bring your photo ID, insurance card, a list of current medications, and any dental records or X-rays from your previous dentist.", "category": "About"},
        {"question": "Do you offer cosmetic dentistry?", "answer": "Yes! We offer teeth whitening, veneers, bonding, Invisalign, and other cosmetic procedures to help you achieve your perfect smile.", "category": "Services"},
    ],
    "restaurant": [
        {"question": "What are your hours?", "answer": "Please check our business hours for the most up-to-date schedule. You can also ask us here!", "category": "Hours"},
        {"question": "Do you offer delivery?", "answer": "Please ask us about our current delivery options and delivery area.", "category": "Orders"},
        {"question": "Can I make a reservation?", "answer": "Yes! You can book a table through our chat widget or call us directly.", "category": "Reservations"},
        {"question": "Do you cater events?", "answer": "Yes, we offer catering services for events of all sizes. Contact us for a custom quote.", "category": "Catering"},
        {"question": "Do you accommodate dietary restrictions?", "answer": "Yes! We can accommodate vegetarian, vegan, gluten-free, and allergy-specific requests. Please let us know when ordering or making a reservation.", "category": "Dietary"},
        {"question": "Do you have a private dining room?", "answer": "Please ask us about our private dining and event space options. We'd love to host your special occasion.", "category": "Events"},
    ],
    "realestate": [
        {"question": "What areas do you cover?", "answer": "We serve the local real estate market. Contact us to discuss your specific area of interest.", "category": "Areas"},
        {"question": "Are you a buyer's or seller's agent?", "answer": "We work with both buyers and sellers. Whether you're looking to buy your dream home or sell your property, we can help.", "category": "Services"},
        {"question": "How do I schedule a showing?", "answer": "You can schedule a showing by chatting with us here, calling, or booking an appointment through our scheduling system.", "category": "Showings"},
        {"question": "Do I need to be pre-approved?", "answer": "Getting pre-approved for a mortgage before house hunting is highly recommended. It shows sellers you're a serious buyer and helps you understand your budget.", "category": "Buying"},
        {"question": "How long does it take to buy a house?", "answer": "The typical home buying process takes 30-60 days from accepted offer to closing. Finding the right home can take a few weeks to several months depending on the market.", "category": "Buying"},
        {"question": "What are your commission rates?", "answer": "Our commission structure is competitive and transparent. Contact us for details — we're happy to explain how our fees work.", "category": "Pricing"},
        {"question": "How do you market my property?", "answer": "We use professional photography, virtual tours, MLS listing, social media marketing, and targeted advertising to maximize your property's exposure.", "category": "Selling"},
        {"question": "What's my home worth?", "answer": "We offer free comparative market analyses (CMA) to help you understand your home's current value. Contact us to schedule yours.", "category": "Selling"},
    ],
    "legal": [
        {"question": "What areas of law do you practice?", "answer": "Contact us to learn about our practice areas and how we can help with your legal matter.", "category": "Services"},
        {"question": "Do you offer free consultations?", "answer": "Yes, we offer free initial consultations. Book an appointment to discuss your case.", "category": "Consultations"},
        {"question": "Are consultations confidential?", "answer": "We take your privacy seriously. Please note that this chat is for general inquiries and does not create an attorney-client relationship. Confidential matters should be discussed during a scheduled consultation with our attorney.", "category": "Privacy"},
        {"question": "What should I bring to my consultation?", "answer": "Please bring any relevant documents, contracts, court papers, or correspondence related to your matter. A timeline of events is also helpful.", "category": "Consultations"},
        {"question": "How are your fees structured?", "answer": "We offer various fee arrangements including hourly rates, flat fees, and contingency fees depending on the type of case. We'll discuss fees during your initial consultation.", "category": "Pricing"},
        {"question": "How long will my case take?", "answer": "Every case is different. During your consultation, we can give you a realistic timeline based on the specifics of your situation.", "category": "Process"},
    ],
    "salon": [
        {"question": "What services do you offer?", "answer": "We offer haircuts, coloring, styling, blowouts, treatments, and more. Contact us for our full service menu.", "category": "Services"},
        {"question": "How do I book an appointment?", "answer": "You can book an appointment right here in our chat, call us, or use our online booking system.", "category": "Booking"},
        {"question": "Do you accept walk-ins?", "answer": "We welcome walk-ins based on availability, but we recommend booking an appointment to guarantee your preferred time.", "category": "Booking"},
        {"question": "What is your cancellation policy?", "answer": "We ask for at least 24 hours notice for cancellations. Late cancellations may be subject to a fee.", "category": "Policy"},
        {"question": "How much do haircuts cost?", "answer": "Our pricing varies by service and stylist. Contact us or check our service menu for current prices.", "category": "Pricing"},
        {"question": "Do you do bridal/event styling?", "answer": "Yes! We offer bridal hair, updos, and makeup services for weddings and special events. Book a consultation to discuss your look.", "category": "Services"},
    ],
    "auto_shop": [
        {"question": "What services do you offer?", "answer": "We offer oil changes, brake service, tire rotation, engine diagnostics, transmission repair, AC service, and more.", "category": "Services"},
        {"question": "Do you give free estimates?", "answer": "Yes, we provide free estimates for most repair work. Bring your vehicle in or describe the issue and we'll give you a quote.", "category": "Pricing"},
        {"question": "Do you work on all makes and models?", "answer": "Yes, our certified technicians work on all makes and models of cars, trucks, and SUVs.", "category": "Services"},
        {"question": "How long will my repair take?", "answer": "Repair times vary. Simple services like oil changes take 30-60 minutes. We'll give you an estimated completion time when you drop off your vehicle.", "category": "Process"},
        {"question": "Do you offer a warranty on repairs?", "answer": "Yes, our repairs come with a warranty on parts and labor. Ask us for specific warranty details.", "category": "Warranty"},
    ],
    "medical": [
        {"question": "Are you accepting new patients?", "answer": "Yes, we are currently accepting new patients. Book an appointment to get started.", "category": "About"},
        {"question": "What insurance do you accept?", "answer": "We accept most major insurance plans. Contact us with your insurance information to verify coverage.", "category": "Insurance"},
        {"question": "Do you offer telehealth appointments?", "answer": "Please ask us about our current telehealth options for virtual visits.", "category": "Services"},
        {"question": "What should I bring to my first visit?", "answer": "Please bring your photo ID, insurance card, list of current medications, and any relevant medical records.", "category": "About"},
        {"question": "What is your cancellation policy?", "answer": "We ask for at least 24 hours notice for cancellations. Late cancellations may be subject to a fee.", "category": "Policy"},
    ],
    "fitness": [
        {"question": "What memberships do you offer?", "answer": "We offer a variety of membership options. Contact us to learn about our plans and pricing.", "category": "Memberships"},
        {"question": "Do you offer personal training?", "answer": "Yes! We have certified personal trainers available. Book a consultation to get started.", "category": "Services"},
        {"question": "Do you offer a free trial?", "answer": "Yes, we offer a free trial so you can experience our facility before committing. Ask us to get started!", "category": "Trial"},
        {"question": "What are your hours?", "answer": "Please check our business hours or ask us here. We're open early mornings through late evenings.", "category": "Hours"},
        {"question": "Do you offer group classes?", "answer": "Yes! We offer a variety of group fitness classes including yoga, spin, HIIT, and more. Ask about our class schedule.", "category": "Services"},
    ],
}


def _seed_industry_faqs(tenant_id: str, industry: str, business_name: str, city: str) -> None:
    """Insert starter FAQ entries for the tenant based on their industry."""
    faqs = INDUSTRY_FAQS.get(industry, [])
    if not faqs:
        return
    db = get_supabase()
    rows = []
    for faq in faqs:
        answer = faq["answer"]
        if city:
            answer = answer.replace("the local area", f"the {city} area")
            answer = answer.replace("the local real estate market", f"the {city} real estate market")
        rows.append({
            "tenant_id": tenant_id,
            "question": faq["question"],
            "answer": answer,
            "category": faq.get("category", "General"),
        })
    try:
        db.table("faq_entries").insert(rows).execute()
        logger.info("Seeded %d industry FAQs for tenant %s (industry=%s)", len(rows), tenant_id, industry)
    except Exception:
        logger.warning("Failed to seed industry FAQs for tenant %s", tenant_id, exc_info=True)


# ── Endpoints ────────────────────────────────────────────────


@router.post("/register", response_model=RegisterResponse)
@limiter.limit("5/minute")
async def register(request: Request, req: RegisterRequest):
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

    # Save optional fields provided at signup
    extra_fields = {}
    if req.website_url:
        extra_fields["website_url"] = req.website_url
    if req.phone:
        extra_fields["notification_phone"] = req.phone
        extra_fields["sms_notifications_enabled"] = True
    if extra_fields:
        try:
            db.table("tenants").update(extra_fields).eq("id", tenant_id).execute()
        except Exception:
            logger.warning("Failed to save signup fields for new tenant %s", tenant_id, exc_info=True)

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

    # Auto-generate industry-specific starter FAQs so the AI has baseline knowledge
    _seed_industry_faqs(tenant_id, req.industry, req.business_name, req.city)

    token = _create_token(tenant_id, req.email, "free", req.business_name, business_type=req.industry)

    # Send welcome email — non-blocking, failure must not prevent signup from completing
    try:
        await send_email(
            to=req.email,
            subject="Welcome to AgentNexLiFy!",
            body_html=(
                f"<h2>Welcome to AgentNexLiFy, {req.owner_name or 'there'}!</h2>"
                "<p>Your AI-powered business automation platform is ready to go.</p>"
                "<p><strong>Here's what to do next:</strong></p>"
                "<ol>"
                "<li>Configure your AI assistant with your business info and FAQs</li>"
                "<li>Customize your chat widget's appearance</li>"
                "<li>Embed the widget on your website with one line of code</li>"
                "</ol>"
                "<p>Your AI assistant will start capturing leads and booking appointments automatically.</p>"
                f"<p><a href='https://agentnexlify.vercel.app/dashboard' style='background:#3b82f6;color:#fff;"
                "padding:10px 20px;border-radius:6px;text-decoration:none;font-weight:600;'>"
                "Go to Dashboard &rarr;</a></p>"
                "<p>&mdash; The AgentNexLiFy Team</p>"
            ),
            tenant_id=tenant_id,
        )
    except Exception:
        # Welcome email failure must never block signup
        logger.warning("Welcome email failed for new tenant %s", tenant_id, exc_info=True)

    # Trigger background website crawl if URL was provided — trains AI from minute one
    if req.website_url:
        try:
            from backend.services.website_crawler import start_crawl
            await start_crawl(tenant_id, req.website_url)
        except Exception:
            # Crawl failure must never block signup
            logger.warning("Signup crawl failed for new tenant %s url=%s", tenant_id, req.website_url, exc_info=True)

    return RegisterResponse(tenant_id=tenant_id, api_key=api_key, token=token)


@router.post("/login", response_model=LoginResponse)
@limiter.limit("10/minute")
async def login(request: Request, req: LoginRequest):
    db = get_supabase()
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

    raise HTTPException(status_code=401, detail="Invalid email or password")


@router.get("/me", response_model=MeResponse)
async def me(claims: dict = Depends(_get_current_tenant)):
    db = get_supabase()

    result = (
        db.table("tenants")
        .select("id, owner_email, business_name, plan, city, owner_name, business_type")
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
        .select("api_key, bot_name, primary_color, greeting_message, position, branding, is_online, offline_message")
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
            is_online=w.get("is_online", True),
            offline_message=w.get("offline_message"),
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

    response = DashboardResponse(
        business_name=t.get("business_name") or "",
        plan=t.get("plan") or "free",
        plan_status=t.get("plan_status", "active"),
        conversations_used_this_month=conversations_used,
        monthly_conversation_limit=None,
        widget_api_key=api_key,
        leads_count=leads_count,
        widget_config=widget_config,
        faq_count=faq_count,
        has_conversations=conversations_used > 0,
        hot_leads_count=hot_leads_count,
        trial_days_remaining=trial["trial_days_remaining"],
        trial_expired=trial["trial_expired"],
        missed_calls_this_week=missed_calls,
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
    plan = tenant_result.data[0].get("plan") or "free" if tenant_result.data else "free"

    updates = {k: v for k, v in req.model_dump(exclude={"branding"}).items() if v is not None}

    # Handle branding separately: sanitize CSS + strip plan-disallowed fields
    if req.branding is not None:
        from backend.routers.widget_helpers import _filter_branding_for_plan, _sanitize_css
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
async def list_conversations(
    tenant_id: str,
    channel: str | None = None,
    search: str | None = Query(None, max_length=200),
    claims: dict = Depends(_get_current_tenant),
):
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

    # Try to attach lead names and IDs to sessions
    lead_map = {}
    lead_id_map = {}
    try:
        leads_result = (
            db.table("leads")
            .select("id, conversation_id, name, email")
            .eq("client_id", tenant_id)
            .execute()
        )
        for lead in (leads_result.data or []):
            cid = lead.get("conversation_id")
            if cid:
                lead_map[cid] = lead.get("name") or lead.get("email") or ""
                lead_id_map[cid] = lead["id"]
    except Exception:
        logger.warning("Failed to map lead names to conversations", exc_info=True)

    # Fetch tags and channel from conversations table
    tags_map = {}
    channel_map = {}
    assigned_map = {}
    try:
        conv_query = (
            db.table("conversations")
            .select("session_id, tags, channel, assigned_to")
            .eq("client_id", tenant_id)
        )
        if channel:
            conv_query = conv_query.eq("channel", channel)
        conv_result = conv_query.execute()
        for conv in (conv_result.data or []):
            sid = conv.get("session_id")
            if sid:
                if conv.get("tags"):
                    tags_map[sid] = conv["tags"]
                channel_map[sid] = conv.get("channel") or "widget"
                if conv.get("assigned_to"):
                    assigned_map[sid] = conv["assigned_to"]
    except Exception:
        logger.warning("Failed to fetch conversation metadata", exc_info=True)

    conv_list = sorted(sessions.values(), key=lambda s: s["last_message_at"], reverse=True)

    # Search filter: match against message content, preview, or lead name
    if search:
        search_lower = search.lower()
        # Build a set of session_ids that have matching messages
        matching_sessions = set()
        for msg in (result.data or []):
            if search_lower in (msg.get("content") or "").lower():
                matching_sessions.add(msg["session_id"])
        # Also match on lead names
        for sid, name in lead_map.items():
            if search_lower in (name or "").lower():
                matching_sessions.add(sid)
        conv_list = [c for c in conv_list if c["session_id"] in matching_sessions]

    # If filtering by channel, limit conv_list to sessions that appear in channel_map
    if channel:
        channel_session_ids = set(channel_map.keys())
        conv_list = [c for c in conv_list if c["session_id"] in channel_session_ids]

    for c in conv_list:
        c["lead_name"] = lead_map.get(c["session_id"], "")
        c["lead_id"] = lead_id_map.get(c["session_id"])
        c["tags"] = tags_map.get(c["session_id"], [])
        c["channel"] = channel_map.get(c["session_id"], "widget")
        c["assigned_to"] = assigned_map.get(c["session_id"])

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


@router.put("/conversations/{tenant_id}/{session_id}/tags")
async def update_conversation_tags(
    tenant_id: str,
    session_id: str,
    req: dict,
    claims: dict = Depends(_get_current_tenant),
):
    """Update tags on a conversation. Body: {"tags": ["tag1", "tag2"]}"""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    tags = req.get("tags", [])
    if not isinstance(tags, list):
        raise HTTPException(status_code=400, detail="tags must be a list")
    # Sanitize: strings only, max 30 chars, max 10 tags
    tags = [str(t)[:30] for t in tags if isinstance(t, str)][:10]

    db = get_supabase()

    # Upsert into conversations table (may not have a row yet for this session)
    existing = (
        db.table("conversations")
        .select("id")
        .eq("client_id", tenant_id)
        .eq("session_id", session_id)
        .limit(1)
        .execute()
    )
    if existing.data:
        db.table("conversations").update({"tags": tags}).eq("id", existing.data[0]["id"]).execute()
    else:
        db.table("conversations").insert({
            "client_id": tenant_id,
            "session_id": session_id,
            "tags": tags,
        }).execute()

    return {"session_id": session_id, "tags": tags}


# ── MCP API Keys ──────────────────────────────────────────


@router.post("/mcp-key/{tenant_id}")
async def generate_mcp_key(tenant_id: str, claims: dict = Depends(require_role("owner"))):
    """Generate or regenerate an MCP API key for the tenant."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    import secrets as sec
    mcp_key = f"mcp_{sec.token_urlsafe(32)}"

    db = get_supabase()
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

    db = get_supabase()
    db.table("tenants").update({"mcp_api_key": None, "mcp_enabled": False}).eq("id", tenant_id).execute()
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
    allowed = {"business_name", "business_type", "city", "owner_name", "notification_phone", "sms_notifications_enabled", "google_review_link", "review_request_config", "website_url", "textback_enabled", "textback_message", "textback_quiet_start", "textback_quiet_end"}
    updates = {k: v for k, v in body.items() if k in allowed and v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update")

    db = get_supabase()
    logger.info("update_settings tenant_id=%s updates=%s", tenant_id, updates)
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

    db = get_supabase()
    result = (
        db.table("tenants")
        .select("id, business_name, business_type, city, owner_email, owner_name, plan, plan_status, notification_phone, sms_notifications_enabled, google_review_link, review_request_config, website_url, business_slug, business_page_enabled, textback_enabled, textback_message, textback_quiet_start, textback_quiet_end, client_login_enabled")
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
    result = db.table("tenants").select("id, owner_email, business_name").eq("id", tenant_id).limit(1).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")
    tenant = result.data[0]

    customer = get_or_create_customer(
        email=tenant.get("owner_email") or "",
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
        raise HTTPException(status_code=400, detail=f"Invalid plan. Must be one of: {', '.join(PLAN_PRICES)}")

    db = get_supabase()
    result = db.table("tenants").select("stripe_customer_id, plan").eq("id", tenant_id).limit(1).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")

    tenant = result.data[0]
    customer_id = tenant.get("stripe_customer_id")
    if not customer_id:
        raise HTTPException(status_code=400, detail="No billing account. Subscribe first.")

    current_plan = tenant.get("plan") or "free"
    if current_plan == new_plan:
        raise HTTPException(status_code=400, detail="Already on this plan")

    # Find active subscription
    subs = stripe.Subscription.list(customer=customer_id, status="active", limit=1)
    if not subs.data:
        raise HTTPException(status_code=400, detail="No active subscription found. Use checkout to subscribe.")

    subscription = subs.data[0]
    sub_item_id = subscription["items"]["data"][0]["id"]
    new_price_id = PLAN_PRICES[new_plan]["monthly"]

    # Modify subscription with proration
    updated = stripe.Subscription.modify(
        subscription.id,
        items=[{"id": sub_item_id, "price": new_price_id}],
        proration_behavior="create_prorations",
        metadata={"tenant_id": tenant_id, "plan": new_plan},
    )

    # Update tenant plan immediately (webhook will also fire)
    db.table("tenants").update({"plan": new_plan}).eq("id", tenant_id).execute()

    logger.info("Plan changed for tenant %s: %s -> %s", tenant_id, current_plan, new_plan)
    return {"status": "changed", "old_plan": current_plan, "new_plan": new_plan}


@router.post("/billing/cancel")
async def billing_cancel(
    claims: dict = Depends(require_role("owner")),
):
    """Cancel subscription at end of billing period."""
    tenant_id = claims["tenant_id"]

    db = get_supabase()
    result = db.table("tenants").select("stripe_customer_id, plan").eq("id", tenant_id).limit(1).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")

    tenant = result.data[0]
    customer_id = tenant.get("stripe_customer_id")
    if not customer_id:
        raise HTTPException(status_code=400, detail="No billing account")

    if tenant.get("plan") == "free":
        raise HTTPException(status_code=400, detail="Already on free plan")

    subs = stripe.Subscription.list(customer=customer_id, status="active", limit=1)
    if not subs.data:
        raise HTTPException(status_code=400, detail="No active subscription")

    # Cancel at period end (don't immediately revoke access)
    stripe.Subscription.modify(subs.data[0].id, cancel_at_period_end=True)

    logger.info("Subscription cancellation scheduled for tenant %s", tenant_id)
    return {"status": "cancellation_scheduled", "current_period_end": subs.data[0].current_period_end}


# ── Free Trial ────────────────────────────────────────────────

FREE_TRIAL_DAYS = 14


def _compute_trial_status(tenant: dict) -> dict:
    """Compute trial status for a tenant. Returns dict with trial fields."""
    plan = tenant.get("plan") or "free"
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
        plan=tenant.get("plan") or "free",
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


@router.get("/knowledge-stats/{tenant_id}")
async def get_knowledge_stats(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Return stats about what the AI chatbot knows: FAQs, website pages, feedback corrections."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db = get_supabase()
    stats = {
        "faq_count": 0,
        "website_pages_crawled": 0,
        "website_crawl_status": None,
        "website_url": None,
        "feedback_corrections_count": 0,
        "active_chat_flow": None,
        "menu_items_count": 0,
        "job_postings_count": 0,
    }

    try:
        faq_res = db.table("faq_entries").select("id", count="exact").eq("tenant_id", tenant_id).execute()
        stats["faq_count"] = faq_res.count or 0
    except Exception:
        logger.debug("knowledge-stats: faq query failed", exc_info=True)

    try:
        wc_res = db.table("website_content").select("pages_found, crawl_status").eq("tenant_id", tenant_id).limit(1).execute()
        if wc_res.data:
            stats["website_pages_crawled"] = wc_res.data[0].get("pages_found") or 0
            stats["website_crawl_status"] = wc_res.data[0].get("crawl_status")
    except Exception:
        logger.debug("knowledge-stats: website_content query failed", exc_info=True)

    try:
        tenant_res = db.table("tenants").select("website_url").eq("id", tenant_id).limit(1).execute()
        if tenant_res.data:
            stats["website_url"] = tenant_res.data[0].get("website_url")
    except Exception:
        logger.debug("knowledge-stats: tenant query failed", exc_info=True)

    try:
        fb_res = db.table("ai_feedback").select("id", count="exact").eq("tenant_id", tenant_id).eq("rating", "down").execute()
        stats["feedback_corrections_count"] = fb_res.count or 0
    except Exception:
        logger.debug("knowledge-stats: ai_feedback query failed", exc_info=True)

    try:
        flow_res = db.table("chat_flows").select("name").eq("tenant_id", tenant_id).eq("is_active", True).limit(1).execute()
        if flow_res.data:
            stats["active_chat_flow"] = flow_res.data[0].get("name")
    except Exception:
        logger.debug("knowledge-stats: chat_flows query failed", exc_info=True)

    try:
        menu_res = db.table("menu_items").select("id", count="exact").eq("tenant_id", tenant_id).execute()
        stats["menu_items_count"] = menu_res.count or 0
    except Exception:
        logger.debug("knowledge-stats: menu query failed", exc_info=True)

    try:
        jobs_res = db.table("jobs").select("id", count="exact").eq("tenant_id", tenant_id).eq("is_active", True).execute()
        stats["job_postings_count"] = jobs_res.count or 0
    except Exception:
        logger.debug("knowledge-stats: jobs query failed", exc_info=True)

    return stats
