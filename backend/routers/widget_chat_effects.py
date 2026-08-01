"""Post-response side effects for the widget chat pipeline (issue #472).

Everything that happens AROUND the visitor-facing reply: new-conversation
notifications, the usage counter, handoff detection + owner alerts, and
the background-task fan-out (OS bridge, lead capture, enrichment,
categorization, action items, response metrics). Moved verbatim from the
widget_chat route body; behavior is unchanged.

Do NOT add 'from __future__ import annotations' — breaks Pydantic on FastAPI.
"""

import logging

from fastapi import BackgroundTasks

from backend.models.database import get_service_supabase
from backend.models.schemas import WidgetChatRequest
from backend.services.escalations import create_escalation
from backend.services.os_inbound_bridge import bridge_widget, is_bridge_enabled
from backend.services.webhook_dispatcher import fire_event_background
from backend.routers.widget_chat_helpers import _record_response_metric
from backend.routers.widget_lead_helpers import (
    _capture_leads_from_session,
    _categorize_conversation,
    _enrich_lead_from_message,
    _extract_action_items,
    _extract_lead_info,
)

logger = logging.getLogger(__name__)


def on_new_conversation(
    background_tasks: BackgroundTasks,
    tenant: dict,
    req: WidgetChatRequest,
    conversation_id,
) -> None:
    """Fire conversation.started webhook + optional owner email for new sessions."""
    fire_event_background(
        tenant["id"],
        "conversation.started",
        {
            "session_id": req.session_id,
            "conversation_id": conversation_id,
        },
    )
    # Email the owner that a new conversation came in (opt-in; background
    # so it never delays the visitor reply). Lightweight: first message +
    # inbox link, not a transcript.
    if tenant.get("conversation_email_notify_enabled"):
        from backend.services.conversation_notify import notify_new_conversation

        background_tasks.add_task(notify_new_conversation, tenant, req.message)


def increment_usage_counter(db, tenant: dict) -> None:
    """Bump conversations_used_this_month with compare-and-swap so concurrent
    requests don't lose increments. Only called for new conversations."""
    try:
        for _attempt in range(3):
            row = (
                db.table("tenants")
                .select("conversations_used_this_month")
                .eq("id", tenant["id"])
                .limit(1)
                .execute()
                .data
            )
            old_val = (
                (row[0].get("conversations_used_this_month") or 0) if row else 0
            )
            # Conditional update: only succeeds if the value hasn't changed
            query = (
                db.table("tenants")
                .update({"conversations_used_this_month": old_val + 1})
                .eq("id", tenant["id"])
            )
            if old_val == 0:
                # NULL and 0 both need to match — use is_ for NULL
                query = query.is_("conversations_used_this_month", "null")
            else:
                query = query.eq("conversations_used_this_month", old_val)
            result = query.execute()
            if result.data:
                break  # update succeeded
        else:
            logger.warning(
                "Usage counter CAS failed for tenant %s after 3 attempts",
                tenant["id"],
            )
    except Exception:
        logger.warning(
            "Failed to increment usage counter for tenant %s",
            tenant["id"],
            exc_info=True,
        )


async def handle_handoff_detection(
    db, tenant: dict, req: WidgetChatRequest, conversation_id, assistant_text: str
) -> tuple[str, bool]:
    """Stage 9c — detect HANDOFF_REQUESTED in the model reply.

    Strips the marker, tags the conversation, and notifies the owner via
    SMS + email + webhook. Returns (clean_text, handoff_triggered).
    """
    if "HANDOFF_REQUESTED" not in assistant_text:
        return assistant_text, False

    assistant_text = assistant_text.replace("HANDOFF_REQUESTED", "").strip()
    # Tag conversation as handoff
    try:
        conv_result = (
            db.table("conversations")
            .select("id, tags")
            .eq("client_id", tenant["id"])
            .eq("session_id", req.session_id)
            .limit(1)
            .execute()
        )
        if conv_result.data:
            existing_tags = conv_result.data[0].get("tags") or []
            if "handoff" not in existing_tags:
                updated_tags = existing_tags + ["handoff"]
                db.table("conversations").update({"tags": updated_tags}).eq(
                    "id", conv_result.data[0]["id"]
                ).execute()
    except Exception:
        logger.warning(
            "Failed to tag conversation as handoff for session %s",
            req.session_id,
            exc_info=True,
        )

    # Send notification to team (SMS + email + webhook)
    try:
        owner_phone = tenant.get("notification_phone")
        if owner_phone and tenant.get("sms_notifications_enabled"):
            from backend.services.twilio_service import send_sms

            await send_sms(
                owner_phone,
                f"[{tenant.get('business_name') or 'Business'}] A customer requested to speak with a team member. Check your inbox.",
                tenant_id=tenant.get("id"),
            )
    except Exception:
        logger.warning("Failed to send handoff SMS notification", exc_info=True)

    try:
        owner_email = tenant.get("owner_email")
        if owner_email:
            from backend.services.email_sender import send_email

            biz = tenant.get("business_name") or "Your business"
            await send_email(
                to=owner_email,
                subject=f"[{biz}] Customer requesting a human",
                body_html=(
                    "<p>A customer on your website chat is asking to speak with a team member.</p>"
                    "<p>Open the <a href='https://app.agentnexlify.com/dashboard/conversations'>Conversations inbox</a> to reply.</p>"
                ),
                tenant_id=tenant["id"],
            )
    except Exception:
        logger.warning("Failed to send handoff email notification", exc_info=True)

    # Persist a first-class escalation row alongside the tag (Phase 1a of
    # plans/nexlify-capabilities-roadmap_plan.md). notify=False: the SMS +
    # email blocks above already notified the owner for this widget
    # handoff — create_escalation's own notify path exists for sources
    # (email/sms/os) that don't have an inline block like this one.
    # source_ref=conversation_id keeps create_escalation idempotent if this
    # detection ever fires twice for the same conversation. conversation_id
    # can fall back to a non-UUID session_id when the conversations insert
    # failed upstream (see widget_chat_helpers._get_or_create_conversation);
    # only pass it through as the FK column when it's a real UUID.
    from uuid import UUID as _UUID

    try:
        _UUID(str(conversation_id))
        safe_conversation_id = conversation_id
    except (ValueError, AttributeError, TypeError):
        safe_conversation_id = None
    create_escalation(
        db,
        client_id=tenant["id"],
        source="widget",
        source_ref=str(conversation_id),
        conversation_id=safe_conversation_id,
        reason=req.message[:280] if req.message else "",
        notify=False,
    )

    fire_event_background(
        tenant["id"],
        "conversation.handoff",
        {
            "session_id": req.session_id,
            "conversation_id": conversation_id,
        },
    )

    return assistant_text, True


def schedule_post_response_effects(
    background_tasks: BackgroundTasks,
    *,
    tenant: dict,
    widget: dict,
    req: WidgetChatRequest,
    conversation_id,
    messages: list[dict],
    assistant_text: str,
    saved_rows: list[dict],
) -> bool:
    """Stages 10b-14 — everything scheduled after the reply is saved.

    OS bridge, conversation.message webhook, lead capture + enrichment,
    periodic categorization / action-item extraction, and the first-response
    metric. Returns whether contact info was detected (`lead_captured`).
    """
    # 10b. Bridge user-side message into the Agent OS inbox (background, opt-in
    # per tenant). The bridge dedup-anchors on chat_messages.id so retries from
    # this same request are idempotent. Skipped silently when toggle is off or
    # the user row didn't insert.
    user_row = next(
        (r for r in saved_rows if r.get("role") == "user"),
        None,
    )
    if user_row and req.message:
        try:
            db_for_bridge = get_service_supabase()
            if is_bridge_enabled(db_for_bridge, tenant["id"], "widget"):
                background_tasks.add_task(
                    bridge_widget,
                    db_for_bridge,
                    tenant["id"],
                    conversation_id,
                    str(user_row["id"]),
                    req.message,
                    {"session_id": req.session_id},
                )
        except Exception:
            logger.warning("os_bridge: widget bridge scheduling failed", exc_info=True)

    # Fire conversation.message webhook
    fire_event_background(
        tenant["id"],
        "conversation.message",
        {
            "session_id": req.session_id,
            "user_message": req.message,
            "assistant_message": assistant_text[:500],
        },
    )

    # 11. Lead capture — runs in background so it doesn't slow the response.
    # Scans ALL messages in the session (not just the current one) for
    # email, phone, and name.  Deduplicates by email + tenant_id.

    # Synchronously detect whether contact info is present so the response
    # can set lead_captured=True immediately (background task does the actual
    # DB write; this check only affects what we report back to the caller).
    has_contact = bool(_extract_lead_info(req.message))
    if not has_contact:
        for _m in messages[-5:]:  # scan last 5 messages for prior contact info
            if _m.get("role") == "user" and _extract_lead_info(_m.get("content", "")):
                has_contact = True
                break

    background_tasks.add_task(
        _capture_leads_from_session,
        tenant["id"],
        req.session_id,
        conversation_id,
        req.attribution,
    )

    # 11b. Structured-extractor lead enrichment (opt-in per tenant).
    # Runs the structured_extractor managed agent on this single message
    # to fill in name/email/phone/interest/timeline/budget fields the
    # regex parser missed. Background task → zero latency impact on the
    # response. Gated on widget_configs.enable_structured_lead_parser
    # (migration 103, default false). See specs/lead-parser-replacement_spec.md.
    if widget.get("enable_structured_lead_parser"):
        background_tasks.add_task(
            _enrich_lead_from_message,
            tenant["id"],
            req.session_id,
            req.message,
            _extract_lead_info(req.message),
        )

    # 12. AI conversation categorization (every 5th message to save API calls)
    total_msgs = len(messages) + 2  # current user message + assistant reply
    if total_msgs >= 4 and total_msgs % 5 == 0:
        all_msgs = messages + [
            {"role": "user", "content": req.message},
            {"role": "assistant", "content": assistant_text},
        ]
        background_tasks.add_task(
            _categorize_conversation,
            tenant["id"],
            req.session_id,
            all_msgs,
        )

    # 13. AI action item extraction (every 8th message to save API calls)
    if total_msgs >= 6 and total_msgs % 8 == 0:
        all_msgs_for_actions = messages + [
            {"role": "user", "content": req.message},
            {"role": "assistant", "content": assistant_text},
        ]
        background_tasks.add_task(
            _extract_action_items,
            tenant["id"],
            req.session_id,
            all_msgs_for_actions,
        )

    # 14. Response time tracking (first message → first response)
    if total_msgs <= 2:  # First exchange — record response time
        background_tasks.add_task(
            _record_response_metric,
            tenant["id"],
            req.session_id,
            conversation_id,
        )

    return has_contact
