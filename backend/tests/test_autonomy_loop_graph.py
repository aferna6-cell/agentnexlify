"""Behavioural tests for scripts/autonomy/loop_graph.py — every terminal path.

The graph's docstring makes a promise: "Every terminal path is explicit —
shipped, parked, escalated, or idle. A run that ends any other way is a bug."
These tests drive the graph to each of those four dispositions plus the two
retry shapes, and assert the `outcome` channel names the right one.

Two seams make that possible without a model or a CI run:

  * ``extras["runner"]`` — `_verify` hands it to `gates.run_local_ci`, so a
    four-line fake decides whether the gate is green.
  * ``Interrupt`` — the three handoff nodes describe work instead of doing it,
    so a test resumes them with a canned session result.

The last test in this file is a regression guard. A pausing node used to charge
itself a visit per pause, so a loop bounded at MAX_IMPLEMENT_ATTEMPTS retries
tripped its own per-node visit cap and ended `budget_exhausted` instead of
reaching `escalate`. A full-escalation run must end `completed`.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from backend.graph import (  # noqa: E402
    STATUS_AWAITING_INPUT,
    STATUS_COMPLETED,
    InMemoryCheckpointer,
    resume as graph_resume,
    run as graph_run,
)
from scripts.autonomy.loop_graph import (  # noqa: E402
    GRAPH_NAME,
    GRAPH_VERSION,
    MAX_IMPLEMENT_ATTEMPTS,
    build,
    default_budget,
)
from scripts.autonomy.runner import CommandResult  # noqa: E402

# --------------------------------------------------------------------------
# Fakes and the drive harness
# --------------------------------------------------------------------------

CI_PASS = "RESULT: PASS (20 required gates green)"
CI_FAIL = "  FAIL  migration numbering\nRESULT: FAIL (1 required gate(s) failed)"

IMPLEMENT_RESULT = {"summary": "added the column", "files_changed": ["backend/x.py"]}
PR_RESULT = {"pr_url": "https://github.com/o/r/pull/7", "pr_number": 7}
ESCALATE_RESULT = {"escalated": True}

DEFAULT_REPLIES = {
    "implement": IMPLEMENT_RESULT,
    "open_pr": PR_RESULT,
    "escalate": ESCALATE_RESULT,
}


def verifier(*verdicts):
    """A fake CI runner. Each call consumes one verdict; the last one repeats.

    Shaped like `scripts.autonomy.runner.Runner`: argv in, ``CommandResult``
    out, which is exactly what `gates.run_local_ci` passes through to
    `run_gate`.
    """
    outcomes = list(verdicts) or [True]

    def run(command, *, cwd=None, timeout=None):
        run.calls.append({"command": list(command), "cwd": cwd, "timeout": timeout})
        passed = outcomes[min(len(run.calls) - 1, len(outcomes) - 1)]
        return CommandResult(returncode=0 if passed else 1, stdout=CI_PASS if passed else CI_FAIL)

    run.calls = []
    return run


def raw_item(item_id="gh-1", **overrides):
    """A backlog entry as `_select` receives it — a plain dict, not a WorkItem."""
    entry = {
        "id": item_id,
        "title": f"Do {item_id}",
        "value": 1.0,
        "effort": 0.2,
        "confidence": 0.9,
        "risk": "low",
        "url": f"https://github.com/o/r/issues/{item_id}",
    }
    entry.update(overrides)
    return entry


BELOW_FLOOR = raw_item("gh-dud", value=0.1, effort=0.9, confidence=0.5)


async def drive(
    backlog,
    *,
    runner=None,
    prs_opened_today=0,
    replies=None,
    max_pauses=10,
    **inputs,
):
    """Run the graph to a terminal status, answering every handoff.

    Returns ``(result, handoffs, checkpointer)`` where ``handoffs`` is the
    ordered list of Interrupt payloads the session would have been asked to
    perform.
    """
    graph = build()
    checkpointer = InMemoryCheckpointer()
    extras = {"runner": runner or verifier(True), "loop_prs_opened_today": prs_opened_today}
    answers = {**DEFAULT_REPLIES, **(replies or {})}

    result = await graph_run(
        graph,
        {"backlog": backlog, **inputs},
        checkpointer=checkpointer,
        budget=default_budget(),
        extras=extras,
    )

    handoffs = []
    while result.status == STATUS_AWAITING_INPUT:
        assert len(handoffs) < max_pauses, f"run paused more than {max_pauses} times"
        node = result.interrupt["nodes"][0]
        handoffs.append(result.interrupt["payloads"][node])
        result = await graph_resume(
            graph,
            result.run_id,
            answers[node],
            checkpointer=checkpointer,
            budget=default_budget(),
            extras=extras,
        )

    return result, handoffs, checkpointer


def actions(handoffs):
    return [payload["action"] for payload in handoffs]


def nodes_run(checkpointer, run_id):
    return [step.node for step in checkpointer.steps(run_id)]


# --------------------------------------------------------------------------
# Structure
# --------------------------------------------------------------------------


def test_build_produces_a_structurally_valid_graph():
    graph = build()

    assert graph.validate() is graph
    assert graph.name == GRAPH_NAME
    assert graph.version == GRAPH_VERSION


def test_every_terminal_path_exists_as_a_node():
    graph = build()

    assert set(graph.nodes) == {
        "select",
        "report_idle",
        "implement",
        "verify",
        "land",
        "open_pr",
        "park",
        "escalate",
    }


def test_to_mermaid_renders_every_node():
    graph = build()

    diagram = graph.to_mermaid()

    assert diagram.startswith("flowchart TD")
    for name, node in graph.nodes.items():
        shape = f'{name}{{"{name}"}}' if node.kind == "router" else f'{name}["{name}"]'
        assert shape in diagram, f"{name} is missing from the diagram"
    assert 'land{"land"}' in diagram  # the one router renders as a diamond


def test_budget_headroom_sits_above_the_attempt_ceiling():
    """The attempt counter, not the budget, must be what stops the retry cycle."""
    budget = default_budget()

    assert budget.max_node_visits == MAX_IMPLEMENT_ATTEMPTS + 1


# --------------------------------------------------------------------------
# Happy path: select -> implement -> verify -> land -> open_pr
# --------------------------------------------------------------------------


async def test_happy_path_opens_a_pr():
    result, handoffs, _ = await drive([raw_item("gh-7")], runner=verifier(True))

    assert result.status == STATUS_COMPLETED
    assert result.state["outcome"] == "pr_opened"
    assert actions(handoffs) == ["implement", "open_pr"]
    assert result.state["pr"] == PR_RESULT
    assert result.state["attempts"] == 1


async def test_happy_path_selects_the_task_and_carries_it_into_every_handoff():
    result, handoffs, _ = await drive([raw_item("gh-7"), BELOW_FLOOR])

    task = {
        "id": "gh-7",
        "title": "Do gh-7",
        "url": "https://github.com/o/r/issues/gh-7",
        "risk": "low",
        "touches_frontend": False,
    }
    assert result.state["task"] == task
    assert handoffs[0]["task"] == task
    assert handoffs[1]["task"] == task
    assert handoffs[1]["implementation"] == IMPLEMENT_RESULT
    assert handoffs[1]["verification"]["passed"] is True


async def test_verify_runs_the_local_ci_mirror_against_the_compare_ref():
    graph = build()
    runner = verifier(True)
    checkpointer = InMemoryCheckpointer()
    extras = {"runner": runner, "compare_ref": "origin/develop", "loop_prs_opened_today": 0}

    paused = await graph_run(
        graph,
        {"backlog": [raw_item("gh-7")]},
        checkpointer=checkpointer,
        budget=default_budget(),
        extras=extras,
    )
    await graph_resume(
        graph,
        paused.run_id,
        IMPLEMENT_RESULT,
        checkpointer=checkpointer,
        budget=default_budget(),
        extras=extras,
    )

    assert runner.calls[0]["command"] == [
        "bash",
        "scripts/ci_local.sh",
        "origin/develop",
    ]


async def test_journal_accumulates_in_order_across_the_whole_run():
    result, _, _ = await drive([raw_item("gh-7")], runner=verifier(True))

    assert result.state["journal"] == [
        "selected gh-7 (Do gh-7)",
        "implemented: added the column",
        "verify: PASS",
        "deploy budget remaining: 4",
        "opened PR https://github.com/o/r/pull/7",
    ]


# --------------------------------------------------------------------------
# Retry then succeed
# --------------------------------------------------------------------------


async def test_a_second_attempt_after_one_red_gate_still_ships():
    result, handoffs, _ = await drive([raw_item("gh-7")], runner=verifier(False, True))

    assert result.state["outcome"] == "pr_opened"
    assert result.state["attempts"] == 2
    assert actions(handoffs) == ["implement", "implement", "open_pr"]


async def test_the_retry_handoff_carries_the_failing_gate_summary():
    """On a retry the session must be told which gate broke, not left guessing."""
    _, handoffs, _ = await drive([raw_item("gh-7")], runner=verifier(False, True))

    first, second = handoffs[0], handoffs[1]

    assert first["attempt"] == 1
    assert first["max_attempts"] == MAX_IMPLEMENT_ATTEMPTS
    assert first["previous_failure"] is None

    assert second["attempt"] == 2
    assert second["max_attempts"] == MAX_IMPLEMENT_ATTEMPTS
    assert second["previous_failure"]["passed"] is False
    assert second["previous_failure"]["returncode"] == 1
    assert "FAIL  migration numbering" in second["previous_failure"]["summary"]


async def test_journal_records_both_verifications():
    result, _, _ = await drive([raw_item("gh-7")], runner=verifier(False, True))

    assert result.state["journal"].count("verify: FAIL") == 1
    assert result.state["journal"].count("verify: PASS") == 1
    assert result.state["journal"].index("verify: FAIL") < result.state["journal"].index(
        "verify: PASS"
    )


# --------------------------------------------------------------------------
# Retry then escalate
# --------------------------------------------------------------------------


async def test_a_permanently_red_gate_escalates_after_the_attempt_ceiling():
    runner = verifier(False)

    result, handoffs, _ = await drive([raw_item("gh-7")], runner=runner)

    assert result.state["outcome"] == "escalated"
    assert actions(handoffs) == ["implement"] * MAX_IMPLEMENT_ATTEMPTS + ["escalate"]
    assert result.state["attempts"] == MAX_IMPLEMENT_ATTEMPTS
    assert len(runner.calls) == MAX_IMPLEMENT_ATTEMPTS


async def test_implement_runs_exactly_max_attempts_times_before_escalating():
    runner = verifier(False)

    result, _, checkpointer = await drive([raw_item("gh-7")], runner=runner)

    executed = nodes_run(checkpointer, result.run_id)
    # Each attempt is one Interrupt plus one resumed execution.
    assert executed.count("implement") == MAX_IMPLEMENT_ATTEMPTS * 2
    assert executed.count("verify") == MAX_IMPLEMENT_ATTEMPTS
    assert executed.count("land") == 0
    assert executed.count("open_pr") == 0


async def test_the_escalation_handoff_reports_what_was_tried():
    _, handoffs, _ = await drive([raw_item("gh-7")], runner=verifier(False))

    escalation = handoffs[-1]

    assert escalation["action"] == "escalate"
    assert escalation["attempts"] == MAX_IMPLEMENT_ATTEMPTS
    assert escalation["verification"]["passed"] is False
    assert "FAIL  migration numbering" in escalation["verification"]["summary"]
    assert escalation["task"]["id"] == "gh-7"


async def test_escalation_journal_names_the_attempt_count():
    result, _, _ = await drive([raw_item("gh-7")], runner=verifier(False))

    assert result.state["journal"][-1] == f"escalated after {MAX_IMPLEMENT_ATTEMPTS} attempts"


async def test_a_full_escalation_run_completes_rather_than_exhausting_its_budget():
    """Regression: a pausing node used to burn its own per-node visit cap.

    `implement` pauses once and resumes once per attempt. When the pause was
    charged as a visit, MAX_IMPLEMENT_ATTEMPTS retries cost 2x the visits the
    budget allows, so the run ended `budget_exhausted` at roughly half its own
    policy's retries and never reached `escalate`.
    """
    result, _, _ = await drive([raw_item("gh-7")], runner=verifier(False))

    assert result.status == STATUS_COMPLETED, result.error
    assert result.error is None
    assert result.state["outcome"] == "escalated"
    assert result.budget["visits"]["implement"] == MAX_IMPLEMENT_ATTEMPTS


# --------------------------------------------------------------------------
# Park: green, but the deploy quota is spent
# --------------------------------------------------------------------------


async def test_a_spent_deploy_quota_parks_a_green_change():
    result, handoffs, _ = await drive(
        [raw_item("gh-7")], runner=verifier(True), prs_opened_today=4
    )

    assert result.status == STATUS_COMPLETED
    assert result.state["outcome"] == "parked"
    assert result.state["deploy_budget_remaining"] == 0
    assert actions(handoffs) == ["implement"], "the session is never asked to open a PR"


async def test_parking_never_sets_the_pr_channel():
    result, _, checkpointer = await drive(
        [raw_item("gh-7")], runner=verifier(True), prs_opened_today=99
    )

    assert result.state["pr"] is None
    assert "open_pr" not in nodes_run(checkpointer, result.run_id)


async def test_parking_says_the_commit_is_still_on_the_branch():
    result, _, _ = await drive(
        [raw_item("gh-7")], runner=verifier(True), prs_opened_today=4
    )

    assert "open the PR next cycle" in result.state["journal"][-1]


async def test_one_pr_of_headroom_still_ships():
    result, handoffs, _ = await drive(
        [raw_item("gh-7")], runner=verifier(True), prs_opened_today=3
    )

    assert result.state["deploy_budget_remaining"] == 1
    assert result.state["outcome"] == "pr_opened"
    assert actions(handoffs) == ["implement", "open_pr"]


# --------------------------------------------------------------------------
# Idle and dry
# --------------------------------------------------------------------------


async def test_nothing_above_the_floor_ends_idle_without_reaching_implement():
    result, handoffs, checkpointer = await drive([BELOW_FLOOR])

    assert result.status == STATUS_COMPLETED
    assert result.state["outcome"] == "idle"
    assert handoffs == []
    assert nodes_run(checkpointer, result.run_id) == ["select", "report_idle"]


async def test_an_empty_backlog_is_idle_too():
    result, _, _ = await drive([])

    assert result.state["outcome"] == "idle"
    assert "no candidate work items were supplied" in result.state["journal"][0]


async def test_idle_records_the_selection_and_its_reason():
    result, _, _ = await drive([BELOW_FLOOR])

    selection = result.state["selection"]
    assert selection["chosen"] is None
    assert selection["dry"] is False
    assert selection["skipped"] == [
        {"id": "gh-dud", "reason": "score 0.05 below floor 0.35"}
    ]
    assert result.state["journal"] == [
        f"idle: {selection['idle_reason']}",
        "no actionable work this round",
    ]


async def test_a_second_consecutive_idle_round_reports_the_backlog_as_dry():
    result, handoffs, _ = await drive([BELOW_FLOOR], idle_rounds=1)

    assert result.state["outcome"] == "dry"
    assert result.state["selection"]["dry"] is True
    assert handoffs == []
    assert result.state["journal"][-1] == (
        "backlog dry — stop scheduling until new work is filed"
    )


async def test_every_candidate_excluded_still_ends_idle_not_stranded():
    result, _, _ = await drive(
        [
            raw_item("blocked", blocked=True, blocked_reason="waiting on #500"),
            raw_item("gated", owner_gated=True),
            raw_item("risky", risk="high"),
        ]
    )

    assert result.status == STATUS_COMPLETED
    assert result.state["outcome"] == "idle"
    assert [s["id"] for s in result.state["selection"]["skipped"]] == [
        "blocked",
        "gated",
        "risky",
    ]


async def test_exclude_ids_and_the_frontend_pause_reach_the_selector():
    result, _, _ = await drive(
        [raw_item("gh-ui", touches_frontend=True), raw_item("gh-api")],
        exclude_ids=["gh-api"],
        allow_frontend=False,
    )

    assert result.state["outcome"] == "idle"
    reasons = {s["id"]: s["reason"] for s in result.state["selection"]["skipped"]}
    assert reasons["gh-api"] == "already attempted this cycle"
    assert "frontend work paused" in reasons["gh-ui"]


# --------------------------------------------------------------------------
# Handoff payload contracts
# --------------------------------------------------------------------------


async def test_the_implement_handoff_tells_the_session_not_to_open_a_pr():
    _, handoffs, _ = await drive([raw_item("gh-7")])

    instructions = handoffs[0]["instructions"]
    assert "Write tests" in instructions
    assert "[skip ci]" in instructions
    assert "do not open" in instructions


async def test_the_open_pr_handoff_demands_a_draft_and_forbids_merging():
    _, handoffs, _ = await drive([raw_item("gh-7")])

    instructions = handoffs[1]["instructions"]
    assert "DRAFT" in instructions
    assert "Do NOT merge" in instructions


@pytest.mark.parametrize(
    ("prs_today", "expected"),
    [(0, "pr_opened"), (3, "pr_opened"), (4, "parked"), (10, "parked")],
)
async def test_the_deploy_quota_boundary(prs_today, expected):
    result, _, _ = await drive(
        [raw_item("gh-7")], runner=verifier(True), prs_opened_today=prs_today
    )

    assert result.state["outcome"] == expected
