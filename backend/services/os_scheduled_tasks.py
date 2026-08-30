"""Recurring Agent OS tasks (suite item 1 — autonomous agents).

Owner-defined prompts that fire on an every-N-days cadence and run through
the EXACT same engine path as a typed ask (`os_thread_runner.process_user_turn`)
— so routing, per-department instructions, approvals, the never-auto-send
set, and the outbound guard all apply unchanged. The scheduler only decides
WHEN the ask happens; trust controls stay where they already live.

`run_due_tasks` is invoked from the 5-minute tier of main._automation_loop
(single-worker lease already held by the caller).
"""

import logging
from datetime import datetime, timedelta, timezone

from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)

_DUE_BATCH_CAP = 10
MAX_PROMPT_LEN = 1000
MIN_INTERVAL_DAYS = 1
MAX_INTERVAL_DAYS = 90


def _now() -> datetime:
    return datetime.now(timezone.utc)


def clamp_interval(days) -> int:
    try:
        days = int(days)
    except (TypeError, ValueError):
        return 7
    return max(MIN_INTERVAL_DAYS, min(MAX_INTERVAL_DAYS, days))


async def run_task(db, task: dict) -> bool:
    """Run one due task through the engine turn path. True on success."""
    from backend.services.os_thread_runner import process_user_turn

    client_id = task["client_id"]
    prompt = (task.get("prompt") or "").strip()[:MAX_PROMPT_LEN]
    if not prompt:
        return False
    thread = (
        tenant_table(db, "os_threads", client_id)
        .insert({"title": f"Scheduled: {prompt[:60]}"})
        .execute()
    ).data[0]
    message = (
        tenant_table(db, "os_messages", client_id)
        .insert({"thread_id": thread["id"], "role": "user", "content": prompt})
        .execute()
    ).data[0]
    await process_user_turn(
        db,
        client_id,
        thread["id"],
        message,
        None,
        force_agent_id=task.get("department") or None,
        request_origin="system",
    )
    return True


async def run_due_tasks(db) -> int:
    """Run every enabled task whose next_run_at has passed. Returns count run.

    Each task advances its next_run_at BEFORE the engine call so a crash
    mid-run cannot cause a rapid-fire retry loop; failures wait for the next
    cadence window rather than hammering the engine.
    """
    now = _now()
    try:
        due = (
            db.table("os_scheduled_tasks")
            .select("*")
            .eq("enabled", True)
            .lte("next_run_at", now.isoformat())
            .limit(_DUE_BATCH_CAP)
            .execute()
        ).data or []
    except Exception:
        logger.warning("os_scheduled_tasks: due query failed", exc_info=True)
        return 0

    ran = 0
    for task in due:
        interval = clamp_interval(task.get("interval_days"))
        try:
            db.table("os_scheduled_tasks").update(
                {
                    "next_run_at": (now + timedelta(days=interval)).isoformat(),
                    "last_run_at": now.isoformat(),
                    "updated_at": now.isoformat(),
                }
            ).eq("id", task["id"]).execute()
            if await run_task(db, task):
                ran += 1
        except Exception:
            logger.warning(
                "os_scheduled_tasks: run failed task=%s client=%s",
                task.get("id"),
                task.get("client_id"),
                exc_info=True,
            )
    return ran
