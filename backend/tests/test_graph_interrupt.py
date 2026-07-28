"""Interrupt and resume tests for backend.graph.runtime.

The guarantee under test is *banked results*: when one node pauses for human
input, the siblings that already finished in that superstep are not re-executed
on resume, and their updates still land in final state. Without it, a human
pause would duplicate every side effect its superstep already performed.
"""

import pytest

from backend.graph.budget import RunBudget
from backend.graph.checkpoint import (
    STATUS_AWAITING_INPUT,
    STATUS_COMPLETED,
    InMemoryCheckpointer,
)
from backend.graph.errors import GraphError, Interrupt
from backend.graph.graph import Graph
from backend.graph.runtime import resume, run


def _cp() -> InMemoryCheckpointer:
    return InMemoryCheckpointer()


def _gated_graph(pause_on=(None,)):
    """entry -> {gate, sibling} -> done -> END.

    ``gate`` pauses whenever its resume value is in ``pause_on``. ``sibling``
    counts its own executions so a test can prove it never ran twice.
    """
    calls = {"sibling": 0, "gate": 0, "done": 0}
    graph = Graph("interruptible")
    graph.declare("log", "append", default=[])

    async def gate(ctx):
        calls["gate"] += 1
        if ctx.resume_value in pause_on:
            raise Interrupt("needs_human_approval", {"question": "approve?"})
        return {"value": ctx.resume_value, "log": f"gate:{ctx.resume_value}"}

    async def sibling(ctx):
        calls["sibling"] += 1
        return {"sibling_ran": True, "log": "sibling"}

    async def done(ctx):
        calls["done"] += 1
        return {"done": True, "log": "done"}

    graph.add_node("gate", gate, kind="human")
    graph.add_node("sibling", sibling)
    graph.add_node("done", done)
    graph.set_entry("gate", "sibling")
    graph.add_edge("gate", "done")
    graph.add_edge("sibling", "done")
    graph.set_finish("done")
    return graph, calls


# ---------------------------------------------------------------------------
# pausing
# ---------------------------------------------------------------------------


async def test_interrupt_pauses_the_run_and_names_the_node_and_reason():
    graph, calls = _gated_graph()
    checkpointer = _cp()

    result = await run(graph, checkpointer=checkpointer)

    assert result.status == STATUS_AWAITING_INPUT
    assert result.awaiting_input is True
    assert result.ok is False
    assert result.interrupt["nodes"] == ["gate"]
    assert result.interrupt["reason"] == "needs_human_approval"
    assert result.interrupt["payloads"] == {"gate": {"question": "approve?"}}
    assert calls == {"gate": 1, "sibling": 1, "done": 0}


async def test_interrupt_is_not_retried():
    """A pause is control flow, not a failure — the retry budget stays unspent."""
    graph = Graph("no-retry-on-interrupt")
    calls = {"n": 0}

    async def gate(ctx):
        calls["n"] += 1
        raise Interrupt("wait")

    graph.add_node("gate", gate, retries=3, retry_backoff_seconds=0)
    graph.set_entry("gate").set_finish("gate")

    checkpointer = _cp()
    result = await run(graph, checkpointer=checkpointer)

    assert result.status == STATUS_AWAITING_INPUT
    assert calls["n"] == 1
    steps = checkpointer.steps(result.run_id)
    assert steps[0].status == "interrupted"
    assert steps[0].attempts == 1


async def test_interrupt_checkpoint_banks_only_the_finished_siblings():
    graph, _ = _gated_graph()
    checkpointer = _cp()

    result = await run(graph, checkpointer=checkpointer)

    checkpoint = await checkpointer.load(result.run_id)
    assert checkpoint.status == STATUS_AWAITING_INPUT
    assert checkpoint.frontier == ["gate", "sibling"]

    banked = checkpoint.interrupt["pending_results"]
    assert [entry["node"] for entry in banked] == ["sibling"]
    assert banked[0]["updates"]["sibling_ran"] is True

    # The interrupt lands before the superstep's writes are folded, so stored
    # state is still the pre-superstep snapshot.
    assert "sibling_ran" not in checkpoint.state


async def test_state_is_unchanged_while_awaiting_input():
    graph, _ = _gated_graph()
    result = await run(graph, {"seed": 1}, checkpointer=_cp())

    assert result.state == {"seed": 1, "log": []}


# ---------------------------------------------------------------------------
# resuming — the banked-results guarantee
# ---------------------------------------------------------------------------


async def test_resume_delivers_the_value_and_completes_the_run():
    graph, calls = _gated_graph()
    checkpointer = _cp()

    paused = await run(graph, checkpointer=checkpointer)
    resumed = await resume(graph, paused.run_id, "approved", checkpointer=checkpointer)

    assert resumed.status == STATUS_COMPLETED
    assert resumed.run_id == paused.run_id
    assert resumed.state["value"] == "approved"
    assert resumed.state["done"] is True
    assert calls["done"] == 1


async def test_resume_does_not_re_execute_a_finished_sibling():
    """The core banked-results guarantee: no duplicate side effects on resume."""
    graph, calls = _gated_graph()
    checkpointer = _cp()

    paused = await run(graph, checkpointer=checkpointer)
    assert calls["sibling"] == 1

    resumed = await resume(graph, paused.run_id, "approved", checkpointer=checkpointer)

    assert calls["sibling"] == 1, "sibling must not run again on resume"
    assert calls["gate"] == 2, "only the interrupting node re-executes"
    # …and the banked updates still reach final state.
    assert resumed.state["sibling_ran"] is True


async def test_resume_folds_banked_and_fresh_writes_in_node_name_order():
    graph, _ = _gated_graph()
    checkpointer = _cp()

    paused = await run(graph, checkpointer=checkpointer)
    resumed = await resume(graph, paused.run_id, "approved", checkpointer=checkpointer)

    # 'gate' sorts before 'sibling' regardless of which one was banked.
    assert resumed.state["log"] == ["gate:approved", "sibling", "done"]


async def test_resume_only_puts_the_interrupted_node_on_the_frontier():
    graph, _ = _gated_graph()
    checkpointer = _cp()

    paused = await run(graph, checkpointer=checkpointer)
    resumed = await resume(graph, paused.run_id, "approved", checkpointer=checkpointer)

    steps = checkpointer.steps(resumed.run_id)
    by_node = {}
    for step in steps:
        by_node.setdefault(step.node, []).append(step)

    assert len(by_node["gate"]) == 2  # once interrupted, once resumed
    assert len(by_node["sibling"]) == 1
    assert len(by_node["done"]) == 1
    assert by_node["gate"][0].status == "interrupted"
    assert by_node["gate"][1].status == "ok"


async def test_resume_value_is_delivered_exactly_once():
    """A second superstep must not see the resume value again."""
    graph = Graph("once-only")
    seen = []

    async def gate(ctx):
        seen.append(("gate", ctx.resume_value))
        if ctx.resume_value is None:
            raise Interrupt("wait")
        return {"value": ctx.resume_value}

    async def after(ctx):
        seen.append(("after", ctx.resume_value))
        return {"after": True}

    graph.add_node("gate", gate)
    graph.add_node("after", after)
    graph.set_entry("gate")
    graph.add_edge("gate", "after")
    graph.set_finish("after")

    checkpointer = _cp()
    paused = await run(graph, checkpointer=checkpointer)
    resumed = await resume(graph, paused.run_id, "v", checkpointer=checkpointer)

    assert resumed.status == STATUS_COMPLETED
    assert seen == [("gate", None), ("gate", "v"), ("after", None)]


# ---------------------------------------------------------------------------
# double interrupt — banked results must survive more than one pause
# ---------------------------------------------------------------------------


async def test_banked_results_survive_a_second_interrupt():
    """Regression: a node that pauses twice used to drop the sibling results
    banked by the first pause, so those updates vanished from final state."""
    graph, calls = _gated_graph(pause_on=(None, "bad"))
    checkpointer = _cp()

    first = await run(graph, checkpointer=checkpointer)
    assert first.status == STATUS_AWAITING_INPUT

    second = await resume(graph, first.run_id, "bad", checkpointer=checkpointer)
    assert second.status == STATUS_AWAITING_INPUT

    final = await resume(graph, first.run_id, "good", checkpointer=checkpointer)

    assert final.status == STATUS_COMPLETED
    assert final.state["sibling_ran"] is True, "banked result survived both pauses"
    assert calls["sibling"] == 1, "sibling never re-executed"
    assert final.state["value"] == "good"
    assert final.state["log"] == ["gate:good", "sibling", "done"]


async def test_second_interrupt_rebanks_the_original_sibling_results():
    graph, _ = _gated_graph(pause_on=(None, "bad"))
    checkpointer = _cp()

    first = await run(graph, checkpointer=checkpointer)
    await resume(graph, first.run_id, "bad", checkpointer=checkpointer)

    checkpoint = await checkpointer.load(first.run_id)
    assert checkpoint.status == STATUS_AWAITING_INPUT
    banked = checkpoint.interrupt["pending_results"]
    assert [entry["node"] for entry in banked] == ["sibling"]


# ---------------------------------------------------------------------------
# resume error cases
# ---------------------------------------------------------------------------


async def test_resume_rejects_an_unknown_run_id():
    graph, _ = _gated_graph()
    with pytest.raises(GraphError) as exc:
        await resume(graph, "no-such-run", "x", checkpointer=_cp())
    assert "no checkpoint found" in str(exc.value)
    assert "no-such-run" in str(exc.value)


async def test_resume_rejects_a_run_that_is_not_awaiting_input():
    graph = Graph("plain")
    graph.add_node("a", lambda ctx: {"ok": True})
    graph.set_entry("a").set_finish("a")

    checkpointer = _cp()
    finished = await run(graph, checkpointer=checkpointer)
    assert finished.status == STATUS_COMPLETED

    with pytest.raises(GraphError) as exc:
        await resume(graph, finished.run_id, "x", checkpointer=checkpointer)
    message = str(exc.value)
    assert finished.run_id in message
    assert "completed" in message
    assert "awaiting_input" in message


async def test_resume_rejects_an_awaiting_checkpoint_naming_no_node():
    graph, _ = _gated_graph()
    checkpointer = _cp()
    paused = await run(graph, checkpointer=checkpointer)

    corrupted = await checkpointer.load(paused.run_id)
    corrupted.interrupt = {"nodes": [], "reason": "?"}
    await checkpointer.save(corrupted)

    with pytest.raises(GraphError) as exc:
        await resume(graph, paused.run_id, "x", checkpointer=checkpointer)
    assert "names no node" in str(exc.value)


# ---------------------------------------------------------------------------
# budget continuity across resume
# ---------------------------------------------------------------------------


async def test_budget_counters_carry_across_resume_instead_of_resetting():
    graph, _ = _gated_graph()
    checkpointer = _cp()

    paused = await run(graph, checkpointer=checkpointer, budget=RunBudget())
    # gate's visit is refunded when it pauses — pausing is not a loop iteration
    # — but its node_run stays charged, so both nodes are still counted as run.
    assert paused.budget["node_runs"] == 2
    assert paused.budget["visits"] == {"sibling": 1}

    fresh_budget = RunBudget()
    resumed = await resume(
        graph, paused.run_id, "approved", checkpointer=checkpointer, budget=fresh_budget
    )

    # gate ran a second time and done ran once, on top of the restored counters.
    assert resumed.budget["node_runs"] == 4
    assert resumed.budget["visits"] == {"gate": 1, "sibling": 1, "done": 1}
    assert fresh_budget.node_runs == 4


async def test_repeated_resumes_cannot_buy_a_fresh_allowance():
    """Resuming a forever-pausing node must never be free.

    Visits are refunded on pause, so the guarantee rides on ``node_runs``:
    it grows monotonically with every execution including the ones that ended
    in an Interrupt, which is what keeps ``max_node_runs`` a real ceiling on a
    caller that resumes in a loop.
    """
    graph, _ = _gated_graph(pause_on=(None, "bad"))
    checkpointer = _cp()

    first = await run(graph, checkpointer=checkpointer)
    assert first.budget["node_runs"] == 2

    second = await resume(graph, first.run_id, "bad", checkpointer=checkpointer)
    assert second.status == STATUS_AWAITING_INPUT
    assert second.budget["node_runs"] == 3
    # Still refunded — gate has paused twice and looped zero times.
    assert "gate" not in second.budget["visits"]

    third = await resume(graph, first.run_id, "good", checkpointer=checkpointer)
    assert third.budget["node_runs"] == 5
    assert third.budget["visits"]["gate"] == 1


async def test_a_pausing_node_cannot_exhaust_its_own_visit_cap():
    """The regression that motivated the refund.

    A human gate with a retry policy of N attempts used to burn 2N visits —
    one to ask, one to resume — so a loop bounded at N attempts tripped its
    visit cap at N/2 and escalated early.
    """
    graph, _ = _gated_graph(pause_on=(None, "again", "again2"))
    checkpointer = _cp()
    budget = RunBudget(max_node_visits=2)

    result = await run(graph, checkpointer=checkpointer, budget=budget)
    for value in ("again", "again2", "approved"):
        result = await resume(
            graph, result.run_id, value, checkpointer=checkpointer, budget=RunBudget(max_node_visits=2)
        )

    assert result.status == STATUS_COMPLETED, result.error
