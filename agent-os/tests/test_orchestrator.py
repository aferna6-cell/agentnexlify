"""The seven §11 routing rules.

Six rules are exercised against the real 18-agent library; the ambiguity gap
(rule 2) is exercised against two deliberately-tied stub agents so the tie is
deterministic and not dependent on the production keyword vocabulary.
"""

from __future__ import annotations

import pytest

import agent_os.agents  # noqa: F401  (populates REGISTRY)
from agent_os.base import BaseAgent
from agent_os.context import SharedContext
from agent_os.errors import RegistryError
from agent_os.orchestrator import Orchestrator
from agent_os.registry import AgentRegistry
from agent_os.result import AgentResult, OwnerAsk
from agent_os.schema import (
    Bucket,
    Channel,
    Example,
    Priority,
    Status,
)
from agent_os.trace import ReasoningTrace

from agent_os.agents._helpers import build_spec


# --------------------------------------------------------------------------- #
# Rule 5 — specialty preference: amount + "quote" → quote_follow_up.           #
# --------------------------------------------------------------------------- #
def test_specialty_rule_quote_with_amount(orchestrator: Orchestrator):
    decision = orchestrator.route(
        OwnerAsk(text="Follow up with Mike on the $1,100 brake job quote I sent.")
    )
    assert decision.agent_id == "quote_follow_up"
    assert decision.used_specialty_rule is True
    assert decision.confidence >= 0.85


# --------------------------------------------------------------------------- #
# Rule 6 — complaint short-circuit.                                           #
# --------------------------------------------------------------------------- #
def test_complaint_short_circuits(orchestrator: Orchestrator):
    decision = orchestrator.route(
        OwnerAsk(text="A customer is furious our tech scratched their bumper.")
    )
    assert decision.agent_id == "complaint_handler"
    assert decision.short_circuited is True


def test_complaint_beats_other_keywords(orchestrator: Orchestrator):
    # Even with a "review" keyword present, complaint language wins.
    decision = orchestrator.route(
        OwnerAsk(text="This awful review came in and I'm furious about it.")
    )
    assert decision.agent_id == "complaint_handler"


# --------------------------------------------------------------------------- #
# Rule 4 — channel inference.                                                 #
# --------------------------------------------------------------------------- #
def test_channel_inference_text_to_sms(orchestrator: Orchestrator):
    decision = orchestrator.route(
        OwnerAsk(text="Text Carlos asking for a Google review after his oil change.")
    )
    assert decision.channel_override == Channel.sms
    assert decision.ask.requested_channel == Channel.sms


def test_channel_inference_email(orchestrator: Orchestrator):
    decision = orchestrator.route(OwnerAsk(text="Email Dana about her hybrid battery."))
    assert decision.channel_override == Channel.email


# --------------------------------------------------------------------------- #
# Rule 7 — bucket awareness.                                                  #
# --------------------------------------------------------------------------- #
def test_bucket_query_lists_marketing(orchestrator: Orchestrator):
    decision = orchestrator.route(OwnerAsk(text="What marketing agents do you have?"))
    assert decision.is_bucket_query is True
    assert decision.agent_id is None
    assert decision.bucket_listing is not None
    assert "marketing" in decision.bucket_listing.lower()


def test_bucket_query_all(orchestrator: Orchestrator):
    decision = orchestrator.route(OwnerAsk(text="What can you do?"))
    assert decision.is_bucket_query is True
    assert decision.bucket_listing


# --------------------------------------------------------------------------- #
# Rule 1 — confidence floor → generalist + wishlist capture.                  #
# --------------------------------------------------------------------------- #
def test_out_of_scope_routes_to_generalist_and_captures_wishlist(
    orchestrator: Orchestrator,
):
    before = len(orchestrator.wishlist)
    decision = orchestrator.route(
        OwnerAsk(text="Help me think through whether to hire a second technician.")
    )
    assert decision.is_generalist
    assert decision.confidence < Orchestrator.CONFIDENCE_FLOOR
    assert len(orchestrator.wishlist) == before + 1
    assert "technician" in orchestrator.wishlist.entries()[-1].ask_text.lower()


# --------------------------------------------------------------------------- #
# Rule 3 — owner override.                                                    #
# --------------------------------------------------------------------------- #
def test_owner_override_reroutes(orchestrator: Orchestrator):
    decision = orchestrator.route(OwnerAsk(text="What marketing agents do you have?"))
    overridden = orchestrator.override(decision, "lead_nurture")
    assert overridden.agent_id == "lead_nurture"
    assert overridden.owner_overrode is True


def test_owner_override_unknown_agent_rejected(orchestrator: Orchestrator):
    decision = orchestrator.route(OwnerAsk(text="What can you do?"))
    with pytest.raises(RegistryError):
        orchestrator.override(decision, "no_such_agent")


# --------------------------------------------------------------------------- #
# Rule 2 — ambiguity gap (two tied specialists → ask the owner).              #
# --------------------------------------------------------------------------- #
class _StubAgent(BaseAgent):
    def __init__(self, agent_id: str, keyword: str) -> None:
        super().__init__()
        self.spec = build_spec(
            agent_id=agent_id,
            display_name=agent_id.replace("_", " ").title(),
            bucket=Bucket.marketing,
            status=Status.new,
            build_priority=Priority.P4,
            purpose="A tied stub used to exercise the ambiguity gap.",
            routes_here_when=("never — test only",),
            channel=Channel.email,
            title_format="Stub — {x}",
            body_format="markdown",
            reasoning_trace_steps=("Business profile",),
            routing_keywords=(keyword,),
            example_interactions=(
                Example(owner_ask="x", expected_route=agent_id, expected_output_excerpt=""),
            ),
        )

    def build(self, ask: OwnerAsk, context: SharedContext, trace: ReasoningTrace):
        return AgentResult(
            agent_id=self.spec.agent_id,
            channel=Channel.email,
            title="Stub",
            body="A grounded stub body.",
            trace=trace,
        )


def test_ambiguity_gap_asks_owner_to_choose():
    reg = AgentRegistry()
    # Two specialists share the exact keyword → identical scores → gap 0 < 0.1.
    reg.register(_StubAgent("newsletter_one", "newsletter"))
    reg.register(_StubAgent("newsletter_two", "newsletter"))
    orch = Orchestrator(registry=reg)

    decision = orch.route(OwnerAsk(text="Send the newsletter."))
    assert decision.needs_owner_choice is True
    assert decision.agent_id is None
    assert set(decision.choice or ()) == {"newsletter_one", "newsletter_two"}
    assert decision.choice_prompt


# --------------------------------------------------------------------------- #
# handle() = route + dispatch in one call; logging accumulates.               #
# --------------------------------------------------------------------------- #
def test_handle_routes_and_dispatches(orchestrator: Orchestrator, context: SharedContext):
    decision, result = orchestrator.handle(
        OwnerAsk(
            text="Follow up with Mike on the $1,100 brake job quote I sent.",
            params={"customer_name": "Mike", "quote_amount": 1100},
        ),
        context,
    )
    assert decision.agent_id == "quote_follow_up"
    assert result is not None
    assert result.body.strip()


def test_bucket_query_dispatches_nothing(orchestrator: Orchestrator, context: SharedContext):
    decision, result = orchestrator.handle(
        OwnerAsk(text="What marketing agents do you have?"), context
    )
    assert result is None  # nothing to run for a listing


def test_every_decision_is_logged(orchestrator: Orchestrator):
    orchestrator.route(OwnerAsk(text="What can you do?"))
    orchestrator.route(OwnerAsk(text="Text Carlos for a review."))
    assert len(orchestrator.log) == 2
