"""Lead-capture diagnostics for tenant health checks.

Extracted from `backend/routers/leads.py` to keep the router under the
600-line god-class threshold. Pure read-only Supabase queries — three
parallel counts (total, last 7 days, last 5 sample) — each wrapped in
try/except so the endpoint never 500s on a partial outage.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.services.tenant_scope import tenant_select

logger = logging.getLogger(__name__)

SAMPLE_LIMIT = 5
RECENT_WINDOW_DAYS = 7


def collect_lead_capture_diagnostics(db: Any, tenant_id: str) -> dict:
    """Return lead-capture health snapshot for a tenant.

    Three independent queries — total count, last-7d count, last-5 sample.
    Each query is isolated so a single failure degrades gracefully:
    failed counts return -1, failed samples return empty.
    """
    total_leads = _count_total(db, tenant_id)
    leads_last_7_days = _count_recent(db, tenant_id)
    last_lead_created_at, sample_lead_ids, has_email_leads = _fetch_sample(
        db, tenant_id
    )

    logger.info(
        "debug_lead_capture: tenant=%s total=%s last_7d=%s last_created=%s",
        tenant_id, total_leads, leads_last_7_days, last_lead_created_at,
    )

    return {
        "total_leads": total_leads,
        "leads_last_7_days": leads_last_7_days,
        "last_lead_created_at": last_lead_created_at,
        "has_email_leads": has_email_leads,
        "sample_lead_ids": sample_lead_ids,
    }


def _count_total(db: Any, tenant_id: str) -> int:
    try:
        result = (
            tenant_select(db, "leads", tenant_id, "id", count="exact")
            .execute()
        )
        return result.count or 0
    except Exception:
        logger.error(
            "debug_lead_capture: total count failed for %s",
            tenant_id, exc_info=True,
        )
        return -1


def _count_recent(db: Any, tenant_id: str) -> int:
    try:
        week_ago = (
            datetime.now(timezone.utc) - timedelta(days=RECENT_WINDOW_DAYS)
        ).isoformat()
        result = (
            tenant_select(db, "leads", tenant_id, "id", count="exact")
            .gte("created_at", week_ago)
            .execute()
        )
        return result.count or 0
    except Exception:
        logger.error(
            "debug_lead_capture: recent count failed for %s",
            tenant_id, exc_info=True,
        )
        return -1


def _fetch_sample(db: Any, tenant_id: str) -> tuple[str | None, list[str], bool]:
    try:
        result = (
            tenant_select(db, "leads", tenant_id, "id, created_at, email, phone")
            .order("created_at", desc=True)
            .limit(SAMPLE_LIMIT)
            .execute()
        )
        leads = result.data or []
        last_created_at = leads[0]["created_at"] if leads else None
        sample_ids = [lead["id"] for lead in leads]
        has_email = any(lead.get("email") for lead in leads)
        return last_created_at, sample_ids, has_email
    except Exception:
        logger.error(
            "debug_lead_capture: sample query failed for %s",
            tenant_id, exc_info=True,
        )
        return None, [], False
