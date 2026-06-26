"""SMS compliance — honor opt-outs (STOP) on every outbound SMS send.

TCPA: texting a recipient who replied STOP is the clearest, costliest violation
($500-$1,500 per text). Inbound STOP already flips ``leads.unsubscribed``
(``os_inbound.py``), and scheduled automation gates on that flag — but the
Agent OS ``sms.send`` action and the missed-call text-back never checked it
before sending, and opt-outs for numbers that aren't lead rows were not stored
anywhere durable.

This module unifies the opt-out signal:
  - the durable ``sms_opt_outs`` table (migration 160), and
  - the existing ``leads.unsubscribed`` flag.

``is_suppressed`` is the single gate every outbound SMS path calls before
sending. It fails CLOSED on the opt-out-table lookup (a lookup error suppresses
the send) because a wrongful send is a legal cost; the secondary leads lookup
fails open.

client_id (not tenant_id) — matches the leads/conversations customer tables.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

# Carrier-level filters also catch these, but we mirror them so the opt-out is
# recorded in our own ledger and honored on every send path. Exact-match only
# (so "stop by the shop tomorrow" does not trip) — mirrors inbound_sms_verify.
OPT_OUT_KEYWORDS = {"stop", "unsubscribe", "cancel", "stopall", "end", "quit"}
OPT_IN_KEYWORDS = {"start", "unstop", "yes"}


def last10(phone: str | None) -> str:
    """Last 10 digits of a phone, for format-agnostic matching."""
    if not phone:
        return ""
    digits = "".join(ch for ch in str(phone) if ch.isdigit())
    return digits[-10:] if len(digits) >= 10 else digits


def classify_inbound(body: str | None) -> str | None:
    """Return 'opt_out', 'opt_in', or None for an inbound SMS body."""
    word = (body or "").strip().lower()
    if word in OPT_OUT_KEYWORDS:
        return "opt_out"
    if word in OPT_IN_KEYWORDS:
        return "opt_in"
    return None


def record_opt_out(db: Any, client_id: str, phone: str, source: str = "sms_stop") -> None:
    """Durably record that this phone opted out of SMS for this tenant."""
    p = last10(phone)
    if not p:
        return
    try:
        db.table("sms_opt_outs").upsert(
            {"client_id": client_id, "phone_last10": p, "source": source},
            on_conflict="client_id,phone_last10",
            ignore_duplicates=True,
        ).execute()
    except Exception:
        logger.warning("record_opt_out failed client=%s", client_id, exc_info=True)


def record_opt_in(db: Any, client_id: str, phone: str) -> None:
    """Remove a phone from the opt-out ledger (inbound START/UNSTOP)."""
    p = last10(phone)
    if not p:
        return
    try:
        db.table("sms_opt_outs").delete().eq("client_id", client_id).eq(
            "phone_last10", p
        ).execute()
    except Exception:
        logger.warning("record_opt_in failed client=%s", client_id, exc_info=True)


def recently_messaged(
    db: Any, tenant_id: str, phone: str, within_hours: int = 24
) -> bool:
    """True if we already sent this caller a text-back within ``within_hours``.

    Per-recipient frequency cap: someone who calls 5 times in an hour gets ONE
    text-back, not five. Protects margin on the $19.99 tier and avoids looking
    like a spammer. Fails OPEN (a lookup error allows the send) — this is a
    quality/cost guard, not a legal one.
    """
    if not phone:
        return False
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=within_hours)).isoformat()
        res = (
            db.table("missed_call_texts")
            .select("id")
            .eq("tenant_id", tenant_id)
            .eq("from_phone", phone)
            .eq("status", "sent")
            .gte("created_at", cutoff)
            .limit(1)
            .execute()
        )
        return bool(res.data)
    except Exception:
        logger.warning(
            "recently_messaged lookup failed tenant=%s — allowing send", tenant_id,
            exc_info=True,
        )
        return False


def is_suppressed(db: Any, client_id: str, phone: str) -> bool:
    """True if this recipient must NOT receive an SMS for this tenant.

    Checks the durable opt-out ledger (fail CLOSED on error — a wrongful send is
    the legal cost) then the leads.unsubscribed flag (fail open — secondary).
    """
    p = last10(phone)
    if not p:
        return False

    # 1) durable opt-out ledger — fail closed
    try:
        res = (
            db.table("sms_opt_outs")
            .select("id")
            .eq("client_id", client_id)
            .eq("phone_last10", p)
            .limit(1)
            .execute()
        )
        if res.data:
            return True
    except Exception:
        logger.warning(
            "is_suppressed: opt-out lookup failed client=%s — suppressing send to be safe",
            client_id,
            exc_info=True,
        )
        return True  # fail closed: do not risk a TCPA violation on a DB blip

    # 2) leads.unsubscribed — secondary signal, fail open
    try:
        rows = (
            db.table("leads")
            .select("phone, unsubscribed")
            .eq("client_id", client_id)
            .eq("unsubscribed", True)
            .filter("phone", "not.is", "null")
            .execute()
        ).data or []
        return any(last10(r.get("phone")) == p for r in rows)
    except Exception:
        logger.warning(
            "is_suppressed: leads lookup failed client=%s", client_id, exc_info=True
        )
        return False
