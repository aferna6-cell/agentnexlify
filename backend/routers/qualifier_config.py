"""Per-tenant AI lead-qualifier settings (migration 134).

Owner-facing controls for the AI lead qualifier
(`backend/services/lead_qualification.py`):

    qualifier_enabled     — kill switch; pause AI qualification without
                            dropping the plan.
    qualifier_min_intent  — only spend on the AI qualifier when the cheap
                            rule-based lead_score (0-10) clears this gate.

Both columns live on the `tenants` table. Reads are resilient to the
columns not existing yet (safe to deploy before/with migration 134):
a missing-column error falls back to the safe defaults
``(enabled=True, min_intent=0)`` that match pre-134 behavior.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.dependencies import _get_current_tenant, require_role
from backend.models.database import get_service_supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/qualifier", tags=["qualifier"])

_DEFAULT_ENABLED = True
_DEFAULT_MIN_INTENT = 0


class QualifierSettings(BaseModel):
    qualifier_enabled: bool = _DEFAULT_ENABLED
    qualifier_min_intent: int = Field(default=_DEFAULT_MIN_INTENT, ge=0, le=10)


def _verify_tenant(claims: dict, tenant_id: str) -> None:
    if claims.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")


def _read_settings(db, tenant_id: str) -> QualifierSettings:
    """Read qualifier settings, falling back to defaults pre-migration."""
    try:
        res = (
            db.table("tenants")
            .select("qualifier_enabled, qualifier_min_intent")
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:  # noqa: BLE001 — columns may not exist pre-134
        logger.info(
            "qualifier_config: settings unavailable for tenant %s (%s); defaults",
            tenant_id,
            exc,
        )
        return QualifierSettings()

    row = res.data[0] if res.data else {}
    enabled = row.get("qualifier_enabled")
    raw_min = row.get("qualifier_min_intent") or _DEFAULT_MIN_INTENT
    try:
        min_intent = max(0, min(10, int(raw_min)))
    except (TypeError, ValueError):
        min_intent = _DEFAULT_MIN_INTENT
    return QualifierSettings(
        qualifier_enabled=_DEFAULT_ENABLED if enabled is None else bool(enabled),
        qualifier_min_intent=min_intent,
    )


@router.get("/{tenant_id}")
async def get_qualifier_settings(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Return the tenant's AI qualifier settings."""
    _verify_tenant(claims, tenant_id)
    db = get_service_supabase()
    return _read_settings(db, tenant_id).model_dump()


@router.put("/{tenant_id}")
async def update_qualifier_settings(
    tenant_id: str,
    req: QualifierSettings,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Update the tenant's AI qualifier kill switch + cost threshold."""
    _verify_tenant(claims, tenant_id)
    db = get_service_supabase()

    try:
        result = (
            db.table("tenants")
            .update(
                {
                    "qualifier_enabled": req.qualifier_enabled,
                    "qualifier_min_intent": req.qualifier_min_intent,
                }
            )
            .eq("id", tenant_id)
            .execute()
        )
    except Exception as exc:  # noqa: BLE001 — columns missing => migration not applied
        logger.warning(
            "qualifier_config: update failed for tenant %s (%s)", tenant_id, exc
        )
        raise HTTPException(
            status_code=503,
            detail="Qualifier settings are not available yet. Try again shortly.",
        ) from exc

    if not result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return _read_settings(db, tenant_id).model_dump()
