"""Agent OS worker base types — shared across every worker module.

A worker is a registered module under ``backend/services/os_workers/``. Each
declares a module-level ``SPEC: WorkerSpec`` and an async ``run`` function. The
package auto-discovers them; the orchestrator routes a ``delegate`` decision to
one by name. See ``__init__.py`` for the registry and the ``run_worker``
background-task harness.
"""

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from backend.services.tenant_scope import tenant_table

if TYPE_CHECKING:
    from backend.services.os_workers.tools import WorkerTools

logger = logging.getLogger(__name__)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class WorkerContext:
    """Inputs plus a live progress channel for one worker run."""

    db: object
    client_id: str
    thread_id: str
    run_id: str
    user_message: str
    deliverable_title: str
    thought: list[dict] = field(default_factory=list)
    tools: "WorkerTools | None" = None

    def step(self, label: str, detail: str = "") -> None:
        """Append a progress step and persist the thought process to the run."""
        self.thought.append(
            {
                "step": len(self.thought) + 1,
                "label": label,
                "status": "done",
                "detail": detail,
                "at": now_iso(),
            }
        )
        try:
            tenant_table(self.db, "os_agent_runs", self.client_id).update(
                {"thought_process": self.thought, "updated_at": now_iso()}
            ).eq("id", self.run_id).execute()
        except Exception:
            logger.warning(
                "worker step persist failed run_id=%s", self.run_id, exc_info=True
            )


@dataclass
class WorkerResult:
    """A worker's output — an approval-gated deliverable plus a chat summary.

    ``deliverable`` is a dict with ``title``, ``format`` and ``body`` keys.
    ``run_worker`` fills ``title``/``format`` defaults if a worker omits them.

    ``action_type`` — when set, ``run_worker`` writes it to ``os_agent_runs``
    so ``approve_deliverable`` can fire the matching Group B action handler
    registered in ``backend/services/os_actions/``. Workers without a side
    effect (e.g. ``generalist``) leave it None.
    """

    deliverable: dict
    summary: str
    memory_writes: list[dict] = field(default_factory=list)
    action_type: str | None = None


WorkerRun = Callable[[WorkerContext], Awaitable[WorkerResult]]


@dataclass
class WorkerSpec:
    """A worker's registry entry. ``description`` is shown to the orchestrator."""

    name: str
    description: str
    run: WorkerRun
