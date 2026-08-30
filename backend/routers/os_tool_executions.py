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

from backend.dependencies import _get_current_tenant, block_demo_role
from backend.models.database import get_service_supabase
from backend.services import (
    agent_os_bridge,
    agent_sdk_client,
    os_calendar_crm,
    os_tool_executions,
    os_tools,
)
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
    owner = _is_owner(claims)
    items = [
        os_tool_executions.present_tool_execution(row, owner=owner) for row in rows
    ]
    return {"count": len(items), "items": items}


@router.get("/tool-executions/{execution_id}")
async def get_tool_execution(
    execution_id: str, claims: dict = Depends(_get_current_tenant)
):
    db = get_service_supabase()
    row = os_tool_executions.get_tool_execution(db, claims["tenant_id"], execution_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Tool execution not found")
    return os_tool_executions.present_tool_execution(row, owner=_is_owner(claims))


@router.post("/tool-executions/{execution_id}/approve")
async def approve_tool_execution(
    execution_id: str,
    claims: dict = Depends(_get_current_tenant),
    _: None = Depends(block_demo_role),
):
    """Approve a parked action and run it — exactly once.

    Owner-only: an approval here is what lets an agent actually change something.
    Approving an action that is no longer pending returns its current state
    instead of running it again, so repeated calls are safe.
    """
    if not _is_owner(claims):
        raise HTTPException(status_code=403, detail="Owner role required")

    client_id = claims["tenant_id"]
    db = get_service_supabase()

    existing = os_tool_executions.get_tool_execution(db, client_id, execution_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Tool execution not found")

    # Schema check THEN claim THEN execute. A Zod-pass / Python-fail email
    # must not consume the only approval claim.
    _row, invalid = os_tool_executions.validate_before_claim(
        db, client_id, execution_id
    )
    if invalid == "invalid_email":
        raise HTTPException(
            status_code=400,
            detail="recipient is not a valid email address",
        )

    if (existing.get("tool_id") or "") == os_tools.SEND_EMAIL_TOOL_ID:
        refused = os_tools.refuse_send_email(
            agent_id=existing.get("agent_id"),
            tool_id=existing.get("tool_id"),
        )
        if refused:
            raise HTTPException(status_code=403, detail=refused)

    if (existing.get("tool_id") or "") in os_calendar_crm.CALENDAR_L2_TOOL_IDS:
        refused = os_calendar_crm.refuse_calendar_tool(
            tool_id=existing.get("tool_id")
        )
        if refused:
            raise HTTPException(status_code=403, detail=refused)

    claimed = await run_in_threadpool(
        os_tool_executions.claim_for_execution,
        db,
        client_id,
        execution_id,
        _actor(claims),
    )
    if claimed is None:
        # Already approved, rejected, running or finished. Idempotent: report
        # where it stands rather than running the tool a second time.
        current = os_tool_executions.get_tool_execution(db, client_id, execution_id)
        return {"execution": current, "already_decided": True}

    if (claimed.get("tool_id") or "") == os_tools.SEND_EMAIL_TOOL_ID:
        ctx = os_tools.ToolContext(
            db=db,
            client_id=client_id,
            execution_id=execution_id,
            tool_id=claimed["tool_id"],
            input=claimed.get("input") or {},
            agent_id=claimed.get("agent_id"),
            approved_by=_actor(claims),
            port=os_tools.production_send_email_port(client_id, db),
        )
        outcome = await os_tools.run_tool(ctx)
        return {
            "execution": os_tool_executions.get_tool_execution(
                db, client_id, execution_id
            ),
            "already_decided": False,
            "outcome": outcome,
        }

    # Calendar L2: claim-gated data plane (booking/Google). Never Collecting.
    if (claimed.get("tool_id") or "") in os_calendar_crm.CALENDAR_L2_TOOL_IDS:
        outcome = await run_in_threadpool(
            os_calendar_crm.run_calendar_l2, db, client_id, claimed
        )
        if outcome.get("refused"):
            os_tool_executions.record_execution_outcome(
                db,
                client_id,
                {
                    "id": execution_id,
                    "status": "failed",
                    "error": {
                        "code": "calendar_refused",
                        "message": outcome.get("reason") or "refused",
                    },
                    "verificationState": "failed",
                },
            )
        elif outcome.get("unknown"):
            os_tool_executions.mark_engine_unavailable(
                db,
                client_id,
                execution_id,
                outcome.get("reason")
                or "calendar provider outcome unknown; not retried",
            )
        elif outcome.get("executed"):
            result = outcome.get("result") or {}
            os_tool_executions.record_execution_outcome(
                db,
                client_id,
                {
                    "id": execution_id,
                    "status": "succeeded",
                    "result": {
                        "eventId": result.get("id") or result.get("event_id"),
                        "googleEventId": result.get("google_event_id"),
                        "detail": outcome.get("reason"),
                        "verified": bool(outcome.get("verified")),
                    },
                    "verificationState": (
                        "passed" if outcome.get("verified") else "pending"
                    ),
                },
            )
        else:
            os_tool_executions.record_execution_outcome(
                db,
                client_id,
                {
                    "id": execution_id,
                    "status": "verification_failed",
                    "error": {
                        "code": "calendar_verify_failed",
                        "message": outcome.get("reason") or "verification failed",
                    },
                    "verificationState": "failed",
                },
            )
        return {
            "execution": os_tool_executions.get_tool_execution(
                db, client_id, execution_id
            ),
            "already_decided": False,
            "outcome": outcome,
        }

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
    customers = out.get("customers") or []
    if customers:
        await run_in_threadpool(
            os_calendar_crm.apply_crm_mutations, db, client_id, customers, [execution]
        )
    calendar_events = out.get("calendarEvents") or []
    if calendar_events:
        await run_in_threadpool(
            os_calendar_crm.apply_calendar_mutations,
            db,
            client_id,
            calendar_events,
            [execution],
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
    _: None = Depends(block_demo_role),
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
