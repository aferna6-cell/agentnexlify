"""Agent OS tool implementations — shared types for the data plane half.

The engine (``agent-service/src/agent-os/actions/``) owns the tool registry,
the risk model, the approval policy and the executor. Tools whose capability
lives in the engine (reads over the assembled context) execute there. Tools
that need a tenant's credentials — Gmail, and every external integration
after it — cannot: the engine holds no database handle and no OAuth tokens by
design. Those declare ``implementation: "data_plane"`` in the engine registry
and their body lives here, behind the same contract.

The split is deliberate, and it is the security boundary: an LLM can ask for a
tool by id, but the credentials, the recipient resolution and the send itself
happen in the data plane, under the authenticated tenant's scope, only after
the owner has approved the execution row.

Mirrors ``backend/services/os_actions/base.py`` on purpose — same dataclass
shapes, same auto-discovery, same "one module per capability" layout — so
there is one set of conventions to learn.
"""

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ToolContext:
    """Everything one tool execution may read.

    Deliberately narrow: the tenant it runs for, the durable execution row it
    is bound to, and the validated input. No ambient credentials — a tool asks
    its provider module, which resolves tokens for ``client_id`` only.
    """

    db: Any
    client_id: str
    execution_id: str
    tool_id: str
    input: dict
    agent_id: str | None = None
    approved_by: str | None = None


@dataclass
class ToolOutcome:
    """What happened when the tool ran.

    ``status`` is ``succeeded`` or ``failed``. ``result`` is the structured,
    non-sensitive output persisted to ``os_tool_executions.result``;
    ``error`` is JSON-friendly diagnostics. ``effect`` records which port
    performed the side effect and whether it is durable, so provenance is
    always declared by the code that actually did the work.
    """

    status: str
    result: dict | None = None
    error: dict | None = None
    effect: dict | None = None


@dataclass
class VerificationOutcome:
    """An independent check that the effect actually landed.

    Separate from ``ToolOutcome`` because "the API call returned 200" and "the
    thing exists" are different claims. ``state`` is ``passed``, ``failed`` or
    ``not_applicable``; ``unknown`` is expressed as ``failed`` with a detail
    that says so, never as ``passed``.
    """

    state: str
    detail: str


ToolExecute = Callable[[ToolContext], Awaitable[ToolOutcome]]
ToolVerify = Callable[[ToolContext, ToolOutcome], Awaitable[VerificationOutcome]]


@dataclass
class ToolSpec:
    """A data-plane tool's registry entry.

    ``risk_level``, ``mutating`` and ``requires_approval`` are duplicated from
    the engine's declaration on purpose: this plane must never depend on the
    engine having classified an execution correctly, and a parity test asserts
    the two declarations agree (see backend/tests/test_os_tools_send_email.py).
    """

    tool_id: str
    risk_level: int
    mutating: bool
    requires_approval: bool
    input_model: type[BaseModel]
    execute: ToolExecute
    verify: ToolVerify | None = None
    required_connectors: list[str] = field(default_factory=list)
    description: str = ""
