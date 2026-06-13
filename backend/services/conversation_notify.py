"""Email-the-owner-when-a-widget-conversation-wraps notifications.

Opt-in per tenant via ``tenants.conversation_email_notify_enabled`` +
``conversation_notify_email``. A scheduled idle-sweep finds conversations whose
last chat message is older than ``idle_minutes`` and not yet notified, emails the
full transcript (plus any captured lead contact) to the configured address, and
stamps ``conversations.notified_at`` so each conversation is emailed exactly once.

The 15-minute idle rule naturally covers every "wrap" case — a team handoff or a
captured lead leaves the conversation idle, and the sweep picks it up once quiet.
"""

import html
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.models.database import get_service_supabase
from backend.services.email_sender import send_email

logger = logging.getLogger(__name__)

IDLE_MINUTES = 15
BATCH_LIMIT = 200
DASHBOARD_URL = "https://app.agentnexlify.com/dashboard/conversations"


def _parse_ts(raw: str) -> datetime:
    """Parse a Postgres/ISO timestamp string to an aware datetime."""
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))


def build_transcript_html(
    business_name: str | None,
    messages: list[dict[str, Any]],
    lead: dict[str, Any] | None = None,
) -> str:
    """Render a conversation transcript as notification-email HTML.

    ``messages`` is ordered ascending by ``created_at``; each has ``role``
    ('user' | 'assistant') and ``content``. All visitor/AI content is HTML-escaped.
    """
    biz = business_name or "your website"
    rows: list[str] = []
    for m in messages:
        who = "Visitor" if m.get("role") == "user" else (business_name or "Assistant")
        rows.append(
            f"<p style='margin:6px 0'><strong>{html.escape(who)}:</strong> "
            f"{html.escape(m.get('content') or '')}</p>"
        )
    transcript = "\n".join(rows) or "<p>(no messages)</p>"

    lead_block = ""
    if lead:
        parts = [
            f"{label}: {html.escape(str(lead[key]))}"
            for label, key in (("Name", "name"), ("Email", "email"), ("Phone", "phone"))
            if lead.get(key)
        ]
        if parts:
            lead_block = (
                "<p><strong>Captured contact</strong><br>" + "<br>".join(parts) + "</p>"
            )

    return (
        f"<p>A conversation on your {html.escape(biz)} chat just wrapped up.</p>"
        f"{lead_block}"
        "<hr><h3 style='margin:8px 0'>Transcript</h3>"
        f"{transcript}"
        f'<hr><p><a href="{DASHBOARD_URL}">Open the Conversations inbox</a> to reply.</p>'
    )


async def notify_idle_conversations(idle_minutes: int = IDLE_MINUTES) -> int:
    """Email the full transcript for each idle, un-notified conversation belonging
    to a tenant that has opted in. Returns the number of emails sent.

    Batched (mirrors ``check_no_response_leads``): a small number of DB round-trips
    regardless of conversation count. Exactly-once is enforced by claiming each
    conversation with a conditional ``notified_at`` update before sending.
    """
    db = get_service_supabase()
    now = datetime.now(timezone.utc)
    idle_cutoff = now - timedelta(minutes=idle_minutes)

    # Q1: tenants that opted in and have a destination address.
    try:
        tres = (
            db.table("tenants")
            .select("id, business_name, conversation_notify_email, owner_email")
            .eq("conversation_email_notify_enabled", True)
            .execute()
        )
    except Exception:
        logger.exception("notify_idle_conversations: tenant query failed")
        return 0
    tenants: dict[str, dict[str, Any]] = {}
    for t in tres.data or []:
        dest = t.get("conversation_notify_email") or t.get("owner_email")
        if dest:
            t["_dest"] = dest
            tenants[t["id"]] = t
    if not tenants:
        return 0

    # Q2: un-notified conversations for those tenants.
    try:
        cres = (
            db.table("conversations")
            .select("id, client_id, session_id, created_at")
            .in_("client_id", list(tenants.keys()))
            .is_("notified_at", "null")
            .limit(BATCH_LIMIT)
            .execute()
        )
    except Exception:
        logger.exception("notify_idle_conversations: conversation query failed")
        return 0
    convos = [c for c in (cres.data or []) if c.get("session_id")]
    if not convos:
        return 0

    # Q3: all messages for those sessions (ascending) → transcript + last-activity.
    session_ids = list({c["session_id"] for c in convos})
    try:
        mres = (
            db.table("chat_messages")
            .select("session_id, role, content, created_at")
            .in_("session_id", session_ids)
            .order("created_at", desc=False)
            .execute()
        )
    except Exception:
        logger.exception("notify_idle_conversations: chat_messages query failed")
        return 0
    by_session: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for m in mres.data or []:
        by_session[m["session_id"]].append(m)

    # Q4 (best-effort): captured lead contact per conversation.
    leads_by_conv: dict[str, dict[str, Any]] = {}
    try:
        lres = (
            db.table("leads")
            .select("conversation_id, name, email, phone")
            .in_("conversation_id", [c["id"] for c in convos])
            .execute()
        )
        for lead in lres.data or []:
            if lead.get("conversation_id"):
                leads_by_conv[lead["conversation_id"]] = lead
    except Exception:
        logger.warning("notify_idle_conversations: leads lookup failed", exc_info=True)

    sent = 0
    for c in convos:
        msgs = by_session.get(c["session_id"], [])
        if not msgs:
            continue  # no content — not a real conversation yet
        if _parse_ts(msgs[-1]["created_at"]) > idle_cutoff:
            continue  # still active

        # Claim exactly-once: only proceed if we win the notified_at stamp.
        try:
            claim = (
                db.table("conversations")
                .update({"notified_at": now.isoformat()})
                .eq("id", c["id"])
                .is_("notified_at", "null")
                .execute()
            )
            if not claim.data:
                continue  # another worker already claimed it
        except Exception:
            logger.warning(
                "notify_idle_conversations: claim failed for %s", c["id"], exc_info=True
            )
            continue

        tenant = tenants[c["client_id"]]
        try:
            biz = tenant.get("business_name")
            await send_email(
                to=tenant["_dest"],
                subject=f"[{biz or 'Your business'}] New website conversation",
                body_html=build_transcript_html(biz, msgs, leads_by_conv.get(c["id"])),
                tenant_id=c["client_id"],
            )
            sent += 1
        except Exception:
            # Release the claim so the next sweep retries this conversation.
            logger.warning(
                "notify_idle_conversations: email failed for conv %s; releasing claim",
                c["id"],
                exc_info=True,
            )
            try:
                db.table("conversations").update({"notified_at": None}).eq(
                    "id", c["id"]
                ).execute()
            except Exception:
                logger.warning(
                    "notify_idle_conversations: failed to release claim for %s",
                    c["id"],
                    exc_info=True,
                )

    if sent:
        logger.info("notify_idle_conversations: sent %d transcript email(s)", sent)
    return sent
