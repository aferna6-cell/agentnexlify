from typing import Any

from pydantic import BaseModel, Field


class WidgetChatRequest(BaseModel):
    api_key: str = Field(..., max_length=100)
    session_id: str = Field(..., max_length=200)
    message: str = Field(..., max_length=10000)
    content_mode: bool = False
    visitor_info: dict[str, Any] | None = None


class WidgetChatResponse(BaseModel):
    response: str
    session_id: str
    lead_captured: bool
    show_watermark: bool
    trial_expired: bool = False
    handoff: bool = False
    # True when the managed-agent fallback (support_agent) handled this turn
    # instead of the inline widget Claude call. Optional metadata for the
    # frontend to show a "deep AI" badge or for telemetry. Defaults to False
    # so existing widget builds keep working without changes.
    ai_fallback_fired: bool = False


class WidgetConfigResponse(BaseModel):
    bot_name: str
    primary_color: str
    greeting_message: str | None
    position: str
    show_watermark: bool
    allowed_domains: list[str] | None
    tenant_id: str | None = None
    booking_enabled: bool = False
    branding: dict | None = None
    agent_name: str | None = None
    is_online: bool = True
    offline_message: str | None = None
    menu_items: list[dict] | None = None
    business_type: str | None = None
    teaser_message: str | None = None
    teaser_delay_seconds: int = 3
    teaser_enabled: bool = True
    plan: str = "free"
    pre_chat_form: list[dict] | None = None


class WidgetLeadRequest(BaseModel):
    api_key: str = Field(..., max_length=100)
    session_id: str = Field(..., max_length=100)
    name: str | None = Field(None, max_length=200)
    email: str | None = Field(None, max_length=320)
    phone: str | None = Field(None, max_length=30)
    service: str | None = Field(None, max_length=500)


class WidgetLeadResponse(BaseModel):
    lead_id: str | None = None
    updated_fields: list[str]


class OnlineStatusRequest(BaseModel):
    is_online: bool


class WidgetOfflineContactRequest(BaseModel):
    api_key: str = Field(..., max_length=100)
    name: str = Field(..., max_length=200)
    email: str = Field(..., max_length=320)
    phone: str | None = Field(None, max_length=30)
    message: str = Field(..., max_length=5000)
