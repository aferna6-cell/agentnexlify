from datetime import datetime
from typing import Any

from pydantic import BaseModel, field_validator


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
