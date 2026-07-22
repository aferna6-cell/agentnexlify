"""Per-run trace viewer endpoint (enterprise-audit item 1).

GET /api/v1/os/agent-runs/{run_id}/trace assembles everything already stored
about one agent run into a single owner-readable timeline: what the agent
saw (thread messages), decided (routing decisions + thought process), and
did (deliverable, action runs and their outcomes) — plus the model calls
behind it (token counts only; no dollar figures on customer surfaces).
"""

import logging

from fastapi import APIRouter, Depends, HTTPException

from backend.dependencies import _get_current_tenant
from backend.services.agent_os_gate import require_agent_os_access
from backend.models.database import get_service_supabase
from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)

# Stage-3 plan gate (2026-07-22, audit H1): suite surface - agent_os
# plan (+ legacy) only; 402 upsell otherwise.
router = APIRouter(
    prefix="/api/v1/os",
    tags=["agent-os"],
    dependencies=[Depends(require_agent_os_access)],
)

_LIMIT = 50


def _rows(db, client_id: str, table: str, column: str, value: str, select: str):
    try:
        return (
            tenant_table(db, table, client_id)
            .select(select)
            .eq(column, value)
            .limit(_LIMIT)
            .execute()
        ).data or []
    except Exception:
        logger.warning(
            "os_run_trace: %s read failed run-linked value=%s", table, value,
            exc_info=True,
        )
        return []


@router.get("/agent-runs/{run_id}/trace")
async def get_run_trace(run_id: str, claims: dict = Depends(_get_current_tenant)):
    client_id = claims["tenant_id"]
    db = get_service_supabase()

    run_rows = (
        tenant_table(db, "os_agent_runs", client_id)
        .select("*")
        .eq("id", run_id)
        .limit(1)
        .execute()
    ).data or []
    if not run_rows:
        raise HTTPException(status_code=404, detail="Agent run not found")
    run = run_rows[0]

    model_calls = _rows(
        db,
        client_id,
        "os_model_call_log",
        "run_id",
        run_id,
        "purpose, model, input_tokens, output_tokens, ok, error, created_at",
    )
    return {
        "run": run,
        "routing_decisions": _rows(
            db,
            client_id,
            "os_routing_decision",
            "run_id",
            run_id,
            "ask, classifier, decision, chosen_agent, confidence, alternates, "
            "accepted, changed_to, created_at",
        ),
        # Token counts only — cost_usd intentionally not selected (same
        # policy as ai_usage_guard.get_ai_usage_status: no dollar figures on
        # customer-facing surfaces).
        "model_calls": model_calls,
        "action_runs": _rows(
            db,
            client_id,
            "os_action_runs",
            "deliverable_id",
            run_id,
            "action_type, status, result, error_detail, created_at, updated_at",
        ),
        "messages": _rows(
            db,
            client_id,
            "os_messages",
            "agent_run_id",
            run_id,
            "role, content, created_at",
        ),
    }
