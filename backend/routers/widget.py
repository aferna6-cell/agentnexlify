"""Widget API endpoints — multi-tenant chat, config, and lead capture."""

from __future__ import annotations

import logging
import re
from typing import Any

import anthropic
from fastapi import APIRouter, HTTPException, Request

from backend.config import settings
from backend.models.database import get_supabase
from backend.models.schemas import (
    WidgetChatRequest,
    WidgetChatResponse,
    WidgetConfigResponse,
    WidgetLeadRequest,
    WidgetLeadResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/widget", tags=["widget"])

MODEL = "claude-sonnet-4-5-20250929"
MAX_TOKENS = 500
TEMPERATURE = 0.7

# Lead extraction patterns (ported from LiveChat.jsx:extractInfo)
NAME_RE = re.compile(
    r"(?:i'm|im|i am|my name is|this is|name's|call me)\s+"
    r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
    re.IGNORECASE,
)
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
PHONE_RE = re.compile(r"(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_widget_config(api_key: str) -> dict[str, Any]:
    db = get_supabase()
    result = db.table("widget_configs").select("*").eq("api_key", api_key).limit(1).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Widget not found")
    return result.data[0]


def _get_tenant(tenant_id: str) -> dict[str, Any]:
    db = get_supabase()
    result = db.table("tenants").select("*").eq("id", tenant_id).limit(1).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")
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
) -> tuple[dict[str, Any], bool]:
    """Return (conversation_row, is_new)."""
    db = get_supabase()
    result = (
        db.table("conversations")
        .select("*")
        .eq("tenant_id", tenant_id)
        .eq("session_id", session_id)
        .order("started_at", desc=True)
        .limit(1)
        .execute()
    )
    if result.data:
        return result.data[0], False

    new_conv = (
        db.table("conversations")
        .insert({"tenant_id": tenant_id, "session_id": session_id, "messages": []})
        .execute()
    )
    return new_conv.data[0], True


def _build_system_prompt(tenant: dict, faq_entries: list[dict]) -> str:
    bot_name = "AI Assistant"
    # Get bot_name from widget config if available (caller should pass it),
    # but fall back to a sensible default.
    business_name = tenant.get("business_name", "our company")
    business_type = tenant.get("business_type", "general")
    city = tenant.get("city", "your area")

    faq_block = ""
    if faq_entries:
        lines = [f"Q: {e['question']}\nA: {e['answer']}" for e in faq_entries]
        faq_block = "\n\nFAQ knowledge:\n" + "\n\n".join(lines)

    return (
        f"You are {bot_name} for {business_name} in {city}.\n"
        f"Business type: {business_type}.\n"
        f"Your goal is to help visitors, answer questions, and capture leads.\n"
        f"Collect the visitor's name, email, and phone number. "
        f"Ask for one piece of information at a time, naturally.\n"
        f"Keep responses concise (1-3 sentences).\n"
        f"Never claim to be human. Be helpful and friendly."
        f"{faq_block}"
    )


def _extract_lead_info(text: str) -> dict[str, str]:
    """Extract name, email, and phone from a user message via regex."""
    info: dict[str, str] = {}
    name_match = NAME_RE.search(text)
    if name_match:
        info["name"] = name_match.group(1).strip()
    email_match = EMAIL_RE.search(text)
    if email_match:
        info["email"] = email_match.group(0)
    phone_match = PHONE_RE.search(text)
    if phone_match:
        info["phone"] = phone_match.group(0)
    return info


def _upsert_lead(
    tenant_id: str, conversation_id: str, fields: dict[str, str]
) -> str | None:
    """Upsert lead row. Returns lead_id if anything was written, else None."""
    if not fields:
        return None
    db = get_supabase()

    # Check for existing lead on this conversation
    existing = (
        db.table("leads")
        .select("id, name, email, phone, service_interest")
        .eq("tenant_id", tenant_id)
        .eq("conversation_id", conversation_id)
        .limit(1)
        .execute()
    )

    # Map 'service' to the DB column name 'service_interest'
    db_fields: dict[str, Any] = {}
    for k, v in fields.items():
        if k == "service":
            db_fields["service_interest"] = v
        else:
            db_fields[k] = v

    if existing.data:
        lead = existing.data[0]
        # Only update fields that are currently NULL
        updates = {k: v for k, v in db_fields.items() if not lead.get(k)}
        if not updates:
            return lead["id"]
        db.table("leads").update(updates).eq("id", lead["id"]).execute()
        return lead["id"]
    else:
        db_fields["tenant_id"] = tenant_id
        db_fields["conversation_id"] = conversation_id
        db_fields["source"] = "widget"
        result = db.table("leads").insert(db_fields).execute()
        return result.data[0]["id"]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/chat", response_model=WidgetChatResponse)
async def widget_chat(request: Request, req: WidgetChatRequest):
    """Process a chat message through the multi-tenant widget pipeline."""
    # 1. Look up widget config + tenant
    widget = _get_widget_config(req.api_key)
    tenant = _get_tenant(widget["tenant_id"])

    # 2. Origin check
    _check_origin(request, widget.get("allowed_domains"))

    # 3. Plan limit check
    used = tenant.get("conversations_used_this_month", 0)
    limit = tenant.get("monthly_conversation_limit", 50)
    if used >= limit:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "limit_reached",
                "upgrade_url": "/pricing",
            },
        )

    # 4. Get or create conversation
    conversation, is_new = _get_or_create_conversation(tenant["id"], req.session_id)
    conversation_id = conversation["id"]

    # Increment usage counter only for new conversations
    if is_new:
        db = get_supabase()
        db.table("tenants").update(
            {"conversations_used_this_month": used + 1}
        ).eq("id", tenant["id"]).execute()

    # 5. Load message history from JSONB
    messages: list[dict[str, str]] = conversation.get("messages") or []

    # 6. Build system prompt with FAQ
    db = get_supabase()
    faq_result = (
        db.table("faq_entries")
        .select("question, answer")
        .eq("tenant_id", tenant["id"])
        .eq("is_active", True)
        .execute()
    )
    system_prompt = _build_system_prompt(tenant, faq_result.data or [])

    # Use bot_name from widget config in the system prompt
    if widget.get("bot_name"):
        system_prompt = system_prompt.replace("AI Assistant", widget["bot_name"], 1)

    # 7. Append user message to history
    messages.append({"role": "user", "content": req.message})

    # 8. Call Anthropic
    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        api_response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
            system=system_prompt,
            messages=messages,
        )
        assistant_text = api_response.content[0].text
    except Exception:
        logger.exception("Anthropic API error")
        assistant_text = (
            "I'm sorry, I'm having trouble right now. "
            "Please try again in a moment or contact us directly."
        )

    # 9. Save messages back to conversation JSONB
    messages.append({"role": "assistant", "content": assistant_text})
    db.table("conversations").update(
        {"messages": messages, "last_message_at": "now()"}
    ).eq("id", conversation_id).execute()

    # 10. Lead extraction
    extracted = _extract_lead_info(req.message)
    lead_id = _upsert_lead(tenant["id"], conversation_id, extracted)

    # 11. Watermark logic
    if tenant.get("plan") == "free":
        show_watermark = True
    else:
        show_watermark = widget.get("show_watermark", True)

    return WidgetChatResponse(
        response=assistant_text,
        session_id=req.session_id,
        lead_captured=lead_id is not None,
        show_watermark=show_watermark,
    )


@router.get("/config/{api_key}", response_model=WidgetConfigResponse)
async def get_config(api_key: str):
    """Return widget configuration for the embedded chat widget."""
    widget = _get_widget_config(api_key)
    tenant = _get_tenant(widget["tenant_id"])

    # Force watermark for free plan
    if tenant.get("plan") == "free":
        show_watermark = True
    else:
        show_watermark = widget.get("show_watermark", True)

    return WidgetConfigResponse(
        bot_name=widget.get("bot_name", "AI Assistant"),
        primary_color=widget.get("primary_color", "#00BFFF"),
        greeting_message=widget.get("greeting_message"),
        position=widget.get("position", "bottom-right"),
        show_watermark=show_watermark,
        allowed_domains=widget.get("allowed_domains"),
    )


@router.post("/lead", response_model=WidgetLeadResponse)
async def submit_lead(req: WidgetLeadRequest):
    """Manually submit or update lead information from the widget."""
    widget = _get_widget_config(req.api_key)
    tenant = _get_tenant(widget["tenant_id"])

    # Find conversation
    db = get_supabase()
    conv_result = (
        db.table("conversations")
        .select("id")
        .eq("tenant_id", tenant["id"])
        .eq("session_id", req.session_id)
        .order("started_at", desc=True)
        .limit(1)
        .execute()
    )
    if not conv_result.data:
        raise HTTPException(status_code=404, detail="Conversation not found")

    conversation_id = conv_result.data[0]["id"]

    # Build fields from request
    fields: dict[str, str] = {}
    if req.name:
        fields["name"] = req.name
    if req.email:
        fields["email"] = req.email
    if req.phone:
        fields["phone"] = req.phone
    if req.service:
        fields["service"] = req.service

    if not fields:
        raise HTTPException(status_code=400, detail="No lead fields provided")

    lead_id = _upsert_lead(tenant["id"], conversation_id, fields)

    return WidgetLeadResponse(
        lead_id=lead_id,
        updated_fields=list(fields.keys()),
    )
