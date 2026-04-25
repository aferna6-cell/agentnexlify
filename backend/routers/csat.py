"""CSAT/NPS satisfaction survey endpoints.

Auto-sends satisfaction surveys after conversations. Tracks customer ratings.
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from backend.limiter import limiter
from backend.models.database import get_service_supabase
from backend.dependencies import _get_current_tenant

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/csat", tags=["csat"])


def _verify_tenant(claims: dict, tenant_id: str) -> None:
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")


# --- Public survey submission (no auth) ---


class SurveySubmit(BaseModel):
    token: str
    rating: int = Field(..., ge=1, le=5)
    feedback: str | None = None


@router.post("/submit")
@limiter.limit("30/minute")
async def submit_survey(req: SurveySubmit, request: Request):
    """Public endpoint — customer submits their CSAT rating."""
    db = get_service_supabase()

    # Decode token: format is {tenant_id}:{session_id}
    parts = req.token.split(":", 1)
    if len(parts) != 2:
        raise HTTPException(status_code=400, detail="Invalid survey token")

    tenant_id, session_id = parts

    # Check for duplicate submission
    try:
        existing = (
            db.table("csat_responses")
            .select("id", count="exact")
            .eq("tenant_id", tenant_id)
            .eq("session_id", session_id)
            .limit(1)
            .execute()
        )
        if existing.count and existing.count > 0:
            return {"success": True, "message": "Thanks! You already submitted a rating."}
    except Exception:
        logger.warning("CSAT duplicate check failed", exc_info=True)

    # Find the lead for this session
    lead_id = None
    try:
        conv = (
            db.table("conversations")
            .select("lead_id")
            .eq("client_id", tenant_id)
            .eq("session_id", session_id)
            .limit(1)
            .execute()
        )
        if conv.data:
            lead_id = conv.data[0].get("lead_id")
    except Exception:
        logger.warning("CSAT: failed to look up lead_id for session %s", session_id, exc_info=True)

    # Store the rating
    try:
        db.table("csat_responses").insert({
            "tenant_id": tenant_id,
            "session_id": session_id,
            "lead_id": lead_id,
            "rating": req.rating,
            "feedback": req.feedback,
            "channel": "email",
        }).execute()
    except Exception:
        logger.exception("Failed to store CSAT response")
        raise HTTPException(status_code=500, detail="Failed to save rating")

    return {"success": True, "message": "Thanks for your feedback!"}


# --- Dashboard endpoints (authenticated) ---


@router.get("/{tenant_id}/stats")
async def csat_stats(
    tenant_id: str,
    period: str = Query("30d", pattern="^(7d|30d|90d)$"),
    claims: dict = Depends(_get_current_tenant),
):
    """CSAT dashboard stats: avg rating, count, distribution, trend."""
    _verify_tenant(claims, tenant_id)

    days = {"7d": 7, "30d": 30, "90d": 90}[period]
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    db = get_service_supabase()
    try:
        result = (
            db.table("csat_responses")
            .select("rating, created_at, feedback")
            .eq("tenant_id", tenant_id)
            .gte("created_at", since)
            .order("created_at", desc=True)
            .limit(500)
            .execute()
        )
    except Exception:
        logger.warning("CSAT stats query failed for %s", tenant_id, exc_info=True)
        return {"avg_rating": 0, "total": 0, "distribution": {}, "nps": 0}

    responses = result.data or []
    if not responses:
        return {"avg_rating": 0, "total": 0, "distribution": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}, "nps": 0}

    total = len(responses)
    avg = round(sum(r["rating"] for r in responses) / total, 1)

    # Distribution
    dist = defaultdict(int)
    for r in responses:
        dist[r["rating"]] += 1

    # NPS-style: (promoters - detractors) / total * 100
    promoters = sum(1 for r in responses if r["rating"] >= 4)
    detractors = sum(1 for r in responses if r["rating"] <= 2)
    nps = round((promoters - detractors) / total * 100) if total > 0 else 0

    # Daily trend
    daily = defaultdict(list)
    for r in responses:
        date = r["created_at"][:10]
        daily[date].append(r["rating"])
    trend = [{"date": d, "avg": round(sum(ratings) / len(ratings), 1), "count": len(ratings)}
             for d, ratings in sorted(daily.items())]

    return {
        "avg_rating": avg,
        "total": total,
        "distribution": {i: dist.get(i, 0) for i in range(1, 6)},
        "nps": nps,
        "trend": trend,
        "recent_feedback": [r for r in responses[:10] if r.get("feedback")],
    }


@router.get("/{tenant_id}/responses")
async def list_csat_responses(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """List all CSAT responses."""
    _verify_tenant(claims, tenant_id)

    db = get_service_supabase()
    result = (
        db.table("csat_responses")
        .select("*")
        .eq("tenant_id", tenant_id)
        .order("created_at", desc=True)
        .limit(100)
        .execute()
    )
    return {"responses": result.data or []}
