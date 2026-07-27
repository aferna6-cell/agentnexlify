"""Reference graph: draft a lead reply, self-critique in a bounded loop, then
pause for owner approval before sending.

This is the shape most AgentNexLiFy agent work actually has, and it exercises
every part of the runtime that a linear sequencer cannot express:

- a **cycle** — draft, critique, redraft — bounded by ``max_node_visits`` rather
  than by a hand-written ``for i in range(3)``
- a **conditional branch** — the critic's verdict decides whether to loop or
  advance, and the condition reads state the previous superstep just wrote
- a **human gate** — ``Interrupt`` pauses the run durably instead of needing a
  bespoke pending-approval table
- **budgeted spend** — token usage from every model turn is charged to one run
  budget, so "this conversation cost too much" is a stop condition

Flow::

    START -> qualify -> draft -> critique -.-> draft   (revise, bounded)
                                            '-> approve -> send -> END

Nothing in the product calls this yet. It is a reference, and the test
``backend/tests/test_graph_example_qualify_lead.py`` runs it against a fake
model so the wiring stays honest.
"""

from typing import Any

from backend.graph import END, Graph, Interrupt, NodeResult, register
from backend.graph.adapters.llm import agent_node

# Two turns of critique is where the quality curve flattens; past that the loop
# is spending tokens to rephrase. The budget's per-node visit cap is the
# backstop if a critic never says "ship it".
MAX_REVISIONS = 2

QUALIFY_SCHEMA = {
    "type": "object",
    "properties": {
        "intent_score": {"type": "number"},
        "fit_score": {"type": "number"},
        "recommendation": {"type": "string"},
        "reasoning": {"type": "string"},
    },
    "required": ["intent_score", "fit_score", "recommendation", "reasoning"],
}

CRITIQUE_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["ship", "revise"]},
        "notes": {"type": "string"},
    },
    "required": ["verdict", "notes"],
}


def _qualify_prompt(state: dict[str, Any]) -> str:
    lead = state.get("lead", {})
    return (
        "Score this inbound lead for a small service business.\n\n"
        f"Name: {lead.get('name', 'unknown')}\n"
        f"Interest: {lead.get('areas_of_interest', 'unstated')}\n"
        f"Message: {lead.get('message', '')}\n"
        f"Timeline: {lead.get('timeline', 'unstated')}\n"
    )


def _draft_prompt(state: dict[str, Any]) -> str:
    qualification = state.get("qualification", {})
    notes = state.get("critique_notes") or []
    base = (
        "Write a short, warm first reply to this lead. Two sentences, no "
        "pricing, one clear next step.\n\n"
        f"Lead: {state.get('lead', {})}\n"
        f"Qualification: {qualification}\n"
    )
    if notes:
        # The revision turn differs from the first only by this block, which is
        # why the loop is worth having rather than one longer prompt.
        base += "\nRevise the previous draft to address this feedback:\n"
        base += f"Previous draft: {state.get('draft', '')}\n"
        base += "Feedback: " + "; ".join(notes[-1:])
    return base


def _needs_revision(state: dict[str, Any]) -> bool:
    """Loop while the critic objects and we have redrafts left.

    The counter is *drafts produced*, not *critiques that objected* — those
    differ by one, and counting the objections silently costs a redraft.
    ``drafts`` is 1 after the first pass, so ``<=`` allows exactly
    ``MAX_REVISIONS`` redrafts on top of it.
    """
    critique = state.get("critique") or {}
    return (
        critique.get("verdict") == "revise"
        and state.get("drafts", 0) <= MAX_REVISIONS
    )


async def _record_critique(ctx) -> NodeResult:
    """Keep the critic's feedback so the next draft prompt can address it."""
    critique = ctx.get("critique") or {}
    if critique.get("verdict") == "revise":
        return NodeResult(updates={"critique_notes": critique.get("notes", "")})
    return NodeResult(updates={})


async def _await_approval(ctx) -> NodeResult:
    """Pause for the owner. Resumes with ``resume(graph, run_id, decision)``.

    On the first pass ``resume_value`` is None and this raises; on resume the
    same node runs again with the decision in hand.
    """
    decision = ctx.resume_value
    if decision is None:
        raise Interrupt(
            "owner approval required before sending",
            payload={"draft": ctx.get("draft"), "qualification": ctx.get("qualification")},
        )
    return NodeResult(updates={"approved": bool(decision.get("approved"))})


async def _send(ctx) -> NodeResult:
    """Terminal side effect. Real implementations call the email/SMS sender here."""
    if not ctx.get("approved"):
        return NodeResult(updates={"outcome": "rejected"})
    return NodeResult(updates={"outcome": "sent"})


@register("qualify_lead", version="1")
def build() -> Graph:
    graph = Graph("qualify_lead", version="1")

    graph.declare("qualification", reducer="last")
    graph.declare("draft", reducer="last")
    graph.declare("critique", reducer="last")
    graph.declare("critique_notes", reducer="append", default=[])
    graph.declare("drafts", reducer="add", default=0)
    graph.declare("approved", reducer="last", default=False)
    graph.declare("outcome", reducer="last")

    graph.add_node(
        "qualify",
        agent_node(
            operation="graph.qualify_lead.qualify",
            model="claude-haiku-4-5-20251001",
            prompt=_qualify_prompt,
            output_key="qualification",
            response_schema=QUALIFY_SCHEMA,
            max_tokens=512,
        ),
        kind="agent",
        retries=1,
        description="Score intent and fit.",
    )

    graph.add_node(
        "draft",
        agent_node(
            operation="graph.qualify_lead.draft",
            model="claude-sonnet-5",
            prompt=_draft_prompt,
            # Count drafts here rather than in the critique branch so the
            # counter tracks work actually done, whatever the critic returns.
            updates=lambda state, text: {"draft": text, "drafts": 1},
            max_tokens=512,
        ),
        kind="agent",
        retries=1,
        description="Write or revise the reply.",
    )

    graph.add_node(
        "critique",
        agent_node(
            operation="graph.qualify_lead.critique",
            model="claude-haiku-4-5-20251001",
            prompt=lambda s: (
                "Judge this reply to a lead. Answer 'ship' if it is warm, "
                "under three sentences, quotes no price, and gives one next "
                "step. Otherwise 'revise' with one concrete fix.\n\n"
                f"Reply: {s.get('draft', '')}"
            ),
            output_key="critique",
            response_schema=CRITIQUE_SCHEMA,
            max_tokens=256,
        ),
        kind="agent",
        # A critic that fails is not worth failing the run over — treat a
        # broken critique as "ship it" and let the human gate catch problems.
        on_error="continue",
        description="Decide ship or revise.",
    )

    graph.add_node("record_critique", _record_critique, description="Count the loop.")
    graph.add_node("approve", _await_approval, kind="human", description="Owner gate.")
    graph.add_node("send", _send, kind="terminal", description="Deliver the reply.")

    graph.set_entry("qualify")
    graph.add_edge("qualify", "draft")
    graph.add_edge("draft", "critique")
    graph.add_edge("critique", "record_critique")
    graph.add_branch(
        "record_critique",
        {"draft": _needs_revision},
        default="approve",
    )
    graph.add_edge("approve", "send")
    graph.add_edge("send", END)

    return graph.validate()
