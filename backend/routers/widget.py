"""Widget API endpoints — multi-tenant chat, config, and lead capture."""

# NOTE: Do NOT add `from __future__ import annotations` here.
# It breaks FastAPI's parameter introspection — Pydantic body models and
# BackgroundTasks get treated as query params, causing 422 errors.

import logging
import re
from typing import Any
from uuid import uuid4

import anthropic
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from backend.config import settings
from backend.limiter import limiter
from backend.models.database import get_supabase
from backend.models.schemas import (
    WidgetChatRequest,
    WidgetChatResponse,
    WidgetConfigResponse,
    WidgetLeadRequest,
    WidgetLeadResponse,
)
from backend.services.activity import log_activity
from backend.services.lead_scoring import score_lead_background

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/widget", tags=["widget"])

MODEL = "claude-sonnet-4-5-20250929"
MAX_TOKENS = 500
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
        logger.debug("conversations lookup failed for session %s", session_id)

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
        logger.debug("conversations insert failed for session %s", session_id)

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
    elif STANDALONE_NAME_RE.match(text.strip()):
        # Catch bare name responses like "John Smith"
        info["name"] = STANDALONE_NAME_RE.match(text.strip()).group(1)
    email_match = EMAIL_RE.search(text)
    if email_match:
        info["email"] = email_match.group(0)
    phone_match = PHONE_RE.search(text)
    if phone_match:
        info["phone"] = phone_match.group(0)
    return info


def _capture_leads_from_session(
    tenant_id: str, session_id: str, conversation_id: str
) -> None:
    """Background task: scan all user messages in session for contact info,
    create or update a lead.  Deduplicates by email + tenant_id."""
    try:
        messages = _load_chat_history(tenant_id, session_id, limit=50)

        # Scan ALL user messages for contact info
        combined: dict[str, str] = {}
        for msg in messages:
            if msg["role"] != "user":
                continue
            extracted = _extract_lead_info(msg["content"])
            combined.update(extracted)

        if not combined.get("email") and not combined.get("phone"):
            return  # Not enough info to create a lead

        db = get_supabase()

        # Dedup: check by email + tenant_id first
        if combined.get("email"):
            existing = (
                db.table("leads")
                .select("id, name, phone")
                .eq("tenant_id", tenant_id)
                .eq("email", combined["email"])
                .limit(1)
                .execute()
            )
            if existing.data:
                lead = existing.data[0]
                updates: dict[str, str] = {}
                if combined.get("name") and not lead.get("name"):
                    updates["name"] = combined["name"]
                if combined.get("phone") and not lead.get("phone"):
                    updates["phone"] = combined["phone"]
                if updates:
                    db.table("leads").update(updates).eq("id", lead["id"]).execute()
                    log_activity(
                        tenant_id=tenant_id,
                        activity_type="lead_updated",
                        description=f"Lead info captured: {', '.join(updates.keys())}",
                        lead_id=lead["id"],
                        metadata={"source": "widget", "fields": list(updates.keys())},
                    )
                return

        # Create new lead
        lead_fields: dict[str, Any] = {
            "tenant_id": tenant_id,
            "source": "widget",
            "lead_stage": "new",
        }
        for key in ("name", "email", "phone"):
            if combined.get(key):
                lead_fields[key] = combined[key]

        # Only set conversation_id if it looks like a valid UUID
        try:
            from uuid import UUID
            UUID(conversation_id)
            lead_fields["conversation_id"] = conversation_id
        except (ValueError, AttributeError):
            pass

        result = db.table("leads").insert(lead_fields).execute()
        if result.data:
            lead_id = result.data[0]["id"]
            lead_name = combined.get("name", "New visitor")
            log_activity(
                tenant_id=tenant_id,
                activity_type="lead_created",
                description=f"New lead from widget: {lead_name}",
                lead_id=lead_id,
                metadata={"source": "widget", "fields": list(lead_fields.keys())},
            )
            logger.info("Lead captured: %s for tenant %s", lead_id, tenant_id)

            # Fire automation trigger for new leads
            try:
                from backend.services.automation_engine import trigger_sequence
                import asyncio
                asyncio.create_task(trigger_sequence(tenant_id, lead_id, "new_lead"))
            except Exception:
                logger.warning("Failed to trigger automation for lead %s", lead_id, exc_info=True)

            # Score the lead
            try:
                score_lead_background(lead_id)
            except Exception:
                pass

    except Exception:
        logger.warning("Lead capture failed for session %s", session_id, exc_info=True)


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
    conversation_id, is_new = _get_or_create_conversation(tenant["id"], req.session_id)
    logger.info("widget_chat: conversation=%s is_new=%s", conversation_id, is_new)

    # Increment usage counter only for new conversations
    if is_new:
        try:
            db = get_supabase()
            db.table("tenants").update(
                {"conversations_used_this_month": used + 1}
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

    # 6. Build system prompt with FAQ
    db = get_supabase()
    try:
        faq_result = (
            db.table("faq_entries")
            .select("question, answer")
            .eq("tenant_id", tenant["id"])
            .eq("is_active", True)
            .execute()
        )
        faq_data = faq_result.data or []
    except Exception:
        logger.warning("faq_entries query failed for tenant %s", tenant["id"], exc_info=True)
        faq_data = []
    system_prompt = _build_system_prompt(tenant, faq_data)

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
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
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

    # 9. Save user + assistant messages to chat_messages table
    _save_chat_messages(tenant["id"], req.session_id, req.message, assistant_text)

    # 10. Lead capture — runs in background so it doesn't slow the response.
    # Scans ALL messages in the session (not just the current one) for
    # email, phone, and name.  Deduplicates by email + tenant_id.
    background_tasks.add_task(
        _capture_leads_from_session, tenant["id"], req.session_id, conversation_id,
    )

    # 11. Watermark logic
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

    return WidgetConfigResponse(
        bot_name=widget.get("bot_name", "AI Assistant"),
        primary_color=widget.get("primary_color", "#00BFFF"),
        greeting_message=widget.get("greeting_message"),
        position=widget.get("position", "bottom-right"),
        show_watermark=show_watermark,
        allowed_domains=widget.get("allowed_domains"),
        tenant_id=widget.get("tenant_id"),
        booking_enabled=widget.get("booking_enabled", False),
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
        fields["service_interest"] = req.service

    if not fields:
        raise HTTPException(status_code=400, detail="No lead fields provided")

    db = get_supabase()
    lead_id = None
    is_new = False

    # Dedup by email + tenant_id
    if fields.get("email"):
        existing = (
            db.table("leads")
            .select("id, name, phone")
            .eq("tenant_id", tenant["id"])
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
            "tenant_id": tenant["id"],
            "source": "widget",
            "lead_stage": "new",
            **fields,
        }
        try:
            from uuid import UUID
            UUID(conversation_id)
            lead_fields["conversation_id"] = conversation_id
        except (ValueError, AttributeError):
            pass
        result = db.table("leads").insert(lead_fields).execute()
        if result.data:
            lead_id = result.data[0]["id"]
            is_new = True

    if lead_id:
        background_tasks.add_task(score_lead_background, lead_id)

    if lead_id and is_new:
        try:
            from backend.services.automation_engine import trigger_sequence
            import asyncio
            asyncio.create_task(trigger_sequence(tenant["id"], lead_id, "new_lead"))
        except Exception:
            logger.warning("Failed to trigger automation for lead %s", lead_id, exc_info=True)

    return WidgetLeadResponse(
        lead_id=lead_id,
        updated_fields=list(fields.keys()),
    )
