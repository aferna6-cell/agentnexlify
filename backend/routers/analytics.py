"""Analytics endpoints for dashboard metrics and trends."""

import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.dependencies import verify_tenant
from backend.models.database import get_supabase
from backend.routers.auth import _get_current_tenant

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])

# Simple in-memory cache: {cache_key: (timestamp, data)}
_cache: dict[str, tuple[float, dict]] = {}
_CACHE_TTL = 300  # 5 minutes

# Safety cap for unbounded queries — prevents timeouts on large tenants
_QUERY_LIMIT = 10000


def _get_cached(key: str) -> dict | None:
    if key in _cache:
        ts, data = _cache[key]
        if time.time() - ts < _CACHE_TTL:
            return data
        del _cache[key]
    return None


def _set_cache(key: str, data: dict) -> None:
    # Evict old entries if cache grows too large
    if len(_cache) > 500:
        cutoff = time.time() - _CACHE_TTL
        expired = [k for k, (ts, _) in _cache.items() if ts < cutoff]
        for k in expired:
            del _cache[k]
    _cache[key] = (time.time(), data)


def _period_to_days(period: str) -> int:
    mapping = {"7d": 7, "30d": 30, "90d": 90}
    return mapping.get(period, 30)


def _date_range(days: int) -> tuple[str, str]:
    """Return (start_iso, prev_start_iso) for current and previous period."""
    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=days)).isoformat()
    prev_start = (now - timedelta(days=days * 2)).isoformat()
    return start, prev_start


def _pct_change(current: float, previous: float) -> float:
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return round(((current - previous) / previous) * 100, 1)


# ------------------------------------------------------------------
# 1. Overview
# ------------------------------------------------------------------


@router.get("/{tenant_id}/overview")
async def get_overview(
    tenant_id: str,
    period: str = Query("30d", pattern="^(7d|30d|90d)$"),
    claims: dict = Depends(_get_current_tenant),
):
    verify_tenant(claims, tenant_id)

    cache_key = f"overview:{tenant_id}:{period}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    days = _period_to_days(period)
    start, prev_start = _date_range(days)
    now_iso = datetime.now(timezone.utc).isoformat()
    db = get_supabase()

    # Current period conversations — count rows in conversations table (avoids
    # fetching up to 10,000 chat_messages rows just to count unique sessions)
    try:
        curr_conv_result = (
            db.table("conversations")
            .select("id", count="exact")
            .eq("client_id", tenant_id)
            .gte("created_at", start)
            .lt("created_at", now_iso)
            .limit(1)
            .execute()
        )
        total_conversations = curr_conv_result.count or 0
    except Exception:
        logger.warning("Failed to fetch conversation analytics for %s", tenant_id, exc_info=True)
        total_conversations = 0

    # Avg messages per conversation via chat_messages (bounded query)
    try:
        curr_msgs = (
            db.table("chat_messages")
            .select("id")
            .eq("tenant_id", tenant_id)
            .gte("created_at", start)
            .lt("created_at", now_iso)
            .limit(_QUERY_LIMIT)
            .execute()
        )
        total_messages = len(curr_msgs.data or [])
        avg_messages = round(total_messages / total_conversations, 1) if total_conversations > 0 else 0
    except Exception:
        logger.warning("Failed to fetch message count for %s", tenant_id, exc_info=True)
        total_messages = 0
        avg_messages = 0

    # Previous period conversations
    try:
        prev_conv_result = (
            db.table("conversations")
            .select("id", count="exact")
            .eq("client_id", tenant_id)
            .gte("created_at", prev_start)
            .lt("created_at", start)
            .limit(1)
            .execute()
        )
        prev_conversations = prev_conv_result.count or 0
    except Exception:
        logger.warning("Failed to fetch previous period conversations for %s", tenant_id, exc_info=True)
        prev_conversations = 0

    # Current period leads (leads use client_id, not tenant_id)
    try:
        curr_leads = (
            db.table("leads")
            .select("id")
            .eq("client_id", tenant_id)
            .gte("created_at", start)
            .lt("created_at", now_iso)
            .limit(_QUERY_LIMIT)
            .execute()
        )
        total_leads = len(curr_leads.data or [])
    except Exception:
        logger.warning("Failed to fetch current period leads for %s", tenant_id, exc_info=True)
        total_leads = 0

    # Previous period leads
    try:
        prev_leads_res = (
            db.table("leads")
            .select("id")
            .eq("client_id", tenant_id)
            .gte("created_at", prev_start)
            .lt("created_at", start)
            .limit(_QUERY_LIMIT)
            .execute()
        )
        prev_leads = len(prev_leads_res.data or [])
    except Exception:
        logger.warning("Failed to fetch previous period leads for %s", tenant_id, exc_info=True)
        prev_leads = 0

    # Conversion rate
    conversion_rate = round((total_leads / total_conversations * 100), 1) if total_conversations > 0 else 0.0
    prev_conversion = round((prev_leads / prev_conversations * 100), 1) if prev_conversations > 0 else 0.0

    # Appointments
    try:
        curr_appts = (
            db.table("appointments")
            .select("id")
            .eq("tenant_id", tenant_id)
            .gte("created_at", start)
            .lt("created_at", now_iso)
            .neq("status", "cancelled")
            .limit(_QUERY_LIMIT)
            .execute()
        )
        total_appointments = len(curr_appts.data or [])
    except Exception:
        logger.warning("Failed to fetch current period appointments for %s", tenant_id, exc_info=True)
        total_appointments = 0

    try:
        prev_appts = (
            db.table("appointments")
            .select("id")
            .eq("tenant_id", tenant_id)
            .gte("created_at", prev_start)
            .lt("created_at", start)
            .neq("status", "cancelled")
            .limit(_QUERY_LIMIT)
            .execute()
        )
        prev_appointments = len(prev_appts.data or [])
    except Exception:
        logger.warning("Failed to fetch previous period appointments for %s", tenant_id, exc_info=True)
        prev_appointments = 0

    # Emails sent (from automation_logs via automation_executions)
    try:
        curr_emails = (
            db.table("automation_logs")
            .select("id, execution_id!inner(tenant_id)")
            .eq("execution_id.tenant_id", tenant_id)
            .eq("action", "email_sent")
            .gte("created_at", start)
            .limit(_QUERY_LIMIT)
            .execute()
        )
        total_emails = len(curr_emails.data or [])
    except Exception:
        # Fallback: count email_sent from activity_log
        try:
            email_acts = (
                db.table("activity_log")
                .select("id")
                .eq("tenant_id", tenant_id)
                .eq("activity_type", "email_sent")
                .gte("created_at", start)
                .limit(_QUERY_LIMIT)
                .execute()
            )
            total_emails = len(email_acts.data or [])
        except Exception:
            logger.warning("Failed to fetch email count from any source for %s", tenant_id, exc_info=True)
            total_emails = 0

    result = {
        "total_conversations": total_conversations,
        "total_leads": total_leads,
        "conversion_rate": conversion_rate,
        "total_messages": total_messages,
        "avg_messages_per_conversation": avg_messages,
        "total_appointments": total_appointments,
        "total_emails_sent": total_emails,
        "changes": {
            "conversations": _pct_change(total_conversations, prev_conversations),
            "leads": _pct_change(total_leads, prev_leads),
            "conversion_rate": round(conversion_rate - prev_conversion, 1),
            "appointments": _pct_change(total_appointments, prev_appointments),
        },
    }

    _set_cache(cache_key, result)
    return result


# ------------------------------------------------------------------
# 2. Conversations over time
# ------------------------------------------------------------------


@router.get("/{tenant_id}/conversations")
async def get_conversations_trend(
    tenant_id: str,
    period: str = Query("30d", pattern="^(7d|30d|90d)$"),
    claims: dict = Depends(_get_current_tenant),
):
    verify_tenant(claims, tenant_id)

    cache_key = f"convos_trend:{tenant_id}:{period}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    days = _period_to_days(period)
    now_iso = datetime.now(timezone.utc).isoformat()
    start = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    db = get_supabase()

    try:
        # Query conversations table directly — avoids fetching thousands of
        # chat_messages rows just to count unique sessions per day.
        convos = (
            db.table("conversations")
            .select("created_at")
            .eq("client_id", tenant_id)
            .gte("created_at", start)
            .lt("created_at", now_iso)
            .order("created_at")
            .limit(_QUERY_LIMIT)
            .execute()
        )

        # Count conversations by date
        count_by_date: dict[str, int] = defaultdict(int)
        for row in convos.data or []:
            date_str = row["created_at"][:10]
            count_by_date[date_str] += 1

        # Build full date range with zeroes for days with no activity
        today = datetime.now(timezone.utc).date()
        result_data = []
        for i in range(days):
            d = (today - timedelta(days=days - 1 - i)).isoformat()
            result_data.append({"date": d, "count": count_by_date.get(d, 0)})
    except Exception:
        logger.warning("Failed to fetch conversation trends for %s", tenant_id, exc_info=True)
        result_data = []

    result = {"data": result_data}
    _set_cache(cache_key, result)
    return result


# ------------------------------------------------------------------
# 3. Leads analytics
# ------------------------------------------------------------------


@router.get("/{tenant_id}/leads")
async def get_leads_analytics(
    tenant_id: str,
    period: str = Query("30d", pattern="^(7d|30d|90d)$"),
    claims: dict = Depends(_get_current_tenant),
):
    verify_tenant(claims, tenant_id)

    cache_key = f"leads_analytics:{tenant_id}:{period}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    days = _period_to_days(period)
    now_iso = datetime.now(timezone.utc).isoformat()
    start = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    db = get_supabase()

    # All leads in period
    try:
        leads_res = (
            db.table("leads")
            .select("id, status, lead_score, created_at")
            .eq("client_id", tenant_id)
            .gte("created_at", start)
            .lt("created_at", now_iso)
            .limit(_QUERY_LIMIT)
            .execute()
        )
        leads = leads_res.data or []
    except Exception:
        logger.warning("Failed to fetch leads analytics", exc_info=True)
        leads = []

    # Daily count
    daily: dict[str, int] = defaultdict(int)
    stage_breakdown: dict[str, int] = defaultdict(int)
    scores = []

    for lead in leads:
        date_str = lead["created_at"][:10]
        daily[date_str] += 1
        stage_breakdown[lead.get("status") or "new"] += 1
        if lead.get("lead_score") is not None:
            scores.append(lead["lead_score"])

    today = datetime.now(timezone.utc).date()
    daily_data = []
    for i in range(days):
        d = (today - timedelta(days=days - 1 - i)).isoformat()
        daily_data.append({"date": d, "count": daily.get(d, 0)})

    avg_score = round(sum(scores) / len(scores), 1) if scores else 0

    result = {
        "daily": daily_data,
        "by_stage": dict(stage_breakdown),
        "by_source": {"widget": len(leads)},
        "avg_lead_score": avg_score,
        "total": len(leads),
    }

    _set_cache(cache_key, result)
    return result


# ------------------------------------------------------------------
# 5. Widget analytics
# ------------------------------------------------------------------


@router.get("/{tenant_id}/widget")
async def get_widget_analytics(
    tenant_id: str,
    period: str = Query("30d", pattern="^(7d|30d|90d)$"),
    claims: dict = Depends(_get_current_tenant),
):
    verify_tenant(claims, tenant_id)

    cache_key = f"widget:{tenant_id}:{period}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    days = _period_to_days(period)
    now_iso = datetime.now(timezone.utc).isoformat()
    start = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    db = get_supabase()

    # Conversations started (unique sessions with messages)
    try:
        msgs = (
            db.table("chat_messages")
            .select("session_id, created_at")
            .eq("tenant_id", tenant_id)
            .gte("created_at", start)
            .lt("created_at", now_iso)
            .order("created_at")
            .limit(_QUERY_LIMIT)
            .execute()
        )

        sessions_data: dict[str, list[str]] = defaultdict(list)
        for row in msgs.data or []:
            sessions_data[row["session_id"]].append(row["created_at"])

        conversations_started = len(sessions_data)

        # Peak hours
        hour_counts: dict[int, int] = defaultdict(int)
        durations: list[float] = []

        for session_id, timestamps in sessions_data.items():
            timestamps.sort()
            # Count by hour of first message
            first_ts = datetime.fromisoformat(timestamps[0].replace("Z", "+00:00"))
            hour_counts[first_ts.hour] += 1

            # Duration
            if len(timestamps) >= 2:
                first = datetime.fromisoformat(timestamps[0].replace("Z", "+00:00"))
                last = datetime.fromisoformat(timestamps[-1].replace("Z", "+00:00"))
                dur = (last - first).total_seconds()
                if dur > 0:
                    durations.append(dur)

        peak_hours = [{"hour": h, "count": hour_counts.get(h, 0)} for h in range(24)]
        avg_duration = round(sum(durations) / len(durations), 1) if durations else 0

    except Exception:
        logger.warning("Failed to fetch widget analytics", exc_info=True)
        conversations_started = 0
        peak_hours = [{"hour": h, "count": 0} for h in range(24)]
        avg_duration = 0

    # Widget loads — use conversations_used_this_month as proxy if no dedicated tracking
    try:
        tenant_res = (
            db.table("tenants")
            .select("conversations_used_this_month")
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
        widget_loads = (tenant_res.data[0]["conversations_used_this_month"] or 0) if tenant_res.data else 0
    except Exception:
        logger.warning("Failed to fetch widget loads for %s", tenant_id, exc_info=True)
        widget_loads = 0

    engagement_rate = round((conversations_started / widget_loads * 100), 1) if widget_loads > 0 else 0

    result = {
        "widget_loads": widget_loads,
        "conversations_started": conversations_started,
        "engagement_rate": engagement_rate,
        "peak_hours": peak_hours,
        "avg_duration_seconds": avg_duration,
    }

    _set_cache(cache_key, result)
    return result


# ------------------------------------------------------------------
# 4. Response times (reads from response_metrics table)
# ------------------------------------------------------------------


@router.get("/{tenant_id}/response-times")
async def get_response_time_analytics(
    tenant_id: str,
    period: str = Query("30d", pattern="^(7d|30d|90d)$"),
    claims: dict = Depends(_get_current_tenant),
):
    """Get response time analytics from the response_metrics table."""
    verify_tenant(claims, tenant_id)

    days = {"7d": 7, "30d": 30, "90d": 90}[period]
    start = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    db = get_supabase()
    try:
        result = (
            db.table("response_metrics")
            .select("response_time_seconds, first_message_at, outcome")
            .eq("tenant_id", tenant_id)
            .gte("created_at", start)
            .order("created_at")
            .limit(1000)
            .execute()
        )
    except Exception:
        logger.warning("response_time_analytics: query failed for %s", tenant_id, exc_info=True)
        return {"avg_response_seconds": 0, "median_response_seconds": 0, "total_conversations": 0, "by_day": [], "outcomes": {}}

    data = result.data or []
    if not data:
        return {"avg_response_seconds": 0, "median_response_seconds": 0, "total_conversations": 0, "by_day": [], "outcomes": {}}

    times = [d["response_time_seconds"] for d in data if d.get("response_time_seconds") is not None]
    avg_time = round(sum(times) / len(times)) if times else 0
    sorted_times = sorted(times)
    median_time = sorted_times[len(sorted_times) // 2] if sorted_times else 0

    # Group by day
    by_day: dict[str, list[int]] = defaultdict(list)
    for d in data:
        if d.get("first_message_at") and d.get("response_time_seconds") is not None:
            day = d["first_message_at"][:10]
            by_day[day].append(d["response_time_seconds"])

    daily = [{"date": day, "avg_seconds": round(sum(v) / len(v)), "count": len(v)} for day, v in sorted(by_day.items())]

    # Outcomes
    outcomes: dict[str, int] = defaultdict(int)
    for d in data:
        outcome = d.get("outcome") or "unknown"
        outcomes[outcome] += 1

    return {
        "avg_response_seconds": avg_time,
        "median_response_seconds": median_time,
        "total_conversations": len(data),
        "by_day": daily,
        "outcomes": dict(outcomes),
    }


# ------------------------------------------------------------------
# 6. Missed opportunity detection
# ------------------------------------------------------------------

# Keywords that signal pricing interest (case-insensitive matching)
_PRICING_KEYWORDS = [
    "price", "pricing", "cost", "costs", "quote", "estimate",
    "how much", "rate", "rates", "fee", "fees", "charge", "charges",
    "budget", "affordable", "expensive", "cheap", "discount",
]


@router.get("/{tenant_id}/missed-opportunities")
async def get_missed_opportunities(
    tenant_id: str,
    period: str = Query("30d", pattern="^(7d|30d|90d)$"),
    claims: dict = Depends(_get_current_tenant),
):
    """Detect conversations that represent missed business opportunities.

    A conversation is flagged as a missed opportunity if:
    - The last message is from the user (no response given)
    - The conversation has fewer than 3 total messages (visitor abandoned)
    - A user message mentions pricing keywords but no appointment was booked
    """
    verify_tenant(claims, tenant_id)

    cache_key = f"missed_opps:{tenant_id}:{period}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    days = _period_to_days(period)
    now_iso = datetime.now(timezone.utc).isoformat()
    start = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    db = get_supabase()

    # --- Batch query 1: All chat messages in the period ---
    try:
        msgs_res = (
            db.table("chat_messages")
            .select("session_id, role, content, created_at")
            .eq("tenant_id", tenant_id)
            .gte("created_at", start)
            .lt("created_at", now_iso)
            .order("created_at")
            .limit(_QUERY_LIMIT)
            .execute()
        )
        all_messages = msgs_res.data or []
    except Exception:
        logger.warning("missed-opportunities: failed to fetch chat_messages for %s", tenant_id, exc_info=True)
        return {
            "total_missed": 0,
            "missed_conversations": [],
            "breakdown": {"no_response": 0, "abandoned": 0, "pricing_no_booking": 0},
        }

    if not all_messages:
        result = {
            "total_missed": 0,
            "missed_conversations": [],
            "breakdown": {"no_response": 0, "abandoned": 0, "pricing_no_booking": 0},
        }
        _set_cache(cache_key, result)
        return result

    # Group messages by session_id, preserving order
    sessions: dict[str, list[dict]] = defaultdict(list)
    for msg in all_messages:
        sessions[msg["session_id"]].append(msg)

    session_ids = list(sessions.keys())

    # --- Batch query 2: conversations table for session_id -> lead_id mapping ---
    lead_ids_by_session: dict[str, str | None] = {}
    try:
        # Query in chunks to avoid URL length limits
        chunk_size = 200
        for i in range(0, len(session_ids), chunk_size):
            chunk = session_ids[i : i + chunk_size]
            convos_res = (
                db.table("conversations")
                .select("session_id, lead_id")
                .eq("client_id", tenant_id)
                .in_("session_id", chunk)
                .execute()
            )
            for row in convos_res.data or []:
                lead_ids_by_session[row["session_id"]] = row.get("lead_id")
    except Exception:
        logger.warning("missed-opportunities: failed to fetch conversations for %s", tenant_id, exc_info=True)
        # Continue without lead mapping — pricing_no_booking won't fire but other checks still work

    # --- Batch query 3: appointments for leads that have bookings ---
    all_lead_ids = [lid for lid in lead_ids_by_session.values() if lid]
    booked_lead_ids: set[str] = set()
    if all_lead_ids:
        try:
            chunk_size = 200
            for i in range(0, len(all_lead_ids), chunk_size):
                chunk = all_lead_ids[i : i + chunk_size]
                appts_res = (
                    db.table("appointments")
                    .select("lead_id")
                    .eq("tenant_id", tenant_id)
                    .in_("lead_id", chunk)
                    .neq("status", "cancelled")
                    .execute()
                )
                for row in appts_res.data or []:
                    if row.get("lead_id"):
                        booked_lead_ids.add(row["lead_id"])
        except Exception:
            logger.warning("missed-opportunities: failed to fetch appointments for %s", tenant_id, exc_info=True)
            # Continue — pricing_no_booking just won't detect bookings

    # --- Evaluate each session for missed opportunity signals ---
    missed_conversations: list[dict] = []
    breakdown = {"no_response": 0, "abandoned": 0, "pricing_no_booking": 0}

    for session_id, messages in sessions.items():
        reasons: list[str] = []

        # Condition 1: Last message is from the user (no response)
        if messages[-1]["role"] == "user":
            reasons.append("no_response")

        # Condition 2: Fewer than 3 total messages (visitor abandoned quickly)
        if len(messages) < 3:
            reasons.append("abandoned")

        # Condition 3: User mentioned pricing keywords but no appointment booked
        lead_id = lead_ids_by_session.get(session_id)
        has_booking = lead_id in booked_lead_ids if lead_id else False

        if not has_booking:
            user_text = " ".join(
                m["content"].lower() for m in messages if m["role"] == "user"
            )
            if any(kw in user_text for kw in _PRICING_KEYWORDS):
                reasons.append("pricing_no_booking")

        if not reasons:
            continue

        # Count each reason in the breakdown
        for reason in reasons:
            breakdown[reason] += 1

        # Build the missed conversation entry
        last_msg = messages[-1]
        preview = last_msg["content"][:120]
        if len(last_msg["content"]) > 120:
            preview += "..."

        missed_conversations.append({
            "session_id": session_id,
            "reason": reasons[0] if len(reasons) == 1 else reasons,
            "last_message_preview": preview,
            "created_at": messages[0]["created_at"],
            "message_count": len(messages),
        })

    # Sort by created_at descending (most recent first), limit to 20
    missed_conversations.sort(key=lambda x: x["created_at"], reverse=True)
    total_missed = len(missed_conversations)
    missed_conversations = missed_conversations[:20]

    result = {
        "total_missed": total_missed,
        "missed_conversations": missed_conversations,
        "breakdown": breakdown,
    }

    _set_cache(cache_key, result)
    return result


@router.get("/{tenant_id}/missed-calls")
async def get_missed_call_analytics(
    tenant_id: str,
    period: str = Query("30d", pattern="^(7d|30d|90d)$"),
    claims: dict = Depends(_get_current_tenant),
):
    """Per-day missed call analytics from activity_log."""
    verify_tenant(claims, tenant_id)

    cache_key = f"missed_calls:{tenant_id}:{period}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    days = {"7d": 7, "30d": 30, "90d": 90}[period]
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    db = get_supabase()
    try:
        entries = (
            db.table("activity_log")
            .select("created_at")
            .eq("tenant_id", tenant_id)
            .eq("activity_type", "missed_call_textback")
            .gte("created_at", since)
            .order("created_at")
            .limit(_QUERY_LIMIT)
            .execute()
        )
    except Exception:
        logger.warning("missed-calls analytics failed for %s", tenant_id, exc_info=True)
        return {"daily": [], "total": 0, "texted_back": 0}

    daily_counts: dict[str, int] = defaultdict(int)
    for entry in entries.data or []:
        date_str = entry.get("created_at", "")[:10]
        if date_str:
            daily_counts[date_str] += 1

    daily = [{"date": d, "count": c} for d, c in sorted(daily_counts.items())]
    total = sum(c for c in daily_counts.values())

    mc_response = {"daily": daily, "total": total, "texted_back": total}
    _set_cache(cache_key, mc_response)
    return mc_response


@router.get("/{tenant_id}/ai-insights")
async def get_ai_insights(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Generate AI-powered business insights for the last 7 days.

    Returns metrics + Claude-generated analysis with actionable recommendations.
    Cached for 1 hour to avoid excessive API calls.
    """
    import anthropic
    from backend.config import settings

    verify_tenant(claims, tenant_id)

    cache_key = f"ai_insights:{tenant_id}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    db = get_supabase()
    now = datetime.now(timezone.utc)
    week_ago = (now - timedelta(days=7)).isoformat()
    prev_week_start = (now - timedelta(days=14)).isoformat()

    metrics = {}

    # Current week leads (uses client_id)
    try:
        leads_result = db.table("leads").select("id, status, lead_temperature, deal_value").eq("client_id", tenant_id).gte("created_at", week_ago).limit(500).execute()
        leads_data = leads_result.data or []
        metrics["new_leads"] = len(leads_data)
        metrics["hot_leads"] = sum(1 for l in leads_data if l.get("lead_temperature") == "hot")
        metrics["pipeline_value"] = sum(float(l.get("deal_value") or 0) for l in leads_data)
    except Exception:
        metrics["new_leads"] = 0
        metrics["hot_leads"] = 0
        metrics["pipeline_value"] = 0

    # Previous week leads for comparison
    try:
        prev_leads = db.table("leads").select("id", count="exact").eq("client_id", tenant_id).gte("created_at", prev_week_start).lt("created_at", week_ago).limit(1).execute()
        metrics["prev_leads"] = prev_leads.count or 0
    except Exception:
        metrics["prev_leads"] = 0

    # Conversations
    try:
        conv_result = db.table("conversations").select("id", count="exact").eq("client_id", tenant_id).gte("created_at", week_ago).limit(1).execute()
        metrics["conversations"] = conv_result.count or 0
    except Exception:
        metrics["conversations"] = 0

    # Appointments
    try:
        appt_result = db.table("appointments").select("id, status").eq("tenant_id", tenant_id).gte("created_at", week_ago).limit(500).execute()
        appt_data = appt_result.data or []
        metrics["appointments"] = len(appt_data)
        metrics["completed_appointments"] = sum(1 for a in appt_data if a.get("status") == "completed")
    except Exception:
        metrics["appointments"] = 0
        metrics["completed_appointments"] = 0

    # Invoices
    try:
        inv_result = db.table("invoices").select("id, status, total").eq("tenant_id", tenant_id).gte("created_at", week_ago).limit(500).execute()
        inv_data = inv_result.data or []
        metrics["invoices_created"] = len(inv_data)
        metrics["invoices_paid"] = sum(1 for i in inv_data if i.get("status") == "paid")
        metrics["revenue"] = sum(float(i.get("total") or 0) for i in inv_data if i.get("status") == "paid")
        metrics["outstanding"] = sum(float(i.get("total") or 0) for i in inv_data if i.get("status") in ("sent", "viewed", "overdue"))
    except Exception:
        metrics["invoices_created"] = 0
        metrics["invoices_paid"] = 0
        metrics["revenue"] = 0
        metrics["outstanding"] = 0

    # Reviews
    try:
        rev_result = db.table("reviews").select("id, rating").eq("tenant_id", tenant_id).gte("created_at", week_ago).limit(50).execute()
        rev_data = rev_result.data or []
        metrics["reviews"] = len(rev_data)
        metrics["avg_rating"] = round(sum(r.get("rating", 0) for r in rev_data) / max(len(rev_data), 1), 1) if rev_data else 0
    except Exception:
        metrics["reviews"] = 0
        metrics["avg_rating"] = 0

    # Pending action items
    try:
        actions_result = db.table("action_items").select("id", count="exact").eq("tenant_id", tenant_id).eq("status", "pending").limit(1).execute()
        metrics["pending_actions"] = actions_result.count or 0
    except Exception:
        metrics["pending_actions"] = 0

    # Get tenant info for AI context
    try:
        tenant_result = db.table("tenants").select("business_name, business_type").eq("id", tenant_id).limit(1).execute()
        tenant_info = tenant_result.data[0] if tenant_result.data else {}
    except Exception:
        tenant_info = {}

    biz_name = tenant_info.get("business_name") or "Your Business"
    biz_type = tenant_info.get("business_type") or "local business"

    # Generate AI analysis
    ai_analysis = ""
    if settings.anthropic_api_key:
        lead_change = metrics["new_leads"] - metrics.get("prev_leads", 0)
        change_text = f"{'up' if lead_change > 0 else 'down'} {abs(lead_change)} from last week" if lead_change != 0 else "same as last week"

        try:
            client = anthropic.Anthropic(api_key=settings.anthropic_api_key, timeout=30.0)
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=400,
                messages=[{"role": "user", "content": f"""You are a business intelligence analyst for a {biz_type} called "{biz_name}".

This week's metrics:
- New leads: {metrics['new_leads']} ({change_text}), {metrics['hot_leads']} hot
- Conversations: {metrics['conversations']}
- Appointments: {metrics['appointments']} ({metrics['completed_appointments']} completed)
- Invoices: {metrics['invoices_created']} created, {metrics['invoices_paid']} paid
- Revenue collected: ${metrics['revenue']:.2f}, outstanding: ${metrics['outstanding']:.2f}
- Pipeline value: ${metrics['pipeline_value']:.2f}
- Reviews: {metrics['reviews']} (avg {metrics['avg_rating']})
- Pending action items: {metrics['pending_actions']}

Write 3-4 bullet points: what's going well, what needs attention, one actionable recommendation. Be specific with numbers. Keep it under 200 words."""}],
            )
            ai_analysis = response.content[0].text if response.content else ""
        except Exception:
            logger.warning("AI insights generation failed for tenant %s", tenant_id, exc_info=True)

    result = {
        "metrics": metrics,
        "ai_analysis": ai_analysis,
        "generated_at": now.isoformat(),
        "business_name": biz_name,
    }

    # Cache for 1 hour (override default TTL)
    _cache[cache_key] = (time.time() + 3600 - _CACHE_TTL, result)
    return result


@router.get("/{tenant_id}/lead-sources")
async def lead_source_breakdown(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Aggregate leads by source for analytics visualization."""
    verify_tenant(claims, tenant_id)

    cache_key = f"lead_sources:{tenant_id}"
    cached = _cache.get(cache_key)
    if cached and time.time() - cached[0] < _CACHE_TTL:
        return cached[1]

    db = get_supabase()
    try:
        result = db.table("leads").select("source").eq("client_id", tenant_id).execute()
    except Exception:
        logger.exception("Failed to fetch lead sources for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to load lead source data")

    counts: dict[str, int] = defaultdict(int)
    for lead in result.data or []:
        source = lead.get("source") or "widget"
        counts[source] += 1

    # Format for charting
    breakdown = [
        {"source": source, "count": count}
        for source, count in sorted(counts.items(), key=lambda x: -x[1])
    ]

    response = {"breakdown": breakdown, "total": sum(counts.values())}
    _cache[cache_key] = (time.time(), response)
    return response


# ---------------------------------------------------------------------------
# Appointment No-Show Analytics
# ---------------------------------------------------------------------------

@router.get("/{tenant_id}/no-show-stats")
async def no_show_stats(
    tenant_id: str,
    days: int = Query(30, ge=7, le=365),
    claims: dict = Depends(_get_current_tenant),
):
    """Get appointment no-show statistics for the specified period.

    Returns:
    - no_show_count: Total no-shows in period
    - total_appointments: Total appointments (excluding cancelled) in period
    - no_show_rate: Percentage of no-shows
    - repeat_no_shows: Leads with 2+ no-shows (chronic no-showers)
    """
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db = get_supabase()
    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=days)).isoformat()

    # Get all non-cancelled appointments in period
    try:
        appts = (
            db.table("appointments")
            .select("id, status, lead_id, customer_name, start_time")
            .eq("tenant_id", tenant_id)
            .gte("start_time", start)
            .neq("status", "cancelled")
            .limit(2000)
            .execute()
        )
    except Exception:
        logger.exception("no_show_stats: failed to query appointments for %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to fetch appointment data")

    all_appts = appts.data or []
    total = len(all_appts)
    no_shows = [a for a in all_appts if a.get("status") == "no_show"]
    no_show_count = len(no_shows)
    no_show_rate = round((no_show_count / total * 100), 1) if total > 0 else 0

    # Find repeat no-show leads
    lead_no_show_counts = {}
    for ns in no_shows:
        lid = ns.get("lead_id")
        if lid:
            if lid not in lead_no_show_counts:
                lead_no_show_counts[lid] = {"count": 0, "name": ns.get("customer_name") or "Unknown"}
            lead_no_show_counts[lid]["count"] += 1

    repeat_no_shows = [
        {"lead_id": lid, "name": info["name"], "no_show_count": info["count"]}
        for lid, info in lead_no_show_counts.items()
        if info["count"] >= 2
    ]
    repeat_no_shows.sort(key=lambda x: -x["no_show_count"])

    return {
        "period_days": days,
        "total_appointments": total,
        "no_show_count": no_show_count,
        "no_show_rate": no_show_rate,
        "completed_count": len([a for a in all_appts if a.get("status") == "completed"]),
        "repeat_no_shows": repeat_no_shows[:20],
    }


# ---------------------------------------------------------------------------
# Appointment Type Analytics (Service Type Breakdown)
# ---------------------------------------------------------------------------


@router.get("/{tenant_id}/appointment-types")
async def get_appointment_type_analytics(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
    days: int = Query(30, ge=7, le=365),
):
    """Analyze appointment data by service type: popularity, revenue, no-show rates."""
    if claims.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    cache_key = f"appt_types:{tenant_id}:{days}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    db = get_supabase()
    start = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    # Get service types for this tenant
    service_types = {}
    try:
        st_result = db.table("service_types").select("id, name, duration_minutes, price").eq("tenant_id", tenant_id).execute()
        for st in (st_result.data or []):
            service_types[st["id"]] = st
    except Exception:
        logger.warning("appointment_type_analytics: failed to fetch service types for %s", tenant_id, exc_info=True)

    # Get appointments in period
    try:
        appts_result = (
            db.table("appointments")
            .select("id, status, notes, start_time, customer_name")
            .eq("tenant_id", tenant_id)
            .gte("start_time", start)
            .limit(_QUERY_LIMIT)
            .execute()
        )
    except Exception:
        logger.exception("appointment_type_analytics: failed to fetch appointments for %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to fetch appointments")

    appts = appts_result.data or []

    # Group by service type (extracted from notes or default)
    type_stats: dict[str, dict] = defaultdict(lambda: {
        "name": "General",
        "count": 0,
        "completed": 0,
        "no_show": 0,
        "cancelled": 0,
        "revenue_estimate": 0.0,
    })

    for appt in appts:
        # Try to identify service type from notes
        notes = appt.get("notes") or ""
        matched_type = "general"
        matched_name = "General"
        matched_price = 0.0

        for st_id, st_info in service_types.items():
            st_name = st_info.get("name") or ""
            if st_name.lower() in notes.lower():
                matched_type = st_id
                matched_name = st_name
                matched_price = float(st_info.get("price") or 0)
                break

        stats = type_stats[matched_type]
        stats["name"] = matched_name
        stats["count"] += 1

        status = appt.get("status") or ""
        if status == "completed":
            stats["completed"] += 1
            stats["revenue_estimate"] += matched_price
        elif status == "no_show":
            stats["no_show"] += 1
        elif status == "cancelled":
            stats["cancelled"] += 1

    # Convert to sorted list
    breakdown = []
    for type_id, stats in type_stats.items():
        no_show_rate = round(stats["no_show"] / stats["count"] * 100, 1) if stats["count"] > 0 else 0
        breakdown.append({
            "service_type": stats["name"],
            "total": stats["count"],
            "completed": stats["completed"],
            "no_show": stats["no_show"],
            "no_show_rate": no_show_rate,
            "cancelled": stats["cancelled"],
            "revenue_estimate": round(stats["revenue_estimate"], 2),
        })
    breakdown.sort(key=lambda x: x["total"], reverse=True)

    result = {
        "period_days": days,
        "total_appointments": len(appts),
        "service_types_configured": len(service_types),
        "breakdown": breakdown[:20],
    }
    _set_cached(cache_key, result)
    return result


# ---------------------------------------------------------------------------
# Widget Visitor Funnel Analytics
# ---------------------------------------------------------------------------


@router.get("/{tenant_id}/widget-funnel")
async def get_widget_funnel(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
    days: int = Query(30, ge=7, le=365),
):
    """Widget conversion funnel: sessions started -> leads captured -> appointments booked.

    Since we don't track raw widget impressions (page loads without interaction),
    we measure from the first interaction point: unique session_ids in chat_messages.
    """
    if claims.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    cache_key = f"widget_funnel:{tenant_id}:{days}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    db = get_supabase()
    start = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    # 1. Unique chat sessions (conversations started)
    sessions_started = 0
    daily_sessions: dict[str, int] = defaultdict(int)
    try:
        msgs = (
            db.table("chat_messages")
            .select("session_id, created_at")
            .eq("tenant_id", tenant_id)
            .eq("role", "user")
            .gte("created_at", start)
            .limit(_QUERY_LIMIT)
            .execute()
        )
        session_dates: dict[str, str] = {}
        for m in (msgs.data or []):
            sid = m.get("session_id")
            if sid and sid not in session_dates:
                session_dates[sid] = (m.get("created_at") or "")[:10]
        sessions_started = len(session_dates)
        for date_str in session_dates.values():
            if date_str:
                daily_sessions[date_str] += 1
    except Exception:
        logger.warning("widget_funnel: failed to count sessions for %s", tenant_id, exc_info=True)

    # 2. Leads captured (from widget source)
    leads_captured = 0
    try:
        leads_r = (
            db.table("leads")
            .select("id", count="exact")
            .eq("client_id", tenant_id)
            .eq("source", "widget")
            .gte("created_at", start)
            .limit(1)
            .execute()
        )
        leads_captured = leads_r.count or 0
    except Exception:
        # Fallback: count all leads in period
        try:
            leads_r2 = (
                db.table("leads")
                .select("id", count="exact")
                .eq("client_id", tenant_id)
                .gte("created_at", start)
                .limit(1)
                .execute()
            )
            leads_captured = leads_r2.count or 0
        except Exception:
            logger.warning("widget_funnel: failed to count leads for %s", tenant_id, exc_info=True)

    # 3. Appointments booked in period
    appts_booked = 0
    try:
        appts_r = (
            db.table("appointments")
            .select("id", count="exact")
            .eq("tenant_id", tenant_id)
            .gte("created_at", start)
            .limit(1)
            .execute()
        )
        appts_booked = appts_r.count or 0
    except Exception:
        logger.warning("widget_funnel: failed to count appointments for %s", tenant_id, exc_info=True)

    # Compute conversion rates
    session_to_lead = round(leads_captured / sessions_started * 100, 1) if sessions_started > 0 else 0
    lead_to_appt = round(appts_booked / leads_captured * 100, 1) if leads_captured > 0 else 0
    session_to_appt = round(appts_booked / sessions_started * 100, 1) if sessions_started > 0 else 0

    # Daily trend (last 14 days)
    daily_trend = sorted(
        [{"date": d, "sessions": c} for d, c in daily_sessions.items()],
        key=lambda x: x["date"],
    )[-14:]

    result = {
        "period_days": days,
        "sessions_started": sessions_started,
        "leads_captured": leads_captured,
        "appointments_booked": appts_booked,
        "session_to_lead_rate": session_to_lead,
        "lead_to_appointment_rate": lead_to_appt,
        "session_to_appointment_rate": session_to_appt,
        "daily_trend": daily_trend,
    }
    _set_cached(cache_key, result)
    return result


# ---------------------------------------------------------------------------
# Customer Lifetime Value (CLV)
# ---------------------------------------------------------------------------


@router.get("/{tenant_id}/customer-lifetime-value")
async def get_customer_lifetime_value(
    tenant_id: str,
    top_n: int = Query(default=20, ge=1, le=100),
    claims: dict = Depends(_get_current_tenant),
):
    """Calculate customer lifetime value from paid invoices per lead.

    Returns top N customers by total revenue, plus aggregate CLV stats.
    No migration needed — computed from existing invoices table.
    """
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    cache_key = f"clv:{tenant_id}:{top_n}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    db = get_supabase()

    try:
        invoices = (
            db.table("invoices")
            .select("lead_id, total, paid_at, status")
            .eq("tenant_id", tenant_id)
            .eq("status", "paid")
            .not_.is_("lead_id", "null")
            .limit(_QUERY_LIMIT)
            .execute()
        )
    except Exception:
        logger.exception("CLV: failed to query invoices for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to query invoices")

    if not invoices.data:
        result = {
            "top_customers": [],
            "total_revenue": 0,
            "avg_clv": 0,
            "median_clv": 0,
            "total_paying_customers": 0,
        }
        _set_cached(cache_key, result)
        return result

    # Aggregate by lead_id
    clv_by_lead: dict[str, dict] = {}
    for inv in invoices.data:
        lid = inv["lead_id"]
        total = float(inv.get("total") or 0)
        if lid not in clv_by_lead:
            clv_by_lead[lid] = {"lead_id": lid, "total_revenue": 0, "invoice_count": 0, "first_payment": None, "last_payment": None}
        clv_by_lead[lid]["total_revenue"] += total
        clv_by_lead[lid]["invoice_count"] += 1
        paid_at = inv.get("paid_at") or ""
        if paid_at:
            if not clv_by_lead[lid]["first_payment"] or paid_at < clv_by_lead[lid]["first_payment"]:
                clv_by_lead[lid]["first_payment"] = paid_at
            if not clv_by_lead[lid]["last_payment"] or paid_at > clv_by_lead[lid]["last_payment"]:
                clv_by_lead[lid]["last_payment"] = paid_at

    # Enrich with lead names
    lead_ids = list(clv_by_lead.keys())
    lead_names: dict[str, str] = {}
    try:
        for i in range(0, len(lead_ids), 50):
            batch = lead_ids[i : i + 50]
            leads_result = db.table("leads").select("id, name, email").in_("id", batch).execute()
            for l in (leads_result.data or []):
                lead_names[l["id"]] = l.get("name") or l.get("email") or "Unknown"
    except Exception:
        logger.warning("CLV: failed to fetch lead names", exc_info=True)

    for lid, data in clv_by_lead.items():
        data["customer_name"] = lead_names.get(lid, "Unknown")

    # Sort by total revenue descending
    sorted_customers = sorted(clv_by_lead.values(), key=lambda x: x["total_revenue"], reverse=True)
    top_customers = sorted_customers[:top_n]

    # Aggregate stats
    all_revenues = [c["total_revenue"] for c in sorted_customers]
    total_revenue = sum(all_revenues)
    total_customers = len(all_revenues)
    avg_clv = total_revenue / total_customers if total_customers > 0 else 0
    sorted_revs = sorted(all_revenues)
    median_clv = sorted_revs[len(sorted_revs) // 2] if sorted_revs else 0

    result = {
        "top_customers": top_customers,
        "total_revenue": round(total_revenue, 2),
        "avg_clv": round(avg_clv, 2),
        "median_clv": round(median_clv, 2),
        "total_paying_customers": total_customers,
    }
    _set_cached(cache_key, result)
    return result


# ---------------------------------------------------------------------------
# Appointment Utilization Rate
# ---------------------------------------------------------------------------


@router.get("/{tenant_id}/appointment-utilization")
async def get_appointment_utilization(
    tenant_id: str,
    days: int = Query(default=30, ge=1, le=365),
    claims: dict = Depends(_get_current_tenant),
):
    """Calculate appointment slot utilization rate.

    Compares available slots vs booked slots per day over the given period.
    Shows capacity utilization percentage to help businesses optimize scheduling.
    """
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    cache_key = f"utilization:{tenant_id}:{days}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    db = get_supabase()
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=days)

    # Get business hours
    try:
        bh = db.table("business_hours").select("hours, slot_duration_minutes").eq("tenant_id", tenant_id).limit(1).execute()
    except Exception:
        logger.exception("utilization: failed to query business_hours for %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to query business hours")

    if not bh.data:
        empty = {"utilization_pct": 0, "total_available_slots": 0, "total_booked_slots": 0, "daily_breakdown": [], "message": "No business hours configured"}
        _set_cached(cache_key, empty)
        return empty

    hours_config = bh.data[0].get("hours") or {}
    slot_duration = bh.data[0].get("slot_duration_minutes") or 30

    day_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

    # Calculate available slots per day of week
    slots_per_dow: dict[int, int] = {}
    for i, day_name in enumerate(day_names):
        day_config = hours_config.get(day_name, {})
        if not day_config.get("enabled", False):
            slots_per_dow[i] = 0
            continue
        start_str = day_config.get("start") or "09:00"
        end_str = day_config.get("end") or "17:00"
        try:
            sh, sm = map(int, start_str.split(":"))
            eh, em = map(int, end_str.split(":"))
            total_minutes = (eh * 60 + em) - (sh * 60 + sm)
            slots_per_dow[i] = max(0, total_minutes // slot_duration)
        except (ValueError, IndexError):
            slots_per_dow[i] = 0

    # Get booked appointments in the period
    try:
        appts = (
            db.table("appointments")
            .select("start_time, status")
            .eq("tenant_id", tenant_id)
            .gte("start_time", start_date.isoformat())
            .lte("start_time", now.isoformat())
            .in_("status", ["confirmed", "completed", "checked_in", "pending"])
            .limit(_QUERY_LIMIT)
            .execute()
        )
    except Exception:
        logger.exception("utilization: failed to query appointments for %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to query appointments")

    # Count booked per date
    booked_per_date: dict[str, int] = defaultdict(int)
    for appt in (appts.data or []):
        try:
            dt = datetime.fromisoformat(appt["start_time"].replace("Z", "+00:00"))
            booked_per_date[dt.strftime("%Y-%m-%d")] += 1
        except (ValueError, TypeError):
            pass

    # Build daily breakdown
    daily_breakdown = []
    total_available = 0
    total_booked = 0

    current = start_date.date()
    end = now.date()
    while current <= end:
        dow = current.weekday()
        available = slots_per_dow.get(dow, 0)
        date_str = current.isoformat()
        booked = booked_per_date.get(date_str, 0)
        total_available += available
        total_booked += booked

        if available > 0:
            daily_breakdown.append({
                "date": date_str,
                "available": available,
                "booked": min(booked, available),
                "utilization_pct": round(min(booked / available * 100, 100), 1),
            })
        current += timedelta(days=1)

    overall_pct = round(total_booked / total_available * 100, 1) if total_available > 0 else 0

    utilization_result = {
        "utilization_pct": min(overall_pct, 100),
        "total_available_slots": total_available,
        "total_booked_slots": min(total_booked, total_available),
        "slot_duration_minutes": slot_duration,
        "daily_breakdown": daily_breakdown[-30:],
    }
    _set_cached(cache_key, utilization_result)
    return utilization_result
