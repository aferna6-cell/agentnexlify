"""Platform admin alert notifications for Agent OS fail/abstain events.

Sends an email to the platform admin (settings.agent_os_alert_email) when the
Agent OS support agent either ERRORS (fail) or ABSTAINS (returns an
escalate_reason or confidence below threshold).

Best-effort: the send is wrapped in try/except and never propagates — it must
not break the user-facing Agent OS reply. If AGENT_OS_ALERT_EMAIL is unset the
function logs a warning and returns immediately.

Attachment format: Resend supports ``attachments`` as a list of
``{filename, content}`` dicts where ``content`` is base64-encoded bytes.
The existing ``send_email`` helper does not expose this; we call resend
directly so the existing tenant quota / rate-limit path is bypassed (this is a
platform alert, not a tenant email).
"""

import base64
import logging
from datetime import datetime, timezone
from typing import Literal

from backend.config import settings

logger = logging.getLogger(__name__)

_KIND = Literal["fail", "abstain"]


def _build_transcript(conversation: list[dict]) -> str:
    """Build a plain-text transcript from a list of message dicts.

    Each dict must have at minimum ``role`` and ``content`` keys.
    Optional ``created_at`` is included when present.
    """
    lines: list[str] = [
        "Agent OS Conversation Transcript",
        "=" * 40,
        "",
    ]
    for msg in conversation:
        role = (msg.get("role") or "unknown").upper()
        ts = msg.get("created_at") or ""
        content = msg.get("content") or ""
        ts_suffix = f"  [{ts}]" if ts else ""
        lines.append(f"{role}{ts_suffix}:")
        lines.append(content.strip())
        lines.append("")
    return "\n".join(lines)


def _send_alert_via_resend(
    *,
    to: str,
    subject: str,
    body_html: str,
    transcript_text: str,
    tenant_id: str,
) -> None:
    """Send the alert email with the transcript attached via Resend directly.

    Uses resend.Emails.send synchronously — call from a threadpool or
    background task. Bypasses the tenant quota path because this is a
    platform-level alert, not a tenant marketing email.
    """
    import resend

    if not settings.resend_api_key:
        logger.warning(
            "os_alert_notifications: RESEND_API_KEY unset — alert not sent "
            "for tenant %s",
            tenant_id,
        )
        return

    resend.api_key = settings.resend_api_key

    # Resend attachment: base64-encoded content string.
    encoded_content = base64.b64encode(transcript_text.encode("utf-8")).decode("ascii")
    ts_stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"transcript_{tenant_id}_{ts_stamp}.txt"

    params = {
        "from": "AgentNexLiFy Alerts <noreply@agentnexlify.com>",
        "to": [to],
        "subject": subject,
        "html": body_html,
        "attachments": [{"filename": filename, "content": encoded_content}],
    }
    resend.Emails.send(params)
    logger.info(
        "os_alert_notifications: alert sent to %s for tenant %s kind=",
        to,
        tenant_id,
    )


def notify_agent_os_event(
    tenant_id: str,
    conversation: list[dict],
    *,
    reason: str,
    kind: _KIND,
    error: str | None = None,
) -> None:
    """Send a platform admin alert for an Agent OS fail or abstain event.

    Args:
        tenant_id: The tenant whose Agent OS session triggered the event.
        conversation: List of message dicts (role, content, created_at?).
            Pass the thread's os_messages rows in chronological order.
        reason: Human-readable reason string (escalate_reason or error
            message summary).
        kind: "fail" (exception/engine error) or "abstain" (low confidence
            or escalate_reason returned by the agent).
        error: Optional raw error string for "fail" events.

    This function is best-effort: exceptions are caught and logged. It never
    propagates to the caller.
    """
    if not settings.agent_os_alert_email:
        logger.warning(
            "os_alert_notifications: AGENT_OS_ALERT_EMAIL not configured — "
            "skipping alert for tenant %s kind=%s",
            tenant_id,
            kind,
        )
        return

    try:
        msg_count = len(conversation)
        subject = f"[Agent OS] {kind} — tenant {tenant_id}"

        error_block = ""
        if error:
            error_block = (
                f"<p><strong>Error:</strong> "
                f"<code>{_html_escape(error[:500])}</code></p>"
            )

        body_html = (
            f"<h2>Agent OS {kind.capitalize()} Alert</h2>"
            f"<p><strong>Tenant:</strong> {_html_escape(tenant_id)}</p>"
            f"<p><strong>Kind:</strong> {_html_escape(kind)}</p>"
            f"<p><strong>Reason:</strong> {_html_escape(reason or '(none)')}</p>"
            f"<p><strong>Messages in thread:</strong> {msg_count}</p>"
            f"{error_block}"
            f"<p>Full conversation transcript is attached.</p>"
        )

        transcript_text = _build_transcript(conversation)

        _send_alert_via_resend(
            to=settings.agent_os_alert_email,
            subject=subject,
            body_html=body_html,
            transcript_text=transcript_text,
            tenant_id=tenant_id,
        )
    except Exception:
        logger.exception(
            "os_alert_notifications: failed to send alert for tenant %s kind=%s",
            tenant_id,
            kind,
        )


def _html_escape(text: str) -> str:
    """Minimal HTML escaping for alert body values."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
