"""The executor — a Pregel-style superstep loop over a graph.

Why supersteps rather than a work queue: every node in a superstep sees the
same input state, and all writes land together at the boundary. That buys three
things a queue does not — deterministic parallel merges, a checkpoint that can
never capture a half-applied step, and a resume point that is always
consistent.

    frontier <- successors(START)
    while frontier:
        results  <- await gather(node(state) for node in frontier)
        state    <- reduce(state, results)      # deterministic, node-name order
        save checkpoint
        frontier <- successors(results, evaluated against the new state)
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from backend.graph.budget import RunBudget
from backend.graph.checkpoint import (
    STATUS_AWAITING_INPUT,
    STATUS_BUDGET_EXHAUSTED,
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_RUNNING,
    Checkpoint,
    Checkpointer,
    InMemoryCheckpointer,
    StepRecord,
    new_run_id,
)
from backend.graph.errors import BudgetExhausted, GraphError, Interrupt
from backend.graph.graph import END, START, Graph
from backend.graph.nodes import ON_ERROR_CONTINUE, NodeContext, NodeResult
from backend.graph.state import apply_updates

logger = logging.getLogger(__name__)


@dataclass
class RunResult:
    """The outcome of a run or resume."""

    run_id: str
    status: str
    state: dict[str, Any]
    superstep: int
    budget: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    interrupt: dict[str, Any] | None = None

    @property
    def ok(self) -> bool:
        return self.status == STATUS_COMPLETED

    @property
    def awaiting_input(self) -> bool:
        return self.status == STATUS_AWAITING_INPUT


@dataclass
class _NodeOutcome:
    """Internal per-node result carried between the executor and the driver."""

    node: str
    result: NodeResult | None = None
    error: BaseException | None = None
    interrupt: Interrupt | None = None
    attempts: int = 1
    duration_ms: int = 0


def _normalize_goto(goto: str | list[str] | None) -> list[str] | None:
    if goto is None:
        return None
    return [goto] if isinstance(goto, str) else list(goto)


async def _execute_node(
    graph: Graph,
    node_name: str,
    ctx: NodeContext,
) -> _NodeOutcome:
    """Run one node, honoring its retry, timeout, and error policy.

    Retries live here rather than in ``Node.invoke`` so every attempt is
    counted and lands on the step ledger.
    """
    node = graph.nodes[node_name]
    started = time.monotonic()
    last_error: BaseException | None = None

    for attempt in range(1, node.retries + 2):
        try:
            if node.timeout_seconds is not None:
                result = await asyncio.wait_for(
                    node.invoke(ctx), timeout=node.timeout_seconds
                )
            else:
                result = await node.invoke(ctx)
            return _NodeOutcome(
                node=node_name,
                result=result,
                attempts=attempt,
                duration_ms=int((time.monotonic() - started) * 1000),
            )
        except Interrupt as interrupt:
            # A pause is not a failure — never retried, never swallowed.
            return _NodeOutcome(
                node=node_name,
                interrupt=interrupt,
                attempts=attempt,
                duration_ms=int((time.monotonic() - started) * 1000),
            )
        except BudgetExhausted:
            raise
        except Exception as exc:  # noqa: BLE001 - policy is applied below
            last_error = exc
            if attempt <= node.retries:
                delay = node.retry_backoff_seconds * (2 ** (attempt - 1))
                logger.warning(
                    "graph.node.retry graph=%s node=%s attempt=%d/%d delay=%.2fs error=%s",
                    graph.name,
                    node_name,
                    attempt,
                    node.retries + 1,
                    delay,
                    exc,
                )
                await asyncio.sleep(delay)
                continue
            break

    duration_ms = int((time.monotonic() - started) * 1000)
    attempts = node.retries + 1

    if node.on_error == ON_ERROR_CONTINUE:
        logger.warning(
            "graph.node.continue_on_error graph=%s node=%s error=%s",
            graph.name,
            node_name,
            last_error,
        )
        return _NodeOutcome(
            node=node_name,
            result=NodeResult(meta={"suppressed_error": str(last_error)}),
            error=None,
            attempts=attempts,
            duration_ms=duration_ms,
        )

    recovery = node.error_goto
    if recovery is not None:
        logger.warning(
            "graph.node.error_goto graph=%s node=%s target=%s error=%s",
            graph.name,
            node_name,
            recovery,
            last_error,
        )
        return _NodeOutcome(
            node=node_name,
            result=NodeResult(
                goto=recovery, meta={"recovered_from_error": str(last_error)}
            ),
            error=None,
            attempts=attempts,
            duration_ms=duration_ms,
        )

    return _NodeOutcome(
        node=node_name,
        error=last_error,
        attempts=attempts,
        duration_ms=duration_ms,
    )


async def _drive(
    graph: Graph,
    *,
    run_id: str,
    state: dict[str, Any],
    frontier: list[str],
    superstep: int,
    budget: RunBudget,
    checkpointer: Checkpointer,
    tenant_id: str | None,
    extras: dict[str, Any],
    resume_values: dict[str, Any] | None = None,
    carried_results: list[dict[str, Any]] | None = None,
) -> RunResult:
    """The superstep loop. Shared by :func:`run` and :func:`resume`."""

    async def _checkpoint(
        status: str,
        *,
        error: str | None = None,
        interrupt: dict[str, Any] | None = None,
        current_frontier: list[str] | None = None,
    ) -> None:
        await checkpointer.save(
            Checkpoint(
                run_id=run_id,
                graph_name=graph.name,
                graph_version=graph.version,
                superstep=superstep,
                status=status,
                state=dict(state),
                frontier=list(
                    current_frontier if current_frontier is not None else frontier
                ),
                budget=budget.snapshot(),
                tenant_id=tenant_id,
                error=error,
                interrupt=interrupt,
            )
        )

    def _result(status: str, error: str | None = None, interrupt: dict | None = None):
        return RunResult(
            run_id=run_id,
            status=status,
            state=state,
            superstep=superstep,
            budget=budget.snapshot(),
            error=error,
            interrupt=interrupt,
        )

    while frontier:
        executable = [name for name in frontier if name != END]
        if not executable:
            break

        try:
            budget.check_superstep()
            for name in executable:
                budget.check_node(name)
        except BudgetExhausted as exc:
            logger.warning(
                "graph.budget.exhausted graph=%s run=%s limit=%s",
                graph.name,
                run_id,
                exc.limit,
            )
            await _checkpoint(STATUS_BUDGET_EXHAUSTED, error=str(exc))
            return _result(STATUS_BUDGET_EXHAUSTED, error=str(exc))

        contexts = {
            name: NodeContext(
                state=dict(state),
                node=name,
                superstep=superstep,
                run_id=run_id,
                tenant_id=tenant_id,
                resume_value=(resume_values or {}).get(name),
                extras=extras,
            )
            for name in executable
        }
        for name in executable:
            budget.charge_node(name)

        try:
            outcomes: list[_NodeOutcome] = list(
                await asyncio.gather(
                    *(_execute_node(graph, name, contexts[name]) for name in executable)
                )
            )
        except BudgetExhausted as exc:
            # Raised from inside a node — the LLM adapter charges tokens as it
            # goes and stops the run the moment the allowance is spent.
            await _checkpoint(STATUS_BUDGET_EXHAUSTED, error=str(exc))
            return _result(STATUS_BUDGET_EXHAUSTED, error=str(exc))

        resume_values = None  # a resume value is delivered exactly once

        # Record every attempt on the ledger before deciding the run's fate, so
        # a failed run still has a full audit trail.
        for outcome in outcomes:
            tokens = int((outcome.result.meta.get("tokens", 0) if outcome.result else 0) or 0)
            if tokens:
                budget.charge_tokens(tokens)
            await checkpointer.record_step(
                StepRecord(
                    run_id=run_id,
                    superstep=superstep,
                    node=outcome.node,
                    kind=graph.nodes[outcome.node].kind,
                    status=(
                        "interrupted"
                        if outcome.interrupt
                        else "failed"
                        if outcome.error
                        else "ok"
                    ),
                    attempts=outcome.attempts,
                    duration_ms=outcome.duration_ms,
                    tokens=tokens,
                    updates=outcome.result.updates if outcome.result else {},
                    meta=outcome.result.meta if outcome.result else {},
                    error=str(outcome.error) if outcome.error else None,
                    tenant_id=tenant_id,
                )
            )

        # A failure aborts the whole superstep, discarding its siblings' writes
        # too. All-or-nothing keeps the checkpoint on the last clean boundary,
        # so a resume never starts from a half-applied step.
        failures = [o for o in outcomes if o.error is not None]
        if failures:
            first = failures[0]
            message = f"{type(first.error).__name__}: {first.error}"
            logger.error(
                "graph.run.failed graph=%s run=%s node=%s error=%s",
                graph.name,
                run_id,
                first.node,
                message,
            )
            await _checkpoint(STATUS_FAILED, error=f"node {first.node!r}: {message}")
            return _result(STATUS_FAILED, error=f"node {first.node!r}: {message}")

        interrupted = [o for o in outcomes if o.interrupt is not None]
        if interrupted:
            # A pause is not a loop iteration. Refund the visit so a human gate
            # does not cost two visits per real attempt (one to ask, one to
            # resume). node_runs stays charged — see RunBudget.refund_node_visit.
            for outcome in interrupted:
                budget.refund_node_visit(outcome.node)
            # Carry forward anything banked by an earlier interrupt in this same
            # superstep, otherwise a node that pauses twice loses the sibling
            # results the first pause preserved.
            banked = list(carried_results or [])
            banked += [
                {
                    "node": o.node,
                    "updates": o.result.updates,
                    "goto": _normalize_goto(o.result.goto),
                    "meta": o.result.meta,
                }
                for o in outcomes
                if o.result is not None
            ]
            info = {
                "nodes": [o.node for o in interrupted],
                "reason": interrupted[0].interrupt.reason,
                "payloads": {o.node: o.interrupt.payload for o in interrupted},
                # Banked so resume() re-runs only the node that paused.
                "pending_results": banked,
            }
            await _checkpoint(
                STATUS_AWAITING_INPUT, interrupt=info, current_frontier=executable
            )
            return _result(STATUS_AWAITING_INPUT, interrupt=info)

        # Fold this superstep's writes, including any banked across an interrupt.
        updates: list[tuple[str, dict[str, Any]]] = [
            (entry["node"], entry.get("updates") or {}) for entry in (carried_results or [])
        ]
        updates += [
            (o.node, o.result.updates) for o in outcomes if o.result is not None
        ]
        state = apply_updates(state, updates, graph.schema)

        superstep += 1
        budget.charge_superstep()

        # Successors are computed against the *new* state, so a condition reads
        # what this superstep just wrote.
        routed: list[tuple[str, list[str] | None]] = [
            (entry["node"], entry.get("goto")) for entry in (carried_results or [])
        ]
        routed += [
            (o.node, _normalize_goto(o.result.goto)) for o in outcomes if o.result
        ]
        carried_results = None

        next_frontier: list[str] = []
        for node_name, goto in routed:
            targets = goto if goto is not None else graph.successors(node_name, state)
            for target in targets:
                if target != END and target not in next_frontier:
                    next_frontier.append(target)

        frontier = next_frontier
        await _checkpoint(STATUS_RUNNING if frontier else STATUS_COMPLETED)

    logger.info(
        "graph.run.completed graph=%s run=%s supersteps=%d tokens=%d",
        graph.name,
        run_id,
        budget.supersteps,
        budget.tokens,
    )
    return _result(STATUS_COMPLETED)


async def run(
    graph: Graph,
    inputs: dict[str, Any] | None = None,
    *,
    run_id: str | None = None,
    tenant_id: str | None = None,
    budget: RunBudget | None = None,
    checkpointer: Checkpointer | None = None,
    extras: dict[str, Any] | None = None,
    validate: bool = True,
) -> RunResult:
    """Execute ``graph`` from START until it terminates.

    Never raises for ordinary failure. A failed node, an exhausted budget, and
    a human pause are all statuses on the returned :class:`RunResult`, because
    every one of them leaves partial state worth inspecting. Only a structural
    defect (:class:`GraphValidationError`) raises.
    """
    if validate:
        graph.validate()

    run_id = run_id or new_run_id()
    budget = budget or RunBudget()
    budget.start()
    checkpointer = checkpointer or InMemoryCheckpointer()

    state = graph.schema.initial()
    state.update(inputs or {})

    node_extras = dict(extras or {})
    node_extras.setdefault("budget", budget)
    node_extras.setdefault("graph", graph)

    frontier = [n for n in graph.successors(START, state) if n != END]

    logger.info(
        "graph.run.start graph=%s version=%s run=%s entry=%s",
        graph.name,
        graph.version,
        run_id,
        frontier,
    )

    return await _drive(
        graph,
        run_id=run_id,
        state=state,
        frontier=frontier,
        superstep=0,
        budget=budget,
        checkpointer=checkpointer,
        tenant_id=tenant_id,
        extras=node_extras,
    )


async def resume(
    graph: Graph,
    run_id: str,
    value: Any = None,
    *,
    checkpointer: Checkpointer,
    budget: RunBudget | None = None,
    extras: dict[str, Any] | None = None,
) -> RunResult:
    """Continue a run that stopped at ``awaiting_input``.

    Only the node that interrupted is re-executed — siblings that completed in
    the same superstep had their results banked in the checkpoint, so a human
    pause never causes a duplicate side effect.

    ``budget`` counters are restored from the checkpoint, so a run cannot get a
    fresh allowance by being resumed repeatedly.
    """
    checkpoint = await checkpointer.load(run_id)
    if checkpoint is None:
        raise GraphError(f"no checkpoint found for run {run_id!r}")
    if checkpoint.status != STATUS_AWAITING_INPUT:
        raise GraphError(
            f"run {run_id!r} has status {checkpoint.status!r}; only "
            f"{STATUS_AWAITING_INPUT!r} runs can be resumed"
        )

    info = checkpoint.interrupt or {}
    interrupted_nodes = list(info.get("nodes") or [])
    if not interrupted_nodes:
        raise GraphError(f"run {run_id!r} is awaiting input but names no node")

    budget = budget or RunBudget()
    budget.restore(checkpoint.budget)
    budget.start()

    node_extras = dict(extras or {})
    node_extras.setdefault("budget", budget)
    node_extras.setdefault("graph", graph)

    logger.info(
        "graph.run.resume graph=%s run=%s nodes=%s", graph.name, run_id, interrupted_nodes
    )

    return await _drive(
        graph,
        run_id=run_id,
        state=dict(checkpoint.state),
        frontier=interrupted_nodes,
        superstep=checkpoint.superstep,
        budget=budget,
        checkpointer=checkpointer,
        tenant_id=checkpoint.tenant_id,
        extras=node_extras,
        resume_values={name: value for name in interrupted_nodes},
        carried_results=list(info.get("pending_results") or []),
    )
