"""Pricing page A/B experiment (launch rubric 9.3).

Deterministic variant assignment for the public marketing pricing section plus
a tiny event sink. Anonymous by design: visitor_id is a first-party cookie
UUID generated client-side — no PII ever stored or logged.

Experiment: ``pricing_page_cta_2026_06`` — control ("Start Free") vs
variant_b ("Try It Free — 2-Minute Setup"). Resolve via
``ops/evals``-style SQL on pricing_ab_events (view → cta_click conversion
per variant).
"""

import hashlib
import logging
import re

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from backend.limiter import limiter
from backend.models.database import get_service_supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/public/pricing-experiment", tags=["public"])

EXPERIMENT = "pricing_page_cta_2026_06"
VARIANTS = ("control", "variant_b")
_ALLOWED_EVENTS = {"view", "cta_click"}
_ALLOWED_PLANS = {"free", "growth", "autopilot", "professional", "enterprise"}
_VISITOR_RE = re.compile(r"^[A-Za-z0-9-]{8,64}$")


def assign_variant(visitor_id: str) -> str:
    """Deterministic 50/50 split: same visitor always gets the same variant."""
    digest = hashlib.sha256(f"{EXPERIMENT}:{visitor_id}".encode()).digest()
    return VARIANTS[digest[0] % 2]


class PricingEventRequest(BaseModel):
    visitor_id: str = Field(..., min_length=8, max_length=64)
    event: str
    plan: str | None = None

    @field_validator("visitor_id")
    @classmethod
    def _visitor_shape(cls, v: str) -> str:
        if not _VISITOR_RE.match(v):
            raise ValueError("visitor_id must be 8-64 chars of [A-Za-z0-9-]")
        return v

    @field_validator("event")
    @classmethod
    def _event_allowed(cls, v: str) -> str:
        if v not in _ALLOWED_EVENTS:
            raise ValueError(f"event must be one of {sorted(_ALLOWED_EVENTS)}")
        return v

    @field_validator("plan")
    @classmethod
    def _plan_allowed(cls, v: str | None) -> str | None:
        if v is not None and v not in _ALLOWED_PLANS:
            raise ValueError(f"plan must be one of {sorted(_ALLOWED_PLANS)}")
        return v


@router.get("")
@limiter.limit("30/minute")
async def get_variant(request: Request, visitor_id: str):
    """Return the deterministic variant for this visitor."""
    if not _VISITOR_RE.match(visitor_id or ""):
        raise HTTPException(status_code=422, detail="Invalid visitor_id")
    return {"experiment": EXPERIMENT, "variant": assign_variant(visitor_id)}


@router.post("/event", status_code=202)
@limiter.limit("30/minute")
async def record_event(request: Request, payload: PricingEventRequest):
    """Record a view / cta_click event. Fault-tolerant: a DB error is logged
    and swallowed — analytics must never break the marketing page."""
    variant = assign_variant(payload.visitor_id)
    try:
        db = get_service_supabase()
        db.table("pricing_ab_events").insert(
            {
                "visitor_id": payload.visitor_id,
                "variant": variant,
                "event": payload.event,
                "plan": payload.plan,
            }
        ).execute()
    except Exception:
        logger.warning("pricing_experiment: event insert failed", exc_info=True)
        return {"recorded": False}
    return {"recorded": True}
