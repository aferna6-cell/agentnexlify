"""Checkpointing — how a run survives a process restart.

The runtime writes one checkpoint per superstep boundary. That granularity is
deliberate: state is only ever consistent at a boundary, so a checkpoint can
never capture a half-applied superstep.
"""

import copy
import json
import os
import tempfile
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
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


CURRENT_FILE = "current.json"
HISTORY_FILE = "history.jsonl"
STEPS_FILE = "steps.jsonl"


class FileCheckpointer:
    """JSON files on disk — durability across processes with zero infrastructure.

    Exists for the split-process loop: ``run_loop start`` and ``run_loop resume``
    are separate CLI invocations, so :class:`InMemoryCheckpointer` loses the run
    the moment the first process exits, and
    :class:`~backend.graph.store.SupabaseCheckpointer` needs migration 189
    applied. A directory of JSON files needs neither a second process nor a
    schema.

    One directory per run under ``root``::

        <root>/<run_id>/current.json    latest checkpoint  — what load() reads
        <root>/<run_id>/history.jsonl   one line per save  — what history() reads
        <root>/<run_id>/steps.jsonl     one line per node execution

    Two files rather than one because they answer different questions and need
    opposite write semantics. ``current.json`` is *overwritten*, which is what
    makes re-saving a boundary — something a resumed run always does — idempotent
    as the protocol requires. ``history.jsonl`` only ever *grows*, so the audit
    trail keeps every boundary the run passed through, re-saved duplicates
    included.

    ``current.json`` is written to a temp file in the same directory and then
    ``os.replace``d onto the target. The rename is atomic within a filesystem,
    so a resume started while a save is in flight reads either the whole
    previous checkpoint or the whole new one. Writing in place would let a
    crashed or interleaved writer leave truncated JSON for the next resume to
    parse, and a resume from a half-written boundary is exactly the corruption
    this class must not have.

    I/O runs inline rather than through ``run_in_executor`` (which
    ``SupabaseCheckpointer`` needs): these are kilobyte-scale writes to a local
    file, so the executor round-trip would cost more than the write it defers.
    """

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def _run_dir(self, run_id: str) -> Path:
        """Resolve the directory for ``run_id``, rejecting anything but a name.

        ``run_id`` arrives from the caller, and a value like ``"../other"``
        would place a run's files outside ``root`` — reading or clobbering a
        neighbouring run. Path separators and the traversal names are refused
        outright rather than sanitized, so a bad id fails where it is passed in.
        """
        if (
            not run_id
            or run_id in {".", ".."}
            or os.sep in run_id
            or (os.altsep and os.altsep in run_id)
        ):
            raise ValueError(f"run_id must be a single path segment, got {run_id!r}")
        return self.root / run_id

    def _prepared_run_dir(self, run_id: str) -> Path:
        """Run dir, created on demand — a read-only run leaves no directory."""
        run_dir = self._run_dir(run_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    async def save(self, checkpoint: Checkpoint) -> None:
        run_dir = self._prepared_run_dir(checkpoint.run_id)
        line = json.dumps(checkpoint.to_dict(), sort_keys=True)
        _write_atomic(run_dir / CURRENT_FILE, line + "\n")
        _append_line(run_dir / HISTORY_FILE, line)

    async def load(self, run_id: str) -> Checkpoint | None:
        """Return the latest checkpoint, or ``None`` when the run is unknown.

        A missing directory or missing ``current.json`` is ``None``; unreadable
        or malformed content *raises*. Same reasoning as
        ``SupabaseCheckpointer.load``: "no such run" and "could not read it"
        mean opposite things to ``resume()``, and collapsing them would let a
        live run restart from scratch and repeat every side effect it already
        performed.
        """
        path = self._run_dir(run_id) / CURRENT_FILE
        if not path.is_file():
            return None
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError(
                f"{path} does not hold a checkpoint object (got {type(raw).__name__})"
            )
        return Checkpoint.from_dict(raw)

    async def record_step(self, step: StepRecord) -> None:
        run_dir = self._prepared_run_dir(step.run_id)
        _append_line(run_dir / STEPS_FILE, json.dumps(step.to_dict(), sort_keys=True))

    async def history(self, run_id: str) -> list[Checkpoint]:
        """Every checkpoint ever saved for ``run_id``, in save order.

        Unlike ``SupabaseCheckpointer.history``, this is the real sequence of
        boundaries rather than just the current one — the log is already on
        disk, so there is nothing to reconstruct.
        """
        path = self._run_dir(run_id) / HISTORY_FILE
        if not path.is_file():
            return []
        checkpoints: list[Checkpoint] = []
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    checkpoints.append(Checkpoint.from_dict(json.loads(line)))
        return checkpoints


def _write_atomic(path: Path, payload: str) -> None:
    """Replace ``path`` with ``payload`` in one step, never leaving it partial.

    The temp file is created in the target's own directory so ``os.replace``
    stays within a single filesystem, where it is atomic. ``fsync`` before the
    rename is what makes the durability real rather than page-cache deep: after
    a crash the file is the old checkpoint or the new one, not a truncated mix.
    """
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise


def _append_line(path: Path, payload: str) -> None:
    """Append one JSON line. Append mode keeps concurrent writers from
    truncating each other's records the way ``"w"`` would."""
    with path.open("a", encoding="utf-8") as handle:
        handle.write(payload + "\n")


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
