from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


# --- Request / Response schemas ---

class ChatMessageRequest(BaseModel):
    client_api_key: str
    session_id: str
    message: str


class ChatMessageResponse(BaseModel):
    reply: str
    conversation_id: str


# --- Signup schemas ---


class SignupRequest(BaseModel):
    business_name: str
    owner_name: str
    email: str
    industry: str = "other"
    city: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        import re
        if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", v):
            raise ValueError("Invalid email address")
        return v


class SignupResponse(BaseModel):
    client_id: str
    widget_api_key: str
    embed_code: str


class WidgetConfigUpdate(BaseModel):
    bot_name: str | None = None
    brand_color: str | None = None
    greeting_message: str | None = None
    position: str | None = None


# --- Auth schemas ---


class RegisterRequest(BaseModel):
    business_name: str
    owner_name: str
    email: str
    password: str
    industry: str = "other"
    city: str = ""

    @field_validator("email")
    @classmethod
    def validate_register_email(cls, v: str) -> str:
        import re
        if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", v):
            raise ValueError("Invalid email address")
        return v.lower().strip()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class RegisterResponse(BaseModel):
    tenant_id: str
    api_key: str
    token: str


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    tenant_id: str
    token: str
    business_name: str
    plan: str


class MeResponse(BaseModel):
    tenant_id: str
    email: str
    business_name: str
    plan: str
    city: str | None = None
    owner_name: str | None = None


class DashboardResponse(BaseModel):
    business_name: str
    plan: str
    plan_status: str
    conversations_used_this_month: int
    monthly_conversation_limit: int
    widget_api_key: str | None = None
    leads_count: int


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


# --- Widget (multi-tenant) schemas ---


# --- Billing schemas ---


class CreateCheckoutRequest(BaseModel):
    tenant_id: str
    plan: str  # foundation|growth|operations|enterprise
    promo_code: str | None = None


class CheckoutResponse(BaseModel):
    checkout_url: str


class PortalResponse(BaseModel):
    portal_url: str


# --- Widget (multi-tenant) schemas ---


class WidgetChatRequest(BaseModel):
    api_key: str
    session_id: str
    message: str
    visitor_info: dict[str, Any] | None = None


class WidgetChatResponse(BaseModel):
    response: str
    session_id: str
    lead_captured: bool
    show_watermark: bool


class WidgetConfigResponse(BaseModel):
    bot_name: str
    primary_color: str
    greeting_message: str | None
    position: str
    show_watermark: bool
    allowed_domains: list[str] | None


class WidgetLeadRequest(BaseModel):
    api_key: str
    session_id: str
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    service: str | None = None


class WidgetLeadResponse(BaseModel):
    lead_id: str
    updated_fields: list[str]


# --- Database row models (old single-tenant) ---


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
