"""Control center analytics endpoint."""

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query, Request

from backend.dependencies import verify_tenant
from backend.limiter import limiter
from backend.models.schemas import AgentControlCenterResponse
from backend.models.database import get_service_supabase
from backend.services.tenant_scope import tenant_table
from backend.dependencies import _get_current_tenant
from backend.routers.analytics._common import (
    _QUERY_LIMIT,
    _get_cached,
    _set_cache,
    _period_to_days,
    _PRICING_KEYWORDS,
    _BOOKING_KEYWORDS,
    _URGENT_KEYWORDS,
    _safe_float,
    _ratio,
    _clamp_score,
    _score_status,
    _first_response_seconds,
    _preview_text,
    _build_control_center_recommendations,
    logger,
)

router = APIRouter()


@router.get("/{tenant_id}/control-center", response_model=AgentControlCenterResponse)
@limiter.limit("30/minute")
async def get_agent_control_center(
    request: Request,
    tenant_id: str,
    period: str = Query("30d", pattern="^(7d|14d|30d|90d)$"),
    claims: dict = Depends(_get_current_tenant),
):
    """Operational view of assistant performance across QA, recovery, and ROI."""
    verify_tenant(claims, tenant_id)

    cache_key = f"control_center:{tenant_id}:{period}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    def _empty_response() -> dict:
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

    days = _period_to_days(period)
    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=days)).isoformat()
    db = get_service_supabase()

    try:
        msgs_res = (
            tenant_table(db, "chat_messages", tenant_id)
            .select("session_id, role, content, created_at")
            .eq("tenant_id", tenant_id)
            .gte("created_at", start)
            .order("created_at")
            .limit(_QUERY_LIMIT)
            .execute()
        )
        all_messages = msgs_res.data or []
    except Exception:
        logger.warning("control-center: failed to fetch chat_messages for %s", tenant_id, exc_info=True)
        return _empty_response()

    if not all_messages:
        empty = _empty_response()
        _set_cache(cache_key, empty)
        return empty

    sessions: dict[str, list[dict]] = defaultdict(list)
    for msg in all_messages:
        session_id = msg.get("session_id")
        if session_id:
            sessions[session_id].append(msg)

    session_ids = list(sessions.keys())
    if not session_ids:
        empty = _empty_response()
        _set_cache(cache_key, empty)
        return empty

    def _chunks(items: list[str], size: int = 200):
        for i in range(0, len(items), size):
            yield items[i : i + size]

    conversation_meta: dict[str, dict] = {}
    conversation_id_to_session: dict[str, str] = {}
    lead_id_to_session: dict[str, str] = {}
    assigned_ids: set[str] = set()

    try:
        for chunk in _chunks(session_ids):
            conv_res = (
                tenant_table(db, "conversations", tenant_id)
                .select("id, session_id, lead_id, assigned_to, channel, lead_captured, created_at, last_message_at")
                .eq("client_id", tenant_id)
                .in_("session_id", chunk)
                .execute()
            )
            for row in conv_res.data or []:
                session_id = row.get("session_id")
                if not session_id:
                    continue
                conversation_meta[session_id] = row
                if row.get("id"):
                    conversation_id_to_session[row["id"]] = session_id
                if row.get("lead_id"):
                    lead_id_to_session[row["lead_id"]] = session_id
                if row.get("assigned_to"):
                    assigned_ids.add(row["assigned_to"])
    except Exception:
        logger.warning("control-center: failed to fetch conversations for %s", tenant_id, exc_info=True)

    leads_by_session: dict[str, dict] = {}
    lead_rows_by_id: dict[str, dict] = {}

    try:
        leads_res = (
            tenant_table(db, "leads", tenant_id)
            .select("id, conversation_id, name, email, status, lead_temperature, deal_value, assigned_to, source, created_at")
            .eq("client_id", tenant_id)
            .gte("created_at", start)
            .order("created_at", desc=True)
            .limit(_QUERY_LIMIT)
            .execute()
        )
        for lead in leads_res.data or []:
            lead_id = lead.get("id")
            if lead_id:
                lead_rows_by_id[lead_id] = lead

            session_id = None
            if lead_id and lead_id in lead_id_to_session:
                session_id = lead_id_to_session[lead_id]
            elif lead.get("conversation_id") in conversation_id_to_session:
                session_id = conversation_id_to_session[lead["conversation_id"]]
            elif lead.get("conversation_id") in sessions:
                session_id = lead["conversation_id"]

            if session_id and session_id not in leads_by_session:
                leads_by_session[session_id] = lead
                if lead.get("assigned_to"):
                    assigned_ids.add(lead["assigned_to"])
    except Exception:
        logger.warning("control-center: failed to fetch leads for %s", tenant_id, exc_info=True)

    for session_id, meta in conversation_meta.items():
        if session_id not in leads_by_session and meta.get("lead_id") in lead_rows_by_id:
            leads_by_session[session_id] = lead_rows_by_id[meta["lead_id"]]

    lead_ids = sorted({
        lead.get("id")
        for lead in leads_by_session.values()
        if lead.get("id")
    })

    appointments_by_lead: dict[str, list[dict]] = defaultdict(list)
    if lead_ids:
        try:
            for chunk in _chunks(lead_ids):
                appt_res = (
                    tenant_table(db, "appointments", tenant_id)
                    .select("id, lead_id, status, created_at, start_time")
                    .eq("tenant_id", tenant_id)
                    .in_("lead_id", chunk)
                    .execute()
                )
                for row in appt_res.data or []:
                    if row.get("lead_id"):
                        appointments_by_lead[row["lead_id"]].append(row)
        except Exception:
            logger.warning("control-center: failed to fetch appointments for %s", tenant_id, exc_info=True)

    invoices_by_lead: dict[str, list[dict]] = defaultdict(list)
    if lead_ids:
        try:
            for chunk in _chunks(lead_ids):
                invoice_res = (
                    tenant_table(db, "invoices", tenant_id)
                    .select("id, lead_id, status, total, amount_paid, created_at, paid_at")
                    .eq("tenant_id", tenant_id)
                    .in_("lead_id", chunk)
                    .execute()
                )
                for row in invoice_res.data or []:
                    if row.get("lead_id"):
                        invoices_by_lead[row["lead_id"]].append(row)
        except Exception:
            logger.warning("control-center: failed to fetch invoices for %s", tenant_id, exc_info=True)

    assigned_name_by_id: dict[str, str] = {}
    if assigned_ids:
        try:
            for chunk in _chunks(sorted(assigned_ids)):
                member_res = (
                    tenant_table(db, "team_members", tenant_id)
                    .select("id, name, email")
                    .eq("tenant_id", tenant_id)
                    .in_("id", chunk)
                    .execute()
                )
                for member in member_res.data or []:
                    member_id = member.get("id")
                    if member_id:
                        assigned_name_by_id[member_id] = member.get("name") or member.get("email") or "Team member"
        except Exception:
            logger.warning("control-center: failed to fetch team members for %s", tenant_id, exc_info=True)

    qa_scorecards: list[dict] = []
    recovery_queue: list[dict] = []
    response_durations: list[float] = []

    strong_sessions = 0
    watch_sessions = 0
    at_risk_sessions = 0
    assisted_conversations = 0
    lead_capture_count = 0
    booked_count = 0
    resolved_count = 0
    deals_won = 0
    total_pipeline_value = 0.0
    total_revenue_won = 0.0
    pricing_gap_count = 0
    no_response_count = 0
    at_risk_pipeline_value = 0.0
    counted_capture_keys: set[str] = set()
    counted_booked_keys: set[str] = set()
    counted_pipeline_keys: set[str] = set()
    counted_revenue_keys: set[str] = set()
    counted_at_risk_keys: set[str] = set()

    for session_id, messages in sessions.items():
        if not messages:
            continue

        ordered_messages = sorted(messages, key=lambda item: item.get("created_at") or "")
        meta = conversation_meta.get(session_id) or {}
        lead = leads_by_session.get(session_id)
        lead_id = (lead or {}).get("id") or meta.get("lead_id")
        appointments = appointments_by_lead.get(lead_id, [])
        invoices = invoices_by_lead.get(lead_id, [])
        last_message = ordered_messages[-1]
        last_user_message = next((m for m in reversed(ordered_messages) if m.get("role") == "user"), None)
        last_message_role = last_message.get("role")

        user_text = " ".join((m.get("content") or "").lower() for m in ordered_messages if m.get("role") == "user")
        pricing_interest = any(keyword in user_text for keyword in _PRICING_KEYWORDS)
        booking_interest = any(keyword in user_text for keyword in _BOOKING_KEYWORDS)
        urgent_interest = any(keyword in user_text for keyword in _URGENT_KEYWORDS)

        first_response_seconds = _first_response_seconds(ordered_messages)
        if first_response_seconds is not None:
            response_durations.append(first_response_seconds)

        has_assistant_reply = any(m.get("role") == "assistant" for m in ordered_messages)
        if has_assistant_reply:
            assisted_conversations += 1

        lead_captured = bool(lead) or bool(meta.get("lead_captured"))
        capture_key = lead_id or session_id
        if lead_captured and capture_key not in counted_capture_keys:
            lead_capture_count += 1
            counted_capture_keys.add(capture_key)

        non_cancelled_appointments = [appt for appt in appointments if appt.get("status") != "cancelled"]
        booked = bool(non_cancelled_appointments) or (lead or {}).get("status") == "appointment_booked"
        booked_key = lead_id or session_id
        if booked and booked_key not in counted_booked_keys:
            booked_count += 1
            counted_booked_keys.add(booked_key)

        completed = any(appt.get("status") == "completed" for appt in appointments) or (lead or {}).get("status") == "closed"
        paid_revenue = sum(
            _safe_float(inv.get("amount_paid") or inv.get("total"))
            for inv in invoices
            if inv.get("status") == "paid"
        )
        revenue_key = lead_id or session_id
        if paid_revenue > 0 and revenue_key not in counted_revenue_keys:
            deals_won += 1
            total_revenue_won += paid_revenue
            counted_revenue_keys.add(revenue_key)

        pipeline_value = _safe_float((lead or {}).get("deal_value"))
        pipeline_key = lead_id or session_id
        if pipeline_value > 0 and pipeline_key not in counted_pipeline_keys:
            total_pipeline_value += pipeline_value
            counted_pipeline_keys.add(pipeline_key)

        assigned_to = meta.get("assigned_to") or (lead or {}).get("assigned_to")
        assigned_to_name = assigned_name_by_id.get(assigned_to) if assigned_to else None
        high_temperature = (lead or {}).get("lead_temperature") == "hot"
        high_intent = pricing_interest or booking_interest or urgent_interest or high_temperature

        qa_score = 60
        if has_assistant_reply:
            qa_score += 10
        else:
            qa_score -= 30
        if first_response_seconds is not None:
            if first_response_seconds <= 300:
                qa_score += 10
            elif first_response_seconds <= 900:
                qa_score += 5
            elif first_response_seconds > 1800:
                qa_score -= 10
        if lead_captured:
            qa_score += 10
        else:
            qa_score -= 10
        if booked:
            qa_score += 10
        if paid_revenue > 0:
            qa_score += 10
        if assigned_to:
            qa_score += 5
        if last_message_role == "user":
            qa_score -= 20
            no_response_count += 1
        if pricing_interest and not booked:
            qa_score -= 10
            pricing_gap_count += 1
        if booking_interest and not booked:
            qa_score -= 8
        if urgent_interest and not has_assistant_reply:
            qa_score -= 15
        if len(ordered_messages) < 3:
            qa_score -= 5
        qa_score = _clamp_score(qa_score)
        qa_status = _score_status(qa_score)

        if qa_status == "strong":
            strong_sessions += 1
        elif qa_status == "watch":
            watch_sessions += 1
        else:
            at_risk_sessions += 1

        strengths: list[str] = []
        risks: list[str] = []
        intent_signals: list[str] = []

        if pricing_interest:
            intent_signals.append("pricing")
        if booking_interest:
            intent_signals.append("booking")
        if urgent_interest:
            intent_signals.append("urgent")
        if high_temperature:
            intent_signals.append("hot lead")

        if has_assistant_reply:
            strengths.append("Assistant responded in the conversation")
        if first_response_seconds is not None and first_response_seconds <= 300:
            strengths.append("First response landed within 5 minutes")
        if lead_captured:
            strengths.append("Lead details were captured from the chat")
        if booked:
            strengths.append("Conversation converted into an appointment")
        if assigned_to:
            strengths.append("A team owner is assigned to this thread")
        if paid_revenue > 0:
            strengths.append("Closed revenue is attached to this conversation")

        if last_message_role == "user":
            risks.append("Customer spoke last and is waiting on a reply")
        if not lead_captured:
            risks.append("No lead record was captured from this conversation")
        if pricing_interest and not booked:
            risks.append("Pricing intent appeared without a booking outcome")
        if booking_interest and not booked:
            risks.append("Booking intent did not turn into an appointment")
        if urgent_interest and not has_assistant_reply:
            risks.append("Urgent language appeared before the conversation stalled")
        if high_intent and not assigned_to:
            risks.append("No team owner is assigned to a high-intent conversation")
        if first_response_seconds is not None and first_response_seconds > 1800:
            risks.append("First response took longer than 30 minutes")

        if paid_revenue > 0 or completed:
            outcome = "revenue_won"
            resolution_status = "won"
            resolved_count += 1
        elif booked:
            outcome = "appointment_booked"
            resolution_status = "booked"
            resolved_count += 1
        elif lead_captured:
            outcome = "lead_captured"
            resolution_status = "captured"
            resolved_count += 1
        elif has_assistant_reply and last_message_role != "user":
            outcome = "engaged"
            resolution_status = "monitor"
        elif last_message_role == "user":
            outcome = "awaiting_reply"
            resolution_status = "needs_follow_up"
        else:
            outcome = "unresolved"
            resolution_status = "at_risk"

        if paid_revenue > 0:
            recommended_action = "Review this winning conversation and reuse it as a prompt or playbook example."
        elif last_message_role == "user" and high_intent:
            recommended_action = "Reply manually now with a direct next step and offer the nearest booking slot."
        elif pricing_interest and not booked:
            recommended_action = "Send pricing guidance with a clear booking CTA so quote requests do not stall."
        elif not lead_captured:
            recommended_action = "Tighten the flow so the assistant asks for contact info before the conversation ends."
        elif lead_captured and not booked:
            recommended_action = "Move this lead into a follow-up sequence that pushes toward an appointment."
        elif high_intent and not assigned_to:
            recommended_action = "Assign an owner and review the transcript before the next customer reply arrives."
        else:
            recommended_action = "Review this conversation and tune the flow for the customer intent that showed up."

        created_at = meta.get("created_at") or ordered_messages[0].get("created_at") or now.isoformat()
        last_message_at = meta.get("last_message_at") or last_message.get("created_at") or created_at
        lead_name = (lead or {}).get("name") or (lead or {}).get("email") or "Visitor"
        preview = _preview_text(last_user_message.get("content") if last_user_message else last_message.get("content"))

        scorecard = {
            "session_id": session_id,
            "lead_name": lead_name,
            "lead_id": lead_id,
            "channel": meta.get("channel") or "widget",
            "assigned_to": assigned_to,
            "assigned_to_name": assigned_to_name,
            "created_at": created_at,
            "last_message_at": last_message_at,
            "message_count": len(ordered_messages),
            "qa_score": qa_score,
            "qa_status": qa_status,
            "resolution_status": resolution_status,
            "outcome": outcome,
            "first_response_seconds": first_response_seconds,
            "intent_signals": intent_signals,
            "strengths": strengths[:3],
            "risks": risks[:3],
            "recommended_action": recommended_action,
            "preview": preview,
            "revenue_won": round(paid_revenue, 2),
            "pipeline_value": round(pipeline_value, 2),
        }
        qa_scorecards.append(scorecard)

        needs_recovery = False
        recovery_reason = ""
        urgency = "low"

        if last_message_role == "user" and pricing_interest and not booked:
            needs_recovery = True
            recovery_reason = "Pricing question stalled without a booking"
            urgency = "high"
        elif last_message_role == "user" and urgent_interest:
            needs_recovery = True
            recovery_reason = "Urgent customer is still waiting on a reply"
            urgency = "high"
        elif high_intent and not lead_captured:
            needs_recovery = True
            recovery_reason = "High-intent conversation ended before contact capture"
            urgency = "high"
        elif lead_captured and not booked and high_intent:
            needs_recovery = True
            recovery_reason = "Captured lead never converted into an appointment"
            urgency = "medium"
        elif last_message_role == "user":
            needs_recovery = True
            recovery_reason = "Customer spoke last and the thread went quiet"
            urgency = "medium"

        if needs_recovery:
            estimated_value = round(pipeline_value, 2)
            at_risk_key = lead_id or session_id
            if estimated_value > 0 and at_risk_key not in counted_at_risk_keys:
                at_risk_pipeline_value += estimated_value
                counted_at_risk_keys.add(at_risk_key)
            recovery_queue.append({
                "session_id": session_id,
                "lead_name": lead_name,
                "lead_id": lead_id,
                "channel": meta.get("channel") or "widget",
                "urgency": urgency,
                "reason": recovery_reason,
                "risk_score": 100 - qa_score,
                "last_customer_message": _preview_text(last_user_message.get("content") if last_user_message else last_message.get("content")),
                "last_activity_at": last_message_at,
                "assigned_to": assigned_to,
                "assigned_to_name": assigned_to_name,
                "suggested_playbook": recommended_action,
                "estimated_value": estimated_value,
            })

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

    avg_qa_score = round(
        sum(item["qa_score"] for item in qa_scorecards) / max(len(qa_scorecards), 1),
        1,
    )
    avg_first_response = round(
        sum(response_durations) / len(response_durations), 1
    ) if response_durations else None

    summary = {
        "total_conversations": len(sessions),
        "assisted_conversations": assisted_conversations,
        "strong_sessions": strong_sessions,
        "watch_sessions": watch_sessions,
        "at_risk_sessions": at_risk_sessions,
        "active_recovery_queue": len(recovery_queue),
        "lead_capture_rate": _ratio(lead_capture_count, len(sessions)),
        "booking_rate": _ratio(booked_count, max(lead_capture_count, 1)),
        "resolved_rate": _ratio(resolved_count, len(sessions)),
        "avg_qa_score": avg_qa_score,
        "avg_first_response_seconds": avg_first_response,
        "at_risk_pipeline_value": round(at_risk_pipeline_value, 2),
    }

    roi = {
        "conversations": len(sessions),
        "assisted": assisted_conversations,
        "leads_captured": lead_capture_count,
        "appointments_booked": booked_count,
        "deals_won": deals_won,
        "revenue_won": round(total_revenue_won, 2),
        "pipeline_value": round(total_pipeline_value, 2),
        "at_risk_pipeline_value": round(at_risk_pipeline_value, 2),
        "capture_rate": _ratio(lead_capture_count, len(sessions)),
        "booking_rate": _ratio(booked_count, max(lead_capture_count, 1)),
        "win_rate": _ratio(deals_won, max(booked_count, 1)),
    }

    response = {
        "period": period,
        "generated_at": now.isoformat(),
        "summary": summary,
        "scorecards": qa_scorecards[:8],
        "recovery_queue": recovery_queue[:12],
        "roi": roi,
        "recommendations": _build_control_center_recommendations(
            total_conversations=len(sessions),
            assisted_conversations=assisted_conversations,
            lead_count=lead_capture_count,
            booked_count=booked_count,
            recovery_queue=recovery_queue[:12],
            pricing_gap_count=pricing_gap_count,
            no_response_count=no_response_count,
            at_risk_pipeline_value=round(at_risk_pipeline_value, 2),
        ),
    }

    _set_cache(cache_key, response)
    return response
