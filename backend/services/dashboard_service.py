"""Dashboard helpers: trial status, activity feed, knowledge stats."""

import logging

from backend.models.database import get_service_supabase as _get_service_supabase

logger = logging.getLogger(__name__)


def _get_db():
    return _get_service_supabase()


FREE_TRIAL_DAYS = 7


def compute_trial_status(tenant: dict) -> dict:
    """Return trial_days_remaining + trial_expired for a tenant row."""
    return {"trial_days_remaining": None, "trial_expired": False}


_compute_trial_status = compute_trial_status


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
