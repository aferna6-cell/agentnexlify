"""Shared Pydantic models + helpers for bids router modules.

Extracted 2026-05-24 alongside bids.py god-class split (Rule 9).
"""

import logging

from fastapi import HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class BidItemModel(BaseModel):
    description: str = Field(..., max_length=500)
    quantity: float = Field(1.0, ge=0)
    unit: str = Field("each", max_length=50)
    unit_price: float = Field(0.0, ge=0)
    total: float = Field(0.0, ge=0)


class BidCreate(BaseModel):
    title: str = Field(..., max_length=300)
    description: str | None = Field(None, max_length=5000)
    items_json: list[BidItemModel] = Field(default_factory=list)
    terms: str | None = Field(None, max_length=5000)
    timeline: str | None = Field(None, max_length=1000)
    warranty: str | None = Field(None, max_length=2000)
    lead_id: str | None = None


class BidUpdate(BaseModel):
    title: str | None = Field(None, max_length=300)
    description: str | None = Field(None, max_length=5000)
    items_json: list[BidItemModel] | None = None
    terms: str | None = Field(None, max_length=5000)
    timeline: str | None = Field(None, max_length=1000)
    warranty: str | None = Field(None, max_length=2000)
    lead_id: str | None = None


class BidStatusUpdate(BaseModel):
    status: str = Field(
        ..., pattern="^(draft|sent|viewed|accepted|rejected|expired)$"
    )


class BidTemplateCreate(BaseModel):
    name: str = Field(..., max_length=200)
    description: str | None = Field(None, max_length=2000)
    default_items: list[BidItemModel] = Field(default_factory=list)


class AIBidGenerateRequest(BaseModel):
    job_description: str = Field(..., max_length=3000)


def _verify_tenant(claims: dict, tenant_id: str) -> None:
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")
