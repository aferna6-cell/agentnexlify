"""Budget tests for backend.graph.budget and its enforcement in the runtime.

A cyclic graph is only safe to execute because something can stop it. These
tests assert each limit trips, that the run ends as ``budget_exhausted`` rather
than raising, and that the partial state built before the limit is preserved —
a run that burns budget and then throws its work away is the worst of both.
"""

import pytest

from backend.graph.budget import DEFAULT_MAX_NODE_VISITS, RunBudget
from backend.graph.checkpoint import (
    STATUS_BUDGET_EXHAUSTED,
    STATUS_COMPLETED,
    InMemoryCheckpointer,
)
from backend.graph.errors import BudgetExhausted
from backend.graph.graph import END, Graph
from backend.graph.nodes import NodeResult
from backend.graph.runtime import run


def _cp() -> InMemoryCheckpointer:
    return InMemoryCheckpointer()


def _spin_graph(tokens: int = 0, sleep: float = 0.0):
    """A graph whose only node loops into itself forever."""
    import asyncio

    graph = Graph("spin")
    graph.declare("count", "add", default=0)

    async def spin(ctx):
        if sleep:
            await asyncio.sleep(sleep)
        return NodeResult(
            updates={"count": 1},
            meta={"tokens": tokens} if tokens else {},
        )

    graph.add_node("spin", spin)
    graph.set_entry("spin")
    graph.add_branch("spin", {"spin": lambda s: True}, default=END)
    return graph


# ---------------------------------------------------------------------------
# RunBudget unit behavior
# ---------------------------------------------------------------------------


def test_default_budget_has_a_superstep_and_node_visit_cap():
    budget = RunBudget()
    assert budget.max_supersteps == 100
    assert budget.max_node_visits == DEFAULT_MAX_NODE_VISITS
    assert budget.max_node_runs is None
    assert budget.max_tokens is None
    assert budget.max_seconds is None


def test_an_all_none_budget_never_trips():
    budget = RunBudget(
        max_supersteps=None,
        max_node_runs=None,
        max_node_visits=None,
        max_tokens=None,
        max_seconds=None,
    )
    budget.start()
    for _ in range(500):
        budget.check_superstep()
        budget.check_node("a")
        budget.charge_node("a")
        budget.charge_superstep()
    assert budget.supersteps == 500


def test_check_superstep_raises_on_the_superstep_limit():
    budget = RunBudget(max_supersteps=2)
    budget.start()
    budget.charge_superstep()
    budget.charge_superstep()

    with pytest.raises(BudgetExhausted) as exc:
        budget.check_superstep()
    assert exc.value.limit == "supersteps"
    assert "superstep limit (2)" in str(exc.value)


def test_check_node_names_the_offending_node():
    budget = RunBudget(max_node_visits=2)
    budget.start()
    budget.charge_node("critique")
    budget.charge_node("critique")

    with pytest.raises(BudgetExhausted) as exc:
        budget.check_node("critique")
    assert exc.value.limit == "node_visits"
    assert "node 'critique'" in str(exc.value)
    assert "not converging" in str(exc.value)


def test_node_visits_are_tracked_per_node_not_in_aggregate():
    budget = RunBudget(max_node_visits=2)
    budget.start()
    budget.charge_node("a")
    budget.charge_node("a")
    budget.charge_node("b")

    budget.check_node("b")  # b has only been visited once
    with pytest.raises(BudgetExhausted):
        budget.check_node("a")


def test_check_node_raises_on_the_node_run_limit():
    budget = RunBudget(max_node_visits=None, max_node_runs=3)
    budget.start()
    for name in ("a", "b", "c"):
        budget.charge_node(name)

    with pytest.raises(BudgetExhausted) as exc:
        budget.check_node("d")
    assert exc.value.limit == "node_runs"
    assert "limit 3" in str(exc.value)


def test_check_superstep_raises_on_the_token_limit():
    budget = RunBudget(max_tokens=100)
    budget.start()
    budget.charge_tokens(120)

    with pytest.raises(BudgetExhausted) as exc:
        budget.check_superstep()
    assert exc.value.limit == "tokens"
    assert "120 tokens" in str(exc.value)


def test_charge_tokens_ignores_negative_counts():
    budget = RunBudget()
    budget.charge_tokens(-50)
    assert budget.tokens == 0
    budget.charge_tokens(10)
    assert budget.tokens == 10


def test_elapsed_seconds_is_zero_before_start():
    assert RunBudget().elapsed_seconds == 0.0


def test_check_superstep_raises_on_the_wall_clock_limit():
    budget = RunBudget(max_seconds=0.0)
    budget.start()

    with pytest.raises(BudgetExhausted) as exc:
        budget.check_superstep()
    assert exc.value.limit == "seconds"
    assert "wall clock" in str(exc.value)


def test_snapshot_shape():
    budget = RunBudget()
    budget.start()
    budget.charge_superstep()
    budget.charge_node("a")
    budget.charge_node("a")
    budget.charge_node("b")
    budget.charge_tokens(42)

    snapshot = budget.snapshot()
    assert set(snapshot) == {
        "supersteps",
        "node_runs",
        "tokens",
        "visits",
        "elapsed_seconds",
    }
    assert snapshot["supersteps"] == 1
    assert snapshot["node_runs"] == 3
    assert snapshot["tokens"] == 42
    assert snapshot["visits"] == {"a": 2, "b": 1}
    assert isinstance(snapshot["elapsed_seconds"], float)
    assert snapshot["elapsed_seconds"] >= 0.0

    # The snapshot copies the visit map rather than aliasing it.
    snapshot["visits"]["a"] = 999
    assert budget.visits["a"] == 2


def test_limits_shape():
    budget = RunBudget(max_supersteps=1, max_node_runs=2, max_node_visits=3,
                       max_tokens=4, max_seconds=5.0)
    assert budget.limits() == {
        "max_supersteps": 1,
        "max_node_runs": 2,
        "max_node_visits": 3,
        "max_tokens": 4,
        "max_seconds": 5.0,
    }


def test_restore_reloads_counters():
    budget = RunBudget()
    budget.restore(
        {
            "supersteps": 7,
            "node_runs": 12,
            "tokens": 900,
            "visits": {"critique": 4},
            "elapsed_seconds": 3.5,
        }
    )
    assert budget.supersteps == 7
    assert budget.node_runs == 12
    assert budget.tokens == 900
    assert budget.visits == {"critique": 4}


def test_restore_copies_the_visit_map():
    snapshot = {"supersteps": 1, "node_runs": 1, "tokens": 0, "visits": {"a": 1}}
    budget = RunBudget()
    budget.restore(snapshot)
    budget.charge_node("a")
    assert snapshot["visits"] == {"a": 1}
    assert budget.visits == {"a": 2}


@pytest.mark.parametrize("snapshot", [None, {}])
def test_restore_is_a_no_op_for_an_empty_snapshot(snapshot):
    budget = RunBudget()
    budget.charge_node("a")
    budget.restore(snapshot)
    assert budget.node_runs == 1
    assert budget.visits == {"a": 1}


def test_restore_tolerates_a_partial_snapshot():
    budget = RunBudget()
    budget.restore({"tokens": 5})
    assert budget.tokens == 5
    assert budget.supersteps == 0
    assert budget.visits == {}


def test_counters_are_not_constructor_arguments():
    with pytest.raises(TypeError):
        RunBudget(supersteps=5)


# ---------------------------------------------------------------------------
# enforcement inside a run
# ---------------------------------------------------------------------------


async def test_infinite_self_loop_terminates_on_the_superstep_limit():
    graph = _spin_graph()
    budget = RunBudget(max_supersteps=4, max_node_visits=None)

    result = await run(graph, checkpointer=_cp(), budget=budget)

    assert result.status == STATUS_BUDGET_EXHAUSTED
    assert "superstep limit (4)" in result.error
    # Partial state survives — the loop's work is not thrown away.
    assert result.state["count"] == 4
    assert result.budget["supersteps"] == 4


async def test_infinite_self_loop_terminates_on_the_node_visit_limit():
    graph = _spin_graph()
    budget = RunBudget(max_supersteps=None, max_node_visits=5)

    result = await run(graph, checkpointer=_cp(), budget=budget)

    assert result.status == STATUS_BUDGET_EXHAUSTED
    assert "node 'spin'" in result.error
    assert "limit 5" in result.error
    assert result.state["count"] == 5
    assert result.budget["visits"] == {"spin": 5}


async def test_infinite_self_loop_terminates_on_the_default_node_visit_limit():
    """A cyclic graph with no explicit cap still terminates."""
    graph = _spin_graph()
    result = await run(graph, checkpointer=_cp(), budget=RunBudget(max_supersteps=None))

    assert result.status == STATUS_BUDGET_EXHAUSTED
    assert result.budget["visits"]["spin"] == DEFAULT_MAX_NODE_VISITS


async def test_node_run_limit_stops_a_run():
    graph = _spin_graph()
    budget = RunBudget(max_supersteps=None, max_node_visits=None, max_node_runs=6)

    result = await run(graph, checkpointer=_cp(), budget=budget)

    assert result.status == STATUS_BUDGET_EXHAUSTED
    assert "limit 6" in result.error
    assert result.budget["node_runs"] == 6
    assert result.state["count"] == 6


async def test_token_limit_stops_a_run_once_the_allowance_is_spent():
    graph = _spin_graph(tokens=40)
    budget = RunBudget(max_supersteps=None, max_node_visits=None, max_tokens=100)

    result = await run(graph, checkpointer=_cp(), budget=budget)

    assert result.status == STATUS_BUDGET_EXHAUSTED
    assert "tokens" in result.error
    # Three supersteps of 40 tokens each pushes past 100 and stops the fourth.
    assert result.budget["tokens"] == 120
    assert result.state["count"] == 3


async def test_wall_clock_limit_stops_a_run():
    graph = _spin_graph(sleep=0.02)
    budget = RunBudget(max_supersteps=None, max_node_visits=None, max_seconds=0.05)

    result = await run(graph, checkpointer=_cp(), budget=budget)

    assert result.status == STATUS_BUDGET_EXHAUSTED
    assert "wall clock" in result.error
    assert result.state["count"] >= 1


async def test_budget_exhaustion_is_checkpointed_not_raised():
    graph = _spin_graph()
    budget = RunBudget(max_supersteps=3, max_node_visits=None)
    checkpointer = _cp()

    result = await run(graph, checkpointer=checkpointer, budget=budget)

    history = await checkpointer.history(result.run_id)
    assert history[-1].status == STATUS_BUDGET_EXHAUSTED
    assert "superstep limit" in history[-1].error
    assert history[-1].state["count"] == 3
    # Every completed superstep still left a step record for cost review.
    assert len(checkpointer.steps(result.run_id)) == 3


async def test_a_generous_budget_lets_a_bounded_loop_finish():
    graph = Graph("bounded")
    graph.declare("count", "add", default=0)

    async def tick(ctx):
        return {"count": 1}

    graph.add_node("tick", tick)
    graph.set_entry("tick")
    graph.add_branch("tick", {"tick": lambda s: s["count"] < 5}, default=END)

    budget = RunBudget(max_supersteps=50, max_node_visits=25)
    result = await run(graph, checkpointer=_cp(), budget=budget)

    assert result.status == STATUS_COMPLETED
    assert result.state["count"] == 5
    assert result.budget["visits"] == {"tick": 5}


async def test_run_starts_the_wall_clock_on_the_supplied_budget():
    graph = Graph("clock")
    graph.add_node("a", lambda ctx: None)
    graph.set_entry("a").set_finish("a")

    budget = RunBudget()
    assert budget.started_at is None

    await run(graph, checkpointer=_cp(), budget=budget)

    assert budget.started_at is not None
    assert budget.elapsed_seconds >= 0.0
