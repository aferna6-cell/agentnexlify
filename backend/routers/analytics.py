"""Analytics endpoints for dashboard metrics and trends."""

import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.models.database import get_supabase
from backend.routers.auth import _get_current_tenant

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])

# Simple in-memory cache: {cache_key: (timestamp, data)}
_cache: dict[str, tuple[float, dict]] = {}
_CACHE_TTL = 300  # 5 minutes

# Safety cap for unbounded queries — prevents timeouts on large tenants
_QUERY_LIMIT = 10000


def _check_tenant(claims: dict, tenant_id: str) -> None:
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")


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
    _check_tenant(claims, tenant_id)

    cache_key = f"overview:{tenant_id}:{period}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    days = _period_to_days(period)
    start, prev_start = _date_range(days)
    now_iso = datetime.now(timezone.utc).isoformat()
    db = get_supabase()

    # Current period conversations (from chat_messages, count unique sessions)
    try:
        curr_convos = (
            db.table("chat_messages")
            .select("session_id")
            .eq("tenant_id", tenant_id)
            .gte("created_at", start)
            .lt("created_at", now_iso)
            .limit(_QUERY_LIMIT)
            .execute()
        )
        curr_sessions = set(r["session_id"] for r in (curr_convos.data or []))
        total_conversations = len(curr_sessions)

        # Total messages
        total_messages = len(curr_convos.data or [])
        avg_messages = round(total_messages / total_conversations, 1) if total_conversations > 0 else 0
    except Exception:
        logger.warning("Failed to fetch conversation analytics", exc_info=True)
        total_conversations = 0
        total_messages = 0
        avg_messages = 0

    # Previous period conversations
    try:
        prev_convos = (
            db.table("chat_messages")
            .select("session_id")
            .eq("tenant_id", tenant_id)
            .gte("created_at", prev_start)
            .lt("created_at", start)
            .limit(_QUERY_LIMIT)
            .execute()
        )
        prev_sessions = set(r["session_id"] for r in (prev_convos.data or []))
        prev_conversations = len(prev_sessions)
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
    _check_tenant(claims, tenant_id)

    cache_key = f"convos_trend:{tenant_id}:{period}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    days = _period_to_days(period)
    now_iso = datetime.now(timezone.utc).isoformat()
    start = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    db = get_supabase()

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

        # Group unique sessions by date
        sessions_by_date: dict[str, set[str]] = defaultdict(set)
        for row in msgs.data or []:
            date_str = row["created_at"][:10]
            sessions_by_date[date_str].add(row["session_id"])

        # Build full date range
        today = datetime.now(timezone.utc).date()
        result_data = []
        for i in range(days):
            d = (today - timedelta(days=days - 1 - i)).isoformat()
            result_data.append({"date": d, "count": len(sessions_by_date.get(d, set()))})
    except Exception:
        logger.warning("Failed to fetch conversation trends", exc_info=True)
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
    _check_tenant(claims, tenant_id)

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
# 4. Response times
# ------------------------------------------------------------------


@router.get("/{tenant_id}/response-times")
async def get_response_times(
    tenant_id: str,
    period: str = Query("30d", pattern="^(7d|30d|90d)$"),
    claims: dict = Depends(_get_current_tenant),
):
    _check_tenant(claims, tenant_id)

    cache_key = f"resp_times:{tenant_id}:{period}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    days = _period_to_days(period)
    now_iso = datetime.now(timezone.utc).isoformat()
    start = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    db = get_supabase()

    try:
        msgs = (
            db.table("chat_messages")
            .select("session_id, role, created_at")
            .eq("tenant_id", tenant_id)
            .gte("created_at", start)
            .lt("created_at", now_iso)
            .order("created_at")
            .limit(_QUERY_LIMIT)
            .execute()
        )

        # Group by session
        sessions: dict[str, list[dict]] = defaultdict(list)
        for row in msgs.data or []:
            sessions[row["session_id"]].append(row)

        response_times: list[float] = []
        first_response_times: list[float] = []
        daily_response: dict[str, list[float]] = defaultdict(list)

        for session_id, messages in sessions.items():
            messages.sort(key=lambda x: x["created_at"])
            first_response_found = False

            for i in range(1, len(messages)):
                if messages[i]["role"] == "assistant" and messages[i - 1]["role"] == "user":
                    user_time = datetime.fromisoformat(messages[i - 1]["created_at"].replace("Z", "+00:00"))
                    bot_time = datetime.fromisoformat(messages[i]["created_at"].replace("Z", "+00:00"))
                    diff = (bot_time - user_time).total_seconds()

                    if 0 < diff < 300:  # Ignore anomalies > 5 min
                        response_times.append(diff)
                        date_str = messages[i]["created_at"][:10]
                        daily_response[date_str].append(diff)

                        if not first_response_found:
                            first_response_times.append(diff)
                            first_response_found = True

        avg_response = round(sum(response_times) / len(response_times), 2) if response_times else 0
        avg_first_response = round(sum(first_response_times) / len(first_response_times), 2) if first_response_times else 0

        # Build daily trend
        today = datetime.now(timezone.utc).date()
        trend_data = []
        for i in range(days):
            d = (today - timedelta(days=days - 1 - i)).isoformat()
            day_times = daily_response.get(d, [])
            avg = round(sum(day_times) / len(day_times), 2) if day_times else None
            trend_data.append({"date": d, "avg_seconds": avg})

    except Exception:
        logger.warning("Failed to compute response times", exc_info=True)
        avg_response = 0
        avg_first_response = 0
        trend_data = []

    result = {
        "avg_response_seconds": avg_response,
        "avg_first_response_seconds": avg_first_response,
        "trend": trend_data,
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
    _check_tenant(claims, tenant_id)

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


@router.get("/{tenant_id}/response-times")
async def get_response_time_analytics(
    tenant_id: str,
    period: str = Query("30d", pattern="^(7d|30d|90d)$"),
    claims: dict = Depends(_get_current_tenant),
):
    """Get response time analytics from the response_metrics table."""
    _check_tenant(claims, tenant_id)

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
    _check_tenant(claims, tenant_id)

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
                .eq("tenant_id", tenant_id)
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
    _check_tenant(claims, tenant_id)

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
