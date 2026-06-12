"""Approve-by-text — the owner replies YES to the approval alert SMS.

The approval alert (os_approval_notify SMS leg) tells the owner a draft is
waiting. This module closes the loop: when an inbound SMS arrives at the
tenant's Twilio number FROM the tenant's own notification_phone, exact
command keywords act on the newest pending draft:

    YES / SEND / APPROVE  -> approve + dispatch (same path as the dashboard
                             approve button: queue_action_for_run, then
                             deliverable_status='approved')
    NO / SKIP / DISMISS   -> deliverable_status='rejected'

Anything else from the owner's phone falls through to the normal inbound
bridge (returns None) — owners can still text their own business line.

Security properties:
  - Caller already passed Twilio signature verification (os_inbound.py).
  - Sender must match notification_phone digit-for-digit (last 10) AND
    sms_notifications_enabled must be on — the same opt-in that gates
    the outbound alert.
  - Only exact keywords are commands; no fuzzy matching.
"""

import logging
import re
from datetime import datetime, timezone
from typing import Any

from backend.services.os_action_dispatch import queue_action_for_run
from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)

_APPROVE_WORDS = {"YES", "SEND", "APPROVE"}
_REJECT_WORDS = {"NO", "SKIP", "DISMISS"}


def _last10(phone: str) -> str:
    return re.sub(r"\D", "", phone or "")[-10:]


def _command(body_text: str) -> str | None:
    word = (body_text or "").strip().upper().rstrip(".!")
    if word in _APPROVE_WORDS:
        return "approve"
    if word in _REJECT_WORDS:
        return "reject"
    return None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def handle_owner_sms(
    db: Any, client_id: str, from_number: str, body_text: str
) -> str | None:
    """Handle an owner command SMS. Returns the reply text, or None to
    fall through to the normal inbound bridge.

    Never raises — any failure returns None so a customer-facing flow is
    never blocked by this feature.
    """
    try:
        cmd = _command(body_text)
        if cmd is None or not from_number:
            return None

        tenant_rows = (
            db.table("tenants")
            .select("notification_phone, sms_notifications_enabled, business_name")
            .eq("id", client_id)
            .limit(1)
            .execute()
        )
        rows = tenant_rows.data or []
        if not rows:
            return None
        tenant = rows[0]
        owner_phone = tenant.get("notification_phone")
        if not owner_phone or not tenant.get("sms_notifications_enabled"):
            return None
        if _last10(from_number) != _last10(owner_phone) or not _last10(from_number):
            return None

        pending = (
            tenant_table(db, "os_agent_runs", client_id)
            .select("*")
            .eq("deliverable_status", "pending_approval")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        runs = pending.data or []
        if not runs:
            return (
                "Nothing is waiting for your approval right now. "
                "You'll get a text when a new draft needs you."
            )
        run = runs[0]
        title = ((run.get("deliverable") or {}).get("title") or "the draft")[:80]

        if cmd == "reject":
            tenant_table(db, "os_agent_runs", client_id).update(
                {"deliverable_status": "rejected", "updated_at": _now()}
            ).eq("id", run["id"]).execute()
            logger.info(
                "os_sms_approval: owner rejected run %s for tenant %s via SMS",
                run["id"],
                client_id,
            )
            return f"Dismissed: {title}. Nothing was sent."

        # Approve — mirror the dashboard endpoint: dispatch first, then flip
        # status (an approved-but-undispatched row would look sent when it
        # wasn't).
        action_run_id = await queue_action_for_run(db, client_id, run, None)
        update_fields: dict[str, Any] = {
            "deliverable_status": "approved",
            "updated_at": _now(),
        }
        if action_run_id:
            update_fields["action_run_id"] = action_run_id
        tenant_table(db, "os_agent_runs", client_id).update(update_fields).eq(
            "id", run["id"]
        ).execute()
        logger.info(
            "os_sms_approval: owner approved run %s for tenant %s via SMS",
            run["id"],
            client_id,
        )
        return f"Approved and sent: {title}."
    except Exception:
        logger.warning(
            "os_sms_approval: failed for tenant %s — falling through to normal bridge",
            client_id,
            exc_info=True,
        )
        return None
