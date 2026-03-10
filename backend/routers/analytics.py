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
    period: str = Query("30d", regex="^(7d|30d|90d)$"),
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
            .execute()
        )
        prev_sessions = set(r["session_id"] for r in (prev_convos.data or []))
        prev_conversations = len(prev_sessions)
    except Exception:
        prev_conversations = 0

    # Current period leads (leads use client_id, not tenant_id)
    try:
        curr_leads = (
            db.table("leads")
            .select("id")
            .eq("client_id", tenant_id)
            .gte("created_at", start)
            .execute()
        )
        total_leads = len(curr_leads.data or [])
    except Exception:
        total_leads = 0

    # Previous period leads
    try:
        prev_leads_res = (
            db.table("leads")
            .select("id")
            .eq("client_id", tenant_id)
            .gte("created_at", prev_start)
            .lt("created_at", start)
            .execute()
        )
        prev_leads = len(prev_leads_res.data or [])
    except Exception:
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
            .neq("status", "cancelled")
            .execute()
        )
        total_appointments = len(curr_appts.data or [])
    except Exception:
        total_appointments = 0

    try:
        prev_appts = (
            db.table("appointments")
            .select("id")
            .eq("tenant_id", tenant_id)
            .gte("created_at", prev_start)
            .lt("created_at", start)
            .neq("status", "cancelled")
            .execute()
        )
        prev_appointments = len(prev_appts.data or [])
    except Exception:
        prev_appointments = 0

    # Emails sent (from automation_logs via automation_executions)
    try:
        curr_emails = (
            db.table("automation_logs")
            .select("id, execution_id!inner(tenant_id)")
            .eq("execution_id.tenant_id", tenant_id)
            .eq("action", "email_sent")
            .gte("created_at", start)
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
                .execute()
            )
            total_emails = len(email_acts.data or [])
        except Exception:
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
    period: str = Query("30d", regex="^(7d|30d|90d)$"),
    claims: dict = Depends(_get_current_tenant),
):
    _check_tenant(claims, tenant_id)

    cache_key = f"convos_trend:{tenant_id}:{period}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    days = _period_to_days(period)
    start = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    db = get_supabase()

    try:
        msgs = (
            db.table("chat_messages")
            .select("session_id, created_at")
            .eq("tenant_id", tenant_id)
            .gte("created_at", start)
            .order("created_at")
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
    period: str = Query("30d", regex="^(7d|30d|90d)$"),
    claims: dict = Depends(_get_current_tenant),
):
    _check_tenant(claims, tenant_id)

    cache_key = f"leads_analytics:{tenant_id}:{period}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    days = _period_to_days(period)
    start = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    db = get_supabase()

    # All leads in period
    try:
        leads_res = (
            db.table("leads")
            .select("id, status, lead_score, created_at")
            .eq("client_id", tenant_id)
            .gte("created_at", start)
            .execute()
        )
        leads = leads_res.data or []
    except Exception:
        logger.warning("Failed to fetch leads analytics", exc_info=True)
        leads = []

    # Daily count
    daily: dict[str, int] = defaultdict(int)
    stage_breakdown: dict[str, int] = defaultdict(int)
    source_breakdown: dict[str, int] = defaultdict(int)
    scores = []

    for lead in leads:
        date_str = lead["created_at"][:10]
        daily[date_str] += 1
        stage_breakdown[lead.get("status") or "new"] += 1
        source_breakdown[lead.get("source") or "widget"] += 1
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
        "by_source": dict(source_breakdown),
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
    period: str = Query("30d", regex="^(7d|30d|90d)$"),
    claims: dict = Depends(_get_current_tenant),
):
    _check_tenant(claims, tenant_id)

    cache_key = f"resp_times:{tenant_id}:{period}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    days = _period_to_days(period)
    start = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    db = get_supabase()

    try:
        msgs = (
            db.table("chat_messages")
            .select("session_id, role, created_at")
            .eq("tenant_id", tenant_id)
            .gte("created_at", start)
            .order("created_at")
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
    period: str = Query("30d", regex="^(7d|30d|90d)$"),
    claims: dict = Depends(_get_current_tenant),
):
    _check_tenant(claims, tenant_id)

    cache_key = f"widget:{tenant_id}:{period}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    days = _period_to_days(period)
    start = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    db = get_supabase()

    # Conversations started (unique sessions with messages)
    try:
        msgs = (
            db.table("chat_messages")
            .select("session_id, created_at")
            .eq("tenant_id", tenant_id)
            .gte("created_at", start)
            .order("created_at")
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
