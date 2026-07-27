"""Execution tests for backend.graph.runtime — the superstep loop.

Covers the properties the Pregel-style loop exists to provide: state threading,
deterministic parallel merges, conditional routing, bounded cycles, retry and
error policy, timeouts, and a checkpoint ledger that survives failure.
"""

import asyncio

import pytest

from backend.graph.budget import RunBudget
from backend.graph.checkpoint import (
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_RUNNING,
    InMemoryCheckpointer,
)
from backend.graph.graph import END, Graph
from backend.graph.nodes import NodeResult
from backend.graph.runtime import run


def _cp() -> InMemoryCheckpointer:
    return InMemoryCheckpointer()


def _budget() -> RunBudget:
    """A budget generous enough that only the test's own limits matter."""
    return RunBudget(max_supersteps=50, max_node_visits=25)


# ---------------------------------------------------------------------------
# linear execution + state threading
# ---------------------------------------------------------------------------


async def test_linear_three_node_run_completes_and_threads_state():
    graph = Graph("linear")

    async def first(ctx):
        return {"x": ctx.get("seed") + 1}

    async def second(ctx):
        return {"y": ctx.get("x") * 10}

    async def third(ctx):
        return {"z": f"{ctx.get('x')}-{ctx.get('y')}"}

    graph.add_node("first", first)
    graph.add_node("second", second)
    graph.add_node("third", third)
    graph.set_entry("first")
    graph.add_edge("first", "second")
    graph.add_edge("second", "third")
    graph.set_finish("third")

    result = await run(graph, {"seed": 1}, checkpointer=_cp())

    assert result.status == STATUS_COMPLETED
    assert result.ok is True
    assert result.state == {"seed": 1, "x": 2, "y": 20, "z": "2-20"}
    assert result.superstep == 3
    assert result.error is None
    assert result.interrupt is None


async def test_node_context_carries_run_metadata():
    graph = Graph("meta")
    seen = {}

    async def probe(ctx):
        seen["node"] = ctx.node
        seen["superstep"] = ctx.superstep
        seen["run_id"] = ctx.run_id
        seen["tenant_id"] = ctx.tenant_id
        seen["has_budget"] = "budget" in ctx.extras
        seen["has_graph"] = "graph" in ctx.extras
        return None

    graph.add_node("probe", probe)
    graph.set_entry("probe").set_finish("probe")

    result = await run(graph, run_id="run-123", tenant_id="tenant-abc", checkpointer=_cp())

    assert seen == {
        "node": "probe",
        "superstep": 0,
        "run_id": "run-123",
        "tenant_id": "tenant-abc",
        "has_budget": True,
        "has_graph": True,
    }
    assert result.run_id == "run-123"


# ---------------------------------------------------------------------------
# parallel fan-out / fan-in
# ---------------------------------------------------------------------------


async def test_parallel_fan_out_and_fan_in_merges_deterministically():
    """Both branches merge through the append reducer in node-name order,
    regardless of which coroutine actually finished first."""
    graph = Graph("fanout")
    graph.declare("log", "append", default=[])
    joined = {}

    async def alpha(ctx):
        # Finishes last on the wall clock; must still fold first.
        await asyncio.sleep(0.03)
        return {"log": "alpha", "alpha_done": True}

    async def beta(ctx):
        return {"log": "beta", "beta_done": True}

    async def join(ctx):
        joined["log"] = list(ctx.get("log"))
        return {"joined": True}

    graph.add_node("alpha", alpha)
    graph.add_node("beta", beta)
    graph.add_node("join", join)
    graph.set_entry("alpha", "beta")
    graph.add_edge("alpha", "join")
    graph.add_edge("beta", "join")
    graph.set_finish("join")

    result = await run(graph, checkpointer=_cp())

    assert result.status == STATUS_COMPLETED
    assert result.state["log"] == ["alpha", "beta"]
    assert joined["log"] == ["alpha", "beta"]
    assert result.state["alpha_done"] is True
    assert result.state["beta_done"] is True
    # Fan-in runs once even though two edges point at it.
    assert result.superstep == 2


async def test_siblings_in_a_superstep_see_the_same_input_snapshot():
    """A node can never observe a half-applied sibling write."""
    graph = Graph("snapshot")
    graph.declare("log", "append", default=[])
    observed = {}

    async def alpha(ctx):
        await asyncio.sleep(0.02)
        observed["alpha_saw"] = list(ctx.get("log"))
        return {"log": "alpha"}

    async def beta(ctx):
        observed["beta_saw"] = list(ctx.get("log"))
        return {"log": "beta"}

    graph.add_node("alpha", alpha)
    graph.add_node("beta", beta)
    graph.set_entry("alpha", "beta")
    graph.set_finish("alpha", "beta")

    await run(graph, checkpointer=_cp())

    assert observed == {"alpha_saw": [], "beta_saw": []}


# ---------------------------------------------------------------------------
# conditional branching
# ---------------------------------------------------------------------------


async def test_conditional_branch_picks_the_matching_target():
    graph, calls = _branch_graph()
    result = await run(graph, {"score": 0.9}, checkpointer=_cp())

    assert result.status == STATUS_COMPLETED
    assert result.state["route"] == "hot"
    assert calls == {"hot": 1, "cold": 0}


async def test_conditional_branch_falls_back_to_the_else_target():
    graph, calls = _branch_graph()
    result = await run(graph, {"score": 0.1}, checkpointer=_cp())

    assert result.status == STATUS_COMPLETED
    assert result.state["route"] == "cold"
    assert calls == {"hot": 0, "cold": 1}


async def test_matching_branch_does_not_also_run_the_else_target():
    """Regression: an else edge used to fire alongside a matching conditional
    edge, fanning the run out to both targets."""
    graph, calls = _branch_graph()
    result = await run(graph, {"score": 0.9}, checkpointer=_cp())

    assert calls["cold"] == 0, "else target must not run when a branch matched"
    assert sum(calls.values()) == 1, "exactly one branch target may run"
    assert result.state["route"] == "hot"


def _branch_graph():
    """router -> {hot when score > 0.8, else cold}. Returns (graph, call counts)."""
    calls = {"hot": 0, "cold": 0}
    graph = Graph("branch")

    async def router(ctx):
        return None

    async def hot(ctx):
        calls["hot"] += 1
        return {"route": "hot"}

    async def cold(ctx):
        calls["cold"] += 1
        return {"route": "cold"}

    graph.add_node("router", router, kind="router")
    graph.add_node("hot", hot)
    graph.add_node("cold", cold)
    graph.set_entry("router")
    graph.add_branch("router", {"hot": lambda s: s["score"] > 0.8}, default="cold")
    graph.set_finish("hot", "cold")
    return graph, calls


# ---------------------------------------------------------------------------
# bounded cycles
# ---------------------------------------------------------------------------


async def test_bounded_cycle_terminates_with_the_expected_visit_count():
    graph = Graph("loop")
    graph.declare("count", "add", default=0)
    visits = []

    async def tick(ctx):
        visits.append(ctx.get("count"))
        return {"count": 1}

    graph.add_node("tick", tick)
    graph.set_entry("tick")
    graph.add_branch("tick", {"tick": lambda s: s["count"] < 3}, default=END)

    budget = _budget()
    result = await run(graph, checkpointer=_cp(), budget=budget)

    assert result.status == STATUS_COMPLETED
    assert result.state["count"] == 3
    assert visits == [0, 1, 2]
    assert budget.visits["tick"] == 3
    assert result.budget["visits"] == {"tick": 3}


# ---------------------------------------------------------------------------
# NodeResult shapes
# ---------------------------------------------------------------------------


async def test_node_result_goto_overrides_static_edges():
    graph = Graph("goto")
    calls = {"static": 0, "chosen": 0}

    async def router(ctx):
        return NodeResult(updates={"routed": True}, goto="chosen")

    async def static(ctx):
        calls["static"] += 1
        return None

    async def chosen(ctx):
        calls["chosen"] += 1
        return {"landed": "chosen"}

    graph.add_node("router", router)
    graph.add_node("static", static)
    graph.add_node("chosen", chosen)
    graph.set_entry("router")
    graph.add_edge("router", "static")
    graph.add_edge("router", "chosen")
    graph.set_finish("static", "chosen")

    result = await run(graph, checkpointer=_cp())

    assert result.status == STATUS_COMPLETED
    assert calls == {"static": 0, "chosen": 1}
    assert result.state["landed"] == "chosen"


async def test_node_result_goto_accepts_a_list_of_targets():
    graph = Graph("goto-list")
    graph.declare("log", "append", default=[])

    async def router(ctx):
        return NodeResult(goto=["left", "right"])

    async def left(ctx):
        return {"log": "left"}

    async def right(ctx):
        return {"log": "right"}

    graph.add_node("router", router)
    graph.add_node("left", left)
    graph.add_node("right", right)
    graph.set_entry("router")
    graph.add_edge("router", "left")
    graph.add_edge("router", "right")
    graph.set_finish("left", "right")

    result = await run(graph, checkpointer=_cp())

    assert result.state["log"] == ["left", "right"]


async def test_node_returning_a_plain_dict_is_coerced_to_updates():
    graph = Graph("dict")

    def sync_node(ctx):
        return {"from_dict": 42}

    graph.add_node("sync_node", sync_node)
    graph.set_entry("sync_node").set_finish("sync_node")

    result = await run(graph, checkpointer=_cp())

    assert result.status == STATUS_COMPLETED
    assert result.state["from_dict"] == 42


async def test_node_returning_none_contributes_nothing():
    graph = Graph("none")

    async def silent(ctx):
        return None

    async def writer(ctx):
        return {"written": True}

    graph.add_node("silent", silent)
    graph.add_node("writer", writer)
    graph.set_entry("silent")
    graph.add_edge("silent", "writer")
    graph.set_finish("writer")

    result = await run(graph, {"seed": 1}, checkpointer=_cp())

    assert result.status == STATUS_COMPLETED
    assert result.state == {"seed": 1, "written": True}


async def test_node_returning_an_unsupported_type_fails_the_run():
    graph = Graph("badreturn")

    async def bad(ctx):
        return "just a string"

    graph.add_node("bad", bad)
    graph.set_entry("bad").set_finish("bad")

    result = await run(graph, checkpointer=_cp())

    assert result.status == STATUS_FAILED
    assert "bad" in result.error
    assert "TypeError" in result.error


# ---------------------------------------------------------------------------
# retries
# ---------------------------------------------------------------------------


async def test_node_retries_until_success_and_records_every_attempt():
    graph = Graph("retry")
    attempts = {"n": 0}

    async def flaky(ctx):
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise RuntimeError(f"transient failure {attempts['n']}")
        return {"value": "eventually"}

    graph.add_node("flaky", flaky, retries=2, retry_backoff_seconds=0)
    graph.set_entry("flaky").set_finish("flaky")

    checkpointer = _cp()
    result = await run(graph, checkpointer=checkpointer)

    assert result.status == STATUS_COMPLETED
    assert result.state["value"] == "eventually"
    assert attempts["n"] == 3

    steps = checkpointer.steps(result.run_id)
    assert len(steps) == 1
    assert steps[0].node == "flaky"
    assert steps[0].attempts == 3
    assert steps[0].status == "ok"


async def test_node_exhausting_its_retries_fails_the_run():
    graph = Graph("retry-exhausted")
    attempts = {"n": 0}

    async def always_fails(ctx):
        attempts["n"] += 1
        raise RuntimeError("nope")

    graph.add_node("always_fails", always_fails, retries=1, retry_backoff_seconds=0)
    graph.set_entry("always_fails").set_finish("always_fails")

    checkpointer = _cp()
    result = await run(graph, checkpointer=checkpointer)

    assert result.status == STATUS_FAILED
    assert attempts["n"] == 2
    steps = checkpointer.steps(result.run_id)
    assert steps[0].attempts == 2
    assert steps[0].status == "failed"


# ---------------------------------------------------------------------------
# error policy
# ---------------------------------------------------------------------------


async def test_on_error_continue_lets_the_run_complete():
    graph = Graph("continue")

    async def broken(ctx):
        raise RuntimeError("permanently broken")

    async def after(ctx):
        return {"reached": True}

    graph.add_node("broken", broken, on_error="continue")
    graph.add_node("after", after)
    graph.set_entry("broken")
    graph.add_edge("broken", "after")
    graph.set_finish("after")

    checkpointer = _cp()
    result = await run(graph, checkpointer=checkpointer)

    assert result.status == STATUS_COMPLETED
    assert result.state["reached"] is True

    steps = {s.node: s for s in checkpointer.steps(result.run_id)}
    assert steps["broken"].status == "ok"
    assert "permanently broken" in steps["broken"].meta["suppressed_error"]


async def test_on_error_goto_routes_to_the_recovery_node():
    graph = Graph("goto-recover")
    calls = {"normal": 0, "recover": 0}

    async def risky(ctx):
        raise RuntimeError("kaboom")

    async def normal(ctx):
        calls["normal"] += 1
        return {"path": "normal"}

    async def recover(ctx):
        calls["recover"] += 1
        return {"path": "recovered"}

    graph.add_node("risky", risky, on_error="goto:recover")
    graph.add_node("normal", normal)
    graph.add_node("recover", recover)
    graph.set_entry("risky")
    graph.add_edge("risky", "normal")
    graph.add_edge("risky", "recover")
    graph.set_finish("normal", "recover")

    checkpointer = _cp()
    result = await run(graph, checkpointer=checkpointer)

    assert result.status == STATUS_COMPLETED
    assert result.state["path"] == "recovered"
    assert calls == {"normal": 0, "recover": 1}

    steps = {s.node: s for s in checkpointer.steps(result.run_id)}
    assert "kaboom" in steps["risky"].meta["recovered_from_error"]


async def test_on_error_raise_is_the_default_and_keeps_the_audit_trail():
    graph = Graph("raise")

    async def ok_node(ctx):
        return {"ok": True}

    async def boom(ctx):
        raise ValueError("detonated")

    graph.add_node("ok_node", ok_node)
    graph.add_node("boom", boom)
    graph.set_entry("ok_node")
    graph.add_edge("ok_node", "boom")
    graph.set_finish("boom")

    checkpointer = _cp()
    result = await run(graph, checkpointer=checkpointer)

    assert result.status == STATUS_FAILED
    assert result.ok is False
    assert "node 'boom'" in result.error
    assert "ValueError" in result.error
    assert "detonated" in result.error

    # Partial state from before the failure survives for inspection.
    assert result.state["ok"] is True

    steps = checkpointer.steps(result.run_id)
    assert [s.node for s in steps] == ["ok_node", "boom"]
    assert steps[0].status == "ok"
    assert steps[1].status == "failed"
    assert "detonated" in steps[1].error

    history = await checkpointer.history(result.run_id)
    assert history[-1].status == STATUS_FAILED
    assert "boom" in history[-1].error


async def test_a_failing_sibling_fails_the_whole_superstep():
    graph = Graph("sibling-failure")

    async def good(ctx):
        return {"good": True}

    async def bad(ctx):
        raise RuntimeError("sibling down")

    graph.add_node("good", good)
    graph.add_node("bad", bad)
    graph.set_entry("good", "bad")
    graph.set_finish("good", "bad")

    result = await run(graph, checkpointer=_cp())

    assert result.status == STATUS_FAILED
    assert "node 'bad'" in result.error


# ---------------------------------------------------------------------------
# timeouts
# ---------------------------------------------------------------------------


async def test_timeout_seconds_trips_on_a_slow_node():
    graph = Graph("timeout")

    async def slow(ctx):
        await asyncio.sleep(5)
        return {"never": True}

    graph.add_node("slow", slow, timeout_seconds=0.02)
    graph.set_entry("slow").set_finish("slow")

    checkpointer = _cp()
    result = await run(graph, checkpointer=checkpointer)

    assert result.status == STATUS_FAILED
    assert "node 'slow'" in result.error
    assert "TimeoutError" in result.error
    assert "never" not in result.state

    steps = checkpointer.steps(result.run_id)
    assert steps[0].status == "failed"


async def test_a_node_inside_its_timeout_succeeds():
    graph = Graph("timeout-ok")

    async def quick(ctx):
        await asyncio.sleep(0.01)
        return {"done": True}

    graph.add_node("quick", quick, timeout_seconds=5)
    graph.set_entry("quick").set_finish("quick")

    result = await run(graph, checkpointer=_cp())

    assert result.status == STATUS_COMPLETED
    assert result.state["done"] is True


# ---------------------------------------------------------------------------
# checkpointing
# ---------------------------------------------------------------------------


async def test_one_checkpoint_per_superstep_with_the_right_terminal_status():
    graph = Graph("checkpoints")

    async def node(ctx):
        return {ctx.node: True}

    for name in ("a", "b", "c"):
        graph.add_node(name, node)
    graph.set_entry("a")
    graph.add_edge("a", "b")
    graph.add_edge("b", "c")
    graph.set_finish("c")

    checkpointer = _cp()
    result = await run(graph, checkpointer=checkpointer)

    history = await checkpointer.history(result.run_id)
    assert len(history) == 3
    assert [c.superstep for c in history] == [1, 2, 3]
    assert [c.status for c in history] == [
        STATUS_RUNNING,
        STATUS_RUNNING,
        STATUS_COMPLETED,
    ]
    assert [c.frontier for c in history] == [["b"], ["c"], []]
    assert history[-1].graph_name == "checkpoints"
    assert history[-1].graph_version == "1"
    assert history[-1].state == {"a": True, "b": True, "c": True}


async def test_one_step_record_per_node_execution():
    graph = Graph("steps")
    graph.declare("log", "append", default=[])

    async def node(ctx):
        return {"log": ctx.node}

    for name in ("alpha", "beta", "join"):
        graph.add_node(name, node)
    graph.set_entry("alpha", "beta")
    graph.add_edge("alpha", "join")
    graph.add_edge("beta", "join")
    graph.set_finish("join")

    checkpointer = _cp()
    result = await run(graph, tenant_id="t-1", checkpointer=checkpointer)

    steps = checkpointer.steps(result.run_id)
    assert len(steps) == 3
    assert sorted(s.node for s in steps) == ["alpha", "beta", "join"]
    assert {s.superstep for s in steps} == {0, 1}
    assert all(s.status == "ok" for s in steps)
    assert all(s.attempts == 1 for s in steps)
    assert all(s.tenant_id == "t-1" for s in steps)
    assert all(s.kind == "task" for s in steps)
    join_step = next(s for s in steps if s.node == "join")
    assert join_step.updates == {"log": "join"}


async def test_checkpoints_are_deep_copied_so_history_cannot_be_corrupted():
    graph = Graph("deepcopy")

    async def node(ctx):
        return {"payload": {"nested": ["original"]}}

    graph.add_node("node", node)
    graph.set_entry("node").set_finish("node")

    checkpointer = _cp()
    result = await run(graph, checkpointer=checkpointer)

    first = await checkpointer.history(result.run_id)
    first[0].state["payload"]["nested"].append("corrupted")
    first[0].status = "tampered"

    second = await checkpointer.history(result.run_id)
    assert second[0].state["payload"]["nested"] == ["original"]
    assert second[0].status == STATUS_COMPLETED

    # Mutating the run's live state must not reach back into stored history.
    result.state["payload"]["nested"].append("late-write")
    third = await checkpointer.history(result.run_id)
    assert third[0].state["payload"]["nested"] == ["original"]


async def test_step_records_are_deep_copied_too():
    graph = Graph("steps-deepcopy")

    async def node(ctx):
        return {"payload": {"nested": ["original"]}}

    graph.add_node("node", node)
    graph.set_entry("node").set_finish("node")

    checkpointer = _cp()
    result = await run(graph, checkpointer=checkpointer)

    checkpointer.steps(result.run_id)[0].updates["payload"]["nested"].append("bad")
    assert checkpointer.steps(result.run_id)[0].updates == {
        "payload": {"nested": ["original"]}
    }


async def test_load_returns_the_latest_checkpoint():
    graph = Graph("load")

    async def node(ctx):
        return {ctx.node: True}

    graph.add_node("a", node)
    graph.add_node("b", node)
    graph.set_entry("a")
    graph.add_edge("a", "b")
    graph.set_finish("b")

    checkpointer = _cp()
    result = await run(graph, checkpointer=checkpointer)

    latest = await checkpointer.load(result.run_id)
    assert latest.status == STATUS_COMPLETED
    assert latest.superstep == 2
    assert await checkpointer.load("no-such-run") is None


# ---------------------------------------------------------------------------
# validation gate
# ---------------------------------------------------------------------------


async def test_run_validates_the_graph_by_default():
    from backend.graph.errors import GraphValidationError

    graph = Graph("invalid")
    graph.add_node("a", lambda ctx: None)
    # no entry, no finish

    with pytest.raises(GraphValidationError):
        await run(graph, checkpointer=_cp())


async def test_run_can_skip_validation():
    graph = Graph("skip-validation")
    graph.add_node("a", lambda ctx: {"ran": True})
    graph.set_entry("a")
    # No edge out of "a" — validate() would reject this, validate=False runs it.

    result = await run(graph, checkpointer=_cp(), validate=False)

    assert result.status == STATUS_COMPLETED
    assert result.state["ran"] is True
