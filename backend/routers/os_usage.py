"""Agent OS usage metering — P0.

Reports the current billing cycle's agent-run/message counters and the
flat cap. The UI uses cap_reached to disable new task submission.
"""

import logging

from fastapi import APIRouter, Depends

from backend.dependencies import _get_current_tenant
from backend.models.database import get_service_supabase
from backend.services import usage_meter
from backend.services.ai_usage_guard import get_ai_usage_status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/os", tags=["agent-os"])


@router.get("/usage")
async def get_usage(claims: dict = Depends(_get_current_tenant)):
    client_id = claims["tenant_id"]
    db = get_service_supabase()
    snapshot = usage_meter.get_usage(db, client_id)
    return {
        "cycle_start": snapshot.cycle_start,
        "agent_runs": snapshot.agent_runs,
        "messages": snapshot.messages,
        "input_tokens": snapshot.input_tokens,
        "output_tokens": snapshot.output_tokens,
        "cap": snapshot.cap,
        "cap_reached": snapshot.cap_reached,
        # AI token spend vs the guard's thresholds (rubric 5.3): owners see
        # how close they are to rate-limiting before a turn is refused.
        "ai_usage": get_ai_usage_status(db, client_id),
    }
