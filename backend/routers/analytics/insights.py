"""Insights analytics endpoints: ai-insights, lead-sources, kpi-deltas."""

import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query

from backend.dependencies import verify_tenant
from backend.models.database import get_service_supabase
from backend.services.llm_runtime import call_claude_messages
from backend.services.tenant_scope import tenant_table
from backend.dependencies import _get_current_tenant
from backend.routers.analytics._common import (
    _cache,
    _CACHE_TTL,
    _QUERY_LIMIT,
    _get_cached,
    _set_cache,
    logger,
)

router = APIRouter()


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

    db = get_service_supabase()
    now = datetime.now(timezone.utc)
    week_ago = (now - timedelta(days=7)).isoformat()
    prev_week_start = (now - timedelta(days=14)).isoformat()

    metrics = {}

    # Current week leads (uses client_id)
    try:
        leads_result = tenant_table(db, "leads", tenant_id).select("id, status, lead_temperature, deal_value").eq("client_id", tenant_id).gte("created_at", week_ago).limit(500).execute()
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
        prev_leads = tenant_table(db, "leads", tenant_id).select("id", count="exact").eq("client_id", tenant_id).gte("created_at", prev_week_start).lt("created_at", week_ago).limit(1).execute()
        metrics["prev_leads"] = prev_leads.count or 0
    except Exception:
        metrics["prev_leads"] = 0

    # Conversations — use chat_messages (canonical store); conversations table
    # was previously empty due to a broken FK and cannot be trusted for counts.
    try:
        conv_msgs = (
            tenant_table(db, "chat_messages", tenant_id)
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
        appt_result = tenant_table(db, "appointments", tenant_id).select("id, status").eq("tenant_id", tenant_id).gte("created_at", week_ago).limit(500).execute()
        appt_data = appt_result.data or []
        metrics["appointments"] = len(appt_data)
        metrics["completed_appointments"] = sum(1 for a in appt_data if a.get("status") == "completed")
    except Exception:
        metrics["appointments"] = 0
        metrics["completed_appointments"] = 0

    # Invoices
    try:
        inv_result = tenant_table(db, "invoices", tenant_id).select("id, status, total").eq("tenant_id", tenant_id).gte("created_at", week_ago).limit(500).execute()
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
        rev_result = tenant_table(db, "reviews", tenant_id).select("id, rating").eq("tenant_id", tenant_id).gte("created_at", week_ago).limit(50).execute()
        rev_data = rev_result.data or []
        metrics["reviews"] = len(rev_data)
        metrics["avg_rating"] = round(sum(r.get("rating", 0) for r in rev_data) / max(len(rev_data), 1), 1) if rev_data else 0
    except Exception:
        metrics["reviews"] = 0
        metrics["avg_rating"] = 0

    # Pending action items
    try:
        actions_result = tenant_table(db, "action_items", tenant_id).select("id", count="exact").eq("tenant_id", tenant_id).eq("status", "pending").limit(1).execute()
        metrics["pending_actions"] = actions_result.count or 0
    except Exception:
        metrics["pending_actions"] = 0

    # Get tenant info for AI context
    try:
        tenant_result = tenant_table(db, "tenants", tenant_id).select("business_name, business_type").eq("id", tenant_id).limit(1).execute()
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
            response = await call_claude_messages(
                operation="analytics.ai_insights",
                model="claude-haiku-4-5-20251001",
                max_tokens=400,
                timeout=30.0,
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
                metadata={"tenant_id": tenant_id, "business_type": biz_type, "new_leads": metrics['new_leads'], "conversations": metrics['conversations']},
            )
            ai_analysis = response.text if response.text else ""
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

    db = get_service_supabase()
    try:
        result = tenant_table(db, "leads", tenant_id).select("source").eq("client_id", tenant_id).execute()
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

    db = get_service_supabase()
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
            q = tenant_table(db, "leads", tenant_id).select("id", count="exact").eq("client_id", tenant_id).gte("created_at", start)
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
                tenant_table(db, "chat_messages", tenant_id)
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
