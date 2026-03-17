"""Widget API endpoints — multi-tenant chat, config, and lead capture."""

# NOTE: Do NOT add `from __future__ import annotations` here.
# It breaks FastAPI's parameter introspection — Pydantic body models and
# BackgroundTasks get treated as query params, causing 422 errors.

import hmac
import json
import logging
import re
import time as _time
from datetime import datetime, timezone
from typing import Any

import anthropic
import uuid
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Header, Query, Request, UploadFile
from fastapi.responses import HTMLResponse

from backend.config import settings
from backend.limiter import limiter
from backend.models.database import get_supabase
from backend.services.email_sender import _make_unsub_sig
from backend.models.schemas import (
    OnlineStatusRequest,
    WidgetChatRequest,
    WidgetChatResponse,
    WidgetConfigResponse,
    WidgetLeadRequest,
    WidgetLeadResponse,
    WidgetOfflineContactRequest,
)
from backend.services.activity import log_activity
from backend.services.email_sender import send_email
from backend.services.lead_scoring import score_lead_background
from backend.services.webhook_dispatcher import fire_event_background

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/widget", tags=["widget"])

# ── Branding plan restrictions ────────────────────────────────
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


MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 700
TEMPERATURE = 0.7

# Lead extraction patterns
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
# Helpers
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

    The live conversations table schema is unreliable (missing columns), so
    this function tries to look up / create a row but falls back to using the
    session_id itself as a stable identifier.  Message history is stored in the
    separate ``chat_messages`` table, not in conversations JSONB.
    """
    db = get_supabase()

    # Try to find an existing conversation
    try:
        result = (
            db.table("conversations")
            .select("id")
            .eq("tenant_id", tenant_id)
            .eq("session_id", session_id)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0]["id"], False
    except Exception:
        logger.warning("conversations lookup failed for session %s", session_id, exc_info=True)

    # Try to create one
    try:
        new_conv = (
            db.table("conversations")
            .insert({"tenant_id": tenant_id, "session_id": session_id})
            .execute()
        )
        if new_conv.data:
            return new_conv.data[0]["id"], True
    except Exception:
        logger.warning("conversations insert failed for session %s", session_id, exc_info=True)

    # Fallback: use session_id as a stable conversation identifier.
    # This lets chat_messages still accumulate history by session_id.
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
    tenant_id: str, session_id: str, user_text: str, assistant_text: str
) -> None:
    """Persist both user and assistant messages to chat_messages table."""
    try:
        db = get_supabase()
        db.table("chat_messages").insert([
            {"tenant_id": tenant_id, "session_id": session_id, "role": "user", "content": user_text},
            {"tenant_id": tenant_id, "session_id": session_id, "role": "assistant", "content": assistant_text},
        ]).execute()
        logger.info("chat_save: OK tenant=%s session=%s", tenant_id, session_id)
    except Exception as e:
        logger.error("chat_save FAILED: tenant=%s session=%s error=%s", tenant_id, session_id, e, exc_info=True)


def _build_system_prompt(
    tenant: dict, faq_entries: list[dict], business_hours: dict | None = None,
    corrections: list[dict] | None = None,
    website_content: str | None = None,
    menu_items: list[dict] | None = None,
    job_listings: list[dict] | None = None,
    bid_templates: list[dict] | None = None,
    custom_field_defs: list[dict] | None = None,
) -> str:
    business_name = tenant.get("business_name", "our company")
    business_type = tenant.get("business_type", "")
    city = tenant.get("city", "")

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

    return (
        f"You are a friendly AI assistant for {business_name}{btype}{location}.\n\n"
        f"Rules:\n"
        f"- Be helpful, friendly, and concise (2-3 sentences max)\n"
        f"- Answer questions about the business using the FAQs and website content below\n"
        f"- During conversation, naturally collect name, email, and phone — but ONLY what's missing\n"
        f"- NEVER re-ask for info already in the conversation. If they said their name, use it. If they gave email, move on.\n"
        f"- Don't follow a rigid script. Have a natural conversation.\n"
        f"- If you don't know something, say you'll have someone follow up\n"
        f"- Never claim to be human\n"
        f"- ALWAYS respond in the same language the visitor uses. If they write in Spanish, reply in Spanish. If they write in French, reply in French. Match their language exactly."
        f"{hours_block}"
        f"{faq_block}"
        f"{website_block}"
        f"{custom_fields_block}"
        f"{menu_block}"
        f"{jobs_block}"
        f"{bid_block}"
        f"{corrections_block}"
    )


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

        db.table("response_metrics").insert({
            "tenant_id": tenant_id,
            "session_id": session_id,
            "conversation_id": conversation_id if conversation_id else None,
            "first_message_at": first_user,
            "first_response_at": first_response,
            "response_time_seconds": response_seconds,
            "channel": "widget",
        }).execute()
    except Exception:
        logger.warning("response_metric: failed for tenant %s session %s", tenant_id, session_id, exc_info=True)


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
            .eq("tenant_id", tenant_id)
            .eq("session_id", session_id)
            .limit(1)
            .execute()
        )
        existing = []
        if conv.data:
            existing = conv.data[0].get("tags") or []

        merged = list(set(existing + valid_tags))
        db.table("conversations").update({"tags": merged}).eq(
            "tenant_id", tenant_id
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
            .eq("tenant_id", tenant_id)
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
                return

        # Extract service interest from conversation context
        service_interest = _extract_service_interest(messages)

        # Create new lead — live schema: client_id, status (not tenant_id, lead_stage)
        lead_fields: dict[str, Any] = {
            "client_id": tenant_id,
            "status": "new",
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

    raw_business_name = tenant.get("business_name", "your business")
    business_name = html_mod.escape(raw_business_name)
    safe_name = html_mod.escape(lead_name)
    safe_email = html_mod.escape(lead_info.get("email", "not provided"))
    safe_phone = html_mod.escape(lead_info.get("phone", "not provided"))

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


# ---------------------------------------------------------------------------
# Order extraction + notifications (restaurant ordering via chat)
# ---------------------------------------------------------------------------

ORDER_JSON_RE = re.compile(r"<!--ORDER_JSON:(.*?)-->", re.DOTALL)


def _extract_order_from_response(response_text: str) -> dict | None:
    """Extract structured order JSON from AI response, if present."""
    match = ORDER_JSON_RE.search(response_text)
    if not match:
        return None
    try:
        return json.loads(match.group(1).strip())
    except (json.JSONDecodeError, ValueError):
        logger.warning("order_extract: found ORDER_JSON marker but JSON parse failed")
        return None


def _strip_order_json_from_response(response_text: str) -> str:
    """Remove the ORDER_JSON marker from the response shown to the user."""
    return ORDER_JSON_RE.sub("", response_text).rstrip()


async def _process_order_from_chat(
    tenant_id: str, session_id: str, order_data: dict,
) -> None:
    """Create an order record and send notifications to owner + customer."""
    import html as html_mod

    db = get_supabase()

    # Build order record
    items = order_data.get("items", [])
    record = {
        "tenant_id": tenant_id,
        "session_id": session_id,
        "customer_name": order_data.get("customer_name"),
        "customer_phone": order_data.get("customer_phone"),
        "customer_email": order_data.get("customer_email"),
        "items_json": items,
        "subtotal": float(order_data.get("subtotal", 0)),
        "tax": float(order_data.get("tax", 0)),
        "total": float(order_data.get("total", 0)),
        "order_type": order_data.get("order_type", "pickup"),
        "delivery_address": order_data.get("delivery_address") or None,
        "notes": order_data.get("notes") or None,
        "status": "new",
    }

    try:
        result = db.table("orders").insert(record).execute()
        if not result.data:
            logger.error("order_create: insert returned no data for tenant=%s", tenant_id)
            return
        order = result.data[0]
        logger.info("order_create: order %s created for tenant=%s", order["id"], tenant_id)
    except Exception:
        logger.exception("order_create: failed for tenant=%s", tenant_id)
        return

    # Fetch tenant info for notifications
    try:
        tenant_result = (
            db.table("tenants")
            .select("owner_email, business_name, business_phone")
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
        if not tenant_result.data:
            return
        tenant = tenant_result.data[0]
    except Exception:
        logger.exception("order_notify: failed to fetch tenant %s", tenant_id)
        return

    business_name = tenant.get("business_name", "Your Business")
    customer_name = record["customer_name"] or "Customer"
    items_summary = ", ".join(
        f"{i.get('name', 'item')} x{i.get('quantity', 1)}"
        for i in items[:5]
    )
    if len(items) > 5:
        items_summary += f" +{len(items) - 5} more"
    total_str = f"${record['total']:.2f}"

    # --- SMS notification to owner ---
    owner_phone = tenant.get("business_phone")
    if owner_phone:
        sms_body = (
            f"New {record['order_type']} order from {customer_name}!\n"
            f"Items: {items_summary}\n"
            f"Total: {total_str}\n"
            f"Check your dashboard to confirm."
        )
        try:
            from backend.services.twilio_service import send_sms
            await send_sms(to=owner_phone, body=sms_body)
            logger.info("order_notify: SMS sent to owner for tenant=%s", tenant_id)
        except Exception:
            logger.error("order_notify: owner SMS failed for tenant=%s", tenant_id, exc_info=True)

    # --- Email notification to owner ---
    owner_email = tenant.get("owner_email")
    if owner_email:
        safe_biz = html_mod.escape(business_name)
        safe_name = html_mod.escape(customer_name)
        safe_phone = html_mod.escape(record.get("customer_phone") or "Not provided")
        safe_type = html_mod.escape(record["order_type"].capitalize())

        items_rows = ""
        for i in items:
            iname = html_mod.escape(i.get("name", "Item"))
            qty = i.get("quantity", 1)
            iprice = f"${float(i.get('price', 0)):.2f}"
            items_rows += (
                f"<tr><td style='padding:4px 12px 4px 0;'>{iname}</td>"
                f"<td style='padding:4px 8px;text-align:center;'>{qty}</td>"
                f"<td style='padding:4px 0;text-align:right;'>{iprice}</td></tr>"
            )

        body_html = (
            f"<h2>New Order for {safe_biz}</h2>"
            f"<p>A new <strong>{safe_type}</strong> order was just placed via your chat widget:</p>"
            f"<p><strong>Customer:</strong> {safe_name}<br>"
            f"<strong>Phone:</strong> {safe_phone}</p>"
            f"<table style='border-collapse:collapse;margin:16px 0;width:100%;'>"
            f"<tr style='border-bottom:1px solid #ddd;'>"
            f"<th style='text-align:left;padding:4px 12px 4px 0;'>Item</th>"
            f"<th style='text-align:center;padding:4px 8px;'>Qty</th>"
            f"<th style='text-align:right;padding:4px 0;'>Price</th></tr>"
            f"{items_rows}"
            f"<tr style='border-top:2px solid #333;'>"
            f"<td colspan='2' style='padding:8px 12px 4px 0;font-weight:bold;'>Total</td>"
            f"<td style='padding:8px 0 4px;text-align:right;font-weight:bold;'>{total_str}</td></tr>"
            f"</table>"
        )
        if record["delivery_address"]:
            safe_addr = html_mod.escape(record["delivery_address"])
            body_html += f"<p><strong>Delivery address:</strong> {safe_addr}</p>"
        if record["notes"]:
            safe_notes = html_mod.escape(record["notes"])
            body_html += f"<p><strong>Notes:</strong> {safe_notes}</p>"
        body_html += "<p>Log in to your dashboard to confirm this order.</p>"

        try:
            await send_email(
                to=owner_email,
                subject=f"New order for {business_name}: {customer_name} ({total_str})",
                body_html=body_html,
                tenant_id=tenant_id,
            )
            logger.info("order_notify: email sent to owner for tenant=%s", tenant_id)
        except Exception:
            logger.error("order_notify: owner email failed for tenant=%s", tenant_id, exc_info=True)

    # --- SMS confirmation to customer ---
    customer_phone = record.get("customer_phone")
    if customer_phone:
        confirm_body = (
            f"Your {record['order_type']} order from {business_name} has been received!\n"
            f"Items: {items_summary}\n"
            f"Total: {total_str}\n"
        )
        if owner_phone:
            confirm_body += f"Questions? Call us at {owner_phone}"
        try:
            from backend.services.twilio_service import send_sms
            await send_sms(to=customer_phone, body=confirm_body)
            logger.info("order_notify: confirmation SMS sent to customer for tenant=%s", tenant_id)
        except Exception:
            logger.error("order_notify: customer SMS failed for tenant=%s", tenant_id, exc_info=True)

    # Fire webhook for new order
    fire_event_background(tenant_id, "order.created", {
        "order_id": order["id"],
        "customer_name": customer_name,
        "total": record["total"],
        "order_type": record["order_type"],
        "items_count": len(items),
    })


# ---------------------------------------------------------------------------
# Bid request extraction from chat (contractor quick-bid via chat)
# ---------------------------------------------------------------------------

BID_REQUEST_RE = re.compile(r"<!--BID_REQUEST:(.*?)-->", re.DOTALL)


def _extract_bid_request_from_response(response_text: str) -> dict | None:
    """Extract structured bid request JSON from AI response, if present."""
    match = BID_REQUEST_RE.search(response_text)
    if not match:
        return None
    try:
        return json.loads(match.group(1).strip())
    except (json.JSONDecodeError, ValueError):
        logger.warning("bid_extract: found BID_REQUEST marker but JSON parse failed")
        return None


def _strip_bid_request_from_response(response_text: str) -> str:
    """Remove the BID_REQUEST marker from the response shown to the user."""
    return BID_REQUEST_RE.sub("", response_text).rstrip()


def _process_bid_request_from_chat(
    tenant_id: str, session_id: str, bid_data: dict,
) -> None:
    """Log a bid request as a high-priority action item for the business owner."""
    db = get_supabase()

    scope = bid_data.get("scope", "")
    customer_name = bid_data.get("customer_name", "Unknown")
    customer_email = bid_data.get("customer_email", "")
    customer_phone = bid_data.get("customer_phone", "")
    timeline = bid_data.get("timeline", "")
    location = bid_data.get("location", "")
    budget = bid_data.get("budget", "")

    # Build a readable description
    parts = [f"Bid request from {customer_name}"]
    if scope:
        parts.append(f"Scope: {scope}")
    if timeline:
        parts.append(f"Timeline: {timeline}")
    if location:
        parts.append(f"Location: {location}")
    if budget:
        parts.append(f"Budget: {budget}")
    if customer_email:
        parts.append(f"Email: {customer_email}")
    if customer_phone:
        parts.append(f"Phone: {customer_phone}")
    description = " | ".join(parts)

    # Find the conversation_id for this session
    conversation_id = None
    try:
        conv_result = (
            db.table("conversations")
            .select("id")
            .eq("tenant_id", tenant_id)
            .eq("session_id", session_id)
            .limit(1)
            .execute()
        )
        if conv_result.data:
            conversation_id = conv_result.data[0]["id"]
    except Exception:
        logger.warning("bid_request: failed to find conversation for session %s", session_id, exc_info=True)

    try:
        db.table("action_items").insert({
            "tenant_id": tenant_id,
            "conversation_id": conversation_id,
            "description": description[:1000],
            "priority": "high",
            "status": "open",
        }).execute()
        logger.info(
            "bid_request: logged action item for tenant=%s session=%s customer=%s",
            tenant_id, session_id, customer_name,
        )
    except Exception:
        logger.exception(
            "bid_request: failed to insert action_item for tenant=%s session=%s",
            tenant_id, session_id,
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/chat", response_model=WidgetChatResponse)
@limiter.limit("60/minute")
async def widget_chat(request: Request, req: WidgetChatRequest, background_tasks: BackgroundTasks):
    """Process a chat message through the multi-tenant widget pipeline."""
    logger.info("widget_chat: received request session=%s api_key=%s...%s",
                req.session_id, req.api_key[:8] if req.api_key else "NONE",
                req.api_key[-4:] if req.api_key else "")

    # 1. Look up widget config + tenant
    widget = _get_widget_config(req.api_key)
    tenant = _get_tenant(widget["tenant_id"])
    logger.info("widget_chat: tenant=%s business=%s", tenant["id"], tenant.get("business_name"))

    # 2. Origin check
    _check_origin(request, widget.get("allowed_domains"))

    # 2b. Free trial expiry check
    if tenant.get("plan") == "free" and tenant.get("free_trial_started_at"):
        from datetime import datetime, timezone
        trial_started = tenant["free_trial_started_at"]
        if isinstance(trial_started, str):
            trial_started = datetime.fromisoformat(trial_started.replace("Z", "+00:00"))
        if trial_started.tzinfo is None:
            trial_started = trial_started.replace(tzinfo=timezone.utc)
        elapsed_days = (datetime.now(timezone.utc) - trial_started).days
        if elapsed_days >= 14:
            return WidgetChatResponse(
                response="Your free trial has expired. Upgrade your plan to continue using your AI assistant.",
                session_id=req.session_id,
                lead_captured=False,
                show_watermark=True,
                trial_expired=True,
            )

    # 3. All plans now have unlimited conversations (limit check removed).

    # 4. Get or create conversation
    conversation_id, is_new = _get_or_create_conversation(tenant["id"], req.session_id)
    logger.info("widget_chat: conversation=%s is_new=%s", conversation_id, is_new)

    # Fire conversation.started webhook for new sessions
    if is_new:
        fire_event_background(tenant["id"], "conversation.started", {
            "session_id": req.session_id,
            "conversation_id": conversation_id,
        })

    # Increment usage counter only for new conversations
    if is_new:
        try:
            db = get_supabase()
            current_used = tenant.get("conversations_used_this_month", 0) or 0
            db.table("tenants").update(
                {"conversations_used_this_month": current_used + 1}
            ).eq("id", tenant["id"]).execute()
        except Exception:
            logger.warning("Failed to increment usage counter for tenant %s", tenant["id"], exc_info=True)

    # 5. Load message history from chat_messages table (last 20 messages)
    messages = _load_chat_history(tenant["id"], req.session_id)
    logger.info(
        "widget_chat: session=%s loaded %d previous messages, first_role=%s",
        req.session_id, len(messages),
        messages[0]["role"] if messages else "NONE",
    )

    # 6. Build system prompt with FAQ (cached per tenant, 5-min TTL)
    tid = tenant["id"]
    db = get_supabase()

    faq_data = _get_cached(f"faq:{tid}", _CHAT_CACHE_TTL)
    if faq_data is None:
        try:
            faq_result = (
                db.table("faq_entries")
                .select("question, answer")
                .eq("tenant_id", tid)
                .eq("is_active", True)
                .execute()
            )
            faq_data = faq_result.data or []
        except Exception:
            logger.warning("faq_entries query failed for tenant %s", tid, exc_info=True)
            faq_data = []
        _set_cache(f"faq:{tid}", faq_data)

    # Load business hours for AI context (cached)
    bh_cache_key = f"bh:{tid}"
    bh_data = _get_cached(bh_cache_key, _CHAT_CACHE_TTL)
    if bh_data is None:
        try:
            bh_result = (
                db.table("business_hours")
                .select("timezone, hours")
                .eq("tenant_id", tid)
                .limit(1)
                .execute()
            )
            bh_data = bh_result.data[0] if bh_result.data else False
        except Exception:
            logger.warning("business_hours query failed for tenant %s", tid, exc_info=True)
            bh_data = False
        _set_cache(bh_cache_key, bh_data)
    if bh_data is False:
        bh_data = None

    # Load AI corrections from owner feedback (cached)
    corrections = _get_cached(f"corr:{tid}", _CHAT_CACHE_TTL)
    if corrections is None:
        try:
            fb_result = (
                db.table("ai_feedback")
                .select("correction")
                .eq("tenant_id", tid)
                .eq("rating", "thumbs_down")
                .not_.is_("correction", "null")
                .order("created_at", desc=True)
                .limit(20)
                .execute()
            )
            corrections = fb_result.data or []
        except Exception:
            logger.warning("ai_feedback query failed for tenant %s", tid, exc_info=True)
            corrections = []
        _set_cache(f"corr:{tid}", corrections)

    # Load crawled website content for AI knowledge (cached)
    website_content = _get_cached(f"wsc:{tid}", _CHAT_CACHE_TTL)
    if website_content is None:
        try:
            from backend.services.website_crawler import get_crawled_content
            website_content = get_crawled_content(tid) or False
        except Exception:
            logger.warning("website_content load failed for tenant %s", tid, exc_info=True)
            website_content = False
        _set_cache(f"wsc:{tid}", website_content)
    if website_content is False:
        website_content = None

    # Load menu items for restaurant tenants
    menu_items = None
    if tenant.get("business_type", "").lower() == "restaurant":
        try:
            menu_result = (
                db.table("menu_items")
                .select("name, description, price, category, available")
                .eq("tenant_id", tenant["id"])
                .order("category")
                .order("sort_order")
                .execute()
            )
            if menu_result.data:
                menu_items = menu_result.data
        except Exception:
            logger.warning("menu_items query failed for tenant %s", tenant["id"], exc_info=True)

    # Load active job listings
    job_listings = None
    try:
        jobs_result = (
            db.table("jobs")
            .select("title, pay_range, schedule, location")
            .eq("tenant_id", tenant["id"])
            .eq("is_active", True)
            .limit(20)
            .execute()
        )
        if jobs_result.data:
            job_listings = jobs_result.data
    except Exception:
        logger.warning("jobs query failed for tenant %s", tenant["id"], exc_info=True)

    # Load bid templates (cached) — enables quote/bid collection in chat
    bid_templates = _get_cached(f"bidtpl:{tid}", _CHAT_CACHE_TTL)
    if bid_templates is None:
        try:
            bt_result = (
                db.table("bid_templates")
                .select("name, description")
                .eq("tenant_id", tid)
                .limit(20)
                .execute()
            )
            bid_templates = bt_result.data if bt_result.data else []
        except Exception:
            logger.warning("bid_templates query failed for tenant %s", tid, exc_info=True)
            bid_templates = []
        _set_cache(f"bidtpl:{tid}", bid_templates)

    # Load custom lead field definitions
    custom_field_defs = []
    try:
        cf_result = (
            db.table("lead_field_definitions")
            .select("field_name, field_type, options, is_required")
            .eq("tenant_id", tid)
            .order("sort_order")
            .limit(20)
            .execute()
        )
        custom_field_defs = cf_result.data if cf_result.data else []
    except Exception:
        logger.debug("custom field defs query failed for tenant %s", tid, exc_info=True)

    # Load active chat flow
    active_flow = None
    active_flow_id = None
    try:
        flow_result = (
            db.table("chat_flows")
            .select("id, flow_json")
            .eq("tenant_id", tenant["id"])
            .eq("is_active", True)
            .limit(1)
            .execute()
        )
        if flow_result.data:
            active_flow = flow_result.data[0].get("flow_json")
            active_flow_id = flow_result.data[0].get("id")
    except Exception:
        logger.warning("chat_flows query failed for tenant %s", tenant["id"], exc_info=True)

    system_prompt = _build_system_prompt(
        tenant, faq_data, bh_data, corrections, website_content,
        menu_items, job_listings, bid_templates=bid_templates or None,
        custom_field_defs=custom_field_defs or None,
    )

    # Inject active flow instructions into system prompt
    if active_flow and active_flow.get("nodes"):
        flow_instructions = _build_flow_instructions(active_flow)
        if flow_instructions:
            system_prompt += flow_instructions

    # Track flow usage in activity_log for new conversations
    if active_flow_id and is_new:
        try:
            log_activity(
                tenant_id=tenant["id"],
                activity_type="flow_used",
                description=f"Chat flow used in conversation",
                metadata={
                    "flow_id": active_flow_id,
                    "session_id": req.session_id,
                    "conversation_id": conversation_id,
                },
            )
        except Exception:
            logger.warning(
                "Failed to log flow_used for tenant %s flow %s",
                tenant["id"], active_flow_id, exc_info=True,
            )

    # Use bot_name from widget config in the system prompt
    if widget.get("bot_name"):
        system_prompt = system_prompt.replace("AI Assistant", widget["bot_name"], 1)

    # 7. Append user message to history
    messages.append({"role": "user", "content": req.message})

    # 8. Call Anthropic
    api_key_present = bool(settings.anthropic_api_key)
    api_key_preview = (settings.anthropic_api_key or "")[:12] + "..." if api_key_present else "MISSING"
    logger.info("widget_chat: calling Anthropic model=%s api_key=%s msg_count=%d",
                MODEL, api_key_preview, len(messages))
    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key, timeout=30.0)
        api_response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
            system=system_prompt,
            messages=messages,
        )
        assistant_text = api_response.content[0].text
        logger.info("widget_chat: Anthropic success, response_len=%d", len(assistant_text))
    except anthropic.AuthenticationError as e:
        logger.error("widget_chat: Anthropic AUTH error — API key invalid: %s", e)
        assistant_text = (
            "I'm sorry, I'm having trouble right now. "
            "Please try again in a moment or contact us directly."
        )
    except anthropic.RateLimitError as e:
        logger.error("widget_chat: Anthropic RATE LIMIT: %s", e)
        assistant_text = (
            "I'm sorry, I'm having trouble right now. "
            "Please try again in a moment or contact us directly."
        )
    except anthropic.APIError as e:
        logger.error("widget_chat: Anthropic API error status=%s: %s", getattr(e, 'status_code', '?'), e)
        assistant_text = (
            "I'm sorry, I'm having trouble right now. "
            "Please try again in a moment or contact us directly."
        )
    except Exception as e:
        logger.exception("widget_chat: unexpected error calling Anthropic: %s", e)
        assistant_text = (
            "I'm sorry, I'm having trouble right now. "
            "Please try again in a moment or contact us directly."
        )

    # 9. Extract order from AI response (restaurant ordering flow)
    order_data = _extract_order_from_response(assistant_text)
    if order_data:
        assistant_text = _strip_order_json_from_response(assistant_text)
        background_tasks.add_task(
            _process_order_from_chat, tenant["id"], req.session_id, order_data,
        )

    # 9b. Extract bid request from AI response (contractor quick-bid flow)
    bid_request_data = _extract_bid_request_from_response(assistant_text)
    if bid_request_data:
        assistant_text = _strip_bid_request_from_response(assistant_text)
        background_tasks.add_task(
            _process_bid_request_from_chat, tenant["id"], req.session_id, bid_request_data,
        )

    # 10. Save user + assistant messages to chat_messages table
    _save_chat_messages(tenant["id"], req.session_id, req.message, assistant_text)

    # Fire conversation.message webhook
    fire_event_background(tenant["id"], "conversation.message", {
        "session_id": req.session_id,
        "user_message": req.message,
        "assistant_message": assistant_text[:500],
    })

    # 11. Lead capture — runs in background so it doesn't slow the response.
    # Scans ALL messages in the session (not just the current one) for
    # email, phone, and name.  Deduplicates by email + tenant_id.
    background_tasks.add_task(
        _capture_leads_from_session, tenant["id"], req.session_id, conversation_id,
    )

    # 12. AI conversation categorization (every 5th message to save API calls)
    total_msgs = len(messages) + 1  # +1 for the assistant reply we just got
    if total_msgs >= 4 and total_msgs % 5 == 0:
        all_msgs = messages + [{"role": "assistant", "content": assistant_text}]
        background_tasks.add_task(
            _categorize_conversation, tenant["id"], req.session_id, all_msgs,
        )

    # 13. AI action item extraction (every 8th message to save API calls)
    if total_msgs >= 6 and total_msgs % 8 == 0:
        all_msgs_for_actions = messages + [{"role": "assistant", "content": assistant_text}]
        background_tasks.add_task(
            _extract_action_items, tenant["id"], req.session_id, all_msgs_for_actions,
        )

    # 14. Response time tracking (first message → first response)
    if total_msgs <= 2:  # First exchange — record response time
        background_tasks.add_task(
            _record_response_metric, tenant["id"], req.session_id, conversation_id,
        )

    # 15. Watermark logic
    if tenant.get("plan") == "free":
        show_watermark = True
    else:
        show_watermark = widget.get("show_watermark", True)

    return WidgetChatResponse(
        response=assistant_text,
        session_id=req.session_id,
        lead_captured=False,  # Actual capture runs in background task
        show_watermark=show_watermark,
    )


@router.get("/config/{api_key}", response_model=WidgetConfigResponse)
@limiter.limit("120/minute")
async def get_config(request: Request, api_key: str):
    """Return widget configuration for the embedded chat widget."""
    widget = _get_widget_config(api_key)
    tenant = _get_tenant(widget["tenant_id"])

    # Force watermark for free plan
    if tenant.get("plan") == "free":
        show_watermark = True
    else:
        show_watermark = widget.get("show_watermark", True)

    # Branding: filter by plan
    plan = tenant.get("plan", "free")
    raw_branding = widget.get("branding") or {}
    branding = _filter_branding_for_plan(raw_branding, plan)
    # Free/growth: enforce powered-by defaults
    if plan in ("free", "growth") and not branding.get("powered_by_text"):
        branding.pop("powered_by_text", None)
        branding.pop("powered_by_url", None)

    # Load menu items for restaurant tenants
    menu_items = None
    if tenant.get("business_type", "").lower() == "restaurant":
        try:
            db = get_supabase()
            menu_result = (
                db.table("menu_items")
                .select("name, description, price, category, available")
                .eq("tenant_id", tenant["id"])
                .eq("available", True)
                .order("category")
                .order("sort_order")
                .execute()
            )
            if menu_result.data:
                menu_items = menu_result.data
        except Exception:
            logger.warning("menu_items config load failed for tenant %s", tenant["id"])

    return WidgetConfigResponse(
        bot_name=widget.get("bot_name", "AI Assistant"),
        primary_color=widget.get("primary_color", "#00BFFF"),
        greeting_message=widget.get("greeting_message"),
        position=widget.get("position", "bottom-right"),
        show_watermark=show_watermark,
        allowed_domains=widget.get("allowed_domains"),
        tenant_id=widget.get("tenant_id"),
        booking_enabled=widget.get("booking_enabled", False),
        branding=branding if branding else None,
        agent_name=tenant.get("business_name"),
        is_online=widget.get("is_online", True),
        offline_message=widget.get("offline_message"),
        menu_items=menu_items,
    )


@router.post("/lead", response_model=WidgetLeadResponse)
@limiter.limit("60/minute")
async def submit_lead(request: Request, req: WidgetLeadRequest, background_tasks: BackgroundTasks):
    """Manually submit or update lead information from the widget."""
    widget = _get_widget_config(req.api_key)
    tenant = _get_tenant(widget["tenant_id"])

    # Find or create conversation
    conversation_id, _ = _get_or_create_conversation(tenant["id"], req.session_id)

    # Build fields from request
    fields: dict[str, str] = {}
    if req.name:
        fields["name"] = req.name
    if req.email:
        fields["email"] = req.email
    if req.phone:
        fields["phone"] = req.phone
    if req.service:
        fields["areas_of_interest"] = req.service

    if not fields:
        raise HTTPException(status_code=400, detail="No lead fields provided")

    db = get_supabase()
    lead_id = None
    is_new = False

    # Dedup by email + client_id (live schema uses client_id, not tenant_id)
    if fields.get("email"):
        existing = (
            db.table("leads")
            .select("id, name, phone")
            .eq("client_id", tenant["id"])
            .eq("email", fields["email"])
            .limit(1)
            .execute()
        )
        if existing.data:
            lead_id = existing.data[0]["id"]
            updates = {k: v for k, v in fields.items()
                       if k != "email" and not existing.data[0].get(k)}
            if updates:
                db.table("leads").update(updates).eq("id", lead_id).execute()

    if not lead_id:
        lead_fields: dict[str, Any] = {
            "client_id": tenant["id"],
            "status": "new",
            **fields,
        }
        try:
            from uuid import UUID
            UUID(conversation_id)
            lead_fields["conversation_id"] = conversation_id
        except (ValueError, AttributeError):
            logger.debug("lead_submit: conversation_id %r is not a UUID, omitting", conversation_id)
        result = db.table("leads").insert(lead_fields).execute()
        if result.data:
            lead_id = result.data[0]["id"]
            is_new = True

    if lead_id:
        background_tasks.add_task(score_lead_background, lead_id)

    if lead_id and is_new:
        logger.info("SMS_TRIGGER[/lead]: new lead created lead_id=%s, about to trigger automation", lead_id)
        try:
            from backend.services.automation_engine import trigger_sequence
            await trigger_sequence(tenant["id"], lead_id, "new_lead")
            logger.info("SMS_TRIGGER[/lead]: trigger_sequence completed for lead %s", lead_id)
        except Exception:
            logger.warning("Failed to trigger automation for lead %s", lead_id, exc_info=True)

        # SMS notification to owner
        logger.info("SMS_TRIGGER[/lead]: about to call SMS notification for lead %s email=%s", lead_id, fields.get("email"))
        try:
            await _send_new_lead_sms_notification(tenant["id"], fields.get("name", "Unknown"), fields)
        except Exception:
            logger.error("SMS_TRIGGER[/lead]: FAILED for lead %s", lead_id, exc_info=True)

        # Email notification to owner
        try:
            await _send_new_lead_email_notification(tenant["id"], fields.get("name", "Unknown"), fields)
        except Exception:
            logger.error("EMAIL_TRIGGER[/lead]: FAILED for lead %s", lead_id, exc_info=True)

    return WidgetLeadResponse(
        lead_id=lead_id,
        updated_fields=list(fields.keys()),
    )


def _get_jwt_claims(authorization: str = Header(...)) -> dict:
    """Extract and verify JWT claims. Returns claims dict."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    from jose import JWTError, jwt as jose_jwt
    try:
        return jose_jwt.decode(
            authorization.removeprefix("Bearer ").strip(),
            settings.api_secret_key,
            algorithms=["HS256"],
        )
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


@router.put("/config/{tenant_id}/online-status")
async def toggle_online_status(
    tenant_id: str,
    body: OnlineStatusRequest,
    claims: dict = Depends(_get_jwt_claims),
):
    """Toggle widget online/offline status. Dashboard-only (JWT required)."""
    if claims.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    try:
        db = get_supabase()
        result = (
            db.table("widget_configs")
            .update({"is_online": body.is_online})
            .eq("tenant_id", tenant_id)
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Widget config not found")
        logger.info(
            "toggle_online_status: tenant=%s is_online=%s",
            tenant_id, body.is_online,
        )
        return {"is_online": body.is_online}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "toggle_online_status FAILED: tenant=%s error=%s",
            tenant_id, e, exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Failed to update online status")


@router.post("/offline-contact")
@limiter.limit("30/minute")
async def submit_offline_contact(request: Request, body: WidgetOfflineContactRequest):
    """Submit contact form when widget is in offline mode. Creates a lead."""
    try:
        # 1. Validate api_key and get widget config / tenant
        widget = _get_widget_config(body.api_key)
        tenant_id = widget["tenant_id"]
        logger.info(
            "offline_contact: tenant=%s name=%s email=%s",
            tenant_id, body.name, body.email,
        )

        db = get_supabase()

        # 2. Dedup by email + client_id (leads table uses client_id)
        lead_id = None
        try:
            existing = (
                db.table("leads")
                .select("id")
                .eq("client_id", tenant_id)
                .eq("email", body.email)
                .limit(1)
                .execute()
            )
            if existing.data:
                lead_id = existing.data[0]["id"]
                # Update existing lead with any new info
                updates: dict[str, Any] = {}
                if body.name:
                    updates["name"] = body.name
                if body.phone:
                    updates["phone"] = body.phone
                if updates:
                    db.table("leads").update(updates).eq("id", lead_id).execute()
                logger.info("offline_contact: updated existing lead %s", lead_id)
        except Exception as dedup_err:
            logger.error(
                "offline_contact: dedup check failed: %s", dedup_err, exc_info=True,
            )

        # 3. Create new lead if no existing one found
        if not lead_id:
            lead_fields: dict[str, Any] = {
                "client_id": tenant_id,
                "name": body.name,
                "email": body.email,
                "status": "new",
                "source": "widget_offline",
            }
            if body.phone:
                lead_fields["phone"] = body.phone
            try:
                result = db.table("leads").insert(lead_fields).execute()
                if result.data:
                    lead_id = result.data[0]["id"]
                    logger.info("offline_contact: created new lead %s", lead_id)
                else:
                    logger.warning("offline_contact: INSERT returned no data")
            except Exception as insert_err:
                logger.error(
                    "offline_contact: lead INSERT failed: %s", insert_err, exc_info=True,
                )

        # 4. Log the message in activity_log
        if lead_id:
            try:
                log_activity(
                    tenant_id=tenant_id,
                    activity_type="offline_message",
                    description=body.message,
                    lead_id=lead_id,
                    metadata={"source": "widget_offline", "email": body.email},
                )
            except Exception:
                logger.warning(
                    "offline_contact: log_activity failed for lead %s",
                    lead_id, exc_info=True,
                )

            # Fire webhook for new offline contact
            try:
                fire_event_background(tenant_id, "lead.created", {
                    "lead_id": lead_id,
                    "name": body.name,
                    "email": body.email,
                    "phone": body.phone,
                    "source": "widget_offline",
                })
            except Exception:
                logger.warning(
                    "offline_contact: fire_event_background failed", exc_info=True,
                )

            # Score the lead
            try:
                score_lead_background(lead_id)
            except Exception:
                logger.warning(
                    "offline_contact: score_lead_background failed for lead %s",
                    lead_id, exc_info=True,
                )

        return {"success": True, "message": "Thank you! We'll get back to you soon."}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("offline_contact FAILED: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to submit contact form")


# --- File Upload ---

_MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB
_ALLOWED_TYPES = {
    "image/jpeg", "image/png", "image/gif", "image/webp",
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


@router.post("/upload")
@limiter.limit("10/minute")
async def upload_file(
    request: Request,
    file: UploadFile,
    api_key: str = Query(...),
    session_id: str = Query(...),
):
    """Upload a file from the chat widget. Returns a public URL.

    Files are stored in Supabase Storage under chat-attachments/{tenant_id}/{session_id}/.
    Max 5 MB. Allowed: images, PDF, Word docs.
    """
    # Validate API key
    db = get_supabase()
    wc = db.table("widget_configs").select("tenant_id").eq("api_key", api_key).limit(1).execute()
    if not wc.data:
        raise HTTPException(status_code=404, detail="Widget not found")
    tenant_id = wc.data[0]["tenant_id"]

    # Validate file type
    content_type = file.content_type or ""
    if content_type not in _ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"File type not allowed: {content_type}")

    # Read file with size check
    data = await file.read()
    if len(data) > _MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 5 MB)")

    # Generate unique path
    ext = (file.filename or "file").rsplit(".", 1)[-1][:10]
    unique_name = f"{uuid.uuid4().hex[:12]}.{ext}"
    path = f"{tenant_id}/{session_id}/{unique_name}"

    try:
        db.storage.from_("chat-attachments").upload(
            path,
            data,
            file_options={"content-type": content_type},
        )
    except Exception:
        logger.exception("File upload failed for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Upload failed")

    # Build public URL
    public_url = f"{settings.supabase_url}/storage/v1/object/public/chat-attachments/{path}"

    return {"url": public_url, "filename": file.filename, "content_type": content_type}


# ---------------------------------------------------------------------------
# Unsubscribe (CAN-SPAM compliance)
# ---------------------------------------------------------------------------

@router.get("/unsubscribe", response_class=HTMLResponse)
@limiter.limit("30/minute")
async def unsubscribe_lead(
    request: Request,
    lid: str = Query(..., description="Lead ID", max_length=50),
    sig: str = Query(..., description="Signature", max_length=200),
):
    """Public endpoint clicked from email unsubscribe links."""
    expected = _make_unsub_sig(lid)
    if not hmac.compare_digest(sig, expected):
        return HTMLResponse(
            "<html><body><h2>Invalid unsubscribe link.</h2></body></html>",
            status_code=400,
        )

    db = get_supabase()
    result = db.table("leads").select("id, unsubscribed").eq("id", lid).limit(1).execute()
    if not result.data:
        return HTMLResponse(
            "<html><body><h2>Lead not found.</h2></body></html>",
            status_code=404,
        )

    if not result.data[0].get("unsubscribed"):
        db.table("leads").update({
            "unsubscribed": True,
            "unsubscribed_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", lid).execute()

    return HTMLResponse(
        "<html><body style='font-family:Arial,sans-serif;text-align:center;padding:60px;'>"
        "<h2>You've been unsubscribed.</h2>"
        "<p>You will no longer receive automated messages from this business.</p>"
        "</body></html>"
    )


# ---------------------------------------------------------------------------
# Email event tracking (open pixel + click redirect)
# ---------------------------------------------------------------------------

# 1x1 transparent GIF
_TRACKING_PIXEL = bytes([
    0x47, 0x49, 0x46, 0x38, 0x39, 0x61, 0x01, 0x00, 0x01, 0x00,
    0x80, 0x00, 0x00, 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0x21,
    0xF9, 0x04, 0x01, 0x00, 0x00, 0x00, 0x00, 0x2C, 0x00, 0x00,
    0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0x02, 0x02, 0x44,
    0x01, 0x00, 0x3B,
])


@router.get("/track/open")
@limiter.limit("300/minute")
async def track_email_open(
    request: Request,
    tid: str = Query(..., description="Tenant ID", max_length=50),
    lid: str = Query("", description="Lead ID", max_length=50),
    eid: str = Query("", description="Execution ID", max_length=50),
):
    """Log an email open event and return a 1x1 tracking pixel."""
    try:
        db = get_supabase()
        db.table("email_events").insert({
            "tenant_id": tid,
            "lead_id": lid or None,
            "event_type": "open",
            "execution_id": eid or None,
        }).execute()
    except Exception:
        pass  # Tracking failures should never affect the user
    from starlette.responses import Response
    return Response(content=_TRACKING_PIXEL, media_type="image/gif")


# ── AI Feedback ──────────────────────────────────────────────────────────────

from pydantic import BaseModel


class AIFeedbackRequest(BaseModel):
    api_key: str
    session_id: str
    message_index: int
    rating: str  # "thumbs_up" or "thumbs_down"
    correction: str | None = None


@router.post("/feedback")
@limiter.limit("30/minute")
async def submit_ai_feedback(request: Request, req: AIFeedbackRequest):
    """Submit thumbs up/down feedback on an AI response from the widget."""
    if req.rating not in ("thumbs_up", "thumbs_down"):
        raise HTTPException(status_code=400, detail="Rating must be thumbs_up or thumbs_down")

    widget = _get_widget_config(req.api_key)
    tenant_id = widget["tenant_id"]

    db = get_supabase()
    db.table("ai_feedback").insert({
        "tenant_id": tenant_id,
        "session_id": req.session_id,
        "message_index": req.message_index,
        "rating": req.rating,
        "correction": req.correction if req.correction and req.correction.strip() else None,
    }).execute()

    return {"status": "ok"}


# Dashboard-authenticated feedback management

from backend.routers.auth import _get_current_tenant as _auth_get_tenant


@router.get("/feedback/{tenant_id}")
async def get_ai_feedback(
    tenant_id: str,
    claims: dict = Depends(_auth_get_tenant),
):
    """Get AI feedback for a tenant (dashboard use)."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db = get_supabase()
    result = (
        db.table("ai_feedback")
        .select("*")
        .eq("tenant_id", tenant_id)
        .order("created_at", desc=True)
        .limit(100)
        .execute()
    )
    return {"feedback": result.data or []}


@router.delete("/feedback/{tenant_id}/{feedback_id}")
async def delete_ai_feedback(
    tenant_id: str,
    feedback_id: str,
    claims: dict = Depends(_auth_get_tenant),
):
    """Delete a feedback entry."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db = get_supabase()
    db.table("ai_feedback").delete().eq("id", feedback_id).eq("tenant_id", tenant_id).execute()
    return {"status": "deleted"}
