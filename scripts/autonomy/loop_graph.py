"""The autonomous engineering loop, as a graph.

    START -> select -+-> implement -> verify -+-> land -+-> open_pr -> END
                     |        ^               |         '-> park ----> END
                     |        '---------------+ (retry, bounded)
                     |                        '-> escalate ---------> END
                     '-> report_idle ---------------------------------> END

Two kinds of node, and the split is the whole design:

**Deterministic nodes** (``select``, ``verify``, ``land``, ``report_idle``,
``park``) are plain Python. They decide what to build, whether it passed, and
whether it may ship. A model cannot argue with them, and their behavior is
testable without running a model at all.

**Handoff nodes** (``implement``, ``open_pr``, ``escalate``) raise
:class:`Interrupt`. They do not do the work — they describe it, the run
checkpoints, and the driving Claude Code session performs it and resumes with
the result. That session already has the capability this process lacks: it can
edit files, run git, and reach GitHub.

So the graph is policy and the session is capability. The loop cannot ship
something the gates rejected, because the gate is code; and it can still do
open-ended engineering, because the executor is a full agent session.

Every terminal path is explicit — shipped, parked, escalated, or idle. A run
that ends any other way is a bug, and ``outcome`` records which one happened.
"""

from typing import Any

from backend.graph import END, Graph, Interrupt, NodeResult, RunBudget
from scripts.autonomy import gates
from scripts.autonomy.backlog import WorkItem, select as select_work

# How many times the loop may re-implement after a failed verification before
# handing the task to a human. Three attempts is where the marginal fix stops
# working: past that the failure is usually a misread of the task, not a slip
# in the patch, and another attempt spends tokens re-deriving the same wrong
# thing. The budget's per-node visit cap is the backstop if this is ever raised.
MAX_IMPLEMENT_ATTEMPTS = 3

GRAPH_NAME = "autonomous_engineering"
GRAPH_VERSION = "1"


def default_budget() -> RunBudget:
    """Budget for one loop run — one task, start to disposition.

    ``max_node_visits`` sits one above ``MAX_IMPLEMENT_ATTEMPTS`` so the
    attempt counter is what stops the retry cycle and the error names the task,
    rather than the budget tripping first and reporting a less useful message.
    Wall clock is generous because ``verify`` shells out to the full 20-gate
    local CI mirror, which legitimately takes minutes.
    """
    return RunBudget(
        max_supersteps=40,
        max_node_visits=MAX_IMPLEMENT_ATTEMPTS + 1,
        max_seconds=3 * 60 * 60,
    )


# --------------------------------------------------------------------- nodes


async def _select(ctx) -> NodeResult:
    """Pick the one task worth doing, or explain why nothing is."""
    items = [WorkItem.from_dict(raw) for raw in ctx.get("backlog", [])]
    selection = select_work(
        items,
        exclude_ids=set(ctx.get("exclude_ids", []) or []),
        allow_frontend=bool(ctx.get("allow_frontend", True)),
        idle_rounds=int(ctx.get("idle_rounds", 0) or 0),
    )
    return NodeResult(
        updates={
            "selection": selection.to_dict(),
            "task": (
                {
                    "id": selection.chosen.id,
                    "title": selection.chosen.title,
                    "url": selection.chosen.url,
                    "risk": selection.chosen.risk,
                    "touches_frontend": selection.chosen.touches_frontend,
                }
                if selection.chosen
                else None
            ),
            "journal": (
                f"selected {selection.chosen.id} ({selection.chosen.title})"
                if selection.chosen
                else f"idle: {selection.idle_reason}"
            ),
        },
        meta={"skipped": len(selection.skipped)},
    )


async def _report_idle(ctx) -> NodeResult:
    """Terminal: nothing cleared the value floor.

    Idling is a success state. The loop existing to produce PRs is what made it
    manufacture work once the good backlog was gone.
    """
    selection = ctx.get("selection") or {}
    dry = bool(selection.get("dry"))
    return NodeResult(
        updates={
            "outcome": "dry" if dry else "idle",
            "journal": "backlog dry — stop scheduling until new work is filed"
            if dry
            else "no actionable work this round",
        }
    )


async def _implement(ctx) -> NodeResult:
    """Handoff: the session writes the change.

    On a retry the previous verification failure is included, so the session
    fixes the named gate instead of guessing at what broke.
    """
    result = ctx.resume_value
    if result is None:
        raise Interrupt(
            "implement",
            payload={
                "action": "implement",
                "task": ctx.get("task"),
                "attempt": int(ctx.get("attempts", 0)) + 1,
                "max_attempts": MAX_IMPLEMENT_ATTEMPTS,
                "previous_failure": ctx.get("verification"),
                "instructions": (
                    "Implement this task on the current branch. Write tests "
                    "first. Commit with [skip ci]. Do not push and do not open "
                    "a PR — the loop does that after the gates pass. Resume "
                    "with {\"summary\": \"...\", \"files_changed\": [...]}."
                ),
            },
        )
    return NodeResult(
        updates={
            "attempts": 1,
            "implementation": result,
            "journal": f"implemented: {result.get('summary', 'no summary')}",
        }
    )


async def _verify(ctx) -> NodeResult:
    """The gate the loop cannot talk its way past.

    Runs the full local CI mirror in-process rather than asking the session
    whether its own work passed. `scripts/ci_local.sh` is gate-parity with
    `pr-check.yml` and costs zero Actions minutes, which is the only reason
    verification is possible at all while GH #500 is open.
    """
    runner = ctx.extras.get("runner")
    compare_ref = ctx.extras.get("compare_ref", "origin/main")
    result = gates.run_local_ci(compare_ref, runner=runner)
    return NodeResult(
        updates={
            "verification": {
                "passed": result.passed,
                "summary": result.summary,
                "returncode": result.returncode,
                "duration_seconds": result.duration_seconds,
            },
            "journal": f"verify: {'PASS' if result.passed else 'FAIL'}",
        },
        meta={"duration_seconds": result.duration_seconds},
    )


async def _land(ctx) -> NodeResult:
    """Decide whether a green change may actually open a PR today."""
    remaining = gates.deploy_budget_remaining(
        int(ctx.extras.get("prs_opened_today", 0))
    )
    return NodeResult(
        updates={
            "deploy_budget_remaining": remaining,
            "journal": f"deploy budget remaining: {remaining}",
        }
    )


async def _open_pr(ctx) -> NodeResult:
    """Handoff: the session pushes and opens a DRAFT PR. Never merges."""
    result = ctx.resume_value
    if result is None:
        raise Interrupt(
            "open_pr",
            payload={
                "action": "open_pr",
                "task": ctx.get("task"),
                "implementation": ctx.get("implementation"),
                "verification": ctx.get("verification"),
                "instructions": (
                    "Push the branch and open a DRAFT pull request. Paste the "
                    "local gate summary as merge evidence. Do NOT merge — "
                    "landing stays a human decision. Resume with "
                    "{\"pr_url\": \"...\", \"pr_number\": N}."
                ),
            },
        )
    return NodeResult(
        updates={
            "outcome": "pr_opened",
            "pr": result,
            "journal": f"opened PR {result.get('pr_url', '?')}",
        }
    )


async def _park(ctx) -> NodeResult:
    """Terminal: work is green but shipping it now would burn a capped resource."""
    return NodeResult(
        updates={
            "outcome": "parked",
            "journal": (
                "verified but not shipped — daily PR/deploy budget spent. "
                "The commit is on the branch; open the PR next cycle."
            ),
        }
    )


async def _escalate(ctx) -> NodeResult:
    """Handoff: hand a stuck task to the owner and stop working it."""
    result = ctx.resume_value
    if result is None:
        raise Interrupt(
            "escalate",
            payload={
                "action": "escalate",
                "task": ctx.get("task"),
                "attempts": ctx.get("attempts"),
                "verification": ctx.get("verification"),
                "instructions": (
                    "Comment on the issue with what was tried, the failing "
                    "gate output, and the specific decision needed. Label it "
                    "for human attention. Resume with {\"escalated\": true}."
                ),
            },
        )
    return NodeResult(
        updates={
            "outcome": "escalated",
            "journal": f"escalated after {ctx.get('attempts')} attempts",
        }
    )


# ------------------------------------------------------------------ routing


def _has_work(state: dict[str, Any]) -> bool:
    return state.get("task") is not None


def _verified(state: dict[str, Any]) -> bool:
    return bool((state.get("verification") or {}).get("passed"))


def _can_retry(state: dict[str, Any]) -> bool:
    verification = state.get("verification") or {}
    if verification.get("passed"):
        return False
    return int(state.get("attempts", 0)) < MAX_IMPLEMENT_ATTEMPTS


def _may_ship(state: dict[str, Any]) -> bool:
    return int(state.get("deploy_budget_remaining", 0)) > 0


# -------------------------------------------------------------------- build


def build() -> Graph:
    graph = Graph(GRAPH_NAME, version=GRAPH_VERSION)

    graph.declare("backlog", reducer="once")
    graph.declare("selection", reducer="last")
    graph.declare("task", reducer="last")
    graph.declare("attempts", reducer="add", default=0)
    graph.declare("implementation", reducer="last")
    graph.declare("verification", reducer="last")
    graph.declare("deploy_budget_remaining", reducer="last", default=0)
    graph.declare("pr", reducer="last")
    graph.declare("outcome", reducer="last")
    graph.declare("journal", reducer="append", default=[])

    graph.add_node("select", _select, description="Pick the one task worth doing.")
    graph.add_node("report_idle", _report_idle, kind="terminal")
    graph.add_node(
        "implement",
        _implement,
        kind="agent",
        description="Session writes the change.",
    )
    graph.add_node(
        "verify",
        _verify,
        # A crashing gate runner must not look like a passing gate. Letting it
        # fail the run surfaces the breakage instead of silently shipping.
        retries=1,
        description="Full local CI mirror.",
    )
    graph.add_node("land", _land, kind="router", description="Daily budget check.")
    graph.add_node("open_pr", _open_pr, kind="agent")
    graph.add_node("park", _park, kind="terminal")
    graph.add_node("escalate", _escalate, kind="human")

    graph.set_entry("select")
    graph.add_branch("select", {"implement": _has_work}, default="report_idle")
    graph.add_edge("report_idle", END)

    graph.add_edge("implement", "verify")
    graph.add_branch(
        "verify",
        {"land": _verified, "implement": _can_retry},
        default="escalate",
    )

    graph.add_branch("land", {"open_pr": _may_ship}, default="park")
    graph.add_edge("open_pr", END)
    graph.add_edge("park", END)
    graph.add_edge("escalate", END)

    return graph.validate()
