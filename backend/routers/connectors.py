"""Unified connector status — read-side surface over
``backend/services/connector_registry.py``.

Phase 1b of ``plans/nexlify-capabilities-roadmap_plan.md``. Intentionally
NOT registered in ``backend/main.py`` yet — the dashboard "connect card"
that consumes this endpoint is a separate follow-up lane; this router ships
the API surface so that lane, and the in-chat deep-link work, can build
against a stable contract.
"""

import logging

from fastapi import APIRouter, Depends

from backend.dependencies import _get_current_tenant
from backend.models.database import get_service_supabase
from backend.services import connector_registry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/connectors", tags=["connectors"])


@router.get("/status")
async def connectors_status(claims: dict = Depends(_get_current_tenant)):
    """Full connector catalog for the current tenant, each entry annotated
    with its live ``connected`` boolean."""
    tenant_id: str = claims["tenant_id"]

    try:
        db = get_service_supabase()
        status = connector_registry.connection_status(db, tenant_id=tenant_id)
    except Exception:
        logger.exception(
            "connectors_status: connection_status lookup failed tenant_id=%s",
            tenant_id,
        )
        status = {}

    return {
        "connectors": [
            {**entry, "connected": status.get(entry["key"], False)}
            for entry in connector_registry.get_registry()
        ]
    }
