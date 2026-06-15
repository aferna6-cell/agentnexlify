"""Alert the platform owner when an Agent OS turn fails or abstains.

Fires on hard failures (run ``status='failed'`` or the engine-offline degrade)
and low-confidence misses (decision ``status='wishlist_fallback'``). Emails the
platform owner a short summary with the full thread transcript attached.

Best-effort: never raises, never blocks the user's turn. Scheduled as a
background task off ``os_thread_runner``. A per-thread throttle keeps one stuck
conversation from email-storming the owner.
"""

import html
import logging
import time
from typing import Any

from backend.services.platform_mailer import send_platform_email, text_attachment
from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)

_THROTTLE_SECONDS = 15 * 60
_last_sent: dict[str, float] = {}

_REASON_LABELS = {
    "failed": "the agent hit an error and could not complete the request",
    "offline": "the agent engine was offline and could not respond",
    "wishlist_fallback": (
        "the agent could not confidently match the request to a department"
    ),
}


def _throttled(thread_id: str) -> bool:
    """True when this thread alerted within the throttle window."""
    now = time.time()
    last = _last_sent.get(thread_id)
    if last is not None and (now - last) < _THROTTLE_SECONDS:
        return True
    _last_sent[thread_id] = now
    return False


def build_transcript(messages: list[dict[str, Any]]) -> str:
    """Render os_messages rows into a plain-text transcript for attachment."""
    lines = []
    for m in messages:
        role = (m.get("role") or "?").upper()
        ts = m.get("created_at") or ""
        content = (m.get("content") or "").strip()
        lines.append(f"[{ts}] {role}:\n{content}\n")
    return "\n".join(lines) if lines else "(no messages found)"


async def notify_agent_failure(
    db: Any,
    client_id: str,
    thread_id: str,
    reason: str,
    business_name: str | None = None,
) -> bool:
    """Email the platform owner about a failed/abstained Agent OS turn.

    Returns True when an email was sent. Never raises.
    """
    try:
        if _throttled(thread_id):
            return False
        messages = (
            tenant_table(db, "os_messages", client_id)
            .select("role, content, created_at")
            .eq("thread_id", thread_id)
            .order("created_at", desc=False)
            .execute()
        ).data or []
        transcript = build_transcript(messages)
        label = _REASON_LABELS.get(reason, reason)
        biz = business_name or client_id
        last_user = next(
            (
                m.get("content")
                for m in reversed(messages)
                if m.get("role") == "user"
            ),
            "",
        )
        body = (
            f"<p>An Agent OS conversation needs your attention: "
            f"{html.escape(label)}.</p>"
            f"<p><strong>Tenant:</strong> {html.escape(str(biz))}<br>"
            f"<strong>Thread:</strong> {html.escape(str(thread_id))}<br>"
            f"<strong>Outcome:</strong> {html.escape(str(reason))}</p>"
        )
        if last_user:
            body += (
                "<p><strong>Last customer message:</strong><br>"
                f"{html.escape(str(last_user).strip())}</p>"
            )
        body += "<p>The full conversation is attached.</p>"

        attachment = text_attachment(
            f"agent-os-conversation-{thread_id}.txt", transcript
        )
        result = await send_platform_email(
            subject=f"[Agent OS] {reason} — {biz}",
            body_html=body,
            attachments=[attachment],
        )
        return bool(result.get("success"))
    except Exception:
        logger.warning(
            "os_failure_notify: failed for thread %s (client %s)",
            thread_id,
            client_id,
            exc_info=True,
        )
        return False
