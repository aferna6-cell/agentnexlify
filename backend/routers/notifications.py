"""Dashboard notifications center — aggregates recent activity into a single feed."""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from backend.models.database import get_service_supabase
from backend.models.schemas import NotificationItem, NotificationsResponse
from backend.routers.auth import _get_current_tenant

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


def _check_tenant(claims: dict, tenant_id: str) -> None:
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")


@router.get("/{tenant_id}", response_model=NotificationsResponse)
async def get_notifications(
    tenant_id: str,
    request: Request,
    claims: dict = Depends(_get_current_tenant),
):
    """Get aggregated notifications for the dashboard bell."""
    _check_tenant(claims, tenant_id)

    db = get_service_supabase()
    now = datetime.now(timezone.utc)
    twenty_four_hours_ago = (now - timedelta(hours=24)).isoformat()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    today_end = (now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)).isoformat()

    recent_items: list[NotificationItem] = []

    # --- 1. New leads in last 24h ---
    new_leads_count = 0
    try:
        leads_res = (
            db.table("leads")
            .select("id, name, email, phone, created_at")
            .eq("client_id", tenant_id)
            .gte("created_at", twenty_four_hours_ago)
            .order("created_at", desc=True)
            .limit(50)
            .execute()
        )
        leads_data = leads_res.data or []
        new_leads_count = len(leads_data)

        for lead in leads_data:
            lead_name = lead.get("name") or "Unknown"
            description = lead.get("email") or lead.get("phone") or "Captured via widget"
            recent_items.append(
                NotificationItem(
                    type="new_lead",
                    title=f"New lead: {lead_name}",
                    description=description,
                    created_at=lead["created_at"],
                )
            )
    except Exception:
        logger.warning("Notifications: failed to fetch new leads for %s", tenant_id, exc_info=True)

    # --- 2. New conversations in last 24h (distinct session_id) ---
    new_conversations_count = 0
    try:
        convos_res = (
            db.table("chat_messages")
            .select("session_id")
            .eq("tenant_id", tenant_id)
            .gte("created_at", twenty_four_hours_ago)
            .limit(5000)
            .execute()
        )
        session_ids = set(r["session_id"] for r in (convos_res.data or []))
        new_conversations_count = len(session_ids)
    except Exception:
        logger.warning("Notifications: failed to fetch new conversations for %s", tenant_id, exc_info=True)

    # --- 3. Today's appointments ---
    todays_appointments_count = 0
    try:
        appts_res = (
            db.table("appointments")
            .select("id, customer_name, start_time, created_at")
            .eq("tenant_id", tenant_id)
            .gte("start_time", today_start)
            .lt("start_time", today_end)
            .neq("status", "cancelled")
            .order("start_time")
            .limit(50)
            .execute()
        )
        appts_data = appts_res.data or []
        todays_appointments_count = len(appts_data)

        for appt in appts_data:
            customer = appt.get("customer_name") or "Customer"
            start = appt.get("start_time", "")
            # Format the start time for display
            try:
                dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
                formatted_time = dt.strftime("%I:%M %p")
            except (ValueError, AttributeError):
                formatted_time = start
            recent_items.append(
                NotificationItem(
                    type="appointment",
                    title=f"Appointment: {customer}",
                    description=f"Scheduled at {formatted_time}",
                    created_at=appt.get("created_at") or start,
                )
            )
    except Exception:
        logger.warning("Notifications: failed to fetch today's appointments for %s", tenant_id, exc_info=True)

    # --- 4. Recent activity (last 10) ---
    try:
        activity_res = (
            db.table("activity_log")
            .select("id, activity_type, description, created_at")
            .eq("tenant_id", tenant_id)
            .order("created_at", desc=True)
            .limit(10)
            .execute()
        )
        for act in (activity_res.data or []):
            recent_items.append(
                NotificationItem(
                    type="activity",
                    title=act.get("activity_type", "activity"),
                    description=act.get("description", ""),
                    created_at=act["created_at"],
                )
            )
    except Exception:
        logger.warning("Notifications: failed to fetch activity log for %s", tenant_id, exc_info=True)

    # --- 5. Overdue action items ---
    overdue_action_items_count = 0
    try:
        today_str = now.strftime("%Y-%m-%d")
        overdue_res = (
            db.table("action_items")
            .select("id, description, due_date, priority")
            .eq("tenant_id", tenant_id)
            .eq("status", "pending")
            .lt("due_date", today_str)
            .order("due_date")
            .limit(10)
            .execute()
        )
        overdue_data = overdue_res.data or []
        overdue_action_items_count = len(overdue_data)

        for item in overdue_data[:5]:
            priority = item.get("priority", "medium")
            recent_items.append(
                NotificationItem(
                    type="overdue_action_item",
                    title=f"Overdue: {item['description'][:60]}",
                    description=f"Priority: {priority} | Due: {item.get('due_date', 'unknown')}",
                    created_at=item.get("due_date"),
                )
            )
    except Exception:
        logger.warning("Notifications: failed to fetch overdue action items for %s", tenant_id, exc_info=True)

    # --- Sort all items by created_at DESC and limit to 20 ---
    recent_items.sort(key=lambda item: item.created_at or "", reverse=True)
    recent_items = recent_items[:20]

    total_unread = new_leads_count + new_conversations_count + todays_appointments_count + overdue_action_items_count

    return NotificationsResponse(
        new_leads_count=new_leads_count,
        new_conversations_count=new_conversations_count,
        todays_appointments_count=todays_appointments_count,
        overdue_action_items_count=overdue_action_items_count,
        total_unread=total_unread,
        recent_items=recent_items,
    )
