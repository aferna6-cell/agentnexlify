"""Agent Control Center orchestration: fetch → score → aggregate."""

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from backend.models.database import get_service_supabase as _get_service_supabase
from backend.routers.analytics._common import (
    _build_control_center_recommendations,
    _period_to_days,
)
from backend.services.control_center_fetch import (
    fetch_appointments,
    fetch_chat_messages,
    fetch_conversations,
    fetch_invoices,
    fetch_leads,
    fetch_team_members,
)
from backend.services.control_center_scoring import (
    new_counters,
    score_session,
    summarize,
)

logger = logging.getLogger(__name__)


def _get_db():
    return _get_service_supabase()


def empty_response(period: str) -> dict:
    """Empty payload for tenants without data or on data-fetch error."""
    return {
        "period": period,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_conversations": 0,
            "assisted_conversations": 0,
            "strong_sessions": 0,
            "watch_sessions": 0,
            "at_risk_sessions": 0,
            "active_recovery_queue": 0,
            "lead_capture_rate": 0.0,
            "booking_rate": 0.0,
            "resolved_rate": 0.0,
            "avg_qa_score": 0.0,
            "avg_first_response_seconds": None,
            "at_risk_pipeline_value": 0.0,
        },
        "scorecards": [],
        "recovery_queue": [],
        "roi": {
            "conversations": 0,
            "assisted": 0,
            "leads_captured": 0,
            "appointments_booked": 0,
            "deals_won": 0,
            "revenue_won": 0.0,
            "pipeline_value": 0.0,
            "at_risk_pipeline_value": 0.0,
            "capture_rate": 0.0,
            "booking_rate": 0.0,
            "win_rate": 0.0,
        },
        "recommendations": [
            "No recent conversations were found yet. Once chats start flowing, this view will score quality, surface recovery opportunities, and connect outcomes to revenue."
        ],
    }


def build_control_center_response(tenant_id: str, period: str) -> dict:
    """Aggregate the full control-center analytics payload."""
    days = _period_to_days(period)
    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=days)).isoformat()
    db = _get_db()

    all_messages = fetch_chat_messages(db, tenant_id, start)
    if all_messages is None or not all_messages:
        return empty_response(period)

    sessions: dict[str, list[dict]] = defaultdict(list)
    for msg in all_messages:
        session_id = msg.get("session_id")
        if session_id:
            sessions[session_id].append(msg)

    session_ids = list(sessions.keys())
    if not session_ids:
        return empty_response(period)

    conversation_meta, conversation_id_to_session, lead_id_to_session, assigned_ids = (
        fetch_conversations(db, tenant_id, session_ids)
    )

    leads_by_session = fetch_leads(
        db,
        tenant_id,
        start,
        sessions,
        conversation_id_to_session,
        lead_id_to_session,
        conversation_meta,
        assigned_ids,
    )

    lead_ids: list[str] = sorted({
        lead["id"]
        for lead in leads_by_session.values()
        if lead.get("id")
    })

    appointments_by_lead = fetch_appointments(db, tenant_id, lead_ids)
    invoices_by_lead = fetch_invoices(db, tenant_id, lead_ids)
    assigned_name_by_id = fetch_team_members(db, tenant_id, assigned_ids)

    counters = new_counters()
    qa_scorecards: list[dict] = []
    recovery_queue: list[dict] = []

    for session_id, messages in sessions.items():
        scorecard, recovery_entry = score_session(
            session_id,
            messages,
            conversation_meta,
            leads_by_session,
            appointments_by_lead,
            invoices_by_lead,
            assigned_name_by_id,
            now,
            counters,
        )
        if scorecard:
            qa_scorecards.append(scorecard)
        if recovery_entry:
            recovery_queue.append(recovery_entry)

    qa_scorecards.sort(key=lambda item: item["last_message_at"], reverse=True)
    urgency_rank = {"high": 3, "medium": 2, "low": 1}
    recovery_queue.sort(
        key=lambda item: (
            urgency_rank.get(item["urgency"], 0),
            item["risk_score"],
            item["last_activity_at"],
        ),
        reverse=True,
    )

    summary, roi = summarize(counters, qa_scorecards, recovery_queue, len(sessions))

    return {
        "period": period,
        "generated_at": now.isoformat(),
        "summary": summary,
        "scorecards": qa_scorecards[:8],
        "recovery_queue": recovery_queue[:12],
        "roi": roi,
        "recommendations": _build_control_center_recommendations(
            total_conversations=len(sessions),
            assisted_conversations=counters["assisted_conversations"],
            lead_count=counters["lead_capture_count"],
            booked_count=counters["booked_count"],
            recovery_queue=recovery_queue[:12],
            pricing_gap_count=counters["pricing_gap_count"],
            no_response_count=counters["no_response_count"],
            at_risk_pipeline_value=round(counters["at_risk_pipeline_value"], 2),
        ),
    }
