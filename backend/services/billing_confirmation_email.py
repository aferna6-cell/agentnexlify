"""Best-effort subscribe and unsubscribe confirmation emails.

Sent through Resend via email_sender.send_email. Failures are logged and
swallowed. Dedupe rows live in the existing idempotency_keys table and are
written only after send_email reports success.

Keys:
  billing_sub_confirm:{checkout_session_id}
  billing_unsub_confirm:{subscription_id}
"""

import asyncio
import contextvars
import html
import logging
from datetime import datetime

from backend.config import settings
from backend.services.email_sender import send_email

logger = logging.getLogger(__name__)

_PROVIDER = "billing_email"
_pending_tasks: contextvars.ContextVar[list[asyncio.Task] | None] = contextvars.ContextVar(
    "billing_confirmation_tasks",
    default=None,
)

_PLAN_LABELS = {
    "chatbot": "Chatbot",
    "agent_os": "Agent OS",
    "agent_os_managed": "Agent OS Managed",
}


def billing_portal_url() -> str:
    base = (settings.frontend_url or "").rstrip("/")
    return f"{base}/billing"


def _plan_label(plan: str) -> str:
    key = str(plan or "").strip()
    return _PLAN_LABELS.get(key, key or "your plan")


def format_access_until(period_end_iso: str | None) -> str | None:
    """Return a UTC calendar date for the period end, or None when absent."""
    if not period_end_iso:
        return None
    try:
        parsed = datetime.fromisoformat(str(period_end_iso).replace("Z", "+00:00"))
    except ValueError:
        return None
    return f"{parsed.strftime('%B')} {parsed.day}, {parsed.year}"


def build_subscribe_confirmation(*, plan: str, plan_status: str) -> tuple[str, str]:
    """Short HTML confirmation that a plan is active, plus the billing link."""
    safe_plan = html.escape(_plan_label(plan))
    safe_status = html.escape(str(plan_status or "active"))
    portal = html.escape(billing_portal_url(), quote=True)
    subject = "Your AgentNexLiFy subscription is active"
    body = (
        "<h2>You're subscribed</h2>"
        f"<p>Your <strong>{safe_plan}</strong> plan is <strong>{safe_status}</strong>.</p>"
        f'<p><a href="{portal}">Open the billing portal</a> to manage your subscription.</p>'
        "<p>— The AgentNexLiFy Team</p>"
    )
    return subject, body


def build_unsubscribe_confirmation(*, plan: str, access_until: str | None) -> tuple[str, str]:
    """Short HTML confirmation that cancellation is scheduled, plus the portal link."""
    safe_plan = html.escape(_plan_label(plan))
    portal = html.escape(billing_portal_url(), quote=True)
    if access_until:
        until = f"<p>You'll keep access until {html.escape(access_until)}.</p>"
    else:
        until = "<p>You'll keep access until the end of the current billing period.</p>"
    subject = "Your AgentNexLiFy cancellation is scheduled"
    body = (
        "<h2>Cancellation scheduled</h2>"
        f"<p>Your <strong>{safe_plan}</strong> subscription will cancel at the end of "
        "the current billing period.</p>"
        f"{until}"
        f'<p><a href="{portal}">Open the billing portal</a> if you want to resubscribe.</p>'
        "<p>— The AgentNexLiFy Team</p>"
    )
    return subject, body


def _log(level: int, key: str, tenant_id: str, error_type: str) -> None:
    """Log a dedupe key, tenant id, and error type. Never the message or address."""
    logger.log(
        level,
        "billing confirmation key=%s tenant_id=%s error_type=%s",
        key,
        tenant_id or "",
        error_type,
    )


def _rows(result) -> list:
    data = getattr(result, "data", None)
    if not isinstance(data, list):
        raise TypeError("IdempotencyLookupShape")
    return data


def _key_recorded(db, key: str) -> bool:
    result = (
        db.table("idempotency_keys")
        .select("key")
        .eq("key", key)
        .limit(1)
        .execute()
    )
    for row in _rows(result):
        if isinstance(row, dict) and row.get("key") == key:
            return True
    return False


def _record_key(db, key: str) -> None:
    db.table("idempotency_keys").insert(
        {
            "key": key,
            "provider": _PROVIDER,
            "response_status": 200,
            "response_body": {"status": "sent"},
        }
    ).execute()


def _owner_email(db, tenant_id: str) -> str:
    result = (
        db.table("tenants")
        .select("owner_email")
        .eq("id", tenant_id)
        .limit(1)
        .execute()
    )
    data = getattr(result, "data", None)
    if not isinstance(data, list) or not data or not isinstance(data[0], dict):
        return ""
    return str(data[0].get("owner_email") or "").strip()


def _session_recipient(session: dict) -> str:
    details = session.get("customer_details")
    detail_email = details.get("email") if isinstance(details, dict) else ""
    return str(session.get("customer_email") or detail_email or "").strip()


async def _send_once(
    db,
    *,
    key: str,
    tenant_id: str,
    recipient: str,
    subject: str,
    body_html: str,
) -> None:
    """Send once. Record the key only after send_email returns success."""
    try:
        if not key or key.endswith(":"):
            _log(logging.INFO, key or "billing_confirm:", tenant_id, "MissingId")
            return
        to = str(recipient or "").strip()
        if not to:
            _log(logging.INFO, key, tenant_id, "MissingRecipient")
            return
        if _key_recorded(db, key):
            _log(logging.INFO, key, tenant_id, "AlreadyRecorded")
            return
        result = await send_email(
            to=to,
            subject=subject,
            body_html=body_html,
            tenant_id=str(tenant_id),
        )
        if not isinstance(result, dict) or not result.get("success"):
            _log(logging.WARNING, key, tenant_id, "SendFailed")
            return
        try:
            _record_key(db, key)
        except Exception as exc:
            _log(logging.WARNING, key, tenant_id, type(exc).__name__)
    except Exception as exc:
        _log(logging.WARNING, key, tenant_id, type(exc).__name__)


async def send_subscription_confirmation(
    db,
    *,
    checkout_session_id: str,
    tenant_id: str,
    plan: str,
    plan_status: str,
    recipient: str,
) -> None:
    """Confirm a newly activated subscription. Never raises."""
    session_id = str(checkout_session_id or "").strip()
    key = f"billing_sub_confirm:{session_id}" if session_id else "billing_sub_confirm:"
    to = str(recipient or "").strip()
    if not to and session_id and tenant_id:
        try:
            to = _owner_email(db, str(tenant_id))
        except Exception as exc:
            _log(logging.WARNING, key, str(tenant_id), type(exc).__name__)
            return
    subject, body = build_subscribe_confirmation(plan=plan, plan_status=plan_status)
    await _send_once(
        db,
        key=key,
        tenant_id=str(tenant_id or ""),
        recipient=to,
        subject=subject,
        body_html=body,
    )


async def send_unsubscribe_confirmation(
    db,
    *,
    subscription_id: str,
    tenant_id: str,
    plan: str,
    recipient: str,
    period_end_iso: str | None,
) -> None:
    """Confirm cancel_at_period_end was scheduled. Never raises."""
    sub_id = str(subscription_id or "").strip()
    key = f"billing_unsub_confirm:{sub_id}" if sub_id else "billing_unsub_confirm:"
    subject, body = build_unsubscribe_confirmation(
        plan=plan,
        access_until=format_access_until(period_end_iso),
    )
    await _send_once(
        db,
        key=key,
        tenant_id=str(tenant_id or ""),
        recipient=recipient,
        subject=subject,
        body_html=body,
    )


def enqueue_subscription_confirmation(db, session: dict, *, tenant_id: str, plan: str) -> None:
    """Schedule the subscribe email on the running webhook loop.

    Sync callers (activation unit tests) have no loop; they return without
    sending. The webhook awaits drain_billing_confirmation_tasks before it
    responds.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return
    session_id = ""
    recipient = ""
    if isinstance(session, dict):
        session_id = str(session.get("id") or "")
        recipient = _session_recipient(session)
    pending = _pending_tasks.get()
    if pending is None:
        pending = []
        _pending_tasks.set(pending)
    pending.append(
        asyncio.create_task(
            send_subscription_confirmation(
                db,
                checkout_session_id=session_id,
                tenant_id=str(tenant_id),
                plan=str(plan),
                plan_status="active",
                recipient=recipient,
            )
        )
    )


async def drain_billing_confirmation_tasks() -> None:
    """Await subscribe-email tasks queued during this webhook delivery."""
    pending = _pending_tasks.get()
    if not pending:
        return
    _pending_tasks.set(None)
    for task in pending:
        try:
            await task
        except Exception as exc:
            _log(logging.WARNING, "billing_confirm:drain", "", type(exc).__name__)
