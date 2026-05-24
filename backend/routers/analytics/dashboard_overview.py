"""Dashboard analytics — overview endpoint.

Returns KPI cards (conversations, leads, conversion, appointments, emails)
plus period-over-period change percentages.

WARNING: PEP 563 deferred annotations are incompatible with FastAPI — do not
add a future-annotations import here.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query

from backend.dependencies import _get_current_tenant, verify_tenant
from backend.models.database import get_service_supabase
from backend.routers.analytics._common import (
    _QUERY_LIMIT,
    _date_range,
    _get_cached,
    _pct_change,
    _period_to_days,
    _set_cache,
    logger,
)
from backend.services.tenant_scope import tenant_table

router = APIRouter()


@router.get("/{tenant_id}/overview")
async def get_overview(
    tenant_id: str,
    period: str = Query("30d", pattern="^(7d|14d|30d|90d)$"),
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
    db = get_service_supabase()

    # Current period conversations — count unique sessions in chat_messages.
    # The conversations table is not reliably populated for all tenants, so
    # chat_messages (which drives the Peak Hours chart) is used as the
    # authoritative source here.
    try:
        curr_msgs_for_count = (
            tenant_table(db, "chat_messages", tenant_id)
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
            tenant_table(db, "chat_messages", tenant_id)
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
            tenant_table(db, "chat_messages", tenant_id)
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
            tenant_table(db, "leads", tenant_id)
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
            tenant_table(db, "leads", tenant_id)
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
