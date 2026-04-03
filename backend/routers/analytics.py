"""Analytics endpoints for dashboard metrics and trends."""

import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from backend.dependencies import verify_tenant
from backend.limiter import limiter
from backend.models.database import get_supabase
from backend.routers.auth import _get_current_tenant, require_role

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
    mapping = {"7d": 7, "14d": 14, "30d": 30, "90d": 90}
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

    # Current period conversations — count unique sessions in chat_messages.
    # The conversations table is not reliably populated for all tenants, so
    # chat_messages (which drives the Peak Hours chart) is used as the
    # authoritative source here.
    try:
        curr_msgs_for_count = (
            db.table("chat_messages")
            .select("session_id")
            .eq("tenant_id", tenant_id)
            .gte("created_at", start)
            .lt("created_at", now_iso)
            .limit(5000)
            .execute()
        )
        unique_sessions = {m["session_id"] for m in (curr_msgs_for_count.data or [])}
        total_conversations = len(unique_sessions)
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

    # Previous period conversations — same approach: unique sessions in chat_messages
    try:
        prev_msgs_for_count = (
            db.table("chat_messages")
            .select("session_id")
            .eq("tenant_id", tenant_id)
            .gte("created_at", prev_start)
            .lt("created_at", start)
            .limit(5000)
            .execute()
        )
        prev_unique_sessions = {m["session_id"] for m in (prev_msgs_for_count.data or [])}
        prev_conversations = len(prev_unique_sessions)
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
        # Query chat_messages for session_id + created_at — conversations table
        # is not reliably populated for all tenants, but chat_messages is the
        # canonical message store and is always written to.
        convos = (
            db.table("chat_messages")
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

    # Conversations — use chat_messages (canonical store); conversations table
    # was previously empty due to a broken FK and cannot be trusted for counts.
    try:
        conv_msgs = (
            db.table("chat_messages")
            .select("session_id")
            .eq("tenant_id", tenant_id)
            .gte("created_at", week_ago)
            .limit(5000)
            .execute()
        )
        metrics["conversations"] = len({r["session_id"] for r in (conv_msgs.data or [])})
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
        logger.warning("Failed to fetch lead sources for tenant %s", tenant_id, exc_info=True)
        return {"breakdown": [], "total": 0}

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


@router.get("/{tenant_id}/kpi-deltas")
async def kpi_deltas(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Return week-over-week KPI deltas for dashboard overview cards.

    Compares this week (last 7 days) vs previous week (8-14 days ago) for:
    - leads captured
    - conversations
    - appointments booked
    - hot leads (score >= 8)
    """
    verify_tenant(claims, tenant_id)

    cache_key = f"kpi_deltas:{tenant_id}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    db = get_supabase()
    now = datetime.now(timezone.utc)
    this_week_start = (now - timedelta(days=7)).isoformat()
    last_week_start = (now - timedelta(days=14)).isoformat()
    last_week_end = (now - timedelta(days=7)).isoformat()

    def _count_in_range(table: str, id_col: str, start: str, end: str | None = None, extra_filters: dict | None = None) -> int:
        try:
            q = db.table(table).select("id", count="exact").eq(id_col, tenant_id).gte("created_at", start)
            if end:
                q = q.lt("created_at", end)
            if extra_filters:
                for k, v in extra_filters.items():
                    q = q.eq(k, v) if not isinstance(v, tuple) else q.gte(k, v[0])
            result = q.execute()
            return result.count or 0
        except Exception:
            logger.warning("KPI delta query failed for %s on %s", tenant_id, table, exc_info=True)
            return 0

    def _count_leads(start: str, end: str | None = None, hot: bool = False) -> int:
        try:
            q = db.table("leads").select("id", count="exact").eq("client_id", tenant_id).gte("created_at", start)
            if end:
                q = q.lt("created_at", end)
            if hot:
                q = q.gte("lead_score", 8)
            result = q.execute()
            return result.count or 0
        except Exception:
            logger.warning("KPI delta leads query failed for %s", tenant_id, exc_info=True)
            return 0

    # This week counts
    leads_this = _count_leads(this_week_start)
    leads_last = _count_leads(last_week_start, last_week_end)

    hot_this = _count_leads(this_week_start, hot=True)
    hot_last = _count_leads(last_week_start, last_week_end, hot=True)

    # Count conversations from chat_messages (unique sessions) rather than the
    # conversations table, which is unreliable and may have FK issues.
    # architecture-decisions.md: "chat_messages is the canonical store"
    def _count_sessions_in_range(start: str, end: str | None = None) -> int:
        try:
            q = (
                db.table("chat_messages")
                .select("session_id")
                .eq("tenant_id", tenant_id)
                .gte("created_at", start)
            )
            if end:
                q = q.lt("created_at", end)
            result = q.limit(5000).execute()
            return len({r["session_id"] for r in (result.data or [])})
        except Exception:
            logger.warning("KPI delta session count failed for %s", tenant_id, exc_info=True)
            return 0

    convos_this = _count_sessions_in_range(this_week_start)
    convos_last = _count_sessions_in_range(last_week_start, last_week_end)

    appts_this = _count_in_range("appointments", "tenant_id", this_week_start)
    appts_last = _count_in_range("appointments", "tenant_id", last_week_start, last_week_end)

    def _delta_pct(current: int, previous: int) -> float | None:
        if previous == 0:
            return 100.0 if current > 0 else 0.0
        return round(((current - previous) / previous) * 100, 1)

    response = {
        "leads": {
            "this_week": leads_this,
            "last_week": leads_last,
            "delta_pct": _delta_pct(leads_this, leads_last),
        },
        "hot_leads": {
            "this_week": hot_this,
            "last_week": hot_last,
            "delta_pct": _delta_pct(hot_this, hot_last),
        },
        "conversations": {
            "this_week": convos_this,
            "last_week": convos_last,
            "delta_pct": _delta_pct(convos_this, convos_last),
        },
        "appointments": {
            "this_week": appts_this,
            "last_week": appts_last,
            "delta_pct": _delta_pct(appts_this, appts_last),
        },
    }

    _cache[cache_key] = (time.time(), response)
    return response


@router.get("/{tenant_id}/health")
async def analytics_health(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Debug endpoint: returns raw data counts for this tenant to diagnose analytics issues."""
    verify_tenant(claims, tenant_id)
    db = get_supabase()

    # Count unique sessions from chat_messages
    try:
        msgs = (
            db.table("chat_messages")
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
            db.table("leads")
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
            db.table("appointments")
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
            db.table("chat_messages")
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

    db = get_supabase()
    days = _period_to_days(period)
    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=days)).isoformat()

    # Business name
    biz_name = "Unknown"
    try:
        t = db.table("tenants").select("business_name").eq("id", tenant_id).single().execute()
        biz_name = (t.data or {}).get("business_name", "Unknown")
    except Exception:
        pass

    # Chat messages
    msgs = []
    try:
        r = db.table("chat_messages").select("session_id, role, content, created_at").eq("tenant_id", tenant_id).gte("created_at", start).order("created_at").limit(_QUERY_LIMIT).execute()
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
    import re as _re
    _skip = {"hi", "hey", "hello", "yo", "sup", "e", "hiya", "howdy", ""}
    real_questions = []
    for m in user_msgs:
        normalized = _re.sub(r"[^a-z ]", "", (m.get("content") or "").strip().lower())
        if normalized not in _skip and len(normalized) > 3:
            real_questions.append(m.get("content", "").strip())

    # Count frequencies
    from collections import Counter
    q_counts = Counter(real_questions)
    top_questions = [q for q, _ in q_counts.most_common(5)]

    # Busiest day
    day_counts = defaultdict(int)
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
        r = db.table("leads").select("id").eq("client_id", tenant_id).gte("created_at", start).limit(_QUERY_LIMIT).execute()
        total_leads = len(r.data or [])
    except Exception:
        logger.warning("snapshot: leads query failed for %s", tenant_id, exc_info=True)

    # Appointments
    total_appointments = 0
    try:
        r = db.table("appointments").select("id").eq("tenant_id", tenant_id).gte("created_at", start).limit(_QUERY_LIMIT).execute()
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
