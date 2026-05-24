from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from backend.models.schemas_leads import ActivityItem, NoteResponse


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
