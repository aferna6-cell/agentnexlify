"""Stranded-run sweeper — recovery for runs a crash left in ``running``.

Issue #605, and it started as a real incident: a container restart killed a
run mid-``verify``. The checkpoint said ``running``, ``resume`` refused it
(there was no interrupt to resume into), ``start`` made a new run instead of
adopting it, and the corpse became permanent. Every crash adds one; nothing
reports them; ``running`` slowly stops meaning "in flight".

The design rule that makes this safe to automate: **the sweeper never
executes a node.** It reads checkpoints, decides staleness, and writes a
terminal status with the reason — that is all. Recovery that re-ran the
frontier would have to know which nodes touch the world (``open_pr`` opened
a PR the instant before the crash?), and getting that wrong double-fires a
side effect. Instead each node carries an explicit re-enterability marking in
:mod:`~scripts.autonomy.loop_graph`, and the sweeper only *reports* whether a
fresh run may safely redo the dead run's frontier. Redoing is a decision for
the next cycle, made by policy, not by the janitor.

Staleness comes from file mtimes, not the checkpoint's ``created_at``: the
checkpointer touches ``current.json`` at every superstep boundary and
``steps.jsonl`` at every node completion, so the newest mtime in the run
directory is the last time the run provably did anything. A run quiet longer
than the threshold with status still ``running`` has no process behind it —
the widest legitimate quiet gap is ``verify``'s ~2-minute gate, far under the
one-hour default.
"""

import asyncio
from dataclasses import dataclass
from pathlib import Path
import time

from backend.graph.checkpoint import (
    STATUS_FAILED,
    STATUS_RUNNING,
    Checkpoint,
    FileCheckpointer,
)
from scripts.autonomy.loop_graph import REENTERABLE_NODES

# A run must be quiet this long before it counts as stranded. Generous on
# purpose: sweeping a live run corrupts real work, while a corpse lingering an
# extra hour costs nothing.
DEFAULT_STALE_AFTER_SECONDS = 3600


@dataclass(frozen=True)
class StrandedRun:
    """One dead run: what it was doing, how long it has been quiet.

    ``safe_to_retry`` is guidance for the *next* run, not permission for the
    sweeper — it is true only when every frontier node is marked re-enterable,
    so an empty frontier (which a ``running`` status should never have, but a
    corrupted crash could) conservatively reads as safe, and any
    non-re-enterable node anywhere in the frontier makes the whole run unsafe.
    """

    run_id: str
    frontier: list[str]
    age_seconds: float
    safe_to_retry: bool
    superstep: int = 0


def _last_activity(run_dir: Path) -> float:
    """Newest mtime under the run directory — the run's last provable sign of life."""
    stamps = [p.stat().st_mtime for p in run_dir.iterdir() if p.is_file()]
    return max(stamps) if stamps else run_dir.stat().st_mtime


def _load(store: FileCheckpointer, run_id: str) -> Checkpoint | None:
    return asyncio.run(store.load(run_id))


def find_stranded(
    root: str | Path,
    *,
    stale_after_seconds: float = DEFAULT_STALE_AFTER_SECONDS,
    now: float | None = None,
) -> list[StrandedRun]:
    """Every run stuck in ``running`` with no sign of life past the threshold.

    Discovers by scanning the state directory, so no ids need to be known —
    that gap is half of #605. Terminal runs are history and ``awaiting_input``
    runs are live handoffs (a run parked on a human gate for a week is the
    interrupt mechanism working); only ``running`` can be a corpse.
    """
    root = Path(root)
    if not root.is_dir():
        return []
    moment = time.time() if now is None else now
    store = FileCheckpointer(root)

    stranded: list[StrandedRun] = []
    for run_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        checkpoint = _load(store, run_dir.name)
        if checkpoint is None or checkpoint.status != STATUS_RUNNING:
            continue
        age = moment - _last_activity(run_dir)
        if age < stale_after_seconds:
            continue
        frontier = list(checkpoint.frontier)
        stranded.append(
            StrandedRun(
                run_id=checkpoint.run_id,
                frontier=frontier,
                age_seconds=age,
                safe_to_retry=all(node in REENTERABLE_NODES for node in frontier),
                superstep=checkpoint.superstep,
            )
        )
    return stranded


def sweep(
    root: str | Path,
    *,
    stale_after_seconds: float = DEFAULT_STALE_AFTER_SECONDS,
    now: float | None = None,
    dry_run: bool = False,
) -> list[StrandedRun]:
    """Resolve every stranded run to ``failed``, reason recorded. Runs nothing.

    Writes go through the checkpointer's own ``save`` so the terminal boundary
    is atomic and lands in ``history.jsonl`` like every boundary before it —
    the audit trail shows the sweep instead of ending mid-flight.
    """
    stranded = find_stranded(
        root, stale_after_seconds=stale_after_seconds, now=now
    )
    if dry_run:
        return stranded

    store = FileCheckpointer(Path(root))
    for run in stranded:
        checkpoint = _load(store, run.run_id)
        if checkpoint is None or checkpoint.status != STATUS_RUNNING:
            continue  # resolved by someone else between find and write
        checkpoint.status = STATUS_FAILED
        checkpoint.error = (
            f"swept: stranded in 'running' at frontier {list(run.frontier)} "
            f"with no activity for {int(run.age_seconds)}s — the driving "
            f"process died mid-superstep. "
            + (
                "Frontier is re-enterable; a fresh run may redo this work."
                if run.safe_to_retry
                else "Frontier has external side effects; check GitHub for a "
                "half-completed handoff before redoing anything."
            )
        )
        asyncio.run(store.save(checkpoint))
    return stranded
