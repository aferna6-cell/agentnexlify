"""Agent OS worker registry — auto-discovers every worker module here.

Drop a module in this package that defines a module-level ``SPEC: WorkerSpec``
and it registers automatically — no edit to this file or the orchestrator. The
orchestrator routes ``delegate`` decisions by worker name; ``run_worker`` runs
one as a FastAPI background task and posts status + thought process +
approval-gated deliverable back to ``os_agent_runs`` / ``os_messages``.
"""

import importlib
import logging
import pkgutil

from backend.models.database import get_service_supabase
from backend.services import usage_meter
from backend.services.os_workers.base import (
    WorkerContext,
    WorkerResult,
    WorkerSpec,
    now_iso,
)
from backend.services.os_workers.tools import WorkerTools
from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)

_REGISTRY: dict[str, WorkerSpec] = {}
_DISCOVERED = False


def _tenant_auto_send_enabled(db, client_id: str) -> bool:
    """Read per-tenant Agent OS auto-send toggle. Defaults to False on error.

    See migration 128_tenants_os_auto_send.sql. When TRUE, worker deliverables
    skip the owner approval gate and start as ``approved`` directly.
    """
    try:
        result = (
            db.table("tenants")
            .select("os_auto_send_enabled")
            .eq("id", client_id)
            .limit(1)
            .execute()
        )
        if result.data:
            return bool(result.data[0].get("os_auto_send_enabled"))
    except Exception:
        logger.warning(
            "os worker could not read auto-send flag client_id=%s",
            client_id,
            exc_info=True,
        )
    return False


def _discover() -> None:
    """Import every worker module once and collect its ``SPEC``."""
    global _DISCOVERED
    if _DISCOVERED:
        return
    _DISCOVERED = True
    package = importlib.import_module(__name__)
    for info in pkgutil.iter_modules(package.__path__):
        if info.name == "base" or info.name.startswith("_"):
            continue
        try:
            module = importlib.import_module(f"{__name__}.{info.name}")
        except Exception:
            logger.exception("os_workers: failed to import module %s", info.name)
            continue
        spec = getattr(module, "SPEC", None)
        if isinstance(spec, WorkerSpec):
            _REGISTRY[spec.name] = spec
        else:
            logger.warning("os_workers: module %s has no WorkerSpec SPEC", info.name)


def all_workers() -> dict[str, WorkerSpec]:
    _discover()
    return dict(_REGISTRY)


def worker_descriptions() -> dict[str, str]:
    """Worker-name -> description map for the orchestrator's routing prompt."""
    return {name: spec.description for name, spec in all_workers().items()}


def get_worker(name: str) -> WorkerSpec | None:
    _discover()
    return _REGISTRY.get(name)


async def run_worker(
    run_id: str,
    client_id: str,
    thread_id: str,
    agent_name: str,
    user_message: str,
    deliverable_title: str,
) -> None:
    """FastAPI background task: run one worker end to end.

    Loads the worker, runs it, and posts status + thought process +
    approval-gated deliverable back to ``os_agent_runs`` / ``os_messages``, then
    meters the run. Every failure is caught and recorded as a failed run.
    """
    try:
        db = get_service_supabase()
        runs = tenant_table(db, "os_agent_runs", client_id)
    except Exception:
        logger.exception("os worker could not open db run_id=%s", run_id)
        return

    try:
        worker = get_worker(agent_name)
        if worker is None:
            raise ValueError(f"unknown worker '{agent_name}'")

        existing = runs.select("thought_process").eq("id", run_id).limit(1).execute()
        thought: list[dict] = []
        if existing.data and existing.data[0].get("thought_process"):
            thought = list(existing.data[0]["thought_process"])

        ctx = WorkerContext(
            db=db,
            client_id=client_id,
            thread_id=thread_id,
            run_id=run_id,
            user_message=user_message,
            deliverable_title=deliverable_title or "Draft",
            thought=thought,
            tools=WorkerTools(db=db, client_id=client_id),
        )
        runs.update({"status": "running", "updated_at": now_iso()}).eq(
            "id", run_id
        ).execute()
        ctx.step("Worker started", f"'{agent_name}' picked up the task.")

        result = await worker.run(ctx)

        deliverable = dict(result.deliverable)
        deliverable.setdefault("title", ctx.deliverable_title)
        deliverable.setdefault("format", "markdown")

        auto_send = _tenant_auto_send_enabled(db, client_id)
        deliverable_status = "approved" if auto_send else "pending_approval"
        if auto_send:
            ctx.step(
                "Auto-send enabled",
                "Tenant has os_auto_send_enabled=TRUE — deliverable marked approved without owner review.",
            )

        update_payload: dict = {
            "status": "succeeded",
            "thought_process": ctx.thought,
            "deliverable": deliverable,
            "deliverable_status": deliverable_status,
            "completed_at": now_iso(),
            "updated_at": now_iso(),
        }
        if result.action_type:
            update_payload["action_type"] = result.action_type

        runs.update(update_payload).eq("id", run_id).execute()

        tenant_table(db, "os_messages", client_id).insert(
            {
                "thread_id": thread_id,
                "role": "agent",
                "content": result.summary,
                "agent_run_id": run_id,
            }
        ).execute()

        usage_meter.record_agent_run(db, client_id)

        if result.memory_writes:
            from backend.services.orchestrator import record_memory_writes

            await record_memory_writes(
                db, client_id, result.memory_writes, source=f"thread:{thread_id}"
            )
    except Exception:
        logger.exception("os worker failed run_id=%s", run_id)
        try:
            runs.update(
                {
                    "status": "failed",
                    "error_detail": "Worker raised an exception.",
                    "completed_at": now_iso(),
                    "updated_at": now_iso(),
                }
            ).eq("id", run_id).execute()
        except Exception:
            logger.exception("os worker could not record failure run_id=%s", run_id)


__all__ = [
    "WorkerContext",
    "WorkerResult",
    "WorkerSpec",
    "WorkerTools",
    "all_workers",
    "worker_descriptions",
    "get_worker",
    "run_worker",
    "now_iso",
]
