"""Pydantic schemas for the email-sequence router.

Extracted from ``backend/routers/email_sequences.py`` so request/response shapes
live next to the service layer rather than inside the HTTP module.
"""

from pydantic import BaseModel

__all__ = [
    "StepCreate",
    "StepUpdate",
    "SequenceCreate",
    "SequenceUpdate",
    "EnrollRequest",
]


class StepCreate(BaseModel):
    step_order: int
    delay_days: int = 0
    delay_hours: int = 0
    subject: str
    body: str
    email_type: str = "email"
    is_active: bool = True


class StepUpdate(BaseModel):
    step_order: int | None = None
    delay_days: int | None = None
    delay_hours: int | None = None
    subject: str | None = None
    body: str | None = None
    email_type: str | None = None
    is_active: bool | None = None


class SequenceCreate(BaseModel):
    name: str
    trigger_type: str = "lead_captured"
    trigger_config: dict = {}
    is_active: bool = True
    steps: list[StepCreate] = []


class SequenceUpdate(BaseModel):
    name: str | None = None
    trigger_type: str | None = None
    trigger_config: dict | None = None
    is_active: bool | None = None
    steps: list[StepCreate] | None = None  # if provided, replaces all steps


class EnrollRequest(BaseModel):
    lead_id: str
