from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


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
    insurance_carrier: str | None = None
    insurance_member_id: str | None = None
    insurance_group: str | None = None
    date_of_birth: str | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_LEAD_STAGES:
            raise ValueError(f"status must be one of {VALID_LEAD_STAGES}")
        return v


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


class StageChangeRequest(BaseModel):
    stage: str

    @field_validator("stage")
    @classmethod
    def validate_stage(cls, v: str) -> str:
        if v not in VALID_LEAD_STAGES:
            raise ValueError(f"stage must be one of {VALID_LEAD_STAGES}")
        return v


class LeadStageUpdate(BaseModel):
    stage: str

    @field_validator("stage")
    @classmethod
    def validate_stage_update(cls, v: str) -> str:
        if v not in VALID_LEAD_STAGES:
            raise ValueError(f"stage must be one of {VALID_LEAD_STAGES}")
        return v
