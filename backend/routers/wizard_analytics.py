"""Wizard drop-off tracking — lightweight analytics for onboarding funnel."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.models.database import get_supabase
from backend.routers.auth import _get_current_tenant

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/wizard", tags=["wizard"])


class WizardEvent(BaseModel):
    step: int = Field(..., ge=1, le=6)
    action: str = Field(..., pattern="^(enter|complete|skip|abandon)$")


def _verify_tenant(claims: dict, tenant_id: str) -> None:
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")


@router.post("/{tenant_id}/event")
async def log_wizard_event(
    tenant_id: str,
    event: WizardEvent,
    claims: dict = Depends(_get_current_tenant),
):
    """Log a wizard step event for drop-off tracking."""
    _verify_tenant(claims, tenant_id)

    try:
        db = get_supabase()
        db.table("wizard_events").insert({
            "tenant_id": tenant_id,
            "step": event.step,
            "action": event.action,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception:
        logger.warning("Failed to log wizard event for tenant %s", tenant_id, exc_info=True)
        # Non-fatal -- don't block the user's onboarding flow
    return {"ok": True}


@router.get("/{tenant_id}/stats")
async def get_wizard_stats(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Get wizard completion funnel stats."""
    _verify_tenant(claims, tenant_id)

    try:
        db = get_supabase()
        result = (
            db.table("wizard_events")
            .select("step, action")
            .eq("tenant_id", tenant_id)
            .execute()
        )
        rows = result.data or []

        funnel: dict[int, dict[str, int]] = {}
        for row in rows:
            step = row["step"]
            action = row["action"]
            if step not in funnel:
                funnel[step] = {"enter": 0, "complete": 0, "skip": 0, "abandon": 0}
            if action in funnel[step]:
                funnel[step][action] += 1

        return {"funnel": funnel, "total_events": len(rows)}
    except Exception:
        logger.warning("Failed to fetch wizard stats for tenant %s", tenant_id, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch wizard stats")
