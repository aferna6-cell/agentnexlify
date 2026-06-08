"""Agent OS action registry — auto-discovers every handler module here.

Drop a module in this package that defines a module-level ``SPEC: ActionSpec``
and it registers automatically — no edit to this file or the deliverables
router. Approve a deliverable whose ``action_type`` matches a registered
handler and ``run_action`` runs it as a FastAPI background task; status,
request/response payloads, and any errors are written back to
``os_action_runs``.
"""

import importlib
import logging
import pkgutil

from backend.models.database import get_service_supabase
from backend.services.os_actions.base import (
    ActionContext,
    ActionResult,
    ActionSpec,
    now_iso,
)
from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)

_REGISTRY: dict[str, ActionSpec] = {}
_DISCOVERED = False


def _discover() -> None:
    """Import every action module once and collect its ``SPEC``."""
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
            logger.exception("os_actions: failed to import module %s", info.name)
            continue
        spec = getattr(module, "SPEC", None)
        if isinstance(spec, ActionSpec):
            _REGISTRY[spec.name] = spec
        else:
            logger.warning("os_actions: module %s has no ActionSpec SPEC", info.name)


def all_actions() -> dict[str, ActionSpec]:
    _discover()
    return dict(_REGISTRY)


def get_action(name: str) -> ActionSpec | None:
    _discover()
    return _REGISTRY.get(name)


async def run_action(
    action_run_id: str,
    client_id: str,
    deliverable_id: str,
    action_type: str,
) -> None:
    """FastAPI background task: run one action handler end to end.

    Loads the handler, runs it, and writes status + payloads back to
    ``os_action_runs``. Every failure is caught and recorded as failed.
    Idempotency: the partial unique index on (deliverable_id, action_type)
    WHERE status = 'succeeded' blocks duplicate side effects at DB level.
    """
    try:
        db = get_service_supabase()
        action_runs = tenant_table(db, "os_action_runs", client_id)
    except Exception:
        logger.exception("os action could not open db action_run_id=%s", action_run_id)
        return

    try:
        handler = get_action(action_type)
        if handler is None:
            raise ValueError(f"unknown action '{action_type}'")

        deliv_row = (
            tenant_table(db, "os_agent_runs", client_id)
            .select("*")
            .eq("id", deliverable_id)
            .limit(1)
            .execute()
        )
        if not deliv_row.data:
            raise ValueError(f"deliverable {deliverable_id} not found")
        agent_run = deliv_row.data[0]
        deliverable = agent_run.get("deliverable") or {}

        ctx = ActionContext(
            db=db,
            client_id=client_id,
            deliverable_id=deliverable_id,
            action_run_id=action_run_id,
            action_type=action_type,
            deliverable=deliverable,
            agent_run=agent_run,
        )

        action_runs.update(
            {"status": "running", "started_at": now_iso(), "updated_at": now_iso()}
        ).eq("id", action_run_id).execute()

        result = await handler.run(ctx)

        update = {
            "status": result.status,
            "request_payload": result.request_payload,
            "response_payload": result.response_payload,
            "error_detail": result.error_detail,
            "finished_at": now_iso(),
            "updated_at": now_iso(),
        }
        action_runs.update(update).eq("id", action_run_id).execute()

        if result.status == "succeeded":
            try:
                from backend.services.os_learning import (
                    record_action_outcome_pending,
                )

                await record_action_outcome_pending(
                    db,
                    client_id,
                    action_run_id,
                    action_type,
                    result.request_payload or {},
                )
            except Exception:
                logger.warning(
                    "os action outcome capture failed action_run_id=%s",
                    action_run_id,
                    exc_info=True,
                )
    except Exception as e:
        logger.exception("os action failed action_run_id=%s", action_run_id)
        try:
            action_runs.update(
                {
                    "status": "failed",
                    "error_detail": {"message": str(e)[:500]},
                    "finished_at": now_iso(),
                    "updated_at": now_iso(),
                }
            ).eq("id", action_run_id).execute()
        except Exception:
            logger.exception(
                "os action could not record failure action_run_id=%s", action_run_id
            )


__all__ = [
    "ActionContext",
    "ActionResult",
    "ActionSpec",
    "all_actions",
    "get_action",
    "run_action",
    "now_iso",
]
