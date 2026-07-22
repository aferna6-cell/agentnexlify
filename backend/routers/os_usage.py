"""Agent OS usage metering — P0.

Reports the current billing cycle's agent-run/message counters and the
flat cap. The UI uses cap_reached to disable new task submission.
"""

import logging

from fastapi import APIRouter, Depends

from backend.dependencies import _get_current_tenant
from backend.services.agent_os_gate import require_agent_os_access
from backend.models.database import get_service_supabase
from backend.services import usage_meter
from backend.services.ai_usage_guard import get_ai_usage_status

logger = logging.getLogger(__name__)

# Stage-3 plan gate (2026-07-22, audit H1): suite surface - agent_os
# plan (+ legacy) only; 402 upsell otherwise.
router = APIRouter(
    prefix="/api/v1/os",
    tags=["agent-os"],
    dependencies=[Depends(require_agent_os_access)],
)


@router.get("/usage")
async def get_usage(claims: dict = Depends(_get_current_tenant)):
    client_id = claims["tenant_id"]
    db = get_service_supabase()
    snapshot = usage_meter.get_usage(db, client_id)
    # percent of the agent-run cap consumed this cycle (0-100, clamped).
    # Powers the in-app upgrade nudge so the UI can decide whether the
    # tenant is near (>=80%) or at the cap without re-deriving the math.
    percent = 0
    if snapshot.cap > 0:
        percent = min(100, round(snapshot.agent_runs * 100 / snapshot.cap))
    return {
        "cycle_start": snapshot.cycle_start,
        "agent_runs": snapshot.agent_runs,
        "messages": snapshot.messages,
        "input_tokens": snapshot.input_tokens,
        "output_tokens": snapshot.output_tokens,
        "cap": snapshot.cap,
        "cap_reached": snapshot.cap_reached,
        # Live plan tier (read from tenants table, never stale JWT claims) so
        # the upgrade nudge can decide whether an upgrade is even available.
        "plan": usage_meter.tenant_plan(db, client_id),
        "percent": percent,
        # AI token spend vs the guard's thresholds (rubric 5.3): owners see
        # how close they are to rate-limiting before a turn is refused.
        "ai_usage": get_ai_usage_status(db, client_id),
    }
