"""First-class escalation records (Phase 1a of the Nexlify capabilities
roadmap — replaces the "handoff" magic-string-only flow).

Prior to this module, "handing off to a human" meant appending the literal
string "handoff" to ``conversations.tags``. That worked as a short-circuit
signal for the widget chat guard (``widget_chat_guards.check_handoff_mode``)
but gave the dashboard nothing to query, assign, or resolve against — no
priority, no owner, no first-response SLA, no audit trail. This module adds
a real ``escalations`` row (migration 190) behind that same tag so every
inbound channel (widget today; email/sms/os follow) can create, list,
assign, and resolve escalations through one contract.

Public contract (other lanes import this — keep stable):
    create_escalation(db, *, client_id, source, source_ref, conversation_id=None,
                       os_thread_id=None, reason="", priority="normal",
                       metadata=None, notify=True) -> dict | None
    resolve_escalation(db, escalation_id, *, client_id, resolution="resolved",
                        resolved_by=None) -> dict | None
    mark_first_response(db, escalation_id, *, client_id) -> None
    list_escalations(db, *, client_id, status=None, limit=50) -> list[dict]

``notify`` on ``create_escalation`` is an additive, backward-compatible
kwarg (defaults to the documented "fires an owner notification" behavior).
It exists so callers that already send their own notification for this
escalation (e.g. widget_chat_effects.handle_handoff_detection, which awaits
SMS/email inline before this module existed) can opt out and avoid a
double-send — see that module for the concrete example.

Do NOT add 'from __future__ import annotations' — breaks Pydantic on FastAPI.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)

_VALID_SOURCES = {"widget", "email", "sms", "os"}
_VALID_PRIORITIES = {"low", "normal", "high", "urgent"}
_VALID_STATUSES = {"open", "in_progress", "resolved", "dismissed"}
_OPEN_STATUSES = ("open", "in_progress")

# Strong references to in-flight fire-and-forget notify tasks so they aren't
# garbage-collected mid-await — same guard asyncio's own docs recommend for
# "fire and forget" tasks, mirrors webhook_dispatcher.fire_event_background.
_PENDING_NOTIFY_TASKS: set = set()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_escalation(
    db: Any,
    *,
    client_id: str,
    source: str,
    source_ref: str,
    conversation_id: str | None = None,
    os_thread_id: str | None = None,
    reason: str = "",
    priority: str = "normal",
    metadata: dict | None = None,
    notify: bool = True,
) -> dict | None:
    """Create an escalation, idempotent on (client_id, source, source_ref).

    On conflict (an escalation for this tuple already exists), returns the
    existing row without inserting a duplicate or re-notifying. Never
    raises to callers — logs and returns None on failure so a broken DB
    call here never blocks the caller's own flow (e.g. a visitor-facing
    chat reply).
    """
    try:
        existing = (
            tenant_table(db, "escalations", client_id)
            .select("*")
            .eq("source", source)
            .eq("source_ref", source_ref)
            .limit(1)
            .execute()
        )
        if existing.data:
            return existing.data[0]
    except Exception:
        logger.warning(
            "create_escalation: idempotency lookup failed client_id=%s source=%s source_ref=%s",
            client_id,
            source,
            source_ref,
            exc_info=True,
        )
        return None

    row = {
        "source": source,
        "source_ref": source_ref,
        "conversation_id": conversation_id,
        "os_thread_id": os_thread_id,
        "reason": reason or "",
        "priority": priority if priority in _VALID_PRIORITIES else "normal",
        "metadata": metadata or {},
    }
    try:
        result = tenant_table(db, "escalations", client_id).insert(row).execute()
        if not result.data:
            logger.warning(
                "create_escalation: insert returned no rows client_id=%s source=%s",
                client_id,
                source,
            )
            return None
        created = result.data[0]
    except Exception:
        logger.warning(
            "create_escalation: insert failed client_id=%s source=%s source_ref=%s",
            client_id,
            source,
            source_ref,
            exc_info=True,
        )
        return None

    if notify:
        _schedule_notify(client_id, reason)

    return created


def resolve_escalation(
    db: Any,
    escalation_id: str,
    *,
    client_id: str,
    resolution: str = "resolved",
    resolved_by: str | None = None,
) -> dict | None:
    """Mark an escalation resolved/dismissed and clear the handoff tag.

    When the escalation carries a ``conversation_id`` and no OTHER open
    escalation exists for that conversation, this removes "handoff" from
    ``conversations.tags`` — the missing return-to-bot flow the magic-string
    tag never had. Never raises; returns None on failure or not-found.
    """
    status = resolution if resolution in _VALID_STATUSES else "resolved"

    try:
        existing = (
            tenant_table(db, "escalations", client_id)
            .select("*")
            .eq("id", escalation_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.warning(
            "resolve_escalation: lookup failed escalation_id=%s client_id=%s",
            escalation_id,
            client_id,
            exc_info=True,
        )
        return None

    if not existing.data:
        return None
    row = existing.data[0]

    updates: dict[str, Any] = {"status": status, "resolved_at": _now_iso()}
    if resolved_by:
        meta = dict(row.get("metadata") or {})
        meta["resolved_by"] = resolved_by
        updates["metadata"] = meta

    try:
        result = (
            tenant_table(db, "escalations", client_id)
            .update(updates)
            .eq("id", escalation_id)
            .execute()
        )
    except Exception:
        logger.warning(
            "resolve_escalation: update failed escalation_id=%s client_id=%s",
            escalation_id,
            client_id,
            exc_info=True,
        )
        return None

    if not result.data:
        return None
    updated = result.data[0]

    conversation_id = row.get("conversation_id")
    if conversation_id:
        try:
            _maybe_clear_handoff_tag(db, client_id, conversation_id, escalation_id)
        except Exception:
            logger.warning(
                "resolve_escalation: handoff-tag clear failed conversation_id=%s client_id=%s",
                conversation_id,
                client_id,
                exc_info=True,
            )

    return updated


def mark_first_response(db: Any, escalation_id: str, *, client_id: str) -> None:
    """Set ``first_response_at`` the first time a team member acts on this
    escalation. No-op if already set or the escalation doesn't exist."""
    try:
        existing = (
            tenant_table(db, "escalations", client_id)
            .select("id, first_response_at")
            .eq("id", escalation_id)
            .limit(1)
            .execute()
        )
        if not existing.data:
            return
        if existing.data[0].get("first_response_at"):
            return
        tenant_table(db, "escalations", client_id).update(
            {"first_response_at": _now_iso()}
        ).eq("id", escalation_id).execute()
    except Exception:
        logger.warning(
            "mark_first_response: failed escalation_id=%s client_id=%s",
            escalation_id,
            client_id,
            exc_info=True,
        )


def list_escalations(
    db: Any, *, client_id: str, status: str | None = None, limit: int = 50
) -> list[dict]:
    """List escalations for a tenant, newest first. Empty list on failure."""
    try:
        query = tenant_table(db, "escalations", client_id).select("*")
        if status:
            query = query.eq("status", status)
        result = query.order("created_at", desc=True).limit(limit).execute()
        return result.data or []
    except Exception:
        logger.warning(
            "list_escalations: failed client_id=%s status=%s",
            client_id,
            status,
            exc_info=True,
        )
        return []


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _maybe_clear_handoff_tag(
    db: Any, client_id: str, conversation_id: str, resolved_escalation_id: str
) -> None:
    """Remove the legacy "handoff" tag once every escalation on this
    conversation is closed. Leaves the tag alone if another open escalation
    still exists (e.g. a second channel raised its own escalation on the
    same conversation)."""
    other_open = (
        tenant_table(db, "escalations", client_id)
        .select("id")
        .eq("conversation_id", conversation_id)
        .in_("status", list(_OPEN_STATUSES))
        .neq("id", resolved_escalation_id)
        .limit(1)
        .execute()
    )
    if other_open.data:
        return

    conv = (
        tenant_table(db, "conversations", client_id)
        .select("id, tags")
        .eq("id", conversation_id)
        .limit(1)
        .execute()
    )
    if not conv.data:
        return
    tags = conv.data[0].get("tags") or []
    if "handoff" not in tags:
        return
    updated_tags = [t for t in tags if t != "handoff"]
    tenant_table(db, "conversations", client_id).update(
        {"tags": updated_tags}
    ).eq("id", conversation_id).execute()


def _schedule_notify(client_id: str, reason: str) -> None:
    """Fire the owner notification best-effort from this sync function.

    Mirrors backend.services.webhook_dispatcher.fire_event_background: when
    called from inside a running event loop (the normal case — every widget
    chat turn and every dashboard request runs inside FastAPI's loop),
    schedule the async notify as a background task. When there is no
    running loop (a script, a sync unit test), skip — notification is
    best-effort and must never block or crash the caller.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        logger.debug(
            "escalations: no running event loop, skipping owner notify for client_id=%s",
            client_id,
        )
        return
    task = loop.create_task(_notify_owner_async(client_id, reason))
    _PENDING_NOTIFY_TASKS.add(task)
    task.add_done_callback(_PENDING_NOTIFY_TASKS.discard)


async def _notify_owner_async(client_id: str, reason: str) -> None:
    """Best-effort SMS + email to the tenant owner.

    Reuses the exact notification pattern that used to live inline in
    widget_chat_effects.handle_handoff_detection: notification_phone +
    sms_notifications_enabled gates SMS via twilio_service.send_sms;
    owner_email gates an email via email_sender.send_email. Fetches its own
    service client rather than trusting a caller-supplied ``db`` — this
    runs as a scheduled task, possibly after the request that created it
    has already returned.
    """
    from backend.models.database import get_service_supabase

    db = get_service_supabase()
    try:
        tenant_row = (
            db.table("tenants")
            .select("business_name, notification_phone, sms_notifications_enabled, owner_email")
            .eq("id", client_id)
            .limit(1)
            .execute()
        )
        tenant = tenant_row.data[0] if tenant_row.data else {}
    except Exception:
        logger.warning(
            "escalations: tenant lookup for notify failed client_id=%s",
            client_id,
            exc_info=True,
        )
        return

    biz = tenant.get("business_name") or "Business"
    detail = f" ({reason})" if reason else ""

    try:
        owner_phone = tenant.get("notification_phone")
        if owner_phone and tenant.get("sms_notifications_enabled"):
            from backend.services.twilio_service import send_sms

            await send_sms(
                owner_phone,
                f"[{biz}] A customer requested to speak with a team member{detail}. Check your inbox.",
                tenant_id=client_id,
            )
    except Exception:
        logger.warning(
            "escalations: SMS notification failed client_id=%s",
            client_id,
            exc_info=True,
        )

    try:
        owner_email = tenant.get("owner_email")
        if owner_email:
            from backend.services.email_sender import send_email

            await send_email(
                to=owner_email,
                subject=f"[{biz}] Customer requesting a human",
                body_html=(
                    "<p>A customer is asking to speak with a team member.</p>"
                    + (f"<p>{reason}</p>" if reason else "")
                    + "<p>Open the <a href='https://app.agentnexlify.com/dashboard/conversations'>"
                    "Conversations inbox</a> to reply.</p>"
                ),
                tenant_id=client_id,
            )
    except Exception:
        logger.warning(
            "escalations: email notification failed client_id=%s",
            client_id,
            exc_info=True,
        )
