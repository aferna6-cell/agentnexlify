"""Widget / integration health endpoint.

WARNING: PEP 563 deferred annotations are incompatible with FastAPI.
Never add 'from __future__ import annotations' to this file.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException

from backend.routers.widget_config import _get_jwt_claims
from backend.services.widget_health import compute_widget_health

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/widget-health", tags=["widget-health"])


@router.get("/{tenant_id}")
def get_widget_health(
    tenant_id: str,
    claims: dict = Depends(_get_jwt_claims),
):
    """Return integration/setup health for the given tenant.

    JWT claim must match the requested tenant_id.
    """
    if claims.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return compute_widget_health(tenant_id)
