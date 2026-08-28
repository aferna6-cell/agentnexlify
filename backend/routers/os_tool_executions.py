"""Agent OS tool executions — audit reads and the approval pathway.

An execution is one attempt by an agent to use a tool (see
``backend/services/os_tool_executions.py`` and the engine's action layer). Most
run and finish inside the turn that created them; the ones that need a human
decision park at ``pending_approval`` and land here.

Approval is at-most-once. The status moves out of ``pending_approval`` with a
conditional update BEFORE the engine is called, so a double-clicked approve, a
retried request, or two operators clicking at the same moment all result in one
tool invocation. A lost engine response leaves the row ``running`` with the
reason attached rather than guessing — the outcome is genuinely unknown and
retrying could double a real-world side effect.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from backend.dependencies import _get_current_tenant
from backend.models.database import get_service_supabase
from backend.services import agent_os_bridge, agent_sdk_client, os_tool_executions, os_tools
from backend.services.agent_os_gate import require_agent_os_access

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/os",
    tags=["agent-os"],
    dependencies=[Depends(require_agent_os_access)],
)


class RejectToolExecutionRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


def _is_owner(claims: dict) -> bool:
    return (claims.get("role") or "").lower() == "owner"


def _actor(claims: dict) -> str:
    return claims.get("email") or claims.get("sub") or "owner"


def _engine_payload(row: dict) -> dict:
    """The stored row, in the shape the engine's /actions/approve expects."""
    return {
        "id": row["id"],
        "accountId": row["client_id"],
        "toolId": row["tool_id"],
        "input": row.get("input") or {},
        "riskLevel": row.get("risk_level"),
        "mutating": bool(row.get("mutating")),
        "requiresApproval": bool(row.get("requires_approval")),
        "runId": row.get("engine_run_id"),
        "agentId": row.get("agent_id"),
        "policyReason": row.get("policy_reason") or "",
        "createdAt": row.get("created_at"),
        "attempts": row.get("attempts") or 0,
    }


@router.get("/tool-executions")
async def list_tool_executions(
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    claims: dict = Depends(_get_current_tenant),
):
    """Recent tool executions for this tenant — the auditable history."""
    if status and status not in os_tool_executions.STATUSES:
        raise HTTPException(status_code=400, detail=f"Unknown status '{status}'")
    db = get_service_supabase()
    rows = os_tool_executions.list_tool_executions(
        db, claims["tenant_id"], status=status, limit=limit
    )
    return {"count": len(rows), "items": rows}


@router.get("/tool-executions/{execution_id}")
async def get_tool_execution(
    execution_id: str, claims: dict = Depends(_get_current_tenant)
):
    db = get_service_supabase()
    row = os_tool_executions.get_tool_execution(db, claims["tenant_id"], execution_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Tool execution not found")
    return row


async def _run_data_plane_tool(db, client_id: str, claimed: dict, actor: str) -> dict:
    """Execute a data-plane tool (Gmail and every external integration).

    The row was already claimed with a conditional update, so exactly one
    approval reached here. ``run_tool`` re-validates the stored input against
    the tool's own model, executes it under this tenant's credentials, and
    verifies it independently. Execution and verification come back separately
    and are stored on separate columns — "it ran" and "we confirmed it landed"
    are different claims and must stay separately representable.
    """
    ctx = os_tools.ToolContext(
        db=db,
        client_id=client_id,
        execution_id=claimed["id"],
        tool_id=claimed["tool_id"],
        input=claimed.get("input") or {},
        agent_id=claimed.get("agent_id"),
        approved_by=actor,
    )
    outcome, verification = await os_tools.run_tool(ctx)

    if outcome.status == "succeeded" and verification.state == "failed":
        status = "verification_failed"
    elif outcome.status == "succeeded":
        status = "succeeded"
    else:
        status = "failed"

    patch = {
        "status": status,
        "approval_state": "approved",
        "approved_by": actor,
        "approved_at": os_tool_executions._now(),
        "attempts": (claimed.get("attempts") or 0) + 1,
        "result": outcome.result,
        "error": outcome.error,
        "effect": outcome.effect,
        "verification_state": verification.state,
        "verification_detail": verification.detail,
        "verified_at": os_tool_executions._now()
        if verification.state in ("passed", "failed")
        else None,
        "finished_at": os_tool_executions._now(),
        "updated_at": os_tool_executions._now(),
    }
    return os_tool_executions.patch_execution(db, client_id, claimed["id"], patch)


@router.post("/tool-executions/{execution_id}/approve")
async def approve_tool_execution(
    execution_id: str, claims: dict = Depends(_get_current_tenant)
):
    """Approve a parked action and run it — exactly once.

    Owner-only: an approval here is what lets an agent actually change
    something in the real world. Approving an action that is no longer pending
    returns its current state instead of running it again, so a double-clicked
    button, a retried request and two operators approving at the same moment
    all produce exactly one send.
    """
    if not _is_owner(claims):
        raise HTTPException(status_code=403, detail="Owner role required")

    client_id = claims["tenant_id"]
    db = get_service_supabase()

    existing = os_tool_executions.get_tool_execution(db, client_id, execution_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Tool execution not found")

    # The at-most-once gate: a conditional UPDATE out of pending_approval,
    # BEFORE anything external is touched. Losing this race means someone else
    # already approved, and we must not send again.
    claimed = await run_in_threadpool(
        os_tool_executions.claim_for_execution, db, client_id, execution_id
    )
    if claimed is None:
        # Already approved, rejected, running or finished. Idempotent: report
        # where it stands rather than running the tool a second time.
        current = os_tool_executions.get_tool_execution(db, client_id, execution_id)
        return {"execution": current, "already_decided": True}

    # Tools whose capability lives here — anything needing this tenant's
    # credentials — run in this process, never in the engine.
    if os_tools.has_tool(claimed["tool_id"]):
        updated = await _run_data_plane_tool(db, client_id, claimed, _actor(claims))
        return {"execution": updated, "already_decided": False}

    context = await run_in_threadpool(
        agent_os_bridge.assemble_shared_context, db, client_id
    )
    out = await run_in_threadpool(
        agent_sdk_client.approve_action_sync,
        client_id,
        _engine_payload(claimed),
        context,
        approved_by=_actor(claims),
    )

    if out is None or not isinstance(out.get("execution"), dict):
        os_tool_executions.mark_engine_unavailable(
            db,
            client_id,
            execution_id,
            "the agent engine did not respond; the outcome of this action is unknown",
        )
        raise HTTPException(
            status_code=502,
            detail=(
                "The agent engine did not respond. This action was not retried "
                "automatically because its outcome is unknown."
            ),
        )

    execution = out["execution"]
    notes = out.get("customerNotes") or []
    if notes:
        await run_in_threadpool(
            os_tool_executions.apply_customer_notes, db, client_id, notes, [execution]
        )
    updated = await run_in_threadpool(
        os_tool_executions.record_execution_outcome, db, client_id, execution
    )
    return {
        "execution": updated
        or os_tool_executions.get_tool_execution(db, client_id, execution_id),
        "already_decided": False,
    }


@router.post("/tool-executions/{execution_id}/reject")
async def reject_tool_execution(
    execution_id: str,
    req: RejectToolExecutionRequest,
    claims: dict = Depends(_get_current_tenant),
):
    """Reject a parked action so it can never run."""
    if not _is_owner(claims):
        raise HTTPException(status_code=403, detail="Owner role required")

    db = get_service_supabase()
    try:
        row = os_tool_executions.reject_tool_execution(
            db,
            claims["tenant_id"],
            execution_id,
            rejected_by=_actor(claims),
            reason=req.reason,
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="Tool execution not found")
    except os_tool_executions.ToolExecutionStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return row
