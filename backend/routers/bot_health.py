"""Bot-Health evals — dashboard read + admin-secret cron trigger.

GET  /api/v1/bot-health/{tenant_id} — JWT, tenant-scoped. Latest score, or
    {"status": "no_data"} if the tenant has never been scored.
POST /api/v1/bot-health/run — admin-secret protected. Scores every tenant
    with recent chat activity (backend.services.bot_health.score_all_tenants).
    Same auth pattern as backend/routers/appointment_reminders.py
    (X-Api-Secret header, hmac.compare_digest) — not yet cron-wired.
"""

import hmac
import logging

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from backend.config import settings
from backend.dependencies import _get_current_tenant
from backend.models.database import get_service_supabase
from backend.services.bot_health import score_all_tenants
from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/bot-health", tags=["bot-health"])


def _admin_secret() -> str:
    admin_secret = getattr(settings, "admin_api_secret_key", "")
    if isinstance(admin_secret, str) and admin_secret:
        return admin_secret
    api_secret = getattr(settings, "api_secret_key", "")
    return api_secret if isinstance(api_secret, str) else ""


def _verify_admin_secret(x_api_secret: str | None) -> None:
    """Verify caller has the platform admin secret. Raises 401 on failure."""
    admin_secret = _admin_secret()
    if (
        not admin_secret
        or not x_api_secret
        or not hmac.compare_digest(x_api_secret, admin_secret)
    ):
        raise HTTPException(status_code=401, detail="Invalid admin secret")


def _verify_tenant(claims: dict, tenant_id: str) -> None:
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")


class BotHealthScoreResponse(BaseModel):
    status: str = "ok"
    id: str | None = None
    tenant_id: str | None = None
    computed_at: str | None = None
    window_days: int | None = None
    sample_size: int | None = None
    resolution_rate: float | None = None
    hallucination_flag_count: int | None = None
    unresolved_intent_count: int | None = None
    avg_sentiment: float | None = None
    health_score: float | None = None
    details: dict | None = None


class BotHealthRunResponse(BaseModel):
    scored: int
    skipped: int


@router.get("/{tenant_id}", response_model=BotHealthScoreResponse)
async def get_latest_bot_health(
    tenant_id: str, claims: dict = Depends(_get_current_tenant)
):
    """Latest bot_health_scores row for this tenant, or status=no_data."""
    _verify_tenant(claims, tenant_id)
    db = get_service_supabase()
    try:
        result = (
            tenant_table(db, "bot_health_scores", tenant_id)
            .select("*")
            .order("computed_at", desc=True)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception(
            "get_latest_bot_health: query failed for tenant %s", tenant_id
        )
        raise HTTPException(status_code=500, detail="Failed to load bot health score")

    rows = result.data or []
    if not rows:
        return BotHealthScoreResponse(status="no_data")

    return BotHealthScoreResponse(status="ok", **rows[0])


@router.post("/run", response_model=BotHealthRunResponse)
async def run_bot_health_scoring(x_api_secret: str | None = Header(None)):
    """Score every tenant with recent chat activity. Admin-secret protected."""
    _verify_admin_secret(x_api_secret)
    try:
        counts = await score_all_tenants()
    except Exception:
        logger.exception("run_bot_health_scoring: score_all_tenants failed")
        raise HTTPException(status_code=500, detail="Failed to run bot health scoring")
    return BotHealthRunResponse(**counts)
