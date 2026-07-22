"""AI Answering Service - call management dashboard endpoints.

List, view, and aggregate call data for the dashboard. The Twilio voice
webhooks (incoming call, AI conversation loop, recording/transcription
pipeline) live in calls_webhooks.py; phone->tenant routing and plan
gating live in services/voice_phone_routing.py (god-file split, audit
2026-07-22 H2). This module mounts the webhook router so registration in
main.py is unchanged.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.models.database import get_service_supabase
from backend.dependencies import _get_current_tenant
from backend.routers import calls_webhooks

# Back-compat re-exports: test_voice_plan_gate.py and older callers import
# these from backend.routers.calls; the definitions moved in the H2 split.
from backend.services.voice_phone_routing import (  # noqa: F401
    _AI_VOICE_PLANS,
    _ai_voice_mode,
    _find_or_create_lead,
    _find_tenant_by_phone,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/calls", tags=["calls"])
router.include_router(calls_webhooks.router)


# ---------------------------------------------------------------------------
# Pydantic models - field names match the `calls` table columns (migration 044)
# ---------------------------------------------------------------------------

class CallOut(BaseModel):
    id: str
    tenant_id: str
    lead_id: str | None = None
    caller_phone: str
    called_number: str | None = None
    direction: str = "inbound"
    duration_seconds: int = 0
    status: str = "completed"
    recording_url: str | None = None
    transcript: list[dict[str, Any]] | None = Field(default_factory=list)
    summary: str | None = None
    sentiment: str | None = None
    action_taken: str | None = None
    twilio_call_sid: str | None = None
    created_at: str | None = None


class CallListResponse(BaseModel):
    calls: list[CallOut]
    total: int
    page: int
    per_page: int


class CallStatsResponse(BaseModel):
    total_calls: int = 0
    missed_calls: int = 0
    avg_duration_seconds: float = 0.0
    calls_today: int = 0
    # G3 Phase 3 metering — minutes used this calendar month vs the included
    # live-AI allowance (included_minutes <= 0 means unmetered).
    minutes_this_month: float = 0.0
    included_minutes: int = 0


# ---------------------------------------------------------------------------
# Dashboard endpoints (authenticated)
# ---------------------------------------------------------------------------


@router.get("/{tenant_id}", response_model=CallListResponse)
async def list_calls(
    tenant_id: str,
    status: str | None = Query(None, description="Filter by call status"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    claims: dict = Depends(_get_current_tenant),
):
    """List calls for a tenant with pagination and optional status filter."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db = get_service_supabase()
    try:
        query = (
            db.table("calls")
            .select("*", count="exact")
            .eq("tenant_id", tenant_id)
        )

        if status:
            query = query.eq("status", status)

        query = query.order("created_at", desc=True)

        offset = (page - 1) * per_page
        query = query.range(offset, offset + per_page - 1)

        result = query.execute()
        total = result.count if result.count is not None else len(result.data or [])

        return CallListResponse(
            calls=result.data or [],
            total=total,
            page=page,
            per_page=per_page,
        )
    except Exception:
        logger.exception("Failed to list calls for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to retrieve calls")


@router.get("/{tenant_id}/stats", response_model=CallStatsResponse)
async def get_call_stats(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Get call statistics for a tenant: total, missed, avg duration, calls today."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db = get_service_supabase()
    stats = CallStatsResponse()

    # Total calls
    try:
        total_result = (
            db.table("calls")
            .select("id", count="exact")
            .eq("tenant_id", tenant_id)
            .execute()
        )
        stats.total_calls = total_result.count if total_result.count is not None else 0
    except Exception:
        logger.warning("Failed to count total calls for tenant %s", tenant_id, exc_info=True)

    # Missed calls (no-answer, busy, failed)
    try:
        for missed_status in ("no-answer", "busy", "failed"):
            missed_result = (
                db.table("calls")
                .select("id", count="exact")
                .eq("tenant_id", tenant_id)
                .eq("status", missed_status)
                .execute()
            )
            count = missed_result.count if missed_result.count is not None else 0
            stats.missed_calls += count
    except Exception:
        logger.warning("Failed to count missed calls for tenant %s", tenant_id, exc_info=True)

    # Average duration (from completed calls with duration > 0)
    try:
        duration_result = (
            db.table("calls")
            .select("duration_seconds")
            .eq("tenant_id", tenant_id)
            .eq("status", "completed")
            .execute()
        )
        durations = [
            r["duration_seconds"]
            for r in (duration_result.data or [])
            if r.get("duration_seconds") and r["duration_seconds"] > 0
        ]
        if durations:
            stats.avg_duration_seconds = round(sum(durations) / len(durations), 1)
    except Exception:
        logger.warning("Failed to compute avg duration for tenant %s", tenant_id, exc_info=True)

    # Calls today
    try:
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        ).isoformat()
        today_result = (
            db.table("calls")
            .select("id", count="exact")
            .eq("tenant_id", tenant_id)
            .gte("created_at", today_start)
            .execute()
        )
        stats.calls_today = today_result.count if today_result.count is not None else 0
    except Exception:
        logger.warning("Failed to count today's calls for tenant %s", tenant_id, exc_info=True)

    # Minutes metering (G3 Phase 3)
    try:
        from backend.services.voice_usage import included_voice_minutes, monthly_voice_seconds

        stats.minutes_this_month = round(monthly_voice_seconds(tenant_id) / 60, 1)
        stats.included_minutes = included_voice_minutes()
    except Exception:
        logger.warning("Failed to compute voice usage for tenant %s", tenant_id, exc_info=True)

    return stats


@router.get("/{tenant_id}/{call_id}", response_model=CallOut)
async def get_call(
    tenant_id: str,
    call_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Get a single call with full details."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db = get_service_supabase()
    try:
        result = (
            db.table("calls")
            .select("*")
            .eq("id", call_id)
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Call not found")
        return result.data[0]
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to get call %s for tenant %s", call_id, tenant_id)
        raise HTTPException(status_code=500, detail="Failed to retrieve call")
