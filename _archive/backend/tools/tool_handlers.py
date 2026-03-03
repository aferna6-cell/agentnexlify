"""Functions that execute when Claude calls a tool."""

from __future__ import annotations

import json
import logging
from typing import Any

from backend.models.database import get_supabase
from backend.models.schemas import ClientRow
from backend.services.notifications import send_agent_notification

logger = logging.getLogger(__name__)


async def handle_tool_call(
    tool_name: str,
    tool_input: dict[str, Any],
    client: ClientRow,
    conversation_id: str,
) -> str:
    """Dispatch a tool call to the appropriate handler. Returns the tool result as a string."""
    handlers = {
        "book_appointment": _handle_book_appointment,
        "search_listings": _handle_search_listings,
        "log_lead": _handle_log_lead,
        "notify_agent": _handle_notify_agent,
    }
    handler = handlers.get(tool_name)
    if handler is None:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})
    try:
        result = await handler(tool_input, client, conversation_id)
        return json.dumps(result)
    except Exception:
        logger.exception("Tool handler error for %s", tool_name)
        return json.dumps({"error": "An internal error occurred while processing."})


async def _handle_book_appointment(
    inputs: dict[str, Any], client: ClientRow, conversation_id: str
) -> dict:
    db = get_supabase()

    # Store appointment in leads table
    lead_data: dict[str, Any] = {
        "tenant_id": client.id,
        "conversation_id": conversation_id,
        "lead_stage": "qualified",
        "source": "chat",
    }
    if inputs.get("lead_name"):
        lead_data["name"] = inputs["lead_name"]
    if inputs.get("lead_email"):
        lead_data["email"] = inputs["lead_email"]
    if inputs.get("lead_phone"):
        lead_data["phone"] = inputs["lead_phone"]

    # Upsert lead by conversation_id
    existing = (
        db.table("leads")
        .select("id")
        .eq("conversation_id", conversation_id)
        .execute()
    )
    if existing.data:
        db.table("leads").update(lead_data).eq("id", existing.data[0]["id"]).execute()
    else:
        db.table("leads").insert(lead_data).execute()

    # Notify the agent about the booking
    appt_type = inputs.get("appointment_type", "consultation_call")
    preferred = f"{inputs.get('preferred_date', 'TBD')} at {inputs.get('preferred_time', 'TBD')}"
    notification_msg = (
        f"New {appt_type.replace('_', ' ')} booked!\n"
        f"Lead: {inputs.get('lead_name', 'Unknown')}\n"
        f"Phone: {inputs.get('lead_phone', 'N/A')}\n"
        f"Email: {inputs.get('lead_email', 'N/A')}\n"
        f"Preferred time: {preferred}"
    )
    await send_agent_notification(client, "hot_lead", notification_msg)

    if client.calendly_link:
        return {
            "success": True,
            "message": f"Appointment request sent. The lead can finalize at: {client.calendly_link}",
            "calendly_link": client.calendly_link,
        }
    return {
        "success": True,
        "message": (
            f"Appointment request recorded. {client.agent_name} will confirm "
            f"the {appt_type.replace('_', ' ')} shortly."
        ),
    }


async def _handle_search_listings(
    inputs: dict[str, Any], client: ClientRow, conversation_id: str
) -> dict:
    # MVP: no MLS integration yet — return a helpful placeholder
    location = inputs.get("location", client.service_area)
    criteria_parts = []
    if inputs.get("min_price") or inputs.get("max_price"):
        lo = f"${inputs['min_price']:,}" if inputs.get("min_price") else "any"
        hi = f"${inputs['max_price']:,}" if inputs.get("max_price") else "any"
        criteria_parts.append(f"price {lo}–{hi}")
    if inputs.get("bedrooms"):
        criteria_parts.append(f"{inputs['bedrooms']}+ bed")
    if inputs.get("bathrooms"):
        criteria_parts.append(f"{inputs['bathrooms']}+ bath")
    if inputs.get("property_type"):
        criteria_parts.append(inputs["property_type"])

    criteria_str = ", ".join(criteria_parts) if criteria_parts else "their criteria"
    return {
        "success": True,
        "message": (
            f"MLS integration is not yet active. {client.agent_name} will personally "
            f"send curated listings in {location} matching {criteria_str}."
        ),
        "listings": [],
    }


async def _handle_log_lead(
    inputs: dict[str, Any], client: ClientRow, conversation_id: str
) -> dict:
    db = get_supabase()

    lead_data: dict[str, Any] = {
        "tenant_id": client.id,
        "conversation_id": conversation_id,
    }
    # Map fields that exist in the leads schema
    field_map = [
        "name", "email", "phone", "timeline", "budget",
        "lead_score", "service_interest", "notes",
    ]
    for field in field_map:
        if field in inputs and inputs[field] is not None:
            lead_data[field] = inputs[field]

    # Upsert: update existing lead for this conversation or create new
    existing = (
        db.table("leads")
        .select("id")
        .eq("conversation_id", conversation_id)
        .execute()
    )
    if existing.data:
        lead_id = existing.data[0]["id"]
        db.table("leads").update(lead_data).eq("id", lead_id).execute()
    else:
        result = db.table("leads").insert(lead_data).execute()
        lead_id = result.data[0]["id"]
        # Link lead to conversation
        db.table("conversations").update({"lead_id": lead_id}).eq("id", conversation_id).execute()

    # If it's a hot lead (score >= 8), auto-notify the agent
    lead_score = inputs.get("lead_score")
    if lead_score is not None and lead_score >= 8:
        msg = (
            f"Hot lead captured!\n"
            f"Name: {inputs.get('name', 'Unknown')}\n"
            f"Phone: {inputs.get('phone', 'N/A')}\n"
            f"Email: {inputs.get('email', 'N/A')}\n"
            f"Score: {lead_score}/10"
        )
        await send_agent_notification(client, "hot_lead", msg)

    return {"success": True, "lead_id": lead_id, "message": "Lead info saved."}


async def _handle_notify_agent(
    inputs: dict[str, Any], client: ClientRow, conversation_id: str
) -> dict:
    urgency = inputs["urgency"]
    message = inputs["message"]
    if inputs.get("lead_name"):
        message = f"Lead: {inputs['lead_name']}\nPhone: {inputs.get('lead_phone', 'N/A')}\n\n{message}"

    await send_agent_notification(client, urgency, message)
    return {"success": True, "message": f"Notification sent to {client.agent_name}."}
