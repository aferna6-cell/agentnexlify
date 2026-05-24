from typing import Any

from pydantic import BaseModel, Field, field_validator


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
