"""Agent OS action base types — shared across every handler module.

An action handler runs after the owner approves a deliverable. It executes
the side-effecting call (Google Calendar event, Resend email, GBP post,
CRM contact upsert, etc.) and writes status + payloads to ``os_action_runs``.

Each handler module under ``backend/services/os_actions/`` declares a
module-level ``SPEC: ActionSpec`` and an async ``run`` function. The
package auto-discovers them; the deliverables approve route fires the
matching action via FastAPI BackgroundTasks.
"""

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ActionContext:
    """Inputs for one action run."""

    db: object
    client_id: str
    deliverable_id: str  # os_agent_runs.id of the approved deliverable
    action_run_id: str  # os_action_runs.id for this attempt
    action_type: str
    deliverable: dict  # the approved deliverable JSON
    agent_run: dict  # the full os_agent_runs row (for thread_id, agent_name)


@dataclass
class ActionResult:
    """A handler's outcome.

    ``status`` is one of ``succeeded`` or ``failed``. ``request_payload`` is
    what we sent to the upstream system (minus secrets); ``response_payload``
    is what came back. ``error_detail`` is JSON-friendly diagnostics on
    failure.
    """

    status: str
    request_payload: dict = field(default_factory=dict)
    response_payload: dict | None = None
    error_detail: dict | None = None


ActionRun = Callable[[ActionContext], Awaitable[ActionResult]]


@dataclass
class ActionSpec:
    """A handler's registry entry."""

    name: str  # canonical action_type, e.g. "calendar.event.create"
    worker: str  # which worker produces deliverables for this action
    run: ActionRun
    required_connectors: list[str] = field(default_factory=list)
    description: str = ""
