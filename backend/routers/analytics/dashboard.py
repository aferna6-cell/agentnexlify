"""Dashboard analytics endpoints: overview, conversations, leads, widget, health, snapshot."""

import re as _re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query, Request

from backend.dependencies import verify_tenant
from backend.limiter import limiter
from backend.models.database import get_service_supabase
from backend.services.tenant_scope import tenant_table
from backend.dependencies import _get_current_tenant
from backend.routers.analytics._common import (
    _cache,
    _CACHE_TTL,
    _QUERY_LIMIT,
    _get_cached,
    _set_cache,
    _period_to_days,
    _date_range,
    _pct_change,
    logger,
)
from backend.services.tenant_activity import (
    activity_window,
    conversation_trend,
    count_conversations,
    count_leads_created,
    count_messages,
    exact_lead_count,
    last_activity_at,
    load_activity_rows,
)

router = APIRouter()


# ------------------------------------------------------------------
# 1. Overview
# ------------------------------------------------------------------


@router.get("/{tenant_id}/overview")
async def get_overview(
    tenant_id: str,
    period: str = Query("month", pattern="^(month|7d|14d|30d|90d)$"),
    claims: dict = Depends(_get_current_tenant),
):
    verify_tenant(claims, tenant_id)

    cache_key = f"overview:{tenant_id}:{period}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    start_dt, end_dt, prev_start_dt = activity_window(period)
    start = start_dt.isoformat()
    prev_start = prev_start_dt.isoformat()
    now_iso = end_dt.isoformat()
    db = get_service_supabase()
    activity = load_activity_rows(db, tenant_id)

    # Conversations: distinct sessions from conversations (client_id) and
    # chat_messages (tenant_id) inside the same window billing uses.
    total_conversations = count_conversations(
        activity["conversations"], activity["messages"], start_dt, end_dt
    )
    prev_conversations = count_conversations(
        activity["conversations"], activity["messages"], prev_start_dt, start_dt
    )
    total_messages = count_messages(activity["messages"], start_dt, end_dt)
    avg_messages = (
        round(total_messages / total_conversations, 1) if total_conversations > 0 else 0
    )

    # Leads captured on the card are the all-time stock (dashboard opportunities
    # and pipeline deals). Period leads drive the conversion rate and the delta.
    period_leads = count_leads_created(activity["leads"], start_dt, end_dt)
    prev_leads = count_leads_created(activity["leads"], prev_start_dt, start_dt)
    leads_all_time = exact_lead_count(db, tenant_id)
    if leads_all_time is None:
        leads_all_time = len(activity["leads"])
    total_leads = leads_all_time

    conversion_rate = (
        round((period_leads / total_conversations * 100), 1)
        if total_conversations > 0
        else 0.0
    )
    prev_conversion = (
        round((prev_leads / prev_conversations * 100), 1)
        if prev_conversations > 0
        else 0.0
    )

    # Appointments
    try:
        curr_appts = (
            tenant_table(db, "appointments", tenant_id)
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
            tenant_table(db, "appointments", tenant_id)
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
            tenant_table(db, "automation_logs", tenant_id)
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
                tenant_table(db, "activity_log", tenant_id)
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
        "leads_all_time": leads_all_time,
        "period_leads": period_leads,
        "conversion_rate": conversion_rate,
        "total_messages": total_messages,
        "avg_messages_per_conversation": avg_messages,
        "total_appointments": total_appointments,
        "total_emails_sent": total_emails,
        "changes": {
            "conversations": _pct_change(total_conversations, prev_conversations),
            "leads": _pct_change(period_leads, prev_leads),
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
    period: str = Query("30d", pattern="^(month|7d|14d|30d|90d)$"),
    claims: dict = Depends(_get_current_tenant),
):
    verify_tenant(claims, tenant_id)

    cache_key = f"convos_trend:{tenant_id}:{period}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    start_dt, end_dt, _prev = activity_window(period)
    days = max(1, (end_dt.date() - start_dt.date()).days + 1)
    db = get_service_supabase()
    activity = load_activity_rows(db, tenant_id)
    count_by_date = conversation_trend(
        activity["conversations"], activity["messages"], start_dt, end_dt
    )

    today = end_dt.date()
    result_data = []
    for i in range(days):
        d = (today - timedelta(days=days - 1 - i)).isoformat()
        result_data.append({"date": d, "count": count_by_date.get(d, 0)})

    result = {"data": result_data}
    _set_cache(cache_key, result)
    return result


# ------------------------------------------------------------------
# 3. Leads analytics
# ------------------------------------------------------------------


@router.get("/{tenant_id}/leads")
async def get_leads_analytics(
    tenant_id: str,
    period: str = Query("30d", pattern="^(month|7d|14d|30d|90d)$"),
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


# ------------------------------------------------------------------
# 5. Widget analytics
# ------------------------------------------------------------------


@router.get("/{tenant_id}/widget")
async def get_widget_analytics(
    tenant_id: str,
    period: str = Query("30d", pattern="^(month|7d|14d|30d|90d)$"),
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


@router.get("/{tenant_id}/health")
async def analytics_health(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Debug endpoint: returns raw data counts for this tenant to diagnose analytics issues."""
    verify_tenant(claims, tenant_id)
    db = get_service_supabase()

    activity = load_activity_rows(db, tenant_id)
    month_start, month_end, _prev = activity_window("month")
    unique_sessions = count_conversations(
        activity["conversations"], activity["messages"], None, None
    )
    conversations_this_month = count_conversations(
        activity["conversations"], activity["messages"], month_start, month_end
    )
    lead_count = exact_lead_count(db, tenant_id)
    if lead_count is None:
        lead_count = len(activity["leads"])
    last_dt = last_activity_at(
        activity["conversations"], activity["messages"], activity["leads"]
    )
    last_iso = last_dt.isoformat() if last_dt else None

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

    return {
        "tenant_id": tenant_id,
        "unique_widget_sessions": unique_sessions,
        "conversations_this_month": conversations_this_month,
        "total_leads": lead_count,
        "total_appointments": appt_count,
        "last_message_at": last_iso,
        "last_activity_at": last_iso,
        "note": (
            "Conversations are distinct sessions from conversations (client_id) "
            "and chat_messages (tenant_id). total_leads is the all-time lead stock. "
            "last_activity_at is the newest timestamp across those rows."
        ),
    }


@router.get("/{tenant_id}/snapshot")
@limiter.limit("30/minute")
async def get_tester_snapshot(
    request: Request,
    tenant_id: str,
    period: str = Query("30d", pattern="^(month|7d|14d|30d|90d)$"),
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
