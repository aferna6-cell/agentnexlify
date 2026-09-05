"""SMS conversation agent — multi-turn AI replies over the Twilio SMS channel.

Phase 3 of plans/nexlify-capabilities-roadmap_plan.md. Wired from
backend/routers/twilio_webhooks.py's ``/sms-reply`` endpoint behind the
per-tenant ``tenants.sms_agent_enabled`` flag (migration 193). When the flag
is off (default), that endpoint keeps its existing deprecated-410 behavior —
this module is never called.

Reuses the widget chat pipeline's KB grounding + system-prompt builder
(backend.routers.widget_chat_helpers) so an SMS conversation is grounded in
the same tenant knowledge as the widget, with SMS-shaped output (short,
plain text, no markdown) layered on top via a channel instruction appended
to the system prompt.

Compliance is checked BEFORE any Claude call, in this order:
  1. STOP/START keyword (sms_compliance.classify_inbound)
  2. Durable opt-out suppression (sms_compliance.is_suppressed)
  3. Daily rate limit (sms_rate_limiter.check_sms_rate_limit)
  4. Handoff lockout — a conversation already tagged 'handoff' never calls
     Claude again; the inbound message is saved and the owner replies
     manually via the inbox.

Claude spend is metered like widget extract_tags: reserve → provider →
record, or release on provider / record-persist failure. Tenant/policy
load failure and a hard cap fail closed here (no provider call) and
return the existing Claude-error fallback SMS. A later reserve RPC
outage is different: reserve_ai_tokens returns allowed=True / reason=
guard_unavailable and this helper may still call the provider without
persisting usage.

Same Twilio MessageSid redelivery is claimed on ``idempotency_keys``
(key ``twilio:sms_agent:<MessageSid>``) after the silent compliance
gates and before increment/reserve/provider/send. A duplicate or
in-flight claim returns None so the webhook does not send again.
Empty MessageSid cannot be claimed (residual). A crash after claim-win
and before ``record_response`` leaves an in-flight row; the existing
helper then skips later deliveries (same residual as Stripe).

Session mapping reuses the existing 'sms_<digits>' session_id convention
established in backend/routers/sms.py (outbound "text this lead" flow) and
the conversations.channel column (migration 057) — no new migration needed
for that part; migration 193 only adds the tenant-level opt-in flag.

WARNING: PEP 563 deferred annotations are incompatible with FastAPI. This
module is not a router, but per project convention no file adjacent to the
FastAPI app adds ``from __future__ import annotations``.
"""

import logging
import re
from typing import Any

from backend.routers.widget_chat_helpers import (
    MODEL,
    _build_system_prompt,
    _compact_messages_for_llm,
    _load_chat_history,
    _query_kb_articles,
    _save_chat_messages,
)
from backend.services import sms_compliance, sms_rate_limiter, twilio_tenant
from backend.services.ai_usage_guard import (
    estimate_widget_chat_tokens,
    record_ai_usage,
    release_ai_token_reservation,
    reserve_ai_tokens,
)
from backend.services.idempotency import check_and_record, delete_key, record_response
from backend.services.llm_runtime import call_claude_messages, resolve_string_setting
from backend.services.twilio_service import send_sms

logger = logging.getLogger(__name__)

# SMS replies stay well under 3 segments (3 * 153 GSM-7 chars ~= 459) so a
# reply never gets carrier-truncated or split into a confusing multi-part text.
SMS_MAX_CHARS = 450
SMS_MAX_TOKENS = 220
SMS_TEMPERATURE = 0.7

HANDOFF_MARKER = "HANDOFF_REQUESTED"
_HANDOFF_ACK = "Got it — a team member will text you back shortly."
_CLAUDE_ERROR_FALLBACK = "Sorry, having trouble replying right now. We'll follow up shortly."
_EMPTY_REPLY_FALLBACK = "Thanks for the message — we'll follow up shortly."

_ESCALATION_REASON = "Visitor requested a human via SMS"
_ESCALATION_PRIORITY = "normal"
REPLY_OPERATION = "sms_agent.reply"
_IDEMPOTENCY_PROVIDER = "twilio"


# ---------------------------------------------------------------------------
# Session / conversation / lead mapping
# ---------------------------------------------------------------------------


def _normalize_phone_for_session(phone: str) -> str:
    return re.sub(r"[\s+\-()]", "", phone or "")


def sms_session_id(from_number: str) -> str:
    """Stable per-(tenant, caller) session key.

    Mirrors backend/routers/sms.py's `sms_<digits>` convention exactly, so a
    caller who has texted a "text this lead" outbound message and later
    texts back inbound lands in the SAME conversation/chat_messages thread.
    """
    return f"sms_{_normalize_phone_for_session(from_number)}"


def _find_or_create_conversation(db: Any, tenant_id: str, session_id: str) -> dict:
    """Find-or-create the conversations row for this SMS thread.

    Returns a dict with at least ``id`` and ``tags`` so the caller can check
    the handoff lockout without a second round trip. Sets ``channel='sms'``
    explicitly on insert (migration 057 only backfilled pre-existing rows).
    """
    try:
        result = (
            db.table("conversations")
            .select("id, tags")
            .eq("client_id", tenant_id)
            .eq("session_id", session_id)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0]
    except Exception:
        logger.warning(
            "sms_agent: conversations lookup failed tenant=%s", tenant_id, exc_info=True
        )

    try:
        inserted = (
            db.table("conversations")
            .insert({"client_id": tenant_id, "session_id": session_id, "channel": "sms"})
            .execute()
        )
        if inserted.data:
            return inserted.data[0]
    except Exception:
        logger.warning(
            "sms_agent: conversations insert failed tenant=%s", tenant_id, exc_info=True
        )

    # Fallback: session_id is stable even if the DB round trip failed, so the
    # caller can still check the (empty) tags and proceed.
    return {"id": session_id, "tags": []}


def _tag_conversation_handoff(
    db: Any, tenant_id: str, conversation_id: str, existing_tags: list[str] | None
) -> None:
    tags = list(existing_tags or [])
    if "handoff" not in tags:
        tags.append("handoff")
    try:
        db.table("conversations").update({"tags": tags}).eq("id", conversation_id).eq(
            "client_id", tenant_id
        ).execute()
    except Exception:
        logger.warning(
            "sms_agent: failed to tag conversation handoff tenant=%s conversation=%s",
            tenant_id,
            conversation_id,
            exc_info=True,
        )


def _find_or_create_lead(db: Any, tenant_id: str, phone: str) -> dict | None:
    """Find-or-create a lead by exact phone match.

    Mirrors backend/routers/twilio_webhooks.py::_find_lead_by_phone (exact
    ``eq`` match — same convention already used for missed-call text-back
    lead linking). Best-effort: any DB failure logs and returns None, it
    never blocks the conversation.
    """
    try:
        result = (
            db.table("leads")
            .select("id, name, phone")
            .eq("client_id", tenant_id)
            .eq("phone", phone)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0]
    except Exception:
        logger.warning(
            "sms_agent: lead lookup failed tenant=%s", tenant_id, exc_info=True
        )
        return None

    try:
        inserted = (
            db.table("leads")
            .insert(
                {
                    "client_id": tenant_id,
                    "phone": phone,
                    "status": "new",
                    "source": "sms",
                }
            )
            .execute()
        )
        if inserted.data:
            return inserted.data[0]
    except Exception:
        logger.warning(
            "sms_agent: lead insert failed tenant=%s", tenant_id, exc_info=True
        )
    return None


# ---------------------------------------------------------------------------
# Grounding loads (mirrors widget_chat_context.build_chat_context, without
# the widget's per-worker TTL cache — SMS traffic volume is far lower)
# ---------------------------------------------------------------------------


def _load_widget_config(db: Any, tenant_id: str) -> dict | None:
    try:
        result = (
            db.table("widget_configs")
            .select("custom_instructions, knowledge_base")
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception:
        logger.warning(
            "sms_agent: widget_configs lookup failed tenant=%s", tenant_id, exc_info=True
        )
        return None


def _load_faq_entries(db: Any, tenant_id: str) -> list[dict]:
    try:
        result = (
            db.table("faq_entries")
            .select("question, answer")
            .eq("tenant_id", tenant_id)
            .eq("is_active", True)
            .execute()
        )
        return result.data or []
    except Exception:
        logger.warning(
            "sms_agent: faq_entries lookup failed tenant=%s", tenant_id, exc_info=True
        )
        return []


def _load_business_hours(db: Any, tenant_id: str) -> dict | None:
    try:
        result = (
            db.table("business_hours")
            .select("timezone, hours")
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception:
        logger.warning(
            "sms_agent: business_hours lookup failed tenant=%s", tenant_id, exc_info=True
        )
        return None


# ---------------------------------------------------------------------------
# Reply shaping
# ---------------------------------------------------------------------------


def _strip_handoff_marker(text: str) -> str:
    return text.replace(HANDOFF_MARKER, "").strip()


def _clean_for_sms(text: str) -> str:
    """Strip markdown formatting and hard-cap length for SMS."""
    cleaned = re.sub(r"\*\*(.*?)\*\*", r"\1", text or "")
    cleaned = re.sub(r"[*_`#]", "", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    if len(cleaned) > SMS_MAX_CHARS:
        cleaned = cleaned[: SMS_MAX_CHARS - 3].rstrip() + "..."
    return cleaned


def _create_sms_escalation(
    db: Any, *, tenant_id: str, session_id: str, conversation_id: str
) -> dict | None:
    """Best-effort escalation create. Never raises — the escalations module
    (backend/services/escalations.py) is built by a different lane; import
    lazily so this file works whether or not it has landed yet."""
    try:
        from backend.services.escalations import create_escalation

        return create_escalation(
            db,
            client_id=tenant_id,
            source="sms",
            source_ref=session_id,
            conversation_id=conversation_id,
            reason=_ESCALATION_REASON,
            priority=_ESCALATION_PRIORITY,
        )
    except Exception:
        logger.warning(
            "sms_agent: create_escalation unavailable or failed tenant=%s session=%s",
            tenant_id,
            session_id,
            exc_info=True,
        )
        return None


# ---------------------------------------------------------------------------
# Outbound send dispatch
# ---------------------------------------------------------------------------


async def send_sms_agent_reply(tenant_id: str, to: str, body: str) -> None:
    """Send an sms_agent reply via the tenant's own Twilio (BYO) when
    connected, else the shared platform pool.

    Mirrors the provider-dispatch order in backend/services/os_actions/sms.py
    (``_pick_provider`` / ``_send_via_twilio_byo`` / ``_send_via_twilio_platform``)
    — kept as a local plain-bool helper here since that module's send
    functions return an ``ActionResult`` tied to the action-run pipeline, not
    a standalone success/failure the caller can act on directly. Called from
    backend/routers/twilio_webhooks.py after ``handle_inbound_sms`` returns a
    reply. Never raises — logs and swallows send failures on both paths.
    """
    try:
        if twilio_tenant.is_connected(tenant_id):
            result = await twilio_tenant.send_sms_via_tenant(
                tenant_id=tenant_id, to=to, body=body
            )
            if result.get("success"):
                return
            logger.warning(
                "sms_agent: twilio_byo send failed tenant=%s detail=%s",
                tenant_id,
                result.get("detail"),
            )
    except Exception:
        logger.warning(
            "sms_agent: twilio_byo dispatch raised tenant=%s", tenant_id, exc_info=True
        )

    sent = await send_sms(to=to, body=body, tenant_id=tenant_id)
    if not sent:
        logger.warning("sms_agent: platform send_sms failed tenant=%s", tenant_id)


# ---------------------------------------------------------------------------
# Budget + inbound-delivery claim
# ---------------------------------------------------------------------------


def _load_reply_budget_tenant(db: Any, tenant_id: str) -> dict[str, Any] | None:
    """Load the tenant row needed for a pack-aware reservation.

    Returns None when the row is missing or the lookup throws. Callers must
    fail closed before the provider — do not invent a free-plan cap (that
    would falsely block a paying tenant or ignore purchased packs) and do
    not call Claude unmetered.
    """
    try:
        rows = (
            db.table("tenants")
            .select(
                "id, plan, ai_monthly_token_alert_threshold, ai_monthly_token_hard_limit"
            )
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        ).data or []
    except Exception:
        # Do not attach the lookup exception: it may contain connection or
        # customer context. Tenant id is enough to find the row.
        logger.warning(
            "sms_agent: tenant load failed tenant=%s",
            tenant_id,
        )
        return None
    if not rows:
        logger.warning(
            "sms_agent: tenant missing tenant=%s — failing closed before provider",
            tenant_id,
        )
        return None
    return {**rows[0], "id": tenant_id}


def _sms_agent_event_id(provider_message_id: str) -> str:
    return f"sms_agent:{provider_message_id.strip()}"


def _sms_agent_delivery_key(provider_message_id: str) -> str:
    sid = (provider_message_id or "").strip()
    if not sid:
        return ""
    return f"{_IDEMPOTENCY_PROVIDER}:{_sms_agent_event_id(sid)}"


def _persist_claude_fallback(tenant_id: str, session_id: str, body: str) -> str:
    """Existing customer-facing Claude-error SMS. Does not invent a new body."""
    reply_text = _CLAUDE_ERROR_FALLBACK
    _save_chat_messages(tenant_id, session_id, body, reply_text)
    return reply_text


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------


async def handle_inbound_sms(
    db: Any,
    *,
    tenant: dict,
    from_number: str,
    to_number: str,
    body: str,
    provider_message_id: str,
) -> str | None:
    """Multi-turn SMS conversational reply.

    Returns the reply text to send back to ``from_number``, or ``None`` when
    the turn must stay silent — opted out, rate-limited, already in human
    handoff, or a duplicate Twilio MessageSid delivery. Budget misses and
    provider errors use the existing Claude-error fallback SMS.
    """
    tenant_id = tenant["id"]
    session_id = sms_session_id(from_number)
    body = body or ""

    # 1. STOP/START keyword — before anything else, mirrors os_inbound.py.
    kind = sms_compliance.classify_inbound(body)
    if kind == "opt_out":
        sms_compliance.record_opt_out(db, tenant_id, from_number, source="sms_stop")
        logger.info(
            "sms_agent: opt-out recorded tenant=%s message_id=%s",
            tenant_id,
            provider_message_id,
        )
        return None
    if kind == "opt_in":
        sms_compliance.record_opt_in(db, tenant_id, from_number)
        logger.info(
            "sms_agent: opt-in recorded tenant=%s message_id=%s",
            tenant_id,
            provider_message_id,
        )
        return None

    # 2. Durable opt-out suppression (fails closed — see sms_compliance.py).
    if sms_compliance.is_suppressed(db, tenant_id, from_number):
        logger.info("sms_agent: suppressed recipient tenant=%s", tenant_id)
        return None

    # 3. Daily rate limit — before any AI reply is generated.
    plan = tenant.get("plan") or "free"
    if not sms_rate_limiter.check_sms_rate_limit(tenant_id, plan):
        logger.info("sms_agent: rate limit reached tenant=%s", tenant_id)
        return None

    conversation = _find_or_create_conversation(db, tenant_id, session_id)
    conversation_id = conversation.get("id")
    existing_tags = conversation.get("tags") or []

    # 4. Handoff lockout — a team member owns this thread; save the inbound
    # message but never call Claude again until the tag is cleared.
    if "handoff" in existing_tags:
        _save_chat_messages(tenant_id, session_id, body, None)
        logger.info(
            "sms_agent: handoff lockout active tenant=%s session=%s",
            tenant_id,
            session_id,
        )
        return None

    # 5. Lead mapping by phone — best-effort, never blocks the conversation.
    _find_or_create_lead(db, tenant_id, from_number)

    # 6. Durable MessageSid claim — after silent compliance, before increment
    # or Claude. Same inbound redelivery must not reserve, call, or send twice.
    delivery_key = _sms_agent_delivery_key(provider_message_id)
    if delivery_key:
        is_new, _cached = await check_and_record(
            db, _IDEMPOTENCY_PROVIDER, _sms_agent_event_id(provider_message_id)
        )
        if not is_new:
            logger.info(
                "sms_agent: duplicate inbound delivery tenant=%s", tenant_id
            )
            return None

    try:
        # From here on a reply WILL be attempted (normal answer, handoff ack,
        # or the Claude-failure fallback) — count it against the daily SMS
        # budget.
        sms_rate_limiter.increment_sms_count(tenant_id)

        # 7. Build multi-turn context, reusing the widget pipeline's grounding +
        # system-prompt builder.
        history = _load_chat_history(tenant_id, session_id, limit=20)
        history_for_model = _compact_messages_for_llm(history)

        widget_config = _load_widget_config(db, tenant_id)
        faq_entries = _load_faq_entries(db, tenant_id)
        business_hours = _load_business_hours(db, tenant_id)

        kb_article_refs: list = []
        try:
            kb_article_refs = await _query_kb_articles(body)
        except Exception:
            logger.warning(
                "sms_agent: kb article retrieval failed tenant=%s", tenant_id
            )

        system_prompt = _build_system_prompt(
            tenant,
            faq_entries,
            business_hours,
            custom_instructions=(widget_config or {}).get("custom_instructions"),
            knowledge_base=(widget_config or {}).get("knowledge_base"),
            kb_article_refs=kb_article_refs or None,
        )
        system_prompt += (
            "\n\nCHANNEL: This conversation is over SMS text message, not the "
            "website chat widget.\n"
            "- Reply in plain text only — no markdown, no bullet lists, no links "
            "unless it is a real URL.\n"
            f"- Keep the reply under {SMS_MAX_CHARS} characters — SMS is billed per "
            "segment.\n"
            "- If the visitor explicitly asks to speak with a human, a real "
            "person, or a team member, include the exact marker HANDOFF_REQUESTED "
            "at the end of your reply."
        )

        llm_messages = history_for_model + [{"role": "user", "content": body}]

        budget_tenant = _load_reply_budget_tenant(db, tenant_id)
        if budget_tenant is None:
            logger.warning(
                "sms_agent: budget tenant unavailable tenant=%s — "
                "failing closed before provider",
                tenant_id,
            )
            reply_text = _persist_claude_fallback(tenant_id, session_id, body)
        else:
            reservation = reserve_ai_tokens(
                tenant=budget_tenant,
                estimated_tokens=estimate_widget_chat_tokens(
                    system_prompt=system_prompt,
                    messages=llm_messages,
                    max_tokens=SMS_MAX_TOKENS,
                ),
                operation=REPLY_OPERATION,
                session_id=session_id,
            )
            if not reservation.allowed:
                logger.warning(
                    "sms_agent: hard cap blocked tenant=%s session=%s",
                    tenant_id,
                    session_id,
                )
                reply_text = _persist_claude_fallback(tenant_id, session_id, body)
            else:
                try:
                    result = await call_claude_messages(
                        operation=REPLY_OPERATION,
                        model=resolve_string_setting("widget_chat_model", MODEL),
                        max_tokens=SMS_MAX_TOKENS,
                        temperature=SMS_TEMPERATURE,
                        system=system_prompt,
                        messages=llm_messages,
                        timeout=30.0,
                        max_retries=1,
                        metadata={
                            "tenant_id": tenant_id,
                            "session_id": session_id,
                            "channel": "sms",
                        },
                    )
                except Exception:
                    release_ai_token_reservation(reservation)
                    logger.warning(
                        "sms_agent: provider error tenant=%s session=%s",
                        tenant_id,
                        session_id,
                    )
                    reply_text = _persist_claude_fallback(tenant_id, session_id, body)
                else:
                    record_ai_usage(
                        reservation=reservation,
                        result=result,
                        operation=REPLY_OPERATION,
                        session_id=session_id,
                        model=resolve_string_setting("widget_chat_model", MODEL),
                    )
                    assistant_text = result.text or ""
                    if HANDOFF_MARKER in assistant_text:
                        _tag_conversation_handoff(
                            db, tenant_id, conversation_id, existing_tags
                        )
                        _create_sms_escalation(
                            db,
                            tenant_id=tenant_id,
                            session_id=session_id,
                            conversation_id=conversation_id,
                        )
                        reply_text = _HANDOFF_ACK
                        _save_chat_messages(
                            tenant_id, session_id, body, reply_text
                        )
                    else:
                        reply_text = (
                            _clean_for_sms(_strip_handoff_marker(assistant_text))
                            or _EMPTY_REPLY_FALLBACK
                        )
                        _save_chat_messages(
                            tenant_id, session_id, body, reply_text
                        )
    except Exception:
        if delivery_key:
            await delete_key(db, delivery_key)
        raise

    if delivery_key:
        await record_response(
            db, delivery_key, 200, {"status": "processed"}
        )
    return reply_text
