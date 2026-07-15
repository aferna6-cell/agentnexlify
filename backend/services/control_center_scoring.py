"""Agent Control Center per-session scoring + recovery classification."""

from datetime import datetime

from backend.services.analytics_common import (
    _BOOKING_KEYWORDS,
    _PRICING_KEYWORDS,
    _URGENT_KEYWORDS,
    _clamp_score,
    _first_response_seconds,
    _preview_text,
    _ratio,
    _safe_float,
    _score_status,
)


def score_session(
    session_id: str,
    messages: list[dict],
    conversation_meta: dict,
    leads_by_session: dict,
    appointments_by_lead: dict,
    invoices_by_lead: dict,
    assigned_name_by_id: dict,
    now: datetime,
    counters: dict,
):
    """Score a single session. Returns (scorecard, recovery_entry_or_None)."""
    if not messages:
        return None, None

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
        counters["response_durations"].append(first_response_seconds)

    has_assistant_reply = any(m.get("role") == "assistant" for m in ordered_messages)
    if has_assistant_reply:
        counters["assisted_conversations"] += 1

    lead_captured = bool(lead) or bool(meta.get("lead_captured"))
    capture_key = lead_id or session_id
    if lead_captured and capture_key not in counters["counted_capture_keys"]:
        counters["lead_capture_count"] += 1
        counters["counted_capture_keys"].add(capture_key)

    non_cancelled_appointments = [appt for appt in appointments if appt.get("status") != "cancelled"]
    booked = bool(non_cancelled_appointments) or (lead or {}).get("status") == "appointment_booked"
    booked_key = lead_id or session_id
    if booked and booked_key not in counters["counted_booked_keys"]:
        counters["booked_count"] += 1
        counters["counted_booked_keys"].add(booked_key)

    completed = any(appt.get("status") == "completed" for appt in appointments) or (lead or {}).get("status") == "closed"
    paid_revenue = sum(
        _safe_float(inv.get("amount_paid") or inv.get("total"))
        for inv in invoices
        if inv.get("status") == "paid"
    )
    revenue_key = lead_id or session_id
    if paid_revenue > 0 and revenue_key not in counters["counted_revenue_keys"]:
        counters["deals_won"] += 1
        counters["total_revenue_won"] += paid_revenue
        counters["counted_revenue_keys"].add(revenue_key)

    pipeline_value = _safe_float((lead or {}).get("deal_value"))
    pipeline_key = lead_id or session_id
    if pipeline_value > 0 and pipeline_key not in counters["counted_pipeline_keys"]:
        counters["total_pipeline_value"] += pipeline_value
        counters["counted_pipeline_keys"].add(pipeline_key)

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
        counters["no_response_count"] += 1
    if pricing_interest and not booked:
        qa_score -= 10
        counters["pricing_gap_count"] += 1
    if booking_interest and not booked:
        qa_score -= 8
    if urgent_interest and not has_assistant_reply:
        qa_score -= 15
    if len(ordered_messages) < 3:
        qa_score -= 5
    qa_score = _clamp_score(qa_score)
    qa_status = _score_status(qa_score)

    if qa_status == "strong":
        counters["strong_sessions"] += 1
    elif qa_status == "watch":
        counters["watch_sessions"] += 1
    else:
        counters["at_risk_sessions"] += 1

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
        counters["resolved_count"] += 1
    elif booked:
        outcome = "appointment_booked"
        resolution_status = "booked"
        counters["resolved_count"] += 1
    elif lead_captured:
        outcome = "lead_captured"
        resolution_status = "captured"
        counters["resolved_count"] += 1
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

    recovery_entry = None
    if needs_recovery:
        estimated_value = round(pipeline_value, 2)
        at_risk_key = lead_id or session_id
        if estimated_value > 0 and at_risk_key not in counters["counted_at_risk_keys"]:
            counters["at_risk_pipeline_value"] += estimated_value
            counters["counted_at_risk_keys"].add(at_risk_key)
        recovery_entry = {
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
        }

    return scorecard, recovery_entry


def new_counters() -> dict:
    """Fresh counter dict for an aggregation pass."""
    return {
        "response_durations": [],
        "strong_sessions": 0,
        "watch_sessions": 0,
        "at_risk_sessions": 0,
        "assisted_conversations": 0,
        "lead_capture_count": 0,
        "booked_count": 0,
        "resolved_count": 0,
        "deals_won": 0,
        "total_pipeline_value": 0.0,
        "total_revenue_won": 0.0,
        "pricing_gap_count": 0,
        "no_response_count": 0,
        "at_risk_pipeline_value": 0.0,
        "counted_capture_keys": set(),
        "counted_booked_keys": set(),
        "counted_pipeline_keys": set(),
        "counted_revenue_keys": set(),
        "counted_at_risk_keys": set(),
    }


def summarize(counters: dict, qa_scorecards: list[dict], recovery_queue: list[dict], total_sessions: int) -> tuple[dict, dict]:
    """Return (summary, roi) from aggregated counters."""
    avg_qa_score = round(
        sum(item["qa_score"] for item in qa_scorecards) / max(len(qa_scorecards), 1),
        1,
    )
    response_durations = counters["response_durations"]
    avg_first_response = round(
        sum(response_durations) / len(response_durations), 1
    ) if response_durations else None

    summary = {
        "total_conversations": total_sessions,
        "assisted_conversations": counters["assisted_conversations"],
        "strong_sessions": counters["strong_sessions"],
        "watch_sessions": counters["watch_sessions"],
        "at_risk_sessions": counters["at_risk_sessions"],
        "active_recovery_queue": len(recovery_queue),
        "lead_capture_rate": _ratio(counters["lead_capture_count"], total_sessions),
        "booking_rate": _ratio(counters["booked_count"], max(counters["lead_capture_count"], 1)),
        "resolved_rate": _ratio(counters["resolved_count"], total_sessions),
        "avg_qa_score": avg_qa_score,
        "avg_first_response_seconds": avg_first_response,
        "at_risk_pipeline_value": round(counters["at_risk_pipeline_value"], 2),
    }

    roi = {
        "conversations": total_sessions,
        "assisted": counters["assisted_conversations"],
        "leads_captured": counters["lead_capture_count"],
        "appointments_booked": counters["booked_count"],
        "deals_won": counters["deals_won"],
        "revenue_won": round(counters["total_revenue_won"], 2),
        "pipeline_value": round(counters["total_pipeline_value"], 2),
        "at_risk_pipeline_value": round(counters["at_risk_pipeline_value"], 2),
        "capture_rate": _ratio(counters["lead_capture_count"], total_sessions),
        "booking_rate": _ratio(counters["booked_count"], max(counters["lead_capture_count"], 1)),
        "win_rate": _ratio(counters["deals_won"], max(counters["booked_count"], 1)),
    }

    return summary, roi
