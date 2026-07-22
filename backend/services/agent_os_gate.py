"""Agent OS suite plan gate (round-3 item 1 - governance + revenue).

The suite surfaces (scheduled tasks, projects, ask-data, MCP, department
instructions) are the $99.99 `agent_os` platform. Until now they were
auth-only, so a $19.99 `chatbot` or lapsed `free` tenant could drive the
full workforce. This dependency returns 402 with an upgrade payload the
dashboard can render as an upsell card.

Plan set: `agent_os` plus every legacy/grandfathered plan still honored on
old contracts (CLAUDE.md "Plan names + prices" - gates include them).
`chatbot` and `free` stay out.

Staged rollout: stage 1 (2026-07-21) gated the six new suite routers;
stage 2 (2026-07-22) widened to the core chat surfaces (os_threads /
os_orchestrate / os_deliverables) once the 402 payload rendered as a real
upsell in the dashboard. Demo tenants carry an allowed plan; inbound
bridges and the signed email-action pages bypass routers entirely.

Fail-open on read errors: a DB blip must not lock paying owners out of
their workforce; the gate only blocks on a positively-known outside plan.
"""

import logging

from fastapi import Depends, HTTPException

from backend.models.database import get_service_supabase
from backend.services.auth_service import get_current_tenant

logger = logging.getLogger(__name__)

AGENT_OS_PLANS = {
    "agent_os",
    # Legacy/grandfathered (still honored on old contracts)
    "growth",
    "autopilot",
    "professional",
    "enterprise",
}

UPGRADE_PATH = "/billing"


async def require_agent_os_access(
    claims: dict = Depends(get_current_tenant),
) -> dict:
    """Dependency: 402 + upgrade payload when the plan lacks the suite."""
    tenant_id = claims.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Unauthenticated")

    plan = None
    try:
        rows = (
            get_service_supabase()
            .table("tenants")
            .select("plan")
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        ).data or []
        if rows:
            plan = str(rows[0].get("plan") or "")
    except Exception:
        logger.warning(
            "agent_os_gate: plan read failed tenant=%s - failing open", tenant_id,
            exc_info=True,
        )
        return claims

    if plan is not None and plan not in AGENT_OS_PLANS:
        raise HTTPException(
            status_code=402,
            detail={
                "error": "plan_upgrade_required",
                "message": (
                    "The AI Workforce suite is part of the Agent OS plan. "
                    "Upgrade to give your business a full AI staff."
                ),
                "required_plan": "agent_os",
                "upgrade_path": UPGRADE_PATH,
            },
        )
    return claims
