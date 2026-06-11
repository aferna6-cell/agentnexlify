"""Agent OS insights — weekly value recap + live suggestions (gaps G2 + G7).

GET /api/v1/os/insights
  {
    "week": {leads_captured, appointments_booked, invoices_sent,
             invoices_sent_total, invoices_paid, invoices_paid_total,
             agent_runs_completed, since},
    "suggestions": [{summary, detail}, ...]
  }

The same numbers feed the Friday digest email; this endpoint powers the
recap card at the top of the Agent OS so the owner sees what their AI
staff was worth without waiting for the email.
"""

import logging

from fastapi import APIRouter, Depends

from backend.dependencies import _get_current_tenant
from backend.models.database import get_service_supabase
from backend.services.os_opportunities import compute_suggestions
from backend.services.weekly_value import compute_weekly_value

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/os", tags=["agent-os"])


@router.get("/insights")
async def get_insights(claims: dict = Depends(_get_current_tenant)):
    client_id = claims["tenant_id"]
    db = get_service_supabase()
    return {
        "week": compute_weekly_value(db, client_id),
        "suggestions": compute_suggestions(db, client_id),
    }
