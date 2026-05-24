"""Dashboard analytics — health + snapshot endpoints.

- /{tenant_id}/health: debug counts for diagnostic verification
- /{tenant_id}/snapshot: shareable tester/client performance snapshot

WARNING: PEP 563 deferred annotations are incompatible with FastAPI — do not
add a future-annotations import here.
"""

import re as _re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query, Request

from backend.dependencies import _get_current_tenant, verify_tenant
from backend.limiter import limiter
from backend.models.database import get_service_supabase
from backend.routers.analytics._common import (
    _QUERY_LIMIT,
    _get_cached,
    _period_to_days,
    _set_cache,
    logger,
)
from backend.services.tenant_scope import tenant_table

router = APIRouter()


@router.get("/{tenant_id}/health")
async def analytics_health(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Debug endpoint: returns raw data counts for this tenant to diagnose analytics issues."""
    verify_tenant(claims, tenant_id)
    db = get_service_supabase()

    # Count unique sessions from chat_messages
    try:
        msgs = (
            tenant_table(db, "chat_messages", tenant_id)
            .select("session_id")
            .eq("tenant_id", tenant_id)
            .limit(5000)
            .execute()
        )
        unique_sessions = len({m["session_id"] for m in (msgs.data or [])})
    except Exception:
        logger.warning("analytics_health: failed to count sessions for %s", tenant_id, exc_info=True)
        unique_sessions = -1

    # Count leads (uses client_id, not tenant_id)
    try:
        leads_res = (
            tenant_table(db, "leads", tenant_id)
            .select("id", count="exact")
            .eq("client_id", tenant_id)
            .execute()
        )
        lead_count = leads_res.count if leads_res.count is not None else len(leads_res.data or [])
    except Exception:
        logger.warning("analytics_health: failed to count leads for %s", tenant_id, exc_info=True)
        lead_count = -1

    # Count appointments
    try:
        appts_res = (
            tenant_table(db, "appointments", tenant_id)
            .select("id", count="exact")
            .eq("tenant_id", tenant_id)
            .execute()
        )
        appt_count = appts_res.count if appts_res.count is not None else len(appts_res.data or [])
    except Exception:
        logger.warning("analytics_health: failed to count appointments for %s", tenant_id, exc_info=True)
        appt_count = -1

    # Most recent message timestamp
    try:
        recent = (
            tenant_table(db, "chat_messages", tenant_id)
            .select("created_at")
            .eq("tenant_id", tenant_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        last_msg_at = recent.data[0]["created_at"] if recent.data else None
    except Exception:
        logger.warning("analytics_health: failed to fetch last message for %s", tenant_id, exc_info=True)
        last_msg_at = None

    return {
        "tenant_id": tenant_id,
        "unique_widget_sessions": unique_sessions,
        "total_leads": lead_count,
        "total_appointments": appt_count,
        "last_message_at": last_msg_at,
        "note": "Use this to verify data exists before debugging dashboard card display",
    }


@router.get("/{tenant_id}/snapshot")
@limiter.limit("30/minute")
async def get_tester_snapshot(
    request: Request,
    tenant_id: str,
    period: str = Query("30d", pattern="^(7d|14d|30d|90d)$"),
    claims: dict = Depends(_get_current_tenant),
):
    """Generate a shareable performance snapshot for a tester/client."""
    verify_tenant(claims, tenant_id)

    cache_key = f"snapshot:{tenant_id}:{period}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    db = get_service_supabase()
    days = _period_to_days(period)
    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=days)).isoformat()

    # Business name
    biz_name = "Unknown"
    try:
        t = tenant_table(db, "tenants", tenant_id).select("business_name").eq("id", tenant_id).single().execute()
        biz_name = (t.data or {}).get("business_name", "Unknown")
    except Exception:
        logger.warning("snapshot: tenant name query failed for %s", tenant_id, exc_info=True)

    # Chat messages
    msgs = []
    try:
        r = tenant_table(db, "chat_messages", tenant_id).select("session_id, role, content, created_at").eq("tenant_id", tenant_id).gte("created_at", start).order("created_at").limit(_QUERY_LIMIT).execute()
        msgs = r.data or []
    except Exception:
        logger.warning("snapshot: chat_messages query failed for %s", tenant_id, exc_info=True)

    total_messages = len(msgs)
    user_msgs = [m for m in msgs if m.get("role") == "user"]
    sessions = {m["session_id"] for m in msgs}
    total_conversations = len(sessions)
    unique_visitors = len({m["session_id"].rsplit("_", 1)[-1] for m in msgs if m.get("session_id")})
    avg_per_conv = round(total_messages / max(total_conversations, 1), 1)

    # Top questions (exclude greetings/junk)
    _skip = {"hi", "hey", "hello", "yo", "sup", "e", "hiya", "howdy", ""}
    real_questions = []
    for m in user_msgs:
        normalized = _re.sub(r"[^a-z ]", "", (m.get("content") or "").strip().lower())
        if normalized not in _skip and len(normalized) > 3:
            real_questions.append(m.get("content", "").strip())

    # Count frequencies
    q_counts = Counter(real_questions)
    top_questions = [q for q, _ in q_counts.most_common(5)]

    # Busiest day
    day_counts: dict[str, int] = defaultdict(int)
    for m in msgs:
        day = (m.get("created_at") or "")[:10]
        if day:
            day_counts[day] += 1
    busiest_day = ""
    if day_counts:
        best = max(day_counts, key=day_counts.get)
        busiest_day = f"{best} ({day_counts[best]} messages)"

    # Leads
    total_leads = 0
    try:
        r = tenant_table(db, "leads", tenant_id).select("id").eq("client_id", tenant_id).gte("created_at", start).limit(_QUERY_LIMIT).execute()
        total_leads = len(r.data or [])
    except Exception:
        logger.warning("snapshot: leads query failed for %s", tenant_id, exc_info=True)

    # Appointments
    total_appointments = 0
    try:
        r = tenant_table(db, "appointments", tenant_id).select("id").eq("tenant_id", tenant_id).gte("created_at", start).limit(_QUERY_LIMIT).execute()
        total_appointments = len(r.data or [])
    except Exception:
        logger.warning("snapshot: appointments query failed for %s", tenant_id, exc_info=True)

    # Period string
    start_date = (now - timedelta(days=days)).strftime("%B %d")
    end_date = now.strftime("%B %d, %Y")
    period_str = f"{start_date} - {end_date}"

    result = {
        "business_name": biz_name,
        "period": period_str,
        "total_conversations": total_conversations,
        "total_messages": total_messages,
        "unique_visitors": unique_visitors,
        "leads_captured": total_leads,
        "appointments_booked": total_appointments,
        "avg_messages_per_conversation": avg_per_conv,
        "top_questions": top_questions,
        "busiest_day": busiest_day,
    }
    _set_cache(cache_key, result)
    return result
