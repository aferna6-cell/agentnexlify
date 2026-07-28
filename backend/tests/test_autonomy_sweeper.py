"""Sweeper for stranded autonomy runs — regression coverage for issue #605.

The incident this pins: on 2026-07-28 a container restart killed run
``a82c9f38`` while the ``verify`` node was mid-flight. The checkpoint on disk
said ``status: running`` with ``frontier: ['verify']``, ``resume`` refused it
(correctly — there was no interrupt to resume into), ``start`` created a new
run rather than adopting it, and nothing in the system would ever touch the
corpse again. Orphans accumulate silently and ``running`` stops meaning
anything.

The sweeper's contract, tested here:

- a stranded ``running`` run is discoverable without knowing its id
- sweeping resolves it to ``failed`` with the reason recorded
- the sweeper NEVER executes a node — non-idempotent handoffs (``open_pr``,
  ``merge``) cannot be double-fired by recovery, because recovery runs nothing
- fresh runs and legitimately paused runs are left alone
"""

import asyncio
import json
import os
import time
from pathlib import Path

import pytest

from backend.graph.checkpoint import (
    STATUS_AWAITING_INPUT,
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_RUNNING,
    Checkpoint,
    FileCheckpointer,
)
from scripts.autonomy import loop_graph
from scripts.autonomy.sweeper import StrandedRun, find_stranded, sweep

STALE = 3600  # the default threshold the CLI uses


def _write_run(
    root: Path,
    run_id: str,
    *,
    status: str,
    frontier: list[str],
    age_seconds: float = 0.0,
) -> None:
    """Create a run directory the way FileCheckpointer would, then age it.

    Built through the real checkpointer so the fixture can't drift from the
    on-disk format. Ageing is done by rewinding file mtimes — the sweeper's
    staleness signal — rather than by faking clocks inside the checkpointer.
    """
    cp = Checkpoint(
        run_id=run_id,
        graph_name="autonomous-engineering-loop",
        graph_version="1",
        superstep=3,
        status=status,
        state={"journal": ["fixture"]},
        frontier=frontier,
    )
    asyncio.run(FileCheckpointer(root).save(cp))
    if age_seconds:
        stamp = time.time() - age_seconds
        for path in (root / run_id).iterdir():
            os.utime(path, (stamp, stamp))


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------


def test_stranded_run_is_found_without_knowing_its_id(tmp_path):
    _write_run(tmp_path, "dead-run", status=STATUS_RUNNING, frontier=["verify"], age_seconds=STALE * 2)

    found = find_stranded(tmp_path, stale_after_seconds=STALE)

    assert [r.run_id for r in found] == ["dead-run"]


def test_fresh_running_run_is_not_reported(tmp_path):
    """A run that wrote a checkpoint moments ago is alive, not stranded.

    ``verify`` legitimately takes ~2 minutes with no checkpoint writes, so the
    threshold has to tolerate a quiet-but-alive run. Freshness == not swept.
    """
    _write_run(tmp_path, "live-run", status=STATUS_RUNNING, frontier=["verify"])

    assert find_stranded(tmp_path, stale_after_seconds=STALE) == []


@pytest.mark.parametrize("status", [STATUS_COMPLETED, STATUS_FAILED, STATUS_AWAITING_INPUT])
def test_only_running_runs_are_candidates(tmp_path, status):
    """Terminal runs are history and awaiting_input runs are resumable.

    ``awaiting_input`` in particular must be exempt no matter how old: a run
    parked on a human gate for a week is the interrupt mechanism working,
    and sweeping it would destroy a live handoff.
    """
    _write_run(tmp_path, "old-run", status=status, frontier=["merge"], age_seconds=STALE * 100)

    assert find_stranded(tmp_path, stale_after_seconds=STALE) == []


def test_detection_reports_frontier_and_retry_safety(tmp_path):
    _write_run(tmp_path, "died-in-verify", status=STATUS_RUNNING, frontier=["verify"], age_seconds=STALE * 2)
    _write_run(tmp_path, "died-in-merge", status=STATUS_RUNNING, frontier=["merge"], age_seconds=STALE * 2)

    by_id = {r.run_id: r for r in find_stranded(tmp_path, stale_after_seconds=STALE)}

    assert by_id["died-in-verify"].frontier == ["verify"]
    assert by_id["died-in-verify"].safe_to_retry is True
    assert by_id["died-in-merge"].safe_to_retry is False


def test_missing_state_dir_is_empty_not_an_error(tmp_path):
    assert find_stranded(tmp_path / "never-created", stale_after_seconds=STALE) == []


# ---------------------------------------------------------------------------
# Re-enterability marking
# ---------------------------------------------------------------------------


def test_every_loop_node_is_explicitly_classified():
    """Each node in the graph is marked re-enterable or not — no defaults.

    A node someone adds later must make the choice consciously; an unclassified
    node failing this test is the enforcement.
    """
    graph = loop_graph.build()
    node_names = set(graph.nodes)

    classified = loop_graph.REENTERABLE_NODES | loop_graph.NON_REENTERABLE_NODES

    assert node_names == classified
    assert not (loop_graph.REENTERABLE_NODES & loop_graph.NON_REENTERABLE_NODES)


def test_external_side_effect_nodes_are_not_reenterable():
    """The nodes that touch the world can never be marked safe to redo.

    Re-running open_pr double-opens; re-running merge double-merges. This
    pins the classification so a refactor can't quietly flip one.
    """
    for node in ("implement", "open_pr", "merge", "escalate"):
        assert node in loop_graph.NON_REENTERABLE_NODES


# ---------------------------------------------------------------------------
# Sweeping
# ---------------------------------------------------------------------------


def test_sweep_resolves_stranded_run_to_failed_with_reason(tmp_path):
    _write_run(tmp_path, "dead-run", status=STATUS_RUNNING, frontier=["verify"], age_seconds=STALE * 2)

    swept = sweep(tmp_path, stale_after_seconds=STALE)

    assert [r.run_id for r in swept] == ["dead-run"]
    after = asyncio.run(FileCheckpointer(tmp_path).load("dead-run"))
    assert after.status == STATUS_FAILED
    assert "swept" in after.error
    assert "verify" in after.error


def test_sweep_is_recorded_in_history_not_just_current(tmp_path):
    """The terminal boundary must land in history.jsonl like any other.

    A swept run whose audit trail still ends at ``running`` would look like
    the corruption the checkpointer exists to prevent.
    """
    _write_run(tmp_path, "dead-run", status=STATUS_RUNNING, frontier=["verify"], age_seconds=STALE * 2)

    sweep(tmp_path, stale_after_seconds=STALE)

    lines = (tmp_path / "dead-run" / "history.jsonl").read_text().strip().splitlines()
    assert json.loads(lines[-1])["status"] == STATUS_FAILED


def test_sweep_leaves_live_and_paused_runs_untouched(tmp_path):
    _write_run(tmp_path, "live", status=STATUS_RUNNING, frontier=["verify"])
    _write_run(tmp_path, "paused", status=STATUS_AWAITING_INPUT, frontier=["merge"], age_seconds=STALE * 100)
    _write_run(tmp_path, "done", status=STATUS_COMPLETED, frontier=[], age_seconds=STALE * 100)

    assert sweep(tmp_path, stale_after_seconds=STALE) == []

    store = FileCheckpointer(tmp_path)
    assert asyncio.run(store.load("live")).status == STATUS_RUNNING
    assert asyncio.run(store.load("paused")).status == STATUS_AWAITING_INPUT
    assert asyncio.run(store.load("done")).status == STATUS_COMPLETED


def test_dry_run_reports_but_writes_nothing(tmp_path):
    _write_run(tmp_path, "dead-run", status=STATUS_RUNNING, frontier=["merge"], age_seconds=STALE * 2)

    found = sweep(tmp_path, stale_after_seconds=STALE, dry_run=True)

    assert [r.run_id for r in found] == ["dead-run"]
    after = asyncio.run(FileCheckpointer(tmp_path).load("dead-run"))
    assert after.status == STATUS_RUNNING


def test_sweep_never_executes_a_node(tmp_path, monkeypatch):
    """The regression #605 demands: recovery must not re-fire side effects.

    Guaranteed structurally — the sweeper resolves state and runs nothing —
    and pinned here by making every node in the loop graph explode if called
    while a run stranded on the most dangerous frontiers is swept.
    """

    def _bomb(name):
        async def _node(ctx):  # noqa: ARG001
            raise AssertionError(f"sweeper executed node {name!r}")

        return _node

    graph = loop_graph.build()
    for name in graph.nodes:
        monkeypatch.setattr(
            loop_graph, f"_{name}", _bomb(name), raising=False
        )

    _write_run(tmp_path, "died-in-open-pr", status=STATUS_RUNNING, frontier=["open_pr"], age_seconds=STALE * 2)
    _write_run(tmp_path, "died-in-merge", status=STATUS_RUNNING, frontier=["merge"], age_seconds=STALE * 2)

    swept = sweep(tmp_path, stale_after_seconds=STALE)

    assert {r.run_id for r in swept} == {"died-in-open-pr", "died-in-merge"}
    store = FileCheckpointer(tmp_path)
    for run_id in ("died-in-open-pr", "died-in-merge"):
        assert asyncio.run(store.load(run_id)).status == STATUS_FAILED


def test_swept_result_carries_retry_guidance(tmp_path):
    """The sweep result tells the operator whether redoing the work is safe.

    StrandedRun.safe_to_retry means "a FRESH run may redo this frontier" —
    the sweeper itself re-runs nothing either way.
    """
    _write_run(tmp_path, "dead-run", status=STATUS_RUNNING, frontier=["select"], age_seconds=STALE * 2)

    (result,) = sweep(tmp_path, stale_after_seconds=STALE)

    assert isinstance(result, StrandedRun)
    assert result.safe_to_retry is True
    assert result.age_seconds >= STALE
