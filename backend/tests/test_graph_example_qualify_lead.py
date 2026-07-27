"""The reference graph must actually run, not just import.

Every model call is faked, so this asserts the *wiring* — that the revision
loop is bounded, that the human gate pauses and resumes, and that token usage
from every turn reaches the run budget.
"""

import json

import pytest

from backend.graph import (
    STATUS_AWAITING_INPUT,
    STATUS_COMPLETED,
    InMemoryCheckpointer,
    RunBudget,
    resume,
    run,
)
from backend.graph.examples.qualify_lead import MAX_REVISIONS, build
from backend.services.llm_runtime import ClaudeCallResult

LEAD = {
    "name": "Dana",
    "areas_of_interest": "kitchen remodel",
    "message": "Looking for a quote on a full kitchen refit.",
    "timeline": "next month",
}


def _result(text: str) -> ClaudeCallResult:
    return ClaudeCallResult(
        text=text,
        duration_ms=5,
        input_tokens=100,
        output_tokens=50,
        stop_reason="end_turn",
    )


@pytest.fixture
def fake_llm(monkeypatch):
    """Route every agent node to a scripted reply, keyed by `operation`."""
    calls: list[str] = []
    script = {
        "qualify": json.dumps(
            {
                "intent_score": 0.9,
                "fit_score": 0.8,
                "recommendation": "pursue",
                "reasoning": "clear budget signal and a near-term timeline",
            }
        ),
        "critique": json.dumps({"verdict": "ship", "notes": "reads well"}),
        "draft": "Thanks Dana — a full refit is right in our wheelhouse. "
        "Want to book a 15-minute call this week?",
    }

    async def fake_call(**kwargs):
        operation = kwargs["operation"].rsplit(".", 1)[-1]
        calls.append(operation)
        return _result(script[operation])

    monkeypatch.setattr("backend.graph.adapters.llm.call_claude_messages", fake_call)
    return calls, script


async def test_happy_path_pauses_for_approval_then_sends(fake_llm):
    calls, _ = fake_llm
    graph = build()
    checkpointer = InMemoryCheckpointer()

    first = await run(graph, {"lead": LEAD}, checkpointer=checkpointer)

    assert first.status == STATUS_AWAITING_INPUT
    assert first.interrupt["nodes"] == ["approve"]
    assert "approval" in first.interrupt["reason"]
    # The owner sees the actual draft, not a run id they have to look up.
    assert first.interrupt["payloads"]["approve"]["draft"]
    assert calls == ["qualify", "draft", "critique"]

    final = await resume(
        graph, first.run_id, {"approved": True}, checkpointer=checkpointer
    )

    assert final.status == STATUS_COMPLETED
    assert final.state["outcome"] == "sent"
    assert final.state["approved"] is True
    # Resume re-ran only the paused node — no extra model calls.
    assert calls == ["qualify", "draft", "critique"]


async def test_owner_rejection_stops_the_send(fake_llm):
    graph = build()
    checkpointer = InMemoryCheckpointer()

    first = await run(graph, {"lead": LEAD}, checkpointer=checkpointer)
    final = await resume(
        graph, first.run_id, {"approved": False}, checkpointer=checkpointer
    )

    assert final.status == STATUS_COMPLETED
    assert final.state["outcome"] == "rejected"


async def test_revision_loop_is_bounded(fake_llm, monkeypatch):
    """A critic that never says ship still terminates, at MAX_REVISIONS."""
    calls, script = fake_llm
    script["critique"] = json.dumps({"verdict": "revise", "notes": "too long"})

    graph = build()
    result = await run(graph, {"lead": LEAD}, checkpointer=InMemoryCheckpointer())

    assert result.status == STATUS_AWAITING_INPUT
    # One initial draft plus one per allowed revision.
    assert result.state["drafts"] == MAX_REVISIONS + 1
    assert calls.count("draft") == MAX_REVISIONS + 1
    assert len(result.state["critique_notes"]) == MAX_REVISIONS + 1


async def test_token_usage_reaches_the_run_budget(fake_llm):
    graph = build()
    budget = RunBudget()

    result = await run(
        graph, {"lead": LEAD}, budget=budget, checkpointer=InMemoryCheckpointer()
    )

    # Three model turns before the approval gate, 150 tokens each.
    assert result.budget["tokens"] == 450


async def test_token_ceiling_stops_the_run(fake_llm):
    graph = build()
    budget = RunBudget(max_tokens=200)

    result = await run(
        graph, {"lead": LEAD}, budget=budget, checkpointer=InMemoryCheckpointer()
    )

    assert result.status == "budget_exhausted"
    assert "tokens" in result.error
    # Partial work survives — the qualification is still inspectable.
    assert result.state["qualification"]["recommendation"] == "pursue"


async def test_graph_validates_and_renders():
    graph = build()
    mermaid = graph.to_mermaid()

    assert mermaid.startswith("flowchart TD")
    for node in ("qualify", "draft", "critique", "approve", "send"):
        assert node in mermaid
