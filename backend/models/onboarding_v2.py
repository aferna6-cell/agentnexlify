"""Pydantic models for the V2 onboarding wizard endpoints.

NO from __future__ import annotations — that breaks Pydantic model resolution
in FastAPI and causes 422 errors on every request.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class VerticalPreset(str, Enum):
    plumbing = "plumbing"
    hvac = "hvac"
    cleaning = "cleaning"
    power_washing = "power_washing"
    landscaping = "landscaping"
    electrical = "electrical"


class WizardStartRequest(BaseModel):
    vertical: Optional[VerticalPreset] = None


class WizardStepRequest(BaseModel):
    field_updates: dict


class WizardCompleteResponse(BaseModel):
    ready_to_launch: bool
    widget_api_key: str


class ReadinessCriteria(BaseModel):
    services_count: int = 0
    hours_filled: bool = False
    faqs_count: int = 0
    logo_uploaded: bool = False


class ReadinessResponse(BaseModel):
    criteria: ReadinessCriteria
    ready_to_launch: bool


class IntegrationKeyProvider(str, Enum):
    stripe = "stripe"
    twilio = "twilio"
    resend = "resend"


class SaveIntegrationKeyRequest(BaseModel):
    provider: IntegrationKeyProvider
    api_key: str = Field(min_length=8)
    metadata: Optional[dict] = None


class IntegrationKeyStatus(BaseModel):
    provider: str
    masked_key: str
    health: str  # green / yellow / red
    last_verified_at: Optional[str] = None


class IntegrationKeysResponse(BaseModel):
    providers: list[IntegrationKeyStatus]


class WidgetHealthResponse(BaseModel):
    loaded: bool
    reachable: bool
    origin_allowed: bool
    last_ping_at: Optional[str] = None
    domain: str
