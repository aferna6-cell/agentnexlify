"""Durability tests for backend.graph.checkpoint.FileCheckpointer.

The property this class exists for is survival across processes: a loop driven
by ``run_loop start`` and later ``run_loop resume`` has no shared memory between
the two invocations, so the checkpoint has to come back off disk. The last test
here is that end-to-end case; the rest pin the pieces it depends on — faithful
round-trips, an overwritten ``current.json``, a growing ``history.jsonl``, and a
corrupt read that raises instead of masquerading as an unknown run.
"""

import json

import pytest

from backend.graph.checkpoint import (
    STATUS_AWAITING_INPUT,
    STATUS_COMPLETED,
    STATUS_RUNNING,
    Checkpoint,
    FileCheckpointer,
    StepRecord,
)
from backend.graph.errors import Interrupt
from backend.graph.graph import Graph
from backend.graph.runtime import resume, run


def _checkpoint(**overrides) -> Checkpoint:
    """A fully-populated checkpoint — every field a resume() actually reads."""
    fields = {
        "run_id": "run-1",
        "graph_name": "qualify",
        "graph_version": "3",
        "superstep": 2,
        "status": STATUS_AWAITING_INPUT,
        "state": {"lead": {"name": "Ada", "tags": ["hot", "urgent"]}, "score": 0.91},
        "frontier": ["gate", "sibling"],
        "budget": {
            "supersteps": 2,
            "node_runs": 4,
            "tokens": 1200,
            "visits": {"gate": 1, "sibling": 1},
            "elapsed_seconds": 1.5,
        },
        "tenant_id": "tenant-abc",
        "error": None,
        "interrupt": {
            "nodes": ["gate"],
            "reason": "needs_human_approval",
            "payloads": {"gate": {"question": "approve?"}},
            "pending_results": [
                {
                    "node": "sibling",
                    "updates": {"sibling_ran": True, "log": "sibling"},
                    "goto": ["done"],
                    "meta": {"tokens": 12},
                }
            ],
        },
    }
    fields.update(overrides)
    return Checkpoint(**fields)


# ---------------------------------------------------------------------------
# round-trip
# ---------------------------------------------------------------------------


async def test_save_then_load_round_trips_every_field(tmp_path):
    checkpointer = FileCheckpointer(tmp_path)
    original = _checkpoint()

    await checkpointer.save(original)
    loaded = await checkpointer.load("run-1")

    assert loaded == original


async def test_round_trip_preserves_nested_interrupt_budget_and_frontier(tmp_path):
    """The three structures resume() rebuilds a run from. Asserted separately
    from equality so a regression names which one drifted."""
    checkpointer = FileCheckpointer(tmp_path)
    await checkpointer.save(_checkpoint())

    loaded = await checkpointer.load("run-1")

    banked = loaded.interrupt["pending_results"]
    assert banked == [
        {
            "node": "sibling",
            "updates": {"sibling_ran": True, "log": "sibling"},
            "goto": ["done"],
            "meta": {"tokens": 12},
        }
    ]
    assert loaded.interrupt["payloads"]["gate"] == {"question": "approve?"}
    assert loaded.budget["visits"] == {"gate": 1, "sibling": 1}
    assert loaded.budget["tokens"] == 1200
    assert loaded.frontier == ["gate", "sibling"]
    assert loaded.state["lead"]["tags"] == ["hot", "urgent"]


async def test_files_land_in_a_directory_named_for_the_run(tmp_path):
    checkpointer = FileCheckpointer(tmp_path)
    await checkpointer.save(_checkpoint())
    await checkpointer.record_step(
        StepRecord(run_id="run-1", superstep=0, node="gate", status="ok")
    )

    run_dir = tmp_path / "run-1"
    assert (run_dir / "current.json").is_file()
    assert (run_dir / "history.jsonl").is_file()
    assert (run_dir / "steps.jsonl").is_file()


async def test_no_directory_is_created_until_the_first_write(tmp_path):
    checkpointer = FileCheckpointer(tmp_path / "store")

    assert await checkpointer.load("run-1") is None

    assert not (tmp_path / "store" / "run-1").exists()


# ---------------------------------------------------------------------------
# absent vs unreadable
# ---------------------------------------------------------------------------


async def test_load_returns_none_for_an_unknown_run(tmp_path):
    checkpointer = FileCheckpointer(tmp_path)
    await checkpointer.save(_checkpoint())

    assert await checkpointer.load("no-such-run") is None


async def test_load_raises_on_a_corrupt_current_json(tmp_path):
    """"No such run" and "could not read it" must not collapse into the same
    answer — a resume that mistakes corruption for absence restarts a live run
    and repeats its side effects."""
    checkpointer = FileCheckpointer(tmp_path)
    await checkpointer.save(_checkpoint())

    (tmp_path / "run-1" / "current.json").write_bytes(b'{"run_id": "run-1", "sup')

    with pytest.raises(ValueError):
        await checkpointer.load("run-1")


async def test_load_raises_when_current_json_holds_a_non_object(tmp_path):
    checkpointer = FileCheckpointer(tmp_path)
    await checkpointer.save(_checkpoint())

    (tmp_path / "run-1" / "current.json").write_text("[1, 2, 3]", encoding="utf-8")

    with pytest.raises(ValueError):
        await checkpointer.load("run-1")


async def test_history_is_empty_for_an_unknown_run(tmp_path):
    assert await FileCheckpointer(tmp_path).history("no-such-run") == []


# ---------------------------------------------------------------------------
# history + steps append
# ---------------------------------------------------------------------------


async def test_history_returns_every_checkpoint_in_order(tmp_path):
    checkpointer = FileCheckpointer(tmp_path)
    for step in range(4):
        await checkpointer.save(
            _checkpoint(superstep=step, status=STATUS_RUNNING, interrupt=None)
        )

    history = await checkpointer.history("run-1")

    assert [c.superstep for c in history] == [0, 1, 2, 3]
    assert all(c.run_id == "run-1" for c in history)


async def test_record_step_appends_and_keeps_every_step(tmp_path):
    checkpointer = FileCheckpointer(tmp_path)
    for index, node in enumerate(["gate", "sibling", "done"]):
        await checkpointer.record_step(
            StepRecord(
                run_id="run-1",
                superstep=index,
                node=node,
                status="ok",
                attempts=index + 1,
                tokens=index * 10,
                updates={"log": node},
                tenant_id="tenant-abc",
            )
        )

    lines = (tmp_path / "run-1" / "steps.jsonl").read_text(encoding="utf-8").splitlines()
    steps = [json.loads(line) for line in lines]

    assert [s["node"] for s in steps] == ["gate", "sibling", "done"]
    assert [s["attempts"] for s in steps] == [1, 2, 3]
    assert [s["superstep"] for s in steps] == [0, 1, 2]
    assert steps[2]["updates"] == {"log": "done"}
    assert all(s["tenant_id"] == "tenant-abc" for s in steps)


async def test_re_saving_a_superstep_overwrites_current_but_appends_history(tmp_path):
    """A resumed run always re-saves the boundary it resumed from. That must be
    idempotent for the resume point and additive for the audit trail."""
    checkpointer = FileCheckpointer(tmp_path)

    await checkpointer.save(_checkpoint(superstep=2, error="first write"))
    await checkpointer.save(_checkpoint(superstep=2, error="second write"))

    loaded = await checkpointer.load("run-1")
    assert loaded.error == "second write"

    history = await checkpointer.history("run-1")
    assert [c.error for c in history] == ["first write", "second write"]
    assert [c.superstep for c in history] == [2, 2]


# ---------------------------------------------------------------------------
# isolation between runs
# ---------------------------------------------------------------------------


async def test_two_runs_do_not_interfere(tmp_path):
    checkpointer = FileCheckpointer(tmp_path)

    await checkpointer.save(_checkpoint(run_id="run-a", state={"who": "a"}))
    await checkpointer.save(_checkpoint(run_id="run-b", state={"who": "b"}))
    await checkpointer.save(_checkpoint(run_id="run-b", state={"who": "b2"}))
    await checkpointer.record_step(
        StepRecord(run_id="run-a", superstep=0, node="only-a", status="ok")
    )

    assert (await checkpointer.load("run-a")).state == {"who": "a"}
    assert (await checkpointer.load("run-b")).state == {"who": "b2"}
    assert len(await checkpointer.history("run-a")) == 1
    assert len(await checkpointer.history("run-b")) == 2
    assert not (tmp_path / "run-b" / "steps.jsonl").exists()


async def test_a_run_id_that_escapes_the_root_is_refused(tmp_path):
    checkpointer = FileCheckpointer(tmp_path / "store")

    with pytest.raises(ValueError):
        await checkpointer.load("../outside")


# ---------------------------------------------------------------------------
# the reason this class exists: resume from a separate process
# ---------------------------------------------------------------------------


def _gated_graph():
    """entry -> {gate, sibling} -> done. ``gate`` pauses until given a resume
    value; ``sibling`` counts itself so a test can prove it never re-ran."""
    calls = {"gate": 0, "sibling": 0, "done": 0}
    graph = Graph("cross-process")
    graph.declare("log", "append", default=[])

    async def gate(ctx):
        calls["gate"] += 1
        if ctx.resume_value is None:
            raise Interrupt("needs_human_approval", {"question": "approve?"})
        return {"approval": ctx.resume_value, "log": "gate"}

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


async def test_a_brand_new_checkpointer_can_resume_an_interrupted_run(tmp_path):
    """The cross-process case in one test: process A pauses the run, process B
    is a fresh FileCheckpointer over the same root and finishes it."""
    graph, calls = _gated_graph()

    # --- process A: start the run, hit the human gate, exit.
    paused = await run(graph, {"lead": "Ada"}, checkpointer=FileCheckpointer(tmp_path))

    assert paused.status == STATUS_AWAITING_INPUT
    assert paused.interrupt["nodes"] == ["gate"]
    assert calls == {"gate": 1, "sibling": 1, "done": 0}

    # --- process B: nothing in memory, only the directory on disk.
    reopened = FileCheckpointer(tmp_path)
    restored = await reopened.load(paused.run_id)
    assert restored is not None
    assert restored.status == STATUS_AWAITING_INPUT
    assert restored.interrupt["reason"] == "needs_human_approval"

    finished = await resume(graph, paused.run_id, "approved", checkpointer=reopened)

    assert finished.status == STATUS_COMPLETED
    assert finished.state["approval"] == "approved"
    assert finished.state["done"] is True
    # Banked from the checkpoint, not re-executed: sibling ran exactly once
    # across both processes and its write still landed.
    assert calls == {"gate": 2, "sibling": 1, "done": 1}
    assert finished.state["sibling_ran"] is True
    # Node-name order, per apply_updates — the banked sibling folds in the same
    # deterministic position it would have had if no pause had happened.
    assert finished.state["log"] == ["gate", "sibling", "done"]


async def test_the_resumed_run_keeps_the_budget_it_had_spent(tmp_path):
    """A run must not earn a fresh allowance by crossing a process boundary."""
    graph, _ = _gated_graph()

    paused = await run(graph, checkpointer=FileCheckpointer(tmp_path))
    spent_before = paused.budget["node_runs"]

    finished = await resume(
        graph, paused.run_id, "approved", checkpointer=FileCheckpointer(tmp_path)
    )

    assert spent_before == 2  # gate + sibling
    assert finished.budget["node_runs"] > spent_before
    # gate's pause was visit-refunded; the resumed execution is the one visit
    # that counts, because that is the one that actually ran to completion.
    assert finished.budget["visits"]["gate"] == 1


async def test_the_whole_boundary_history_survives_on_disk(tmp_path):
    graph, _ = _gated_graph()

    paused = await run(graph, checkpointer=FileCheckpointer(tmp_path))
    await resume(
        graph, paused.run_id, "approved", checkpointer=FileCheckpointer(tmp_path)
    )

    history = await FileCheckpointer(tmp_path).history(paused.run_id)

    assert [c.status for c in history] == [
        STATUS_AWAITING_INPUT,
        STATUS_RUNNING,
        STATUS_COMPLETED,
    ]
    assert history[-1].state["done"] is True
