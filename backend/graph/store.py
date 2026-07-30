"""Supabase-backed checkpointer — the durable half of :mod:`backend.graph`.

Backs the :class:`~backend.graph.checkpoint.Checkpointer` protocol with the two
tables created by ``migrations/189_graph_runs.sql``:

* ``graph_runs`` — ONE row per run, upserted on ``id`` at every superstep
  boundary. It is the resume point, not a log: current state, current frontier,
  current budget.
* ``graph_run_steps`` — append-only ledger, one row per node execution.

Two deliberate tradeoffs, both load-bearing:

**Writes are best-effort; reads are not.** A checkpoint write that fails is
logged with ``logger.exception`` and swallowed. Durability is a nice-to-have;
the correctness of the run in progress is not, and killing a live agent run
because Supabase hiccuped trades a real outcome for a bookkeeping one. The cost
is honest: a swallowed write means that boundary is not resumable, and the row
still on disk is a *stale* boundary — a resume would replay from further back
and could repeat a side effect. ``load()`` therefore *raises*. Resuming from a
checkpoint you could not read is the one failure that silently corrupts a run,
so it fails loudly instead.

**The Supabase client is synchronous.** The runtime awaits every method here
from the FastAPI event loop, so each blocking call goes through
``run_in_executor`` rather than running inline.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from backend.graph.checkpoint import Checkpoint, StepRecord

logger = logging.getLogger(__name__)

RUNS_TABLE = "graph_runs"
STEPS_TABLE = "graph_run_steps"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SupabaseCheckpointer:
    """Persist graph runs and their step ledger to Supabase.

    ``client`` is optional so production callers get the service-role client
    lazily (matching ``backend/services/retry_worker.py``) while tests inject a
    fake. Resolution is deferred to first use, so constructing a checkpointer
    never requires credentials.
    """

    def __init__(self, client: Any = None) -> None:
        self._client = client

    @property
    def client(self) -> Any:
        if self._client is None:
            from backend.models.database import get_service_supabase

            self._client = get_service_supabase()
        return self._client

    async def _run_blocking(self, fn) -> Any:
        """Execute a blocking Supabase call off the event loop."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, fn)

    # -- writes (best-effort) ------------------------------------------------

    async def save(self, checkpoint: Checkpoint) -> None:
        """Upsert the run row for ``checkpoint``.

        One row per run, keyed on ``run_id`` — a run is *updated* each
        superstep, not appended to. The per-superstep history lives in
        ``graph_run_steps``. That makes re-saving the same boundary (which a
        resumed run always does) idempotent, as the protocol requires.

        ``created_at`` is left to the column default: the dataclass regenerates
        it on every construction, so writing it would push the run's birth
        timestamp forward at every superstep. ``updated_at`` is set here.
        """
        row = {
            "id": checkpoint.run_id,
            "tenant_id": checkpoint.tenant_id,
            "graph_name": checkpoint.graph_name,
            "graph_version": checkpoint.graph_version,
            "status": checkpoint.status,
            "superstep": checkpoint.superstep,
            "state": checkpoint.state or {},
            "frontier": list(checkpoint.frontier or []),
            "budget": checkpoint.budget or {},
            "interrupt": checkpoint.interrupt,
            "error": checkpoint.error,
            "updated_at": _now_iso(),
        }
        try:
            await self._run_blocking(
                lambda: self.client.table(RUNS_TABLE)
                .upsert(row, on_conflict="id")
                .execute()
            )
        except Exception:
            logger.exception(
                "graph.store.save_failed run=%s graph=%s superstep=%s",
                checkpoint.run_id,
                checkpoint.graph_name,
                checkpoint.superstep,
            )

    async def record_step(self, step: StepRecord) -> None:
        """Append one node execution to the ledger.

        ``created_at`` IS written here (unlike ``save``): the ledger is
        append-only, so there is no drift to cause, and the runtime's own
        timestamp preserves execution order within a superstep.
        """
        row = {
            "run_id": step.run_id,
            "tenant_id": step.tenant_id,
            "superstep": step.superstep,
            "node": step.node,
            "kind": step.kind,
            "status": step.status,
            "attempts": step.attempts,
            "duration_ms": step.duration_ms,
            "tokens": step.tokens,
            "updates": step.updates or {},
            "meta": step.meta or {},
            "error": step.error,
            "created_at": step.created_at,
        }
        try:
            await self._run_blocking(
                lambda: self.client.table(STEPS_TABLE).insert(row).execute()
            )
        except Exception:
            logger.exception(
                "graph.store.record_step_failed run=%s node=%s superstep=%s",
                step.run_id,
                step.node,
                step.superstep,
            )

    # -- reads (must not lie) ------------------------------------------------

    async def load(
        self, run_id: str, tenant_id: str | None = None
    ) -> Checkpoint | None:
        """Return the current checkpoint for ``run_id``, or ``None`` if absent.

        Raises on a DB error rather than returning ``None``: "no such run" and
        "could not reach the database" mean opposite things to ``resume()``, and
        conflating them would restart a live run from stale state.

        ``tenant_id`` narrows the query to a single tenant when provided.
        Callers in multi-tenant contexts MUST supply it to prevent cross-tenant
        checkpoint access via the service-role client, which bypasses RLS.
        """

        def _query():
            q = self.client.table(RUNS_TABLE).select("*").eq("id", run_id)
            if tenant_id is not None:
                q = q.eq("tenant_id", tenant_id)
            return q.limit(1).execute()

        response = await self._run_blocking(_query)
        rows = getattr(response, "data", None) or []
        if not rows:
            return None
        return _row_to_checkpoint(rows[0])

    async def history(
        self, run_id: str, tenant_id: str | None = None
    ) -> list[Checkpoint]:
        """Return the run's current checkpoint as a single-element list.

        Deliberately NOT reconstructed from ``graph_run_steps``. Step rows carry
        per-node updates, never a folded state snapshot, so rebuilding the
        intermediate boundaries would mean re-running the reducers — an
        expensive read that produces states the runtime never actually
        checkpointed. Callers wanting per-step detail should read
        ``graph_run_steps`` directly; this method answers "where is this run
        now?". Empty list when the run is unknown.
        """
        checkpoint = await self.load(run_id, tenant_id)
        return [checkpoint] if checkpoint is not None else []


def _row_to_checkpoint(row: dict[str, Any]) -> Checkpoint:
    """Map a ``graph_runs`` row onto a :class:`Checkpoint`.

    ``id`` becomes ``run_id``; jsonb columns are coerced past ``None`` so a
    hand-nulled column can never hand the runtime a non-dict state.
    """
    return Checkpoint(
        run_id=row.get("id"),
        graph_name=row.get("graph_name"),
        graph_version=row.get("graph_version"),
        superstep=row.get("superstep") or 0,
        status=row.get("status"),
        state=row.get("state") or {},
        frontier=list(row.get("frontier") or []),
        budget=row.get("budget") or {},
        tenant_id=row.get("tenant_id"),
        error=row.get("error"),
        interrupt=row.get("interrupt"),
        created_at=row.get("created_at") or _now_iso(),
    )
