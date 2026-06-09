"""Shared action dispatch for approved Agent OS deliverables.

One code path decides whether an approved deliverable fires a side-effecting
action handler, used by BOTH approval surfaces:

1. The owner clicking Approve (``backend/routers/os_deliverables.py``).
2. Tenant-opted auto-send, where the engine marks a draft approved at persist
   time (``backend/services/agent_os_bridge.py`` callers).

Keeping the two on one helper means the idempotency rule (one succeeded
action per (deliverable, action_type)) and the queued ``os_action_runs``
bookkeeping can never drift between human and automatic approval.
"""

import logging

from fastapi import BackgroundTasks

from backend.services.os_actions import get_action, run_action
from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)


async def queue_action_for_run(
    db,
    client_id: str,
    run: dict,
    background: BackgroundTasks | None,
) -> str | None:
    """Queue (or inline-run) the action handler for an approved run.

    ``run`` is the full ``os_agent_runs`` row. Returns the ``os_action_runs``
    id when an action was queued or already succeeded, else None (no
    action_type, unknown handler). With ``background=None`` the handler runs
    inline — for callers already inside a background task (inbound bridges).
    """
    action_type = run.get("action_type")
    if not action_type:
        return None

    run_id = run["id"]
    handler = get_action(action_type)
    if handler is None:
        logger.warning(
            "os_action_dispatch: unknown action_type=%s run_id=%s",
            action_type,
            run_id,
        )
        return None

    existing_succeeded = (
        tenant_table(db, "os_action_runs", client_id)
        .select("id")
        .eq("deliverable_id", run_id)
        .eq("action_type", action_type)
        .eq("status", "succeeded")
        .limit(1)
        .execute()
    )
    if existing_succeeded.data:
        return existing_succeeded.data[0]["id"]

    created = (
        tenant_table(db, "os_action_runs", client_id)
        .insert(
            {
                "client_id": client_id,
                "deliverable_id": run_id,
                "action_type": action_type,
                "status": "queued",
                "request_payload": {},
            }
        )
        .execute()
    )
    if not created.data:
        return None
    action_run_id = created.data[0]["id"]

    if background is not None:
        background.add_task(run_action, action_run_id, client_id, run_id, action_type)
    else:
        await run_action(action_run_id, client_id, run_id, action_type)
    return action_run_id
