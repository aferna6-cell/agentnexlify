"""Branding, widget-config, FAQ, and conversation management services.

Extracted from backend/routers/auth.py (was 1,918 LOC) to isolate non-auth
concerns: industry FAQ seeding, widget config updates, FAQ CRUD, and
conversation list/detail logic.

Auth routes in auth.py delegate to these functions — import paths for callers
that used to reach these symbols via auth.py are unchanged (auth.py re-exports
INDUSTRY_FAQS and _seed_industry_faqs for backward compat).
"""

import logging
from typing import Any

from fastapi import HTTPException

from backend.models.database import get_service_supabase as _get_service_supabase
from backend.services.business_profiles import resolve_business_profile_key

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_db():
    return _get_service_supabase()


# ---------------------------------------------------------------------------
# Industry FAQ seeding — runs once during tenant provisioning
# ---------------------------------------------------------------------------

INDUSTRY_FAQS: dict[str, list[dict]] = {
    "hvac": [
        {"question": "What HVAC services do you offer?", "answer": "We help with AC repair, heating service, tune-ups, indoor air quality, thermostat upgrades, system replacements, and emergency HVAC support.", "category": "Services"},
        {"question": "Do you offer emergency HVAC service?", "answer": "Yes, we handle urgent heating and cooling issues. Contact us with your issue and we'll respond as quickly as possible.", "category": "Services"},
        {"question": "Do you service both heating and air conditioning systems?", "answer": "Yes, we work on both heating and cooling equipment, including furnaces, heat pumps, central AC systems, and more.", "category": "Services"},
        {"question": "Do you provide estimates for new systems?", "answer": "Yes, we can provide an estimate for repairs, replacements, or a new HVAC system based on your needs and property.", "category": "Pricing"},
        {"question": "What areas do you serve?", "answer": "We serve the local area. Contact us to confirm we can service your location.", "category": "About"},
    ],
    "plumbing": [
        {"question": "What services do you offer?", "answer": "We offer a full range of plumbing services including drain cleaning, water heater installation and repair, leak detection, pipe repair, sewer line services, faucet and fixture installation, and emergency plumbing.", "category": "Services"},
        {"question": "Do you offer emergency service?", "answer": "Yes, we offer emergency plumbing services. Contact us and we'll get back to you as quickly as possible.", "category": "Services"},
        {"question": "Are you licensed and insured?", "answer": "Yes, we are fully licensed and insured. We carry all required licenses and liability insurance for your protection.", "category": "About"},
        {"question": "What areas do you serve?", "answer": "We serve the local area. Contact us to confirm we can service your location.", "category": "About"},
        {"question": "Do you give free estimates?", "answer": "Yes, we provide free estimates for most plumbing jobs. Contact us to schedule an estimate.", "category": "Pricing"},
    ],
    "home_services": [
        {"question": "What services do you offer?", "answer": "We help with repairs, replacements, installations, inspections, and estimate requests for your home or property. If you're not sure what category your project fits into, send us a quick message and we'll point you in the right direction.", "category": "Services"},
        {"question": "Do you provide free estimates?", "answer": "Yes, we offer free estimates for most projects. For larger jobs, we may schedule an in-person visit so we can give you the most accurate quote possible.", "category": "Pricing"},
        {"question": "Are you licensed and insured?", "answer": "Yes, we are licensed and insured. If you need license or insurance details for a permit, HOA, or property manager, we can provide them on request.", "category": "About"},
        {"question": "How soon can you get here?", "answer": "It depends on the job and our current schedule, but we always try to handle urgent repairs as quickly as possible. If it's an emergency, tell us what is happening and we'll do our best to prioritize it.", "category": "Services"},
        {"question": "What should I send before the estimate?", "answer": "Photos of the issue or project area, your address, a short description of the work, and your ideal timeline are the most helpful details. The more we know up front, the faster we can quote it.", "category": "Pricing"},
        {"question": "Do you stand behind your work?", "answer": "Yes. We want every customer to feel confident in the work we do, and we can explain warranty coverage for labor and parts before the job starts.", "category": "Policy"},
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


def seed_industry_faqs(tenant_id: str, industry: str, business_name: str, city: str) -> None:
    """Insert starter FAQ entries for a new tenant based on their industry."""
    raw_industry = (industry or "").strip().lower()
    normalized = resolve_business_profile_key(industry)
    faq_key = {
        "home_services": "home_services",
        "contractor": "home_services",
        "contractors": "home_services",
        "general_contractor": "home_services",
        "plumbing": "plumbing",
        "hvac": "hvac",
        "real_estate": "realestate",
    }.get(raw_industry, normalized)
    faqs = INDUSTRY_FAQS.get(faq_key, [])
    if not faqs:
        return
    db = _get_db()
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


# Backward-compat alias — auth.py provisioning code calls _seed_industry_faqs
_seed_industry_faqs = seed_industry_faqs


# ---------------------------------------------------------------------------
# Widget config service
# ---------------------------------------------------------------------------

def update_widget_config_service(
    tenant_id: str,
    req: Any,  # WidgetConfigUpdateRequest — avoid circular import
) -> dict:
    """Update widget_configs row and return the updated row dict."""
    from backend.services.branding_helpers import _filter_branding_for_plan, _sanitize_css

    db = _get_db()

    # Fetch tenant plan for branding field filtering
    tenant_result = db.table("tenants").select("plan").eq("id", tenant_id).limit(1).execute()
    plan = tenant_result.data[0].get("plan") or "free" if tenant_result.data else "free"

    updates = {k: v for k, v in req.model_dump(exclude={"branding"}).items() if v is not None}

    # Handle branding separately: sanitize CSS + strip plan-disallowed fields
    if req.branding is not None:
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

    return result.data[0]


# ---------------------------------------------------------------------------
# FAQ CRUD service
# ---------------------------------------------------------------------------

def list_faqs(tenant_id: str) -> list[dict]:
    """Return active FAQ entries for a tenant."""
    db = _get_db()
    result = (
        db.table("faq_entries")
        .select("id, question, answer, category, is_active")
        .eq("tenant_id", tenant_id)
        .eq("is_active", True)
        .order("created_at", desc=False)
        .execute()
    )
    return result.data or []


def create_faq(tenant_id: str, question: str, answer: str, category: str | None) -> dict:
    """Insert a new FAQ entry. Returns the created row."""
    db = _get_db()
    result = (
        db.table("faq_entries")
        .insert({
            "tenant_id": tenant_id,
            "question": question,
            "answer": answer,
            "category": category,
            "is_active": True,
        })
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create FAQ entry")
    return result.data[0]


def update_faq(tenant_id: str, faq_id: str, question: str, answer: str, category: str | None) -> dict:
    """Update an existing FAQ entry. Returns updated row or raises 404."""
    db = _get_db()
    update_data: dict = {"question": question, "answer": answer}
    if category is not None:
        update_data["category"] = category
    result = (
        db.table("faq_entries")
        .update(update_data)
        .eq("id", faq_id)
        .eq("tenant_id", tenant_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="FAQ entry not found")
    return result.data[0]


def delete_faq(tenant_id: str, faq_id: str) -> None:
    """Soft-delete a FAQ entry (sets is_active=False)."""
    db = _get_db()
    db.table("faq_entries").update({"is_active": False}).eq("id", faq_id).eq("tenant_id", tenant_id).execute()


# ---------------------------------------------------------------------------
# Conversation list/detail service
# ---------------------------------------------------------------------------

def list_conversations(
    tenant_id: str,
    channel: str | None = None,
    search: str | None = None,
) -> dict:
    """Return paginated conversation list with lead name enrichment."""
    db = _get_db()
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
        if msg["role"] == "user" and not sessions[sid]["preview"]:
            sessions[sid]["preview"] = (msg["content"] or "")[:120]
        if msg["created_at"] >= sessions[sid]["last_message_at"]:
            sessions[sid]["last_message_at"] = msg["created_at"]
            sessions[sid]["last_message"] = (msg["content"] or "")[:120]

    # Attach lead names + IDs
    lead_map: dict = {}
    lead_id_map: dict = {}
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
        logger.warning("Failed to map lead names to conversations for tenant %s", tenant_id, exc_info=True)

    # Fetch tags + channel from conversations table (uses client_id per schema rules)
    tags_map: dict = {}
    channel_map: dict = {}
    assigned_map: dict = {}
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
        logger.warning("Failed to fetch conversation metadata for tenant %s", tenant_id, exc_info=True)

    conv_list = sorted(sessions.values(), key=lambda s: s["last_message_at"], reverse=True)

    if search:
        search_lower = search.lower()
        matching_sessions: set = set()
        for msg in (result.data or []):
            if search_lower in (msg.get("content") or "").lower():
                matching_sessions.add(msg["session_id"])
        for sid, name in lead_map.items():
            if search_lower in (name or "").lower():
                matching_sessions.add(sid)
        conv_list = [c for c in conv_list if c["session_id"] in matching_sessions]

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


def get_conversation_messages(tenant_id: str, session_id: str) -> dict:
    """Return messages for a single conversation session."""
    db = _get_db()
    result = (
        db.table("chat_messages")
        .select("id, role, content, created_at")
        .eq("tenant_id", tenant_id)
        .eq("session_id", session_id)
        .order("created_at", desc=False)
        .execute()
    )
    return {"messages": result.data or []}


# ---------------------------------------------------------------------------
# Trial status helper (used by dashboard + trial-status endpoint)
# ---------------------------------------------------------------------------

FREE_TRIAL_DAYS = 7


def compute_trial_status(tenant: dict) -> dict:
    """Return trial_days_remaining + trial_expired for a tenant row."""
    return {"trial_days_remaining": None, "trial_expired": False}


# Backward-compat alias used in dashboard handler
_compute_trial_status = compute_trial_status


# ---------------------------------------------------------------------------
# Activity feed
# ---------------------------------------------------------------------------

def get_activity(tenant_id: str) -> dict:
    """Return recent activity for the dashboard activity feed (uses client_id for leads)."""
    db = _get_db()
    items: list[dict] = []

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
        logger.debug("activity_log query failed, falling back for tenant %s", tenant_id, exc_info=True)

    if not items:
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
            logger.debug("leads fallback query failed for tenant %s", tenant_id, exc_info=True)

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
            logger.debug("chat_messages fallback query failed for tenant %s", tenant_id, exc_info=True)

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
            logger.debug("appointments fallback query failed for tenant %s", tenant_id, exc_info=True)

        items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        items = items[:20]

    return {"activity": items}


# ---------------------------------------------------------------------------
# Knowledge stats
# ---------------------------------------------------------------------------

def get_knowledge_stats(tenant_id: str) -> dict:
    """Return stats about what the AI chatbot knows (FAQs, pages, corrections, etc.)."""
    db = _get_db()
    stats: dict = {
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
        logger.debug("knowledge-stats: faq query failed for tenant %s", tenant_id, exc_info=True)

    try:
        wc_res = db.table("website_content").select("pages_found, crawl_status").eq("tenant_id", tenant_id).limit(1).execute()
        if wc_res.data:
            stats["website_pages_crawled"] = wc_res.data[0].get("pages_found") or 0
            stats["website_crawl_status"] = wc_res.data[0].get("crawl_status")
    except Exception:
        logger.debug("knowledge-stats: website_content query failed for tenant %s", tenant_id, exc_info=True)

    try:
        tenant_res = db.table("tenants").select("website_url").eq("id", tenant_id).limit(1).execute()
        if tenant_res.data:
            stats["website_url"] = tenant_res.data[0].get("website_url")
    except Exception:
        logger.debug("knowledge-stats: tenant query failed for tenant %s", tenant_id, exc_info=True)

    try:
        fb_res = db.table("ai_feedback").select("id", count="exact").eq("tenant_id", tenant_id).eq("rating", "down").execute()
        stats["feedback_corrections_count"] = fb_res.count or 0
    except Exception:
        logger.debug("knowledge-stats: ai_feedback query failed for tenant %s", tenant_id, exc_info=True)

    try:
        flow_res = db.table("chat_flows").select("name").eq("tenant_id", tenant_id).eq("is_active", True).limit(1).execute()
        if flow_res.data:
            stats["active_chat_flow"] = flow_res.data[0].get("name")
    except Exception:
        logger.debug("knowledge-stats: chat_flows query failed for tenant %s", tenant_id, exc_info=True)

    try:
        menu_res = db.table("menu_items").select("id", count="exact").eq("tenant_id", tenant_id).execute()
        stats["menu_items_count"] = menu_res.count or 0
    except Exception:
        logger.debug("knowledge-stats: menu query failed for tenant %s", tenant_id, exc_info=True)

    try:
        jobs_res = db.table("jobs").select("id", count="exact").eq("tenant_id", tenant_id).eq("is_active", True).execute()
        stats["job_postings_count"] = jobs_res.count or 0
    except Exception:
        logger.debug("knowledge-stats: jobs query failed for tenant %s", tenant_id, exc_info=True)

    return stats


# ---------------------------------------------------------------------------
# Conversation tag upsert (defined after the section above for clarity)
# ---------------------------------------------------------------------------

def update_conversation_tags(tenant_id: str, session_id: str, tags: list) -> dict:
    """Upsert tags on a conversation row. Uses client_id (conversations table rule)."""
    if not isinstance(tags, list):
        raise HTTPException(status_code=400, detail="tags must be a list")
    # Sanitize: strings only, max 30 chars, max 10 tags
    tags = [str(t)[:30] for t in tags if isinstance(t, str)][:10]

    db = _get_db()
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
