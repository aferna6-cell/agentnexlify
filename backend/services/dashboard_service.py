"""Dashboard helpers: trial status, activity feed, knowledge stats, dashboard payload."""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from backend.models.database import get_service_supabase as _get_service_supabase
from backend.models.schemas import TrialStatusResponse

logger = logging.getLogger(__name__)


def _get_db():
    return _get_service_supabase()


FREE_TRIAL_DAYS = 7


def compute_trial_status(tenant: dict) -> dict:
    """Return trial_days_remaining + trial_expired for a tenant row."""
    return {"trial_days_remaining": None, "trial_expired": False}


_compute_trial_status = compute_trial_status


def get_trial_status(tenant_id: str, claims: dict) -> TrialStatusResponse:
    """Return TrialStatusResponse for a tenant after authz check."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db = _get_db()
    result = (
        db.table("tenants")
        .select("plan, free_trial_started_at, created_at")
        .eq("id", tenant_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")

    tenant = result.data[0]
    trial = _compute_trial_status(tenant)
    trial_started = tenant.get("free_trial_started_at")

    trial_expires = None
    if trial_started and trial["trial_days_remaining"] is not None:
        if isinstance(trial_started, str):
            ts = datetime.fromisoformat(trial_started.replace("Z", "+00:00"))
        else:
            ts = trial_started
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        trial_expires = (ts + timedelta(days=FREE_TRIAL_DAYS)).isoformat()

    return TrialStatusResponse(
        plan=tenant.get("plan") or "free",
        trial_started=(
            trial_started
            if isinstance(trial_started, str)
            else (trial_started.isoformat() if trial_started else None)
        ),
        trial_expires=trial_expires,
        days_remaining=trial["trial_days_remaining"],
        is_expired=trial["trial_expired"],
    )


def get_activity(tenant_id: str) -> dict:
    """Return recent activity for the dashboard activity feed (uses client_id for leads)."""
    db = _get_db()
    items: list[dict] = []

    try:
        result = (
            db.table("activity_log")
            .select("id, activity_type, description, lead_id, metadata, created_at")
            .eq("tenant_id", tenant_id)
            .order("created_at", desc=True)
            .limit(20)
            .execute()
        )
        if result.data:
            for row in result.data:
                items.append(
                    {
                        "id": row["id"],
                        "type": row["activity_type"],
                        "message": row["description"],
                        "created_at": row["created_at"],
                    }
                )
    except Exception:
        logger.debug(
            "activity_log query failed, falling back for tenant %s",
            tenant_id,
            exc_info=True,
        )

    if not items:
        try:
            leads_result = (
                db.table("leads")
                .select("id, name, email, created_at")
                .eq("client_id", tenant_id)
                .order("created_at", desc=True)
                .limit(5)
                .execute()
            )
            for row in leads_result.data or []:
                name = row.get("name") or row.get("email") or "Unknown"
                items.append(
                    {
                        "id": f"lead_{row['id']}",
                        "type": "new_lead",
                        "message": f"New lead captured: {name}",
                        "created_at": row["created_at"],
                    }
                )
        except Exception:
            logger.debug(
                "leads fallback query failed for tenant %s", tenant_id, exc_info=True
            )

        try:
            chats_result = (
                db.table("chat_messages")
                .select("session_id, created_at")
                .eq("tenant_id", tenant_id)
                .eq("role", "user")
                .order("created_at", desc=True)
                .limit(20)
                .execute()
            )
            seen_sessions: set[str] = set()
            for row in chats_result.data or []:
                sid = row["session_id"]
                if sid not in seen_sessions and len(seen_sessions) < 5:
                    seen_sessions.add(sid)
                    items.append(
                        {
                            "id": f"chat_{sid}",
                            "type": "conversation_summary",
                            "message": f"New conversation: {sid[:12]}...",
                            "created_at": row["created_at"],
                        }
                    )
        except Exception:
            logger.debug(
                "chat_messages fallback query failed for tenant %s",
                tenant_id,
                exc_info=True,
            )

        try:
            appt_result = (
                db.table("appointments")
                .select("id, customer_name, start_time, created_at")
                .eq("tenant_id", tenant_id)
                .order("created_at", desc=True)
                .limit(5)
                .execute()
            )
            for row in appt_result.data or []:
                name = row.get("customer_name") or "Customer"
                items.append(
                    {
                        "id": f"appt_{row['id']}",
                        "type": "appointment",
                        "message": f"Appointment booked: {name}",
                        "created_at": row["created_at"],
                    }
                )
        except Exception:
            logger.debug(
                "appointments fallback query failed for tenant %s",
                tenant_id,
                exc_info=True,
            )

        items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        items = items[:20]

    return {"activity": items}


def get_knowledge_stats(tenant_id: str) -> dict:
    """Return stats about what the AI chatbot knows (FAQs, pages, corrections, etc.)."""
    db = _get_db()
    stats: dict = {
        "faq_count": 0,
        "website_pages_crawled": 0,
        "website_crawl_status": None,
        "website_url": None,
        "feedback_corrections_count": 0,
        "active_chat_flow": None,
        "menu_items_count": 0,
        "job_postings_count": 0,
    }

    try:
        faq_res = (
            db.table("faq_entries")
            .select("id", count="exact")
            .eq("tenant_id", tenant_id)
            .execute()
        )
        stats["faq_count"] = faq_res.count or 0
    except Exception:
        logger.debug(
            "knowledge-stats: faq query failed for tenant %s", tenant_id, exc_info=True
        )

    try:
        wc_res = (
            db.table("website_content")
            .select("pages_found, crawl_status")
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
        if wc_res.data:
            stats["website_pages_crawled"] = wc_res.data[0].get("pages_found") or 0
            stats["website_crawl_status"] = wc_res.data[0].get("crawl_status")
    except Exception:
        logger.debug(
            "knowledge-stats: website_content query failed for tenant %s",
            tenant_id,
            exc_info=True,
        )

    try:
        tenant_res = (
            db.table("tenants")
            .select("website_url")
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
        if tenant_res.data:
            stats["website_url"] = tenant_res.data[0].get("website_url")
    except Exception:
        logger.debug(
            "knowledge-stats: tenant query failed for tenant %s",
            tenant_id,
            exc_info=True,
        )

    try:
        fb_res = (
            db.table("ai_feedback")
            .select("id", count="exact")
            .eq("tenant_id", tenant_id)
            .eq("rating", "down")
            .execute()
        )
        stats["feedback_corrections_count"] = fb_res.count or 0
    except Exception:
        logger.debug(
            "knowledge-stats: ai_feedback query failed for tenant %s",
            tenant_id,
            exc_info=True,
        )

    try:
        flow_res = (
            db.table("chat_flows")
            .select("name")
            .eq("tenant_id", tenant_id)
            .eq("is_active", True)
            .limit(1)
            .execute()
        )
        if flow_res.data:
            stats["active_chat_flow"] = flow_res.data[0].get("name")
    except Exception:
        logger.debug(
            "knowledge-stats: chat_flows query failed for tenant %s",
            tenant_id,
            exc_info=True,
        )

    try:
        menu_res = (
            db.table("menu_items")
            .select("id", count="exact")
            .eq("tenant_id", tenant_id)
            .execute()
        )
        stats["menu_items_count"] = menu_res.count or 0
    except Exception:
        logger.debug(
            "knowledge-stats: menu query failed for tenant %s", tenant_id, exc_info=True
        )

    try:
        jobs_res = (
            db.table("jobs")
            .select("id", count="exact")
            .eq("tenant_id", tenant_id)
            .eq("is_active", True)
            .execute()
        )
        stats["job_postings_count"] = jobs_res.count or 0
    except Exception:
        logger.debug(
            "knowledge-stats: jobs query failed for tenant %s", tenant_id, exc_info=True
        )

    return stats


def build_dashboard_payload(tenant_id: str, db):
    """Assemble the dashboard payload for /api/v1/auth/dashboard/{tenant_id}.

    Takes the db handle as a parameter so the caller controls test-time patching.
    Returns a DashboardResponse pydantic model.
    """
    import secrets

    from fastapi import HTTPException

    from backend.models.schemas import DashboardResponse, WidgetConfigDetail
    from backend.services.business_profiles import (
        get_dashboard_business_profile,
        get_widget_defaults,
    )

    tenant_result = (
        db.table("tenants")
        .select(
            "business_name, business_type, plan, plan_status, conversations_used_this_month, "
            "monthly_conversation_limit, free_trial_started_at"
        )
        .eq("id", tenant_id)
        .limit(1)
        .execute()
    )
    if not tenant_result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")
    t = tenant_result.data[0]
    logger.info("Dashboard tenant row loaded for %s", tenant_id)

    widget_result = (
        db.table("widget_configs")
        .select(
            "api_key, bot_name, primary_color, greeting_message, position, branding, is_online, "
            "offline_message, teaser_message, teaser_delay_seconds, teaser_enabled"
        )
        .eq("tenant_id", tenant_id)
        .limit(1)
        .execute()
    )
    logger.info(
        "Dashboard widget_configs query for tenant_id=%s found=%s",
        tenant_id,
        bool(widget_result.data),
    )

    if widget_result.data:
        w = widget_result.data[0]
        api_key = w["api_key"]
        widget_config = WidgetConfigDetail(
            bot_name=w.get("bot_name", ""),
            primary_color=w.get("primary_color", "#00BFFF"),
            greeting_message=w.get("greeting_message", "Hi! How can I help you today?"),
            position=w.get("position", "bottom-right"),
            branding=w.get("branding") or None,
            is_online=w.get("is_online", True),
            offline_message=w.get("offline_message"),
            teaser_message=w.get("teaser_message"),
            teaser_delay_seconds=w.get("teaser_delay_seconds") or 3,
            teaser_enabled=w.get("teaser_enabled", True),
            enable_ai_fallback=w.get("enable_ai_fallback", False),
            enable_structured_lead_parser=w.get("enable_structured_lead_parser", False),
        )
    else:
        api_key = f"anx_{secrets.token_urlsafe(32)}"
        widget_defaults = get_widget_defaults(
            t.get("business_type"), t.get("business_name")
        )
        logger.info("Dashboard auto-creating widget_config for %s", tenant_id)
        db.table("widget_configs").insert(
            {
                "tenant_id": tenant_id,
                "api_key": api_key,
                "bot_name": widget_defaults["bot_name"],
                "primary_color": widget_defaults["primary_color"],
                "greeting_message": widget_defaults["greeting_message"],
                "position": widget_defaults["position"],
                "show_watermark": True,
            }
        ).execute()
        widget_config = WidgetConfigDetail(
            bot_name=widget_defaults["bot_name"],
            primary_color=widget_defaults["primary_color"],
            greeting_message=widget_defaults["greeting_message"],
            position=widget_defaults["position"],
        )

    try:
        leads_result = (
            db.table("leads")
            .select("id", count="exact")
            .eq("client_id", tenant_id)
            .execute()
        )
        leads_count = leads_result.count or 0
    except Exception:
        logger.warning(
            "Leads count query failed for tenant %s", tenant_id, exc_info=True
        )
        leads_count = 0

    try:
        hot_result = (
            db.table("leads")
            .select("id", count="exact")
            .eq("client_id", tenant_id)
            .gte("lead_score", 8)
            .execute()
        )
        hot_leads_count = hot_result.count or 0
    except Exception:
        logger.warning(
            "Hot leads count query failed for tenant %s", tenant_id, exc_info=True
        )
        hot_leads_count = 0

    try:
        faq_result = (
            db.table("faq_entries")
            .select("id", count="exact")
            .eq("tenant_id", tenant_id)
            .eq("is_active", True)
            .execute()
        )
        faq_count = faq_result.count or 0
    except Exception:
        logger.warning("FAQ count query failed for tenant %s", tenant_id, exc_info=True)
        faq_count = 0

    conversations_used = t.get("conversations_used_this_month") or 0
    try:
        chat_sessions = (
            db.table("chat_messages")
            .select("session_id")
            .eq("tenant_id", tenant_id)
            .limit(5000)
            .execute()
        )
        if chat_sessions.data:
            unique_sessions = len({r["session_id"] for r in chat_sessions.data})
            conversations_used = max(conversations_used, unique_sessions)
    except Exception:
        logger.warning(
            "chat_messages count failed for tenant %s", tenant_id, exc_info=True
        )

    missed_calls = 0
    try:
        from datetime import datetime, timedelta, timezone as tz

        week_ago = (datetime.now(tz.utc) - timedelta(days=7)).isoformat()
        mc_result = (
            db.table("activity_log")
            .select("id", count="exact")
            .eq("tenant_id", tenant_id)
            .eq("activity_type", "missed_call_textback")
            .gte("created_at", week_ago)
            .execute()
        )
        missed_calls = mc_result.count or 0
    except Exception:
        logger.debug("Missed calls count failed for tenant %s", tenant_id)

    trial = compute_trial_status(t)
    business_profile = get_dashboard_business_profile(
        t.get("business_type"), t.get("business_name")
    )

    response = DashboardResponse(
        business_name=t.get("business_name") or "",
        business_type=t.get("business_type"),
        plan=t.get("plan") or "free",
        plan_status=t.get("plan_status", "active"),
        conversations_used_this_month=conversations_used,
        monthly_conversation_limit=None,
        widget_api_key=api_key,
        leads_count=leads_count,
        widget_config=widget_config,
        business_profile=business_profile,
        faq_count=faq_count,
        has_conversations=conversations_used > 0,
        hot_leads_count=hot_leads_count,
        trial_days_remaining=trial["trial_days_remaining"],
        trial_expired=trial["trial_expired"],
        missed_calls_this_week=missed_calls,
    )
    logger.info(
        "Dashboard response assembled for %s leads=%s conversations=%s",
        tenant_id,
        leads_count,
        conversations_used,
    )
    return response
