
from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field, field_validator


# --- Branding schema ---


class BrandingConfig(BaseModel):
    logo_url: str | None = None
    primary_color: str | None = None
    secondary_color: str | None = None
    accent_color: str | None = None
    font_family: str | None = None
    widget_title: str | None = None
    powered_by_text: str | None = None
    powered_by_url: str | None = None
    hide_powered_by: bool = False
    custom_css: str | None = None


# --- Request / Response schemas ---

class ContactRequest(BaseModel):
    name: str
    email: EmailStr
    message: str


class ContactResponse(BaseModel):
    success: bool
    message: str


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
    business_type: str | None = None


class WidgetConfigDetail(BaseModel):
    bot_name: str = ""
    primary_color: str = "#00BFFF"
    greeting_message: str = "Hi! How can I help you today?"
    position: str = "bottom-right"
    branding: dict | None = None
    is_online: bool = True
    offline_message: str | None = None


class DashboardResponse(BaseModel):
    business_name: str
    plan: str
    plan_status: str
    conversations_used_this_month: int
    monthly_conversation_limit: int | None = None
    widget_api_key: str | None = None
    leads_count: int
    widget_config: WidgetConfigDetail | None = None
    faq_count: int = 0
    has_conversations: bool = False
    hot_leads_count: int = 0
    trial_days_remaining: int | None = None
    trial_expired: bool = False


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


class FaqEntryResponse(BaseModel):
    id: str
    question: str
    answer: str
    category: str | None = None
    is_active: bool = True


class FaqCreateRequest(BaseModel):
    question: str
    answer: str
    category: str | None = None


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


# --- Widget (multi-tenant) schemas ---


# --- Billing schemas ---


class CreateCheckoutRequest(BaseModel):
    tenant_id: str
    plan: str  # growth|professional|enterprise
    promo_code: str | None = None


class CheckoutResponse(BaseModel):
    checkout_url: str


class PortalResponse(BaseModel):
    portal_url: str


# --- Widget (multi-tenant) schemas ---


class WidgetChatRequest(BaseModel):
    api_key: str
    session_id: str
    message: str = Field(..., max_length=10000)
    visitor_info: dict[str, Any] | None = None


class WidgetChatResponse(BaseModel):
    response: str
    session_id: str
    lead_captured: bool
    show_watermark: bool
    trial_expired: bool = False


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


# --- Database row models ---


class LeadRow(BaseModel):
    """Matches live Supabase leads table (archive schema)."""
    id: str
    client_id: str
    conversation_id: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
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
    tags: list[str] = Field(default_factory=list)


# Live schema CHECK constraint: new, contacted, appointment_booked, closed, lost
VALID_LEAD_STAGES = {"new", "contacted", "appointment_booked", "closed", "lost"}


class LeadUpdateRequest(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    status: str | None = None
    conversation_summary: str | None = None
    lead_type: str | None = None
    areas_of_interest: str | None = None
    timeline: str | None = None
    budget: str | None = None
    next_steps: str | None = None
    tags: list[str] | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_LEAD_STAGES:
            raise ValueError(f"status must be one of {VALID_LEAD_STAGES}")
        return v


# --- CRM schemas ---


class ActivityItem(BaseModel):
    id: str
    activity_type: str
    description: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    lead_id: str | None = None
    created_at: datetime


class NoteCreateRequest(BaseModel):
    content: str


class NoteResponse(BaseModel):
    id: str
    lead_id: str
    content: str
    created_at: datetime


class ClientUpdateRequest(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    lead_type: str | None = None
    areas_of_interest: str | None = None
    timeline: str | None = None
    budget: str | None = None
    next_steps: str | None = None

    @field_validator("email")
    @classmethod
    def validate_client_email(cls, v: str | None) -> str | None:
        if v is not None:
            import re
            if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", v):
                raise ValueError("Invalid email address")
        return v


class StageChangeRequest(BaseModel):
    stage: str

    @field_validator("stage")
    @classmethod
    def validate_stage(cls, v: str) -> str:
        if v not in VALID_LEAD_STAGES:
            raise ValueError(f"stage must be one of {VALID_LEAD_STAGES}")
        return v


# --- Appointment / Availability schemas ---


class DayHours(BaseModel):
    enabled: bool = False
    start: str = "09:00"
    end: str = "17:00"


class AvailabilityConfigRequest(BaseModel):
    timezone: str = "America/New_York"
    hours: dict[str, DayHours] | None = None
    slot_duration_minutes: int = Field(default=30, ge=15, le=120)
    buffer_minutes: int = Field(default=0, ge=0, le=60)
    max_advance_days: int = Field(default=30, ge=1, le=90)


class AvailabilityConfigResponse(BaseModel):
    timezone: str
    hours: dict[str, Any]
    slot_duration_minutes: int
    buffer_minutes: int
    max_advance_days: int


class TimeSlot(BaseModel):
    start: str
    end: str
    start_utc: str
    end_utc: str


class AvailableSlotsResponse(BaseModel):
    date: str
    timezone: str
    slots: list[TimeSlot]


class BookAppointmentRequest(BaseModel):
    api_key: str
    customer_name: str
    customer_email: str
    customer_phone: str | None = None
    start_utc: str
    end_utc: str
    notes: str | None = None

    @field_validator("customer_email")
    @classmethod
    def validate_booking_email(cls, v: str) -> str:
        import re
        if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", v):
            raise ValueError("Invalid email address")
        return v.lower().strip()


class BookAppointmentResponse(BaseModel):
    id: str
    start_time: str
    end_time: str
    status: str
    customer_name: str
    customer_email: str


class AppointmentOut(BaseModel):
    id: str
    tenant_id: str
    lead_id: str | None = None
    customer_name: str
    customer_email: str
    customer_phone: str | None = None
    start_time: str
    end_time: str
    status: str
    notes: str | None = None
    google_event_id: str | None = None
    created_at: str | None = None
    recurrence_rule: str | None = None
    recurrence_parent_id: str | None = None
    recurrence_end_date: str | None = None


class AppointmentListResponse(BaseModel):
    appointments: list[AppointmentOut]
    timezone: str = "America/New_York"


class AppointmentUpdateRequest(BaseModel):
    status: str | None = None
    notes: str | None = None
    start_time: str | None = None
    end_time: str | None = None

    @field_validator("status")
    @classmethod
    def validate_appt_status(cls, v: str | None) -> str | None:
        if v is not None and v not in {"confirmed", "cancelled", "completed", "no_show"}:
            raise ValueError("status must be one of: confirmed, cancelled, completed, no_show")
        return v


class RecurrenceRequest(BaseModel):
    rule: str  # weekly, biweekly, monthly
    end_date: str  # YYYY-MM-DD — when the series ends

    @field_validator("rule")
    @classmethod
    def validate_rule(cls, v: str) -> str:
        if v not in {"weekly", "biweekly", "monthly"}:
            raise ValueError("rule must be one of: weekly, biweekly, monthly")
        return v


class ClientListItem(BaseModel):
    id: str
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    lead_score: int = 0
    status: str = "new"
    lead_temperature: str | None = None
    created_at: datetime
    last_activity: datetime | None = None
    tags: list[str] = Field(default_factory=list)


class ClientProfile(BaseModel):
    id: str
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    lead_score: int = 0
    status: str = "new"
    lead_type: str | None = None
    lead_temperature: str | None = None
    areas_of_interest: str | None = None
    timeline: str | None = None
    budget: str | None = None
    conversation_summary: str | None = None
    next_steps: str | None = None
    created_at: datetime
    tags: list[str] = Field(default_factory=list)
    client_notes: list[NoteResponse] = Field(default_factory=list)
    conversations: list[dict[str, Any]] = Field(default_factory=list)
    recent_activity: list[ActivityItem] = Field(default_factory=list)


class CrmDashboardWidgets(BaseModel):
    recent_activity: list[ActivityItem] = Field(default_factory=list)
    needs_attention: list[ClientListItem] = Field(default_factory=list)
    weekly_stats: dict[str, int] = Field(default_factory=dict)


# --- Automation Sequence schemas ---

VALID_TRIGGER_EVENTS = {"new_lead", "lead_stage_change", "no_response_24h", "appointment_completed"}


class AutomationStepCreate(BaseModel):
    step_order: int
    delay_minutes: int = 0
    action_type: str = "email"
    subject_template: str = ""
    body_template: str


class SequenceCreateRequest(BaseModel):
    name: str
    trigger_event: str
    trigger_config: dict = {}
    steps: list[AutomationStepCreate]

    @field_validator("trigger_event")
    @classmethod
    def validate_trigger_event(cls, v: str) -> str:
        if v not in VALID_TRIGGER_EVENTS:
            raise ValueError(f"trigger_event must be one of {VALID_TRIGGER_EVENTS}")
        return v


class SequenceUpdateRequest(BaseModel):
    name: str | None = None
    trigger_event: str | None = None
    trigger_config: dict | None = None
    steps: list[AutomationStepCreate] | None = None

    @field_validator("trigger_event")
    @classmethod
    def validate_trigger_event(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_TRIGGER_EVENTS:
            raise ValueError(f"trigger_event must be one of {VALID_TRIGGER_EVENTS}")
        return v


class LeadStageUpdate(BaseModel):
    stage: str

    @field_validator("stage")
    @classmethod
    def validate_stage_update(cls, v: str) -> str:
        if v not in VALID_LEAD_STAGES:
            raise ValueError(f"stage must be one of {VALID_LEAD_STAGES}")
        return v


# --- Email Template schemas ---

VALID_TEMPLATE_CATEGORIES = {"welcome", "follow_up", "reminder", "review", "promotion", "custom"}


class EmailTemplateCreate(BaseModel):
    name: str
    category: str = "custom"
    subject_template: str = ""
    body_template: str

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        if v not in VALID_TEMPLATE_CATEGORIES:
            raise ValueError(f"category must be one of {VALID_TEMPLATE_CATEGORIES}")
        return v


class EmailTemplateUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    subject_template: str | None = None
    body_template: str | None = None

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_TEMPLATE_CATEGORIES:
            raise ValueError(f"category must be one of {VALID_TEMPLATE_CATEGORIES}")
        return v


# --- Webhook schemas ---


class WebhookCreateRequest(BaseModel):
    name: str
    url: str
    events: list[str]
    secret: str | None = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith("https://"):
            raise ValueError("Webhook URL must use HTTPS")
        return v


class WebhookUpdateRequest(BaseModel):
    name: str | None = None
    url: str | None = None
    events: list[str] | None = None
    secret: str | None = None
    is_active: bool | None = None

    @field_validator("url")
    @classmethod
    def validate_update_url(cls, v: str | None) -> str | None:
        if v is not None and not v.startswith("https://"):
            raise ValueError("Webhook URL must use HTTPS")
        return v


class WebhookResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    url: str
    events: list[str]
    secret: str | None = None
    is_active: bool = True
    last_triggered_at: datetime | None = None
    failure_count: int = 0
    created_at: datetime


class WebhookListResponse(BaseModel):
    """Webhook response without secret — used for list/get endpoints."""
    id: str
    tenant_id: str
    name: str
    url: str
    events: list[str]
    is_active: bool = True
    last_triggered_at: datetime | None = None
    failure_count: int = 0
    created_at: datetime


class WebhookLogResponse(BaseModel):
    id: str
    webhook_id: str
    event: str
    payload: dict[str, Any] | None = None
    response_status: int | None = None
    response_body: str | None = None
    success: bool | None = None
    created_at: datetime


class WebhookTestResponse(BaseModel):
    success: bool
    status_code: int | None = None
    response_body: str | None = None
    event: str


# --- Team schemas ---


class TeamInviteRequest(BaseModel):
    email: str
    role: str = "member"
    name: str | None = None

    @field_validator("email")
    @classmethod
    def validate_invite_email(cls, v: str) -> str:
        import re
        if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", v):
            raise ValueError("Invalid email address")
        return v.lower().strip()

    @field_validator("role")
    @classmethod
    def validate_invite_role(cls, v: str) -> str:
        if v not in ("admin", "member", "viewer"):
            raise ValueError("role must be one of: admin, member, viewer")
        return v


class TeamMemberResponse(BaseModel):
    id: str
    email: str
    name: str | None = None
    role: str
    invite_accepted: bool
    last_login: datetime | None = None
    created_at: datetime


class AcceptInviteRequest(BaseModel):
    token: str
    name: str
    password: str

    @field_validator("password")
    @classmethod
    def validate_accept_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class InviteValidationResponse(BaseModel):
    email: str
    business_name: str
    role: str


# --- Notification schemas ---


class NotificationItem(BaseModel):
    type: str  # "new_lead", "new_conversation", "appointment", "activity"
    title: str
    description: str
    created_at: str | None = None


class NotificationsResponse(BaseModel):
    new_leads_count: int = 0
    new_conversations_count: int = 0
    todays_appointments_count: int = 0
    overdue_action_items_count: int = 0
    total_unread: int = 0
    recent_items: list[NotificationItem] = Field(default_factory=list)
