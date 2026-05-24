from typing import Any

from pydantic import BaseModel, Field

from backend.models.schemas_auth import WidgetConfigDetail
from backend.models.schemas_branding import BrandingConfig


class DashboardQuickAction(BaseModel):
    label: str
    description: str
    action: str
    page: str | None = None


class DashboardBusinessProfile(BaseModel):
    key: str
    label: str
    headline: str
    subheadline: str
    focus_areas: list[str] = Field(default_factory=list)
    conversation_label: str = "Conversations This Month"
    conversation_empty_hint: str = "Set up your widget to start capturing conversations"
    lead_label: str = "Leads Captured"
    lead_empty_hint: str = "Leads appear automatically from widget chats"
    automation_label: str = "Automations Active"
    automation_empty_hint: str = "Set up your first automation"
    appointment_label: str = "Appointments This Week"
    missed_call_label: str = "Missed Calls This Week"
    missed_call_empty_hint: str = "Enable missed call text-back in Settings"
    proof_metric_label: str = "Customer opportunities captured"
    proof_metric_empty_hint: str = "Your proof metric appears once customers start chatting"
    quick_actions: list[DashboardQuickAction] = Field(default_factory=list)


class DashboardResponse(BaseModel):
    business_name: str
    business_type: str | None = None
    plan: str
    plan_status: str
    conversations_used_this_month: int
    monthly_conversation_limit: int | None = None
    widget_api_key: str | None = None
    leads_count: int
    widget_config: WidgetConfigDetail | None = None
    business_profile: DashboardBusinessProfile | None = None
    faq_count: int = 0
    has_conversations: bool = False
    hot_leads_count: int = 0
    trial_days_remaining: int | None = None
    trial_expired: bool = False
    missed_calls_this_week: int | None = None


class TrialStatusResponse(BaseModel):
    plan: str
    trial_started: str | None = None
    trial_expires: str | None = None
    days_remaining: int | None = None
    is_expired: bool = False


class LeadScoreResponse(BaseModel):
    lead_id: str
    score: int
    raw_score: int
    breakdown: dict[str, Any]


class ScoreAllResponse(BaseModel):
    tenant_id: str
    scored: int
    errors: int
    total: int


class WidgetConfigUpdateRequest(BaseModel):
    bot_name: str | None = None
    primary_color: str | None = None
    greeting_message: str | None = None
    position: str | None = None
    branding: BrandingConfig | None = None
    teaser_message: str | None = Field(None, max_length=150)
    teaser_delay_seconds: int | None = Field(None, ge=0, le=60)
    teaser_enabled: bool | None = None
    pre_chat_form: list[dict] | None = None
    enable_ai_fallback: bool | None = None
    enable_structured_lead_parser: bool | None = None
