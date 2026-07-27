"""Checkpointing — how a run survives a process restart.

The runtime writes one checkpoint per superstep boundary. That granularity is
deliberate: state is only ever consistent at a boundary, so a checkpoint can
never capture a half-applied superstep.
"""

import copy
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol

# Terminal statuses stop the loop; RUNNING and AWAITING_INPUT can be resumed.
STATUS_RUNNING = "running"
STATUS_AWAITING_INPUT = "awaiting_input"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_BUDGET_EXHAUSTED = "budget_exhausted"

TERMINAL_STATUSES = frozenset(
    {STATUS_COMPLETED, STATUS_FAILED, STATUS_BUDGET_EXHAUSTED}
)


def new_run_id() -> str:
    return str(uuid.uuid4())


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Checkpoint:
    """A consistent snapshot of a run at a superstep boundary."""

    run_id: str
    graph_name: str
    graph_version: str
    superstep: int
    status: str
    state: dict[str, Any] = field(default_factory=dict)
    # Nodes to execute in the next superstep. Empty means the run is finished.
    frontier: list[str] = field(default_factory=list)
    budget: dict[str, Any] = field(default_factory=dict)
    tenant_id: str | None = None
    error: str | None = None
    # Set when status is awaiting_input: which node interrupted and why.
    interrupt: dict[str, Any] | None = None
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Checkpoint":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in raw.items() if k in known})


@dataclass
class StepRecord:
    """One node execution. The unit of the audit trail and of cost review."""

    run_id: str
    superstep: int
    node: str
    status: str
    kind: str = "task"
    attempts: int = 1
    duration_ms: int = 0
    tokens: int = 0
    updates: dict[str, Any] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    tenant_id: str | None = None
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class Checkpointer(Protocol):
    """Storage for run checkpoints and step records.

    Implementations must tolerate being called with the same checkpoint twice —
    a resumed run re-writes the boundary it resumed from.
    """

    async def save(self, checkpoint: Checkpoint) -> None: ...

    async def load(self, run_id: str) -> Checkpoint | None: ...

    async def record_step(self, step: StepRecord) -> None: ...

    async def history(self, run_id: str) -> list[Checkpoint]: ...


class InMemoryCheckpointer:
    """In-process checkpointer for tests and single-shot runs.

    Deep-copies on the way in and out so a caller mutating returned state
    cannot corrupt stored history — the bug this class exists to not have.
    """

    def __init__(self) -> None:
        self._checkpoints: dict[str, list[Checkpoint]] = {}
        self._steps: dict[str, list[StepRecord]] = {}

    async def save(self, checkpoint: Checkpoint) -> None:
        stored = copy.deepcopy(checkpoint)
        self._checkpoints.setdefault(checkpoint.run_id, []).append(stored)

    async def load(self, run_id: str) -> Checkpoint | None:
        entries = self._checkpoints.get(run_id)
        if not entries:
            return None
        return copy.deepcopy(entries[-1])

    async def record_step(self, step: StepRecord) -> None:
        self._steps.setdefault(step.run_id, []).append(copy.deepcopy(step))

    async def history(self, run_id: str) -> list[Checkpoint]:
        return copy.deepcopy(self._checkpoints.get(run_id, []))

    def steps(self, run_id: str) -> list[StepRecord]:
        """Test/debug helper — not part of the Checkpointer protocol."""
        return copy.deepcopy(self._steps.get(run_id, []))


class NullCheckpointer:
    """Discards everything. For throwaway runs where durability is not wanted."""

    async def save(self, checkpoint: Checkpoint) -> None:
        return None

    async def load(self, run_id: str) -> Checkpoint | None:
        return None

    async def record_step(self, step: StepRecord) -> None:
        return None

    async def history(self, run_id: str) -> list[Checkpoint]:
        return []
