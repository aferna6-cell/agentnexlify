"""Lead scoring engine — rule-based 0-100 scoring with engagement, intent, recency, and decay."""


import logging
from datetime import datetime, timezone
from typing import Any

from backend.models.database import get_service_supabase

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Intent keyword lists
# ---------------------------------------------------------------------------

_PRICING_KEYWORDS = ["price", "pricing", "cost", "fee", "rate", "charge", "quote", "estimate", "budget", "afford"]
_AVAILABILITY_KEYWORDS = ["available", "availability", "schedule", "appointment", "book", "when can", "open", "slot"]
_SERVICES_KEYWORDS = ["service", "offer", "provide", "do you", "help with", "looking for", "need", "want"]
_URGENCY_KEYWORDS = ["urgent", "asap", "today", "tomorrow", "right away", "immediately", "soon", "rush"]
_EMERGENCY_KEYWORDS = [
    "emergency", "leak", "flood", "flooded", "flooding", "burst", "broken",
    "no hot water", "no heat", "no power", "overflowing", "sewage",
    "gas smell", "smoke", "fire", "water damage", "mold",
    "locked out", "break-in", "alarm", "pain", "severe",
    "can't wait", "right now", "911", "help me",
]


# ---------------------------------------------------------------------------
# Sub-scoring functions
# ---------------------------------------------------------------------------


def _score_engagement(lead: dict[str, Any], message_count: int) -> tuple[int, dict]:
    """Score based on contact info completeness and message volume. Max 40."""
    points = 0
    breakdown: dict[str, Any] = {}

    if lead.get("email"):
        points += 15
        breakdown["email"] = 15
    if lead.get("phone"):
        points += 15
        breakdown["phone"] = 15
    if lead.get("name"):
        points += 5
        breakdown["name"] = 5

    if message_count >= 8:
        msg_pts = 10
    elif message_count >= 4:
        msg_pts = 5
    elif message_count >= 1:
        msg_pts = 2
    else:
        msg_pts = 0
    points += msg_pts
    breakdown["messages"] = msg_pts
    breakdown["message_count"] = message_count

    capped = min(points, 40)
    breakdown["total"] = capped
    breakdown["max"] = 40
    return capped, breakdown


def _score_intent(messages: list[dict[str, Any]]) -> tuple[int, dict]:
    """Score based on intent keywords in user messages. Max 40."""
    # Concatenate all user messages
    text = " ".join(
        m.get("content", "") for m in messages if m.get("role") == "user"
    ).lower()

    points = 0
    breakdown: dict[str, Any] = {}

    if any(kw in text for kw in _PRICING_KEYWORDS):
        points += 15
        breakdown["pricing"] = 15
    if any(kw in text for kw in _AVAILABILITY_KEYWORDS):
        points += 15
        breakdown["availability"] = 15
    if any(kw in text for kw in _SERVICES_KEYWORDS):
        points += 10
        breakdown["services"] = 10
    if any(kw in text for kw in _URGENCY_KEYWORDS):
        points += 10
        breakdown["urgency"] = 10
    if any(kw in text for kw in _EMERGENCY_KEYWORDS):
        points += 15
        breakdown["emergency"] = 15

    capped = min(points, 40)
    breakdown["total"] = capped
    breakdown["max"] = 40
    return capped, breakdown


def _score_recency(
    last_message_at: str | None, created_at: str | None
) -> tuple[int, dict]:
    """Score based on how recently the lead was active. Max 20."""
    ref = last_message_at or created_at
    if not ref:
        return 0, {"total": 0, "max": 20, "hours_ago": None}

    try:
        ts = datetime.fromisoformat(ref.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        hours = (now - ts).total_seconds() / 3600
    except (ValueError, TypeError):
        return 0, {"total": 0, "max": 20, "hours_ago": None}

    if hours <= 1:
        pts = 20
    elif hours <= 24:
        pts = 15
    elif hours <= 72:
        pts = 10
    elif hours <= 168:
        pts = 5
    else:
        pts = 0

    return pts, {"total": pts, "max": 20, "hours_ago": round(hours, 1)}


def _compute_decay(
    last_message_at: str | None, created_at: str | None
) -> tuple[int, dict]:
    """Compute decay penalty for leads inactive > 7 days."""
    ref = last_message_at or created_at
    if not ref:
        return 0, {"total": 0, "days_inactive": None}

    try:
        ts = datetime.fromisoformat(ref.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        days = (now - ts).total_seconds() / 86400
    except (ValueError, TypeError):
        return 0, {"total": 0, "days_inactive": None}

    if days <= 7:
        return 0, {"total": 0, "days_inactive": round(days, 1)}

    penalty = int((days - 7) * 5)
    return penalty, {"total": penalty, "days_inactive": round(days, 1)}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _compute_lead_score(
    lead: dict[str, Any],
    messages: list[dict[str, Any]],
    last_message_at: str | None,
) -> dict[str, Any]:
    """Pure scoring: lead row + its messages in, scoring details out.

    Shared by score_lead (single fetch) and score_all_leads (batch fetch) so
    the batch path never re-queries per lead.
    """
    # 3. Count user messages
    user_msg_count = sum(1 for m in messages if m.get("role") == "user")

    # 4. Compute sub-scores
    engagement, eng_bd = _score_engagement(lead, user_msg_count)
    intent, int_bd = _score_intent(messages)
    recency, rec_bd = _score_recency(last_message_at, lead.get("created_at"))
    decay, dec_bd = _compute_decay(last_message_at, lead.get("created_at"))

    raw_score = min(engagement + intent + recency, 100)
    final_score = max(0, raw_score - decay)

    # 5. Compute temperature from final score
    # Emergency keywords force "hot" regardless of score
    has_emergency = int_bd.get("emergency", 0) > 0
    if has_emergency or final_score >= 70:
        temperature = "hot"
    elif final_score >= 40:
        temperature = "warm"
    else:
        temperature = "cold"

    # 6. Build human-readable score factors breakdown
    factors: list[str] = []
    if eng_bd.get("email"):
        factors.append(f"Has email (+{eng_bd['email']})")
    if eng_bd.get("phone"):
        factors.append(f"Has phone (+{eng_bd['phone']})")
    if eng_bd.get("name"):
        factors.append(f"Has name (+{eng_bd['name']})")
    if eng_bd.get("messages", 0) > 0:
        factors.append(f"Messages: {eng_bd.get('message_count', 0)} (+{eng_bd['messages']})")
    if int_bd.get("pricing"):
        factors.append(f"Asked about pricing (+{int_bd['pricing']})")
    if int_bd.get("availability"):
        factors.append(f"Asked about availability (+{int_bd['availability']})")
    if int_bd.get("services"):
        factors.append(f"Interested in services (+{int_bd['services']})")
    if int_bd.get("urgency"):
        factors.append(f"Expressed urgency (+{int_bd['urgency']})")
    if int_bd.get("emergency"):
        factors.append(f"Emergency detected (+{int_bd['emergency']})")
    if rec_bd.get("total", 0) > 0:
        factors.append(f"Recent activity (+{rec_bd['total']})")
    if dec_bd.get("total", 0) > 0:
        factors.append(f"Inactivity decay (-{dec_bd['total']})")

    return {
        "lead_id": lead.get("id"),
        "score": final_score,
        "raw_score": raw_score,
        "temperature": temperature,
        "factors": factors,
        "breakdown": {
            "engagement": eng_bd,
            "intent": int_bd,
            "recency": rec_bd,
            "decay": dec_bd,
        },
    }


def _persist_score(db, lead: dict[str, Any], details: dict[str, Any]) -> dict[str, Any] | None:
    """Write lead_score/lead_temperature; return the activity_log row (unsent)."""
    db_score = max(1, min(10, round(details["score"] / 10)))
    db.table("leads").update({
        "lead_score": db_score,
        "lead_temperature": details["temperature"],
    }).eq("id", lead["id"]).execute()

    client_id = lead.get("client_id")
    if client_id and details["factors"]:
        return {
            "tenant_id": client_id,
            "lead_id": lead["id"],
            "activity_type": "lead_scored",
            "description": f"Lead scored {details['score']}/100 ({details['temperature']})",
            "metadata": {
                "factors": details["factors"],
                "score": details["score"],
                "temperature": details["temperature"],
            },
        }
    return None


def score_lead(lead_id: str) -> dict[str, Any]:
    """Score a single lead and persist the result. Returns scoring details."""
    db = get_service_supabase()

    # 1. Fetch lead
    lead_result = db.table("leads").select("*").eq("id", lead_id).limit(1).execute()
    if not lead_result.data:
        raise ValueError(f"Lead {lead_id} not found")
    lead = lead_result.data[0]

    # 2. Fetch conversation messages via chat_messages (canonical store).
    # Live schema dropped conversations.messages JSONB — messages live in
    # chat_messages, linked by tenant_id + session_id.
    messages: list[dict[str, Any]] = []
    last_message_at: str | None = None
    conv_id = lead.get("conversation_id")
    tenant_id = lead.get("client_id")
    if conv_id:
        conv_result = (
            db.table("conversations")
            .select("session_id, last_message_at")
            .eq("id", conv_id)
            .limit(1)
            .execute()
        )
        if conv_result.data:
            session_id = conv_result.data[0].get("session_id")
            last_message_at = conv_result.data[0].get("last_message_at")
            if session_id and tenant_id:
                msg_result = (
                    db.table("chat_messages")
                    .select("role, content, created_at")
                    .eq("tenant_id", tenant_id)
                    .eq("session_id", session_id)
                    .order("created_at")
                    .execute()
                )
                messages = msg_result.data or []

    details = _compute_lead_score(lead, messages, last_message_at)
    activity_row = _persist_score(db, lead, details)
    if activity_row:
        try:
            db.table("activity_log").insert(activity_row).execute()
        except Exception:
            logger.warning("Failed to log score factors for lead %s", lead_id, exc_info=True)
    return details


def score_all_leads(tenant_id: str) -> dict[str, Any]:
    """Re-score all leads for a tenant. Returns summary.

    Batch reads (audit 2026-06-10 HIGH): 3 queries total instead of 3 per
    lead — leads, their conversations, and the tenant's chat_messages are
    fetched up front and joined in memory. Score updates stay per-lead
    (PostgREST has no multi-value bulk update); activity_log rows are
    inserted in one batch.
    """
    db = get_service_supabase()
    result = db.table("leads").select("*").eq("client_id", tenant_id).execute()
    leads = result.data or []

    # Batch-fetch conversations for all leads with one.
    conv_ids = [l["conversation_id"] for l in leads if l.get("conversation_id")]
    conv_by_id: dict[str, dict[str, Any]] = {}
    if conv_ids:
        conv_result = (
            db.table("conversations")
            .select("id, session_id, last_message_at")
            .in_("id", conv_ids)
            .execute()
        )
        conv_by_id = {c["id"]: c for c in (conv_result.data or [])}

    # Batch-fetch this tenant's chat messages for the sessions in play.
    session_ids = [c["session_id"] for c in conv_by_id.values() if c.get("session_id")]
    msgs_by_session: dict[str, list[dict[str, Any]]] = {}
    if session_ids:
        msg_result = (
            db.table("chat_messages")
            .select("session_id, role, content, created_at")
            .eq("tenant_id", tenant_id)
            .in_("session_id", session_ids)
            .order("created_at")
            .execute()
        )
        for m in msg_result.data or []:
            msgs_by_session.setdefault(m["session_id"], []).append(m)

    scored = 0
    errors = 0
    activity_rows: list[dict[str, Any]] = []
    for lead in leads:
        try:
            conv = conv_by_id.get(lead.get("conversation_id")) or {}
            messages = msgs_by_session.get(conv.get("session_id"), [])
            details = _compute_lead_score(lead, messages, conv.get("last_message_at"))
            activity_row = _persist_score(db, lead, details)
            if activity_row:
                activity_rows.append(activity_row)
            scored += 1
        except Exception:
            logger.warning("Failed to score lead %s", lead.get("id"), exc_info=True)
            errors += 1

    if activity_rows:
        try:
            db.table("activity_log").insert(activity_rows).execute()
        except Exception:
            logger.warning(
                "Failed to batch-log score factors for tenant %s", tenant_id, exc_info=True
            )

    return {
        "tenant_id": tenant_id,
        "scored": scored,
        "errors": errors,
        "total": len(leads),
    }


def score_lead_background(lead_id: str) -> None:
    """Fire-and-forget scoring wrapper for BackgroundTasks."""
    try:
        score_lead(lead_id)
    except Exception:
        logger.warning("Background scoring failed for lead %s", lead_id, exc_info=True)
