"""Dashboard analytics — engagement endpoints.

- /{tenant_id}/conversations: daily conversation count trend
- /{tenant_id}/leads: lead daily count + stage breakdown + avg score
- /{tenant_id}/widget: widget-level engagement (peak hours, duration, loads)

WARNING: PEP 563 deferred annotations are incompatible with FastAPI — do not
add a future-annotations import here.
"""

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query

from backend.dependencies import _get_current_tenant, verify_tenant
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


@router.get("/{tenant_id}/conversations")
async def get_conversations_trend(
    tenant_id: str,
    period: str = Query("30d", pattern="^(7d|14d|30d|90d)$"),
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
    db = get_service_supabase()

    try:
        # Query chat_messages for session_id + created_at — conversations table
        # is not reliably populated for all tenants, but chat_messages is the
        # canonical message store and is always written to.
        convos = (
            tenant_table(db, "chat_messages", tenant_id)
            .select("session_id, created_at")
            .eq("tenant_id", tenant_id)
            .gte("created_at", start)
            .lt("created_at", now_iso)
            .order("created_at")
            .limit(_QUERY_LIMIT)
            .execute()
        )

        # Count unique sessions by date (one conversation = one unique session_id per day)
        date_sessions: dict[str, set] = defaultdict(set)
        for row in convos.data or []:
            date_str = row["created_at"][:10]
            date_sessions[date_str].add(row["session_id"])
        count_by_date: dict[str, int] = {d: len(s) for d, s in date_sessions.items()}

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


@router.get("/{tenant_id}/leads")
async def get_leads_analytics(
    tenant_id: str,
    period: str = Query("30d", pattern="^(7d|14d|30d|90d)$"),
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
    db = get_service_supabase()

    # All leads in period
    try:
        leads_res = (
            tenant_table(db, "leads", tenant_id)
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


@router.get("/{tenant_id}/widget")
async def get_widget_analytics(
    tenant_id: str,
    period: str = Query("30d", pattern="^(7d|14d|30d|90d)$"),
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
    db = get_service_supabase()

    # Conversations started (unique sessions with messages)
    try:
        msgs = (
            tenant_table(db, "chat_messages", tenant_id)
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
            tenant_table(db, "tenants", tenant_id)
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
