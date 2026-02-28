from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# --- Request / Response schemas ---

class ChatMessageRequest(BaseModel):
    client_api_key: str
    session_id: str
    message: str


class ChatMessageResponse(BaseModel):
    reply: str
    conversation_id: str


class CreateClientRequest(BaseModel):
    agent_name: str
    agent_type: str = "agent"
    brokerage_name: str | None = None
    service_area: str
    bot_name: str = "Aria"
    calendly_link: str | None = None
    notification_email: str | None = None
    notification_phone: str | None = None
    custom_instructions: str | None = None
    brand_color: str = "#6cff5c"


# --- Database row models ---

class ClientRow(BaseModel):
    id: str
    created_at: datetime
    agent_name: str
    agent_type: str
    brokerage_name: str | None = None
    service_area: str
    bot_name: str
    calendly_link: str | None = None
    notification_email: str | None = None
    notification_phone: str | None = None
    widget_api_key: str
    active: bool
    custom_instructions: str | None = None
    brand_color: str


class ConversationRow(BaseModel):
    id: str
    client_id: str
    created_at: datetime
    updated_at: datetime
    channel: str
    session_id: str
    status: str
    lead_id: str | None = None


class MessageRow(BaseModel):
    id: str
    conversation_id: str
    created_at: datetime
    role: str
    content: str
    metadata: dict[str, Any] | None = None


class LeadRow(BaseModel):
    id: str
    client_id: str
    conversation_id: str | None = None
    created_at: datetime
    updated_at: datetime
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    lead_type: str | None = None
    timeline: str | None = None
    budget: str | None = None
    pre_approved: bool | None = None
    areas_of_interest: str | None = None
    must_haves: str | None = None
    lead_score: int | None = None
    lead_temperature: str | None = None
    conversation_summary: str | None = None
    next_steps: str | None = None
    status: str = "new"
    appointment_date: datetime | None = None
