"""Shared helpers for the widget module family.

Used by widget_chat.py, widget_config.py, widget_lead.py, and widget_booking.py.

WARNING: PEP 563 deferred annotations are incompatible with FastAPI.
It breaks FastAPI's parameter introspection — Pydantic body models and
BackgroundTasks get treated as query params, causing 422 errors.
"""

import json
import logging
import re
import time as _time
from typing import Any

import anthropic
from fastapi import HTTPException, Request

from backend.config import settings
from backend.models.database import get_supabase
from backend.services.activity import log_activity
from backend.services.email_sender import send_email
from backend.services.lead_scoring import score_lead_background
from backend.services.webhook_dispatcher import fire_event_background

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# AI model constants
# ---------------------------------------------------------------------------

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 700
TEMPERATURE = 0.7

# ---------------------------------------------------------------------------
# Branding plan restrictions
# ---------------------------------------------------------------------------

_BRANDING_PLAN_FIELDS: dict[str, set[str]] = {
    "free": {"primary_color"},
    "growth": {"primary_color", "secondary_color", "accent_color", "widget_title", "powered_by_text", "powered_by_url"},
    "professional": {"primary_color", "secondary_color", "accent_color", "widget_title", "powered_by_text", "powered_by_url", "hide_powered_by", "logo_url", "font_family"},
    "enterprise": {"primary_color", "secondary_color", "accent_color", "widget_title", "powered_by_text", "powered_by_url", "hide_powered_by", "logo_url", "font_family", "custom_css"},
}

_DANGEROUS_CSS_RE = re.compile(
    r"<script|javascript:|@import|expression\s*\(", re.IGNORECASE
)
_CSS_URL_RE = re.compile(r"url\s*\(", re.IGNORECASE)
_FONT_URL_RE = re.compile(r"(src\s*:\s*url\s*\(|font-face)", re.IGNORECASE)


def _sanitize_css(css: str | None) -> str | None:
    """Strip dangerous patterns from custom CSS."""
    if not css:
        return css
    css = _DANGEROUS_CSS_RE.sub("", css)
    lines = css.split("\n")
    cleaned = []
    in_font_face = False
    for line in lines:
        if "@font-face" in line.lower():
            in_font_face = True
        if in_font_face and "}" in line:
            in_font_face = False
        if not in_font_face and _CSS_URL_RE.search(line) and not _FONT_URL_RE.search(line):
            line = _CSS_URL_RE.sub("/* sanitized */", line)
        cleaned.append(line)
    return "\n".join(cleaned)


def _filter_branding_for_plan(branding: dict | None, plan: str) -> dict:
    """Return only branding fields allowed for the given plan."""
    if not branding:
        return {}
    allowed = _BRANDING_PLAN_FIELDS.get(plan, _BRANDING_PLAN_FIELDS["free"])
    filtered = {k: v for k, v in branding.items() if k in allowed and v is not None}
    if plan in ("free", "growth"):
        filtered.pop("hide_powered_by", None)
    return filtered


# ---------------------------------------------------------------------------
# Lead extraction patterns
# ---------------------------------------------------------------------------

NAME_RE = re.compile(
    r"(?:i'm|im|i am|my name is|this is|name's|call me)\s+"
    r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
    re.IGNORECASE,
)
# Standalone name: entire message is 1-3 capitalized words (e.g. "John Smith")
STANDALONE_NAME_RE = re.compile(
    r"^([A-Z][a-z]{1,20}(?:\s+[A-Z][a-z]{1,20}){0,2})\.?$"
)
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,10}(?![a-zA-Z])")
PHONE_RE = re.compile(
    r"(?:\+\d{1,3}[-.\s]?)?"       # optional country code: +1, +44, +91
    r"\(?\d{2,4}\)?"               # area/city code (2-4 digits, optional parens)
    r"[-.\s]?\d{2,4}"              # number group 2
    r"[-.\s]?\d{2,4}"              # number group 3
    r"(?:[-.\s]?\d{1,4})?"         # optional group 4 (longer intl numbers)
)

# ---------------------------------------------------------------------------
# In-memory TTL cache — reduces DB load on hot widget endpoints
# ---------------------------------------------------------------------------

_cache: dict[str, tuple[float, Any]] = {}
_WIDGET_CACHE_TTL = 300  # 5 minutes for config data
_CHAT_CACHE_TTL = 300    # 5 minutes for FAQ/hours/corrections


def _get_cached(key: str, ttl: int = _WIDGET_CACHE_TTL) -> Any | None:
    if key in _cache:
        ts, data = _cache[key]
        if _time.time() - ts < ttl:
            return data
        del _cache[key]
    return None


def _set_cache(key: str, data: Any) -> None:
    if len(_cache) > 1000:
        cutoff = _time.time() - _WIDGET_CACHE_TTL
        expired = [k for k, (ts, _) in _cache.items() if ts < cutoff]
        for k in expired:
            del _cache[k]
    _cache[key] = (_time.time(), data)


def _invalidate_cache(prefix: str) -> None:
    """Remove all cache entries matching a prefix."""
    to_del = [k for k in _cache if k.startswith(prefix)]
    for k in to_del:
        del _cache[k]


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------


def _get_widget_config(api_key: str) -> dict[str, Any]:
    cached = _get_cached(f"wc:{api_key}")
    if cached is not None:
        return cached
    try:
        db = get_supabase()
        result = db.table("widget_configs").select("*").eq("api_key", api_key).limit(1).execute()
    except Exception:
        logger.warning("Database unreachable in _get_widget_config", exc_info=True)
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")
    if not result.data:
        raise HTTPException(status_code=404, detail="Widget not found")
    _set_cache(f"wc:{api_key}", result.data[0])
    return result.data[0]


def _get_tenant(tenant_id: str) -> dict[str, Any]:
    cached = _get_cached(f"t:{tenant_id}")
    if cached is not None:
        return cached
    try:
        db = get_supabase()
        result = db.table("tenants").select(
            "id, business_name, business_type, city, plan, plan_status, "
            "free_trial_started_at, conversations_used_this_month, "
            "sms_notifications_enabled, notification_phone"
        ).eq("id", tenant_id).limit(1).execute()
    except Exception:
        logger.warning("Database unreachable in _get_tenant", exc_info=True)
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")
    if not result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")
    _set_cache(f"t:{tenant_id}", result.data[0])
    return result.data[0]


def _check_origin(request: Request, allowed_domains: list[str] | None) -> None:
    if not allowed_domains:
        return
    origin = request.headers.get("origin", "")
    if not origin:
        return
    # Strip protocol for comparison
    origin_host = origin.replace("https://", "").replace("http://", "").rstrip("/")
    for domain in allowed_domains:
        domain_clean = domain.replace("https://", "").replace("http://", "").rstrip("/")
        if origin_host == domain_clean:
            return
    raise HTTPException(status_code=403, detail="Origin not allowed")


def _get_or_create_conversation(
    tenant_id: str, session_id: str
) -> tuple[str, bool]:
    """Return (conversation_id, is_new).

    Looks up or creates a conversations row.  Message history is stored in the
    separate ``chat_messages`` table, not in conversations JSONB.

    If the insert fails, falls back to session_id — but downstream code must
    validate the conversation_id is a real UUID before using it for updates.
    """
    db = get_supabase()

    # Try to find an existing conversation
    try:
        result = (
            db.table("conversations")
            .select("id")
            .eq("client_id", tenant_id)
            .eq("session_id", session_id)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0]["id"], False
    except Exception:
        logger.warning("conversations lookup failed for session %s", session_id, exc_info=True)

    # Try to create one (upsert — safe against race conditions with unique constraint)
    try:
        new_conv = (
            db.table("conversations")
            .upsert(
                {"client_id": tenant_id, "session_id": session_id},
                on_conflict="client_id,session_id",
            )
            .execute()
        )
        if new_conv.data:
            return new_conv.data[0]["id"], True
        else:
            logger.error("conversations upsert returned no data for session %s tenant %s", session_id, tenant_id)
    except Exception:
        logger.error("conversations upsert FAILED for session %s tenant %s", session_id, tenant_id, exc_info=True)

    # Fallback: use session_id as a stable conversation identifier.
    # WARNING: This is NOT a UUID — downstream code must validate before DB updates.
    logger.warning("conversations fallback: using session_id %s as conversation_id (not a UUID)", session_id)
    return session_id, True


def _load_chat_history(
    tenant_id: str, session_id: str, limit: int = 20
) -> list[dict[str, str]]:
    """Load recent chat messages from the chat_messages table."""
    try:
        db = get_supabase()
        result = (
            db.table("chat_messages")
            .select("role, content")
            .eq("tenant_id", tenant_id)
            .eq("session_id", session_id)
            .order("created_at")
            .limit(limit)
            .execute()
        )
        msgs = [{"role": m["role"], "content": m["content"]} for m in (result.data or [])]
        logger.info(
            "chat_history: tenant=%s session=%s → %d messages loaded",
            tenant_id, session_id, len(msgs),
        )
        return msgs
    except Exception as e:
        logger.error(
            "chat_history FAILED: tenant=%s session=%s error=%s",
            tenant_id, session_id, e, exc_info=True,
        )
        # Retry without .order() in case created_at column is missing
        try:
            db = get_supabase()
            result = (
                db.table("chat_messages")
                .select("role, content")
                .eq("tenant_id", tenant_id)
                .eq("session_id", session_id)
                .limit(limit)
                .execute()
            )
            msgs = [{"role": m["role"], "content": m["content"]} for m in (result.data or [])]
            logger.info("chat_history: retry without order succeeded, %d messages", len(msgs))
            return msgs
        except Exception as e2:
            logger.error("chat_history retry also FAILED: %s", e2, exc_info=True)
            return []


def _save_chat_messages(
    tenant_id: str, session_id: str, user_text: str | None, assistant_text: str | None
) -> None:
    """Persist user and/or assistant messages to chat_messages table."""
    try:
        db = get_supabase()
        rows = []
        if user_text:
            rows.append({"tenant_id": tenant_id, "session_id": session_id, "role": "user", "content": user_text})
        if assistant_text:
            rows.append({"tenant_id": tenant_id, "session_id": session_id, "role": "assistant", "content": assistant_text})
        if rows:
            db.table("chat_messages").insert(rows).execute()
        logger.info("chat_save: OK tenant=%s session=%s msgs=%d", tenant_id, session_id, len(rows))
    except Exception as e:
        logger.error("chat_save FAILED: tenant=%s session=%s error=%s", tenant_id, session_id, e, exc_info=True)


# ---------------------------------------------------------------------------
# System prompt construction
# ---------------------------------------------------------------------------


def _format_hours_block(bh: dict) -> str:
    """Format business hours into a system prompt block."""
    from datetime import datetime

    import zoneinfo
    try:
        tz = zoneinfo.ZoneInfo(bh.get("timezone", "America/New_York"))
    except Exception:
        tz = zoneinfo.ZoneInfo("America/New_York")

    now = datetime.now(tz)
    day_name = now.strftime("%A").lower()
    current_time = now.strftime("%-I:%M %p")

    hours = bh.get("hours", {})
    day_config = hours.get(day_name, {})
    is_open = day_config.get("enabled", False)

    lines = [f"\n\nBusiness Hours (current time: {current_time} {bh.get('timezone', '')}):\n"]
    day_order = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    for d in day_order:
        cfg = hours.get(d, {})
        if cfg.get("enabled"):
            lines.append(f"- {d.capitalize()}: {cfg.get('start', '09:00')} - {cfg.get('end', '17:00')}")
        else:
            lines.append(f"- {d.capitalize()}: Closed")

    if is_open:
        start = day_config.get("start", "09:00")
        end = day_config.get("end", "17:00")
        lines.append(f"\nThe business is currently OPEN (today's hours: {start} - {end}).")
    else:
        # Find next open day
        for i in range(1, 8):
            next_day = day_order[(day_order.index(day_name) + i) % 7]
            next_cfg = hours.get(next_day, {})
            if next_cfg.get("enabled"):
                lines.append(f"\nThe business is currently CLOSED. Next open: {next_day.capitalize()} at {next_cfg.get('start', '09:00')}.")
                break

    lines.append("If a visitor asks about hours or availability, refer to this schedule.")
    return "\n".join(lines)


def _build_system_prompt(
    tenant: dict, faq_entries: list[dict], business_hours: dict | None = None,
    corrections: list[dict] | None = None,
    website_content: str | None = None,
    menu_items: list[dict] | None = None,
    job_listings: list[dict] | None = None,
    bid_templates: list[dict] | None = None,
    custom_field_defs: list[dict] | None = None,
    custom_instructions: str | None = None,
    knowledge_base: str | None = None,
) -> str:
    business_name = tenant.get("business_name") or "our company"
    business_type = tenant.get("business_type") or ""
    city = tenant.get("city") or ""

    location = f" in {city}" if city else ""
    btype = f" ({business_type})" if business_type else ""

    faq_block = ""
    if faq_entries:
        lines = [f"Q: {e['question']}\nA: {e['answer']}" for e in faq_entries]
        faq_block = "\n\nFAQs:\n" + "\n\n".join(lines)

    hours_block = ""
    if business_hours:
        hours_block = _format_hours_block(business_hours)

    corrections_block = ""
    if corrections:
        lines = [f"- {c['correction']}" for c in corrections if c.get("correction")]
        if lines:
            corrections_block = "\n\nBusiness owner corrections (follow these closely):\n" + "\n".join(lines)

    website_block = ""
    if website_content:
        # Truncate to keep system prompt reasonable (~8KB max for website content)
        content = website_content[:8000]
        if len(website_content) > 8000:
            content += "\n[Content truncated]"
        website_block = f"\n\nBusiness website content (use this to answer questions about the business):\n{content}"

    knowledge_block = ""
    if knowledge_base:
        kb_content = knowledge_base[:6000]
        if len(knowledge_base) > 6000:
            kb_content += "\n[Content truncated]"
        knowledge_block = f"\n\nBusiness Knowledge Base (use this as primary reference for customer questions):\n{kb_content}"

    menu_block = ""
    if menu_items:
        # Group by category
        categories = {}
        for item in menu_items:
            cat = item.get("category", "Other")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(item)

        lines = []
        for cat, items in categories.items():
            lines.append(f"\n{cat}:")
            for item in items:
                price = f"${float(item['price']):.2f}"
                desc = f" — {item['description']}" if item.get("description") else ""
                avail = "" if item.get("available", True) else " [OUT OF STOCK]"
                lines.append(f"  - {item['name']} {price}{desc}{avail}")

        menu_block = (
            "\n\nRESTAURANT MENU (use this to help customers order):"
            + "\n".join(lines)
            + "\n\nORDERING INSTRUCTIONS:"
            + "\n- When a customer wants to order food, present the menu organized by category."
            + "\n- Take their order item by item. Ask about modifiers if applicable."
            + "\n- Confirm the full order with itemized prices and total."
            + "\n- Ask: pickup or delivery?"
            + "\n- Collect customer name and phone number."
            + "\n- If delivery, ask for their delivery address."
            + "\n- After confirming, say the order has been placed and they'll receive a confirmation."
            + "\n- Items marked [OUT OF STOCK] are unavailable — let the customer know and suggest alternatives."
            + "\n\nIMPORTANT — When the order is FULLY confirmed (customer agreed to the order summary),"
            + " append this EXACT block at the very end of your response (after your normal message):"
            + '\n<!--ORDER_JSON:{"items":[{"name":"Item Name","price":9.99,"quantity":1}],'
            + '"subtotal":9.99,"tax":0.80,"total":10.79,"order_type":"pickup",'
            + '"customer_name":"Name","customer_phone":"555-1234",'
            + '"delivery_address":"","notes":""}-->'
            + "\n- Fill in the real values from the conversation. Calculate tax at 8%."
            + "\n- Only output this ONCE when the order is confirmed, never before."
        )

    jobs_block = ""
    if job_listings:
        lines = []
        for job in job_listings:
            parts = [f"  - {job['title']}"]
            if job.get("pay_range"):
                parts.append(f"Pay: {job['pay_range']}")
            if job.get("schedule"):
                parts.append(f"Schedule: {job['schedule']}")
            if job.get("location"):
                parts.append(f"Location: {job['location']}")
            lines.append(" | ".join(parts))
        jobs_block = (
            "\n\nOPEN JOB POSITIONS:\n"
            + "\n".join(lines)
            + "\n\nJOB INSTRUCTIONS:"
            + "\n- If someone asks about hiring, jobs, or careers, tell them about the open positions."
            + "\n- Share the job details (title, pay, schedule, location) when relevant."
            + "\n- If they're interested in applying, ask for their name, phone number, and a short message about why they're a good fit."
            + "\n- Be enthusiastic about the opportunity."
        )

    bid_block = ""
    if bid_templates:
        lines = []
        for tmpl in bid_templates:
            name = tmpl.get("name", "Unnamed template")
            desc = f" — {tmpl['description']}" if tmpl.get("description") else ""
            lines.append(f"  - {name}{desc}")
        bid_block = (
            "\n\nQUOTE/BID COLLECTION:"
            "\n- If someone asks for a quote, estimate, bid, or pricing on a job, "
            "collect the job details conversationally:"
            "\n  1. Scope of work (what needs to be done)"
            "\n  2. Timeline (when they need it done)"
            "\n  3. Location / address"
            "\n  4. Budget range (if they're willing to share)"
            "\n  5. Their name, email, and phone"
            "\n- Available service templates:\n"
            + "\n".join(lines)
            + "\n- After collecting details, summarize the request and let them know someone will "
            "follow up with a formal estimate."
            + "\n\nIMPORTANT — When you have enough details to create a bid request (at minimum: "
            "scope of work and contact info), append this EXACT block at the very end of your "
            "response (after your normal message):"
            + '\n<!--BID_REQUEST:{"scope":"Description of work","timeline":"When needed",'
            '"location":"Address or area","budget":"Budget range or empty string",'
            '"customer_name":"Name","customer_email":"email@example.com",'
            '"customer_phone":"555-1234"}-->'
            + "\n- Fill in the real values from the conversation."
            + "\n- Only output this ONCE when you have enough info, never before."
        )

    custom_fields_block = ""
    if custom_field_defs:
        lines = []
        for f in custom_field_defs:
            name = f.get("field_name", "")
            ftype = f.get("field_type", "text")
            req = " (required)" if f.get("is_required") else ""
            opts = f" Options: {', '.join(f['options'])}" if f.get("options") else ""
            lines.append(f"  - {name} ({ftype}){req}{opts}")
        custom_fields_block = (
            "\n\nCUSTOM INFORMATION TO COLLECT:"
            "\nDuring conversation, try to naturally collect these details when relevant:"
            "\n" + "\n".join(lines)
            + "\n- Only ask for these when it fits the conversation flow. Don't interrogate the visitor."
        )

    # Industry-specific compliance blocks
    healthcare_block = ""
    bt_lower = (business_type or "").lower()
    if bt_lower in ("dental", "medical", "healthcare", "doctor", "clinic"):
        healthcare_block = (
            "\n\nHEALTHCARE PRIVACY:"
            "\n- If someone shares medical or health information, acknowledge it professionally"
            "\n- Do NOT store, repeat, or reference specific medical conditions in detail"
            "\n- If asked about privacy, say: 'Your information is kept confidential and handled in accordance with privacy regulations.'"
            "\n- Recommend patients complete a health history form before their visit"
            "\n- Never provide medical advice, diagnoses, or treatment recommendations"
        )
    elif bt_lower in ("legal", "lawyer", "law_firm", "attorney"):
        healthcare_block = (
            "\n\nLEGAL COMPLIANCE:"
            "\n- In your first response, include: 'Please note this chat does not create an attorney-client relationship.'"
            "\n- NEVER provide legal advice, opinions on the merits of a case, or predict case outcomes"
            "\n- For substantive legal questions, recommend scheduling a consultation"
            "\n- Ask about the type of legal matter early in the conversation to help screen the inquiry"
            "\n- Ask which state/jurisdiction the matter involves"
            "\n- If the matter doesn't match the firm's practice areas, politely explain and suggest they contact a different attorney"
            "\n- Do not discuss fees in detail — recommend a consultation to discuss fee arrangements"
            "\n- Treat all information shared as confidential, but note that full confidentiality requires a formal attorney-client relationship"
        )

    # Identity line: use custom_instructions if set, otherwise generic opener
    if custom_instructions:
        identity_line = custom_instructions.strip()
    else:
        identity_line = f"You are a friendly AI assistant for {business_name}{btype}{location}."

    return (
        f"{identity_line}\n\n"
        f"Rules:\n"
        f"- Be helpful, friendly, and concise (2-3 sentences max)\n"
        f"- Answer questions about the business using the FAQs and website content below\n"
        f"- Lead capture: When a visitor asks about pricing, cost, free trial, getting started, or shows clear buying intent, naturally ask for their email to send details or get them started. Frame it helpfully, e.g. 'I can send you the full details — what email should I use?' or 'I can set that up for you. What's your email address?'\n"
        f"- Don't ask for email on the first message, casual greetings, or simple questions. Wait for real interest or a question about services/pricing/trial.\n"
        f"- If they provide an email, thank them and move forward. Never ask for it again.\n"
        f"- NEVER re-ask for info already in the conversation. If they said their name, use it. If they gave email, move on.\n"
        f"- Don't follow a rigid script. Have a natural conversation.\n"
        f"- If you don't know something, say you'll have someone follow up\n"
        f"- Never claim to be human\n"
        f"- ALWAYS respond in the same language the visitor uses. If they write in Spanish, reply in Spanish. If they write in French, reply in French. Match their language exactly.\n"
        f"- If the visitor explicitly asks to speak with a human, a real person, or a team member, include the exact marker HANDOFF_REQUESTED at the very end of your response (after your message). Say something like 'Let me connect you with a team member who can help.' followed by HANDOFF_REQUESTED"
        f"{healthcare_block}"
        f"{hours_block}"
        f"{faq_block}"
        f"{website_block}"
        f"{knowledge_block}"
        f"{custom_fields_block}"
        f"{menu_block}"
        f"{jobs_block}"
        f"{bid_block}"
        f"{corrections_block}"
    )


# ---------------------------------------------------------------------------
# Lead extraction helpers
# ---------------------------------------------------------------------------


def _extract_lead_info(text: str) -> dict[str, str]:
    """Extract name, email, and phone from a user message via regex."""
    info: dict[str, str] = {}
    name_match = NAME_RE.search(text)
    if name_match:
        info["name"] = name_match.group(1).strip()
    elif STANDALONE_NAME_RE.match(text.strip()):
        # Catch bare name responses like "John Smith"
        info["name"] = STANDALONE_NAME_RE.match(text.strip()).group(1)
    # Strip spaces around @ to handle "sara@ test.com" or "john @ gmail.com"
    # but do NOT remove all spaces (that collapses other words into the email)
    email_match = EMAIL_RE.search(re.sub(r"\s*@\s*", "@", text))
    if email_match:
        email = email_match.group(0).strip().lower()
        # Final validation: no spaces, has @ and at least one dot after @
        if " " not in email and "@" in email and "." in email.split("@")[1]:
            info["email"] = email
    phone_match = PHONE_RE.search(text)
    if phone_match:
        raw = phone_match.group(0).strip()
        digits = re.sub(r"\D", "", raw)
        if 7 <= len(digits) <= 15:
            info["phone"] = raw
    return info


def _build_flow_instructions(flow_json: dict) -> str:
    """Convert a chat flow definition into natural language instructions for the AI."""
    nodes = flow_json.get("nodes", [])
    edges = flow_json.get("edges", [])
    if not nodes:
        return ""

    lines = ["\n\nCONVERSATION FLOW INSTRUCTIONS:"]
    lines.append("Follow this conversation flow when appropriate:")

    for node in nodes:
        ntype = node.get("type", "")
        data = node.get("data", {})
        nid = node.get("id", "")

        if ntype == "greeting":
            msg = data.get("message", "")
            if msg:
                lines.append(f"- Start with: \"{msg}\"")
        elif ntype == "question":
            q = data.get("question", data.get("label", ""))
            if q:
                lines.append(f"- Ask: \"{q}\"")
        elif ntype == "condition":
            label = data.get("label", "")
            condition = data.get("condition", "")
            # Find edges from this node
            outgoing = [e for e in edges if e.get("source") == nid]
            if label and outgoing:
                options = [f"'{e.get('label', 'next')}'" for e in outgoing if e.get("label")]
                if options:
                    lines.append(f"- Decision: {label} → options: {', '.join(options)}")
        elif ntype == "action":
            action = data.get("action", "")
            label = data.get("label", "")
            action_map = {
                "show_booking": "offer to book an appointment",
                "show_menu": "show the menu",
                "take_order": "help place an order",
                "confirm_order": "confirm the order details",
                "collect_info": "collect the visitor's contact information and requirements",
            }
            instruction = action_map.get(action, label)
            if instruction:
                lines.append(f"- Action: {instruction}")
        elif ntype == "handoff":
            lines.append("- If the visitor needs human help, let them know a team member will follow up")
        elif ntype == "ai_response":
            label = data.get("label", "Answer questions")
            lines.append(f"- {label} using your knowledge and the business context above")

    lines.append("- For anything not covered by this flow, use your best judgment based on the business context.")
    return "\n".join(lines)


def _record_response_metric(tenant_id: str, session_id: str, conversation_id: str) -> None:
    """Background task: record response time for the first message exchange."""
    try:
        db = get_supabase()
        messages = (
            db.table("chat_messages")
            .select("role, created_at")
            .eq("tenant_id", tenant_id)
            .eq("session_id", session_id)
            .order("created_at")
            .limit(5)
            .execute()
        )
        if not messages.data or len(messages.data) < 2:
            return

        first_user = None
        first_response = None
        for msg in messages.data:
            if msg["role"] == "user" and not first_user:
                first_user = msg["created_at"]
            elif msg["role"] == "assistant" and first_user and not first_response:
                first_response = msg["created_at"]

        if not first_user or not first_response:
            return

        from datetime import datetime
        t1 = datetime.fromisoformat(first_user.replace("Z", "+00:00"))
        t2 = datetime.fromisoformat(first_response.replace("Z", "+00:00"))
        response_seconds = max(0, int((t2 - t1).total_seconds()))

        # Only pass conversation_id if it is a valid UUID.  _get_or_create_conversation
        # can fall back to returning session_id (a plain text string like "sess_abc123")
        # when the conversations table is unreachable.  Inserting that value into a UUID
        # column raises a PostgreSQL cast error.
        from uuid import UUID as _UUID
        try:
            _UUID(conversation_id or "")
            safe_conversation_id = conversation_id
        except (ValueError, AttributeError):
            logger.debug(
                "response_metric: conversation_id %r is not a UUID, omitting from insert",
                conversation_id,
            )
            safe_conversation_id = None

        db.table("response_metrics").insert({
            "tenant_id": tenant_id,
            "session_id": session_id,
            "conversation_id": safe_conversation_id,
            "first_message_at": first_user,
            "first_response_at": first_response,
            "response_time_seconds": response_seconds,
            "channel": "widget",
        }).execute()
    except Exception:
        logger.error(
            "response_metric: failed for tenant %s session %s",
            tenant_id, session_id, exc_info=True,
        )


def _extract_service_interest(messages: list[dict]) -> str | None:
    """Extract the visitor's primary service interest from user messages.
    Uses simple keyword matching — no AI call to keep it fast."""
    user_texts = " ".join(
        msg["content"].lower() for msg in messages if msg["role"] == "user"
    )
    if len(user_texts) < 20:
        return None

    # Common service interest keywords
    interests = []
    keywords = {
        "quote": "requesting a quote",
        "estimate": "requesting an estimate",
        "price": "pricing inquiry",
        "cost": "pricing inquiry",
        "appointment": "booking appointment",
        "schedule": "scheduling",
        "repair": "repair service",
        "install": "installation",
        "consult": "consultation",
        "emergency": "emergency service",
        "order": "placing an order",
        "reserv": "reservation",
        "book": "booking",
    }
    for kw, interest in keywords.items():
        if kw in user_texts:
            interests.append(interest)

    return interests[0] if interests else None


def _build_conversation_summary(messages: list[dict[str, str]]) -> str | None:
    """Build a brief summary of the conversation from user messages.
    Returns a 1-2 sentence summary or None if too short."""
    user_msgs = [m["content"] for m in messages if m["role"] == "user"]
    if len(user_msgs) < 2:
        return None
    # Combine up to 500 chars of user messages into a summary
    combined = " ".join(user_msgs)[:500]
    # Simple extractive summary: first user message + last user message
    first = user_msgs[0][:150].strip()
    last = user_msgs[-1][:150].strip() if len(user_msgs) > 1 else ""
    if last and last != first:
        return f"{first} ... {last}"
    return first if len(first) > 20 else None


def _extract_tags_from_conversation(messages: list[dict[str, str]]) -> list[str]:
    """Use Claude to extract auto-tags from conversation messages.

    Returns a list of short tags like "interested in: kitchen remodel",
    "budget: high", "timeline: urgent", "service: plumbing".
    """
    if not messages or len(messages) < 2:
        return []

    # Build a compact transcript (limit to last 20 messages to save tokens)
    transcript_lines = []
    for msg in messages[-20:]:
        role = "Visitor" if msg["role"] == "user" else "Agent"
        transcript_lines.append(f"{role}: {msg['content']}")
    transcript = "\n".join(transcript_lines)

    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key, timeout=30.0)
        resp = client.messages.create(
            model=MODEL,
            max_tokens=200,
            temperature=0,
            system=(
                "Extract business-relevant tags from this chat conversation between a visitor and a business AI assistant. "
                "Return ONLY a JSON array of short tag strings. Tags should capture: "
                "service interests (e.g. 'interested in: kitchen remodel'), "
                "budget level (e.g. 'budget: high'), "
                "timeline urgency (e.g. 'timeline: urgent', 'timeline: 3 months'), "
                "and any other business-relevant signals (e.g. 'returning customer', 'referred by friend'). "
                "If no meaningful tags can be extracted, return []. Max 5 tags. Keep each tag under 40 chars."
            ),
            messages=[{"role": "user", "content": transcript}],
        )
        raw = resp.content[0].text.strip()
        # Handle cases where Claude wraps in markdown code block
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        tags = json.loads(raw)
        if isinstance(tags, list):
            # Sanitize: only strings, max 40 chars, max 5 tags
            return [str(t)[:40] for t in tags if isinstance(t, str)][:5]
    except json.JSONDecodeError:
        logger.warning("tag_extraction: Claude returned non-JSON response")
    except anthropic.APIError as e:
        logger.error("tag_extraction: Claude API error — %s", e)
    except Exception:
        logger.warning("tag_extraction: unexpected failure", exc_info=True)
    return []


SYSTEM_TAGS = [
    "New Lead", "Pricing Question", "Complaint",
    "Appointment Request", "Urgent", "Follow-up Needed",
]


def _categorize_conversation(tenant_id: str, session_id: str, messages: list[dict]) -> None:
    """Background task: AI auto-categorize conversation into preset business tags."""
    if not messages or len(messages) < 3:
        return

    # Load tenant's tag definitions
    db = get_supabase()
    try:
        tag_defs = (
            db.table("tenant_tag_definitions")
            .select("tag_name")
            .eq("tenant_id", tenant_id)
            .eq("is_enabled", True)
            .execute()
        )
        available_tags = [t["tag_name"] for t in (tag_defs.data or [])]
    except Exception:
        # Fall back to system tags if table doesn't exist yet
        available_tags = SYSTEM_TAGS

    if not available_tags:
        available_tags = SYSTEM_TAGS

    transcript_lines = []
    for msg in messages[-20:]:
        role = "Visitor" if msg["role"] == "user" else "Agent"
        transcript_lines.append(f"{role}: {msg['content']}")
    transcript = "\n".join(transcript_lines)

    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key, timeout=30.0)
        resp = client.messages.create(
            model=MODEL,
            max_tokens=100,
            temperature=0,
            system=(
                "Categorize this chat conversation into 1-3 tags from this list ONLY:\n"
                + ", ".join(available_tags)
                + "\n\nReturn ONLY a JSON array of matching tag names. "
                "If none match, return []. Use exact tag names from the list."
            ),
            messages=[{"role": "user", "content": transcript}],
        )
        raw = resp.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        tags = json.loads(raw)
        if not isinstance(tags, list) or not tags:
            return

        # Filter to valid tags only
        valid_tags = [t for t in tags if isinstance(t, str) and t in available_tags][:3]
        if not valid_tags:
            return

        # Update conversation tags (merge with existing)
        conv = (
            db.table("conversations")
            .select("tags")
            .eq("client_id", tenant_id)
            .eq("session_id", session_id)
            .limit(1)
            .execute()
        )
        existing = []
        if conv.data:
            existing = conv.data[0].get("tags") or []

        merged = list(set(existing + valid_tags))
        db.table("conversations").update({"tags": merged}).eq(
            "client_id", tenant_id
        ).eq("session_id", session_id).execute()

    except json.JSONDecodeError:
        logger.warning("conversation_categorize: non-JSON response")
    except anthropic.APIError as e:
        logger.warning("conversation_categorize: API error — %s", e)
    except Exception:
        logger.warning("conversation_categorize: unexpected failure", exc_info=True)


def _extract_action_items(tenant_id: str, session_id: str, messages: list[dict]) -> None:
    """Background task: AI extracts actionable items from conversation."""
    if not messages or len(messages) < 4:
        return

    transcript_lines = []
    for msg in messages[-20:]:
        role = "Visitor" if msg["role"] == "user" else "Agent"
        transcript_lines.append(f"{role}: {msg['content']}")
    transcript = "\n".join(transcript_lines)

    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key, timeout=30.0)
        resp = client.messages.create(
            model=MODEL,
            max_tokens=300,
            temperature=0,
            system=(
                "Extract actionable items from this business chat conversation. "
                "Action items are things the business needs to DO: send a quote, "
                "schedule a follow-up, prepare a document, call someone back, etc.\n\n"
                "Return ONLY a JSON array of objects with these fields:\n"
                '- "description": what needs to be done (max 100 chars)\n'
                '- "priority": "low", "medium", or "high"\n'
                '- "due_hint": natural language due date if mentioned, or null\n\n'
                "If no action items exist, return []. Max 3 items."
            ),
            messages=[{"role": "user", "content": transcript}],
        )
        raw = resp.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        items = json.loads(raw)
        if not isinstance(items, list) or not items:
            return

        db = get_supabase()

        # Find conversation_id for this session
        conv = (
            db.table("conversations")
            .select("id")
            .eq("client_id", tenant_id)
            .eq("session_id", session_id)
            .limit(1)
            .execute()
        )
        conv_id = conv.data[0]["id"] if conv.data else None

        for item in items[:3]:
            if not isinstance(item, dict) or not item.get("description"):
                continue
            data = {
                "tenant_id": tenant_id,
                "description": str(item["description"])[:500],
                "priority": item.get("priority", "medium") if item.get("priority") in ("low", "medium", "high") else "medium",
            }
            if conv_id:
                data["conversation_id"] = conv_id
            db.table("action_items").insert(data).execute()

    except json.JSONDecodeError:
        logger.warning("action_item_extract: non-JSON response")
    except anthropic.APIError as e:
        logger.warning("action_item_extract: API error — %s", e)
    except Exception:
        logger.warning("action_item_extract: unexpected failure", exc_info=True)


# ---------------------------------------------------------------------------
# Lead capture + notifications
# ---------------------------------------------------------------------------


async def _capture_leads_from_session(
    tenant_id: str, session_id: str, conversation_id: str
) -> None:
    """Background task: scan all user messages in session for contact info,
    create or update a lead.  Deduplicates by email + client_id.

    NOTE: Live Supabase leads table uses the archive schema:
      client_id (not tenant_id), status (not lead_stage), no source column.
    """
    try:
        logger.info(
            "lead_capture START: tenant=%s session=%s conv=%s",
            tenant_id, session_id, conversation_id,
        )
        messages = _load_chat_history(tenant_id, session_id, limit=50)
        logger.info("lead_capture: loaded %d messages from session", len(messages))

        # Scan ALL user messages for contact info
        combined: dict[str, str] = {}
        for msg in messages:
            if msg["role"] != "user":
                continue
            extracted = _extract_lead_info(msg["content"])
            if extracted:
                logger.info(
                    "lead_capture: extracted from message %r → %s",
                    msg["content"][:80], extracted,
                )
            combined.update(extracted)

        logger.info("lead_capture: combined info = %s", combined)

        if not combined.get("email") and not combined.get("phone"):
            logger.info("lead_capture: no email or phone found, skipping")
            return

        db = get_supabase()

        # Dedup: check by email + client_id first
        if combined.get("email"):
            logger.info(
                "lead_capture: dedup check — email=%s client_id=%s",
                combined["email"], tenant_id,
            )
            try:
                existing = (
                    db.table("leads")
                    .select("id, name, phone, areas_of_interest, conversation_summary")
                    .eq("client_id", tenant_id)
                    .eq("email", combined["email"])
                    .limit(1)
                    .execute()
                )
            except Exception as dedup_err:
                logger.error(
                    "lead_capture: dedup query FAILED: %s", dedup_err, exc_info=True,
                )
                existing = type("R", (), {"data": []})()

            if existing.data:
                lead = existing.data[0]
                logger.info("lead_capture: existing lead found id=%s", lead["id"])
                updates: dict[str, str] = {}
                suggestions: dict[str, dict] = {}  # field → {old, new}
                for field, db_field in [("name", "name"), ("phone", "phone")]:
                    if combined.get(field):
                        if not lead.get(db_field):
                            updates[db_field] = combined[field]  # auto-fill blanks
                        elif lead[db_field] != combined[field]:
                            suggestions[db_field] = {"old": lead[db_field], "new": combined[field]}
                if combined.get("service_interest"):
                    if not lead.get("areas_of_interest"):
                        updates["areas_of_interest"] = combined["service_interest"]
                    elif lead["areas_of_interest"] != combined["service_interest"]:
                        suggestions["areas_of_interest"] = {"old": lead["areas_of_interest"], "new": combined["service_interest"]}
                # Auto-update conversation summary (always overwrite with latest)
                summary = _build_conversation_summary(messages)
                if summary and not lead.get("conversation_summary"):
                    updates["conversation_summary"] = summary
                # Create pending suggestions for conflicting data
                if suggestions:
                    try:
                        log_activity(
                            tenant_id=tenant_id,
                            activity_type="lead_suggestion",
                            description=f"AI suggests updating {', '.join(suggestions.keys())} for {lead.get('name') or lead.get('email') or 'lead'}",
                            lead_id=lead["id"],
                            metadata={"suggestions": suggestions, "source": "widget"},
                        )
                        logger.info("lead_capture: created suggestion for lead %s: %s", lead["id"], list(suggestions.keys()))
                    except Exception:
                        logger.warning("lead_capture: failed to create suggestion", exc_info=True)
                if updates:
                    db.table("leads").update(updates).eq("id", lead["id"]).execute()
                    log_activity(
                        tenant_id=tenant_id,
                        activity_type="lead_updated",
                        description=f"Lead info captured: {', '.join(updates.keys())}",
                        lead_id=lead["id"],
                        metadata={"source": "widget", "fields": list(updates.keys())},
                    )
                    logger.info("lead_capture: updated lead %s fields=%s", lead["id"], list(updates.keys()))
                    fire_event_background(tenant_id, "lead.updated", {
                        "lead_id": lead["id"],
                        "updated_fields": list(updates.keys()),
                        "source": "widget",
                    })
                # Auto-tag existing lead from conversation
                try:
                    tags = _extract_tags_from_conversation(messages)
                    if tags:
                        db.table("leads").update({"tags": tags}).eq("id", lead["id"]).execute()
                        logger.info("lead_capture: tagged existing lead %s with %s", lead["id"], tags)
                except Exception:
                    logger.warning("lead_capture: tag extraction failed for lead %s", lead["id"], exc_info=True)
                # Mark conversation as having captured a lead
                if conversation_id:
                    try:
                        from uuid import UUID
                        UUID(conversation_id)  # Validate it's a real UUID, not a session_id fallback
                        db.table("conversations").update({"lead_captured": True}).eq("id", conversation_id).execute()
                        logger.info("lead_capture: set lead_captured=true on conversation %s (existing lead)", conversation_id)
                    except (ValueError, AttributeError):
                        logger.warning("lead_capture: conversation_id %r is not a UUID, skipping lead_captured update", conversation_id)
                    except Exception:
                        logger.warning("lead_capture: failed to update lead_captured on conversation %s", conversation_id, exc_info=True)
                return

        # Extract service interest from conversation context
        service_interest = _extract_service_interest(messages)

        # Create new lead — live schema: client_id, status (not tenant_id, lead_stage)
        lead_fields: dict[str, Any] = {
            "client_id": tenant_id,
            "status": "new",
            "source": "widget",
        }
        for key in ("name", "email", "phone"):
            if combined.get(key):
                lead_fields[key] = combined[key]
        if service_interest:
            lead_fields["areas_of_interest"] = service_interest
        # Auto-populate conversation summary
        summary = _build_conversation_summary(messages)
        if summary:
            lead_fields["conversation_summary"] = summary

        # Only set conversation_id if it looks like a valid UUID
        try:
            from uuid import UUID
            UUID(conversation_id)
            lead_fields["conversation_id"] = conversation_id
        except (ValueError, AttributeError):
            logger.debug("lead_capture: conversation_id %r is not a UUID, omitting", conversation_id)

        logger.info("lead_capture: inserting new lead with fields=%s", lead_fields)
        try:
            result = db.table("leads").insert(lead_fields).execute()
        except Exception as insert_err:
            logger.error(
                "lead_capture: INSERT FAILED: %s — fields were %s",
                insert_err, lead_fields, exc_info=True,
            )
            return

        if result.data:
            lead_id = result.data[0]["id"]
            lead_name = combined.get("name", "New visitor")
            logger.info("lead_capture: SUCCESS lead_id=%s client_id=%s", lead_id, tenant_id)

            try:
                log_activity(
                    tenant_id=tenant_id,
                    activity_type="lead_created",
                    description=f"New lead from widget: {lead_name}",
                    lead_id=lead_id,
                    metadata={"source": "widget", "fields": list(lead_fields.keys())},
                )
            except Exception:
                logger.warning("lead_capture: log_activity failed", exc_info=True)

            # Fire webhook for new lead
            try:
                fire_event_background(tenant_id, "lead.created", {
                    "lead_id": lead_id,
                    "name": combined.get("name"),
                    "email": combined.get("email"),
                    "phone": combined.get("phone"),
                    "source": "widget",
                })
            except Exception:
                logger.warning("lead_capture: fire_event_background failed", exc_info=True)

            # Fire automation trigger for new leads
            logger.info("lead_capture: about to call trigger_sequence for lead %s", lead_id)
            try:
                from backend.services.automation_engine import trigger_sequence
                await trigger_sequence(tenant_id, lead_id, "new_lead")
                logger.info("lead_capture: trigger_sequence completed for lead %s", lead_id)
            except Exception:
                logger.warning("Failed to trigger automation for lead %s", lead_id, exc_info=True)

            # Email sequence enrollment trigger
            try:
                from backend.routers.email_sequences import enroll_lead_in_sequences
                await enroll_lead_in_sequences(tenant_id, lead_id)
                logger.info("lead_capture: enroll_lead_in_sequences completed for lead %s", lead_id)
            except Exception:
                logger.warning("lead_capture: enroll_lead_in_sequences failed for lead %s", lead_id, exc_info=True)

            # SMS notification to owner
            logger.info("SMS_TRIGGER: about to call SMS notification for lead %s email=%s", lead_id, combined.get("email"))
            try:
                await _send_new_lead_sms_notification(tenant_id, lead_name, combined)
            except Exception:
                logger.error("SMS_TRIGGER: FAILED for lead %s", lead_id, exc_info=True)

            # Email notification to owner
            try:
                await _send_new_lead_email_notification(tenant_id, lead_name, combined)
            except Exception:
                logger.error("EMAIL_TRIGGER: FAILED for lead %s", lead_id, exc_info=True)

            # Auto-tag the new lead from conversation
            try:
                tags = _extract_tags_from_conversation(messages)
                if tags:
                    db.table("leads").update({"tags": tags}).eq("id", lead_id).execute()
                    logger.info("lead_capture: tagged new lead %s with %s", lead_id, tags)
            except Exception:
                logger.warning("lead_capture: tag extraction failed for new lead %s", lead_id, exc_info=True)

            # Score the lead
            try:
                score_lead_background(lead_id)
            except Exception:
                logger.warning("Failed to score lead %s in background", lead_id, exc_info=True)

            # Mark conversation as having captured a lead
            if conversation_id:
                try:
                    from uuid import UUID
                    UUID(conversation_id)  # Validate it's a real UUID, not a session_id fallback
                    db.table("conversations").update({"lead_captured": True}).eq("id", conversation_id).execute()
                    logger.info("lead_capture: set lead_captured=true on conversation %s", conversation_id)
                except (ValueError, AttributeError):
                    logger.warning("lead_capture: conversation_id %r is not a UUID, skipping lead_captured update", conversation_id)
                except Exception:
                    logger.warning("lead_capture: failed to update lead_captured on conversation %s", conversation_id, exc_info=True)
        else:
            logger.warning("lead_capture: INSERT returned no data — result=%s", result)

    except Exception:
        logger.error("lead_capture FAILED: session=%s tenant=%s", session_id, tenant_id, exc_info=True)


async def _send_new_lead_sms_notification(
    tenant_id: str, lead_name: str, lead_info: dict[str, str]
) -> None:
    """Send SMS notification to tenant owner when a new lead is captured."""
    logger.info("SMS_FUNCTION: entered function tenant=%s lead=%s", tenant_id, lead_name)
    logger.info(
        "sms_notification: starting for tenant=%s lead=%s info_keys=%s",
        tenant_id, lead_name, list(lead_info.keys()),
    )
    db = get_supabase()
    result = (
        db.table("tenants")
        .select("notification_phone, sms_notifications_enabled, business_name")
        .eq("id", tenant_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        logger.warning("sms_notification: no tenant found for id=%s", tenant_id)
        return
    tenant = result.data[0]
    sms_enabled = tenant.get("sms_notifications_enabled")
    phone = tenant.get("notification_phone")
    logger.info(
        "sms_notification: tenant=%s sms_enabled=%s phone=%s",
        tenant_id, sms_enabled, phone,
    )
    if not sms_enabled or not phone:
        logger.info("sms_notification: skipping — sms_enabled=%s phone=%s", sms_enabled, phone)
        return

    contact = lead_info.get("email") or lead_info.get("phone") or "no contact info"
    body = f"New lead for {tenant.get('business_name', 'your business')}: {lead_name} ({contact})"
    logger.info("sms_notification: sending to=%s body_len=%d", phone, len(body))

    try:
        from backend.services.twilio_service import send_sms
        await send_sms(to=phone, body=body)
        logger.info("sms_notification: sent successfully for tenant=%s", tenant_id)
    except Exception:
        logger.error("sms_notification: FAILED to send for tenant=%s", tenant_id, exc_info=True)


async def _send_new_lead_email_notification(
    tenant_id: str, lead_name: str, lead_info: dict[str, str]
) -> None:
    """Send email notification to tenant owner when a new lead is captured."""
    import html as html_mod

    db = get_supabase()
    result = (
        db.table("tenants")
        .select("owner_email, business_name")
        .eq("id", tenant_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        return
    tenant = result.data[0]
    owner_email = tenant.get("owner_email")
    if not owner_email:
        return

    raw_business_name = tenant.get("business_name") or "your business"
    business_name = html_mod.escape(raw_business_name)
    safe_name = html_mod.escape(lead_name)
    safe_email = html_mod.escape(lead_info.get("email") or "not provided")
    safe_phone = html_mod.escape(lead_info.get("phone") or "not provided")

    body_html = (
        f"<h2>New lead for {business_name}</h2>"
        f"<p>A new lead was just captured from your chat widget:</p>"
        f"<table style='border-collapse:collapse;margin:16px 0;'>"
        f"<tr><td style='padding:4px 12px 4px 0;font-weight:bold;'>Name</td>"
        f"<td style='padding:4px 0;'>{safe_name}</td></tr>"
        f"<tr><td style='padding:4px 12px 4px 0;font-weight:bold;'>Email</td>"
        f"<td style='padding:4px 0;'>{safe_email}</td></tr>"
        f"<tr><td style='padding:4px 12px 4px 0;font-weight:bold;'>Phone</td>"
        f"<td style='padding:4px 0;'>{safe_phone}</td></tr>"
        f"</table>"
        f"<p>Log in to your dashboard to view and follow up with this lead.</p>"
        f"<p>— The AgentNexLiFy Team</p>"
    )

    try:
        await send_email(
            to=owner_email,
            subject=f"New lead for {raw_business_name}: {lead_name}",
            body_html=body_html,
            tenant_id=tenant_id,
        )
    except Exception:
        logger.error(
            "email_notification: FAILED for tenant=%s lead=%s",
            tenant_id, lead_name, exc_info=True,
        )
