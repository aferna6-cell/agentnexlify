"""Status-bucket counts for the leads sidebar/summary card.

Extracted from `backend/routers/leads.py` to keep the router under the
600-line god-class threshold. Pure aggregation — one DB call, no events,
no writes.
"""

import logging
from typing import Any

from backend.services.tenant_scope import tenant_select

logger = logging.getLogger(__name__)

_STATUS_BUCKETS = ("new", "contacted", "appointment_booked", "closed", "lost")


def compute_lead_summary(db: Any, tenant_id: str) -> dict:
    """Return per-status counts for tenant.

    Raises `RuntimeError("query_failed")` if the DB call blows up.
    Router maps to HTTP 503.
    """
    try:
        result = tenant_select(db, "leads", tenant_id, "status, lead_score").execute()
    except Exception as exc:
        logger.warning("Lead summary query failed for tenant %s", tenant_id, exc_info=True)
        raise RuntimeError("query_failed") from exc

    leads = result.data or []
    summary: dict = {"total": len(leads)}
    for bucket in _STATUS_BUCKETS:
        summary[bucket] = sum(1 for l in leads if l.get("status") == bucket)
    return summary
