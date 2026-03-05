"""Lead scoring engine — rule-based 0-100 scoring with engagement, intent, recency, and decay."""


import logging
from datetime import datetime, timezone
from typing import Any

from backend.models.database import get_supabase

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Intent keyword lists
# ---------------------------------------------------------------------------

_PRICING_KEYWORDS = ["price", "pricing", "cost", "fee", "rate", "charge", "quote", "estimate", "budget", "afford"]
_AVAILABILITY_KEYWORDS = ["available", "availability", "schedule", "appointment", "book", "when can", "open", "slot"]
_SERVICES_KEYWORDS = ["service", "offer", "provide", "do you", "help with", "looking for", "need", "want"]
_URGENCY_KEYWORDS = ["urgent", "asap", "today", "tomorrow", "right away", "immediately", "soon", "rush"]


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


def score_lead(lead_id: str) -> dict[str, Any]:
    """Score a single lead and persist the result. Returns scoring details."""
    db = get_supabase()

    # 1. Fetch lead
    lead_result = db.table("leads").select("*").eq("id", lead_id).limit(1).execute()
    if not lead_result.data:
        raise ValueError(f"Lead {lead_id} not found")
    lead = lead_result.data[0]

    # 2. Fetch conversation messages
    messages: list[dict[str, Any]] = []
    last_message_at: str | None = None
    conv_id = lead.get("conversation_id")
    if conv_id:
        conv_result = (
            db.table("conversations")
            .select("messages, last_message_at")
            .eq("id", conv_id)
            .limit(1)
            .execute()
        )
        if conv_result.data:
            messages = conv_result.data[0].get("messages") or []
            last_message_at = conv_result.data[0].get("last_message_at")

    # 3. Count user messages
    user_msg_count = sum(1 for m in messages if m.get("role") == "user")

    # 4. Compute sub-scores
    engagement, eng_bd = _score_engagement(lead, user_msg_count)
    intent, int_bd = _score_intent(messages)
    recency, rec_bd = _score_recency(last_message_at, lead.get("created_at"))
    decay, dec_bd = _compute_decay(last_message_at, lead.get("created_at"))

    raw_score = min(engagement + intent + recency, 100)
    final_score = max(0, raw_score - decay)

    # 5. Persist score (live schema: lead_score CHECK 1-10, scale from 0-100)
    db_score = max(1, min(10, round(final_score / 10)))
    db.table("leads").update({"lead_score": db_score}).eq("id", lead_id).execute()

    return {
        "lead_id": lead_id,
        "score": final_score,
        "raw_score": raw_score,
        "breakdown": {
            "engagement": eng_bd,
            "intent": int_bd,
            "recency": rec_bd,
            "decay": dec_bd,
        },
    }


def score_all_leads(tenant_id: str) -> dict[str, Any]:
    """Re-score all leads for a tenant. Returns summary."""
    db = get_supabase()
    result = db.table("leads").select("id").eq("client_id", tenant_id).execute()
    lead_ids = [r["id"] for r in (result.data or [])]

    scored = 0
    errors = 0
    for lid in lead_ids:
        try:
            score_lead(lid)
            scored += 1
        except Exception:
            logger.warning("Failed to score lead %s", lid, exc_info=True)
            errors += 1

    return {
        "tenant_id": tenant_id,
        "scored": scored,
        "errors": errors,
        "total": len(lead_ids),
    }


def score_lead_background(lead_id: str) -> None:
    """Fire-and-forget scoring wrapper for BackgroundTasks."""
    try:
        score_lead(lead_id)
    except Exception:
        logger.warning("Background scoring failed for lead %s", lead_id, exc_info=True)
