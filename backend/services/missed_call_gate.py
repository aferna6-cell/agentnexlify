"""Missed-call text-back gating + retry-enqueue helpers (#117).

Pure, testable logic factored out of the ``twilio_webhooks.handle_missed_call``
webhook handler (user-rules Rule 9/12 — keep the live webhook edit minimal; the
handler calls these as guard clauses). The handler already does the replay
window, automation ``is_enabled`` gate, quiet hours, personalization, TCPA
suppression, frequency cap, and the ``missed_call_texts`` insert. This module
adds the four remaining spec items:

- plan-tier gate (branded automation is a premium feature),
- call-duration gate (an answered call is not a missed call),
- spam-blocklist gate,
- ``pending_automations`` retry enqueue on Twilio send failure — the Phase-4
  TODO the handler left at its send-failure branch.

Eligibility uses the canonical ``plan_catalog.PREMIUM_PLANS`` (agent_os + legacy
paid), NOT the stale plan list in the issue body (it predates the 2026-06-15
repricing and omits agent_os). CLAUDE.md / plan_catalog is authoritative.

The enqueue is fail-open (mirrors ``retry_worker`` #118 / ``booking_gcal`` #119):
``pending_automations`` is migration 180 (unapplied) — a missing table is logged
and swallowed, never raised into the webhook response.
"""

import logging
from datetime import datetime, timedelta, timezone

from backend.services.plan_catalog import PREMIUM_PLANS

logger = logging.getLogger(__name__)

# Retry cadence for a failed missed-call text-back (seconds): 30s / 2min / 10min.
_RETRY_BACKOFF_SECONDS = (30, 120, 600)

# An answered call longer than this (seconds) is not a missed call.
_MAX_MISSED_DURATION_SECONDS = 10


def is_plan_eligible(plan: str | None) -> bool:
    """True when the tenant's plan unlocks branded automation (premium tier)."""
    return (plan or "") in PREMIUM_PLANS


def _phone_key(phone: str | None) -> str:
    """Last 10 digits, separators stripped — the order-free match key."""
    digits = "".join(ch for ch in (phone or "") if ch.isdigit())
    return digits[-10:]


def is_spam_blocked(caller: str | None, config: dict | None) -> bool:
    """True when ``caller`` is in the automation's ``config.spam_blocklist``.

    Matching is on the last-10-digit key so formatting differences
    (``+1 555…`` vs ``(555)…``) never let a blocked number through.
    """
    if not config:
        return False
    blocklist = config.get("spam_blocklist")
    if not isinstance(blocklist, (list, tuple)) or not blocklist:
        return False
    caller_key = _phone_key(caller)
    if not caller_key:
        return False
    return any(_phone_key(entry) == caller_key for entry in blocklist)


def should_skip_for_duration(call_duration) -> bool:
    """True when the call was actually answered (duration > 10s), so no text-back.

    A missing/blank/garbage ``CallDuration`` is treated as 0 (a genuine missed
    call) — the guard errs toward sending the text-back, never toward skipping.
    """
    try:
        return int(call_duration) > _MAX_MISSED_DURATION_SECONDS
    except (TypeError, ValueError):
        return False


def enqueue_missed_call_retry(
    tenant_id: str,
    payload: dict,
    *,
    db,
    now: datetime | None = None,
) -> bool:
    """Enqueue a ``pending_automations`` retry for a failed text-back.

    Returns True when the row was enqueued, False when it was swallowed (table
    unapplied / transient). Never raises — the webhook must always return 200.
    """
    now = now or datetime.now(timezone.utc)
    scheduled_for = (now + timedelta(seconds=_RETRY_BACKOFF_SECONDS[0])).isoformat()
    try:
        db.table("pending_automations").insert(
            {
                "tenant_id": tenant_id,
                "automation_type": "missed_call_text",
                "payload": payload,
                "status": "pending",
                "attempts": 0,
                "scheduled_for": scheduled_for,
            }
        ).execute()
        return True
    except Exception:
        logger.warning(
            "enqueue_missed_call_retry: pending_automations enqueue failed "
            "(table may be unapplied) — text-back failure not retried this cycle"
        )
        return False
