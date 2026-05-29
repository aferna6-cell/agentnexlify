"""Smoke test: every one of the 18 agents runs through the registry on the
Bright Auto context and produces a rule-clean result.

Because :meth:`AgentRegistry.run` re-validates output against all three rules,
a passing run here is also proof the agent obeys the rules on real data. Agents
are run with a generous param bag so the grounded (non-stub) drafting path is
exercised; routing still isn't involved — we call each agent directly by id.
"""

from __future__ import annotations

import pytest

import agent_os.agents  # noqa: F401  (populates REGISTRY)
from agent_os.context import SharedContext
from agent_os.registry import REGISTRY
from agent_os.result import AgentResult, OwnerAsk
from agent_os.schema import CUSTOMER_FACING_CHANNELS, Channel

# Params any agent might reach for — supplied to every run so the grounded
# drafting path (not a routing stub) is what gets validated.
_PARAMS = {
    "customer_name": "Mike",
    "quote_amount": 1100,
    "quote_scope": "the brake job",
    "subject": "a tire rotation",
    "complaint_text": "Your tech showed up late and scratched my bumper.",
    "customer_question": "Do you service hybrid batteries on a Prius?",
}

_AGENT_IDS = sorted(spec.agent_id for spec in REGISTRY.specs())


def test_smoke_covers_all_18():
    assert len(_AGENT_IDS) == 18


@pytest.mark.parametrize("agent_id", _AGENT_IDS)
def test_agent_runs_clean(agent_id: str, context: SharedContext):
    ask = OwnerAsk(text=f"Run {agent_id} please.", params=dict(_PARAMS))
    result = REGISTRY.run(agent_id, ask, context)  # validates all 3 rules

    assert isinstance(result, AgentResult)
    assert result.agent_id == agent_id
    assert isinstance(result.channel, Channel)
    # A result either carries a real draft or honestly surfaces a reason.
    if result.has_draft:
        assert result.body.strip()
    else:
        assert result.orchestrator_messages
    # The substrate load is always the first recorded trace step.
    assert result.trace.steps
    assert result.trace.steps[0].name == "Business profile"


@pytest.mark.parametrize("agent_id", _AGENT_IDS)
def test_customer_facing_agents_emit_no_back_channel(
    agent_id: str, context: SharedContext
):
    """Gaps go to orchestrator_messages, never into a customer body."""

    spec = REGISTRY.get(agent_id).spec
    if spec.channel not in CUSTOMER_FACING_CHANNELS:
        pytest.skip("not a customer-facing channel")
    ask = OwnerAsk(text=f"Run {agent_id}.", params=dict(_PARAMS))
    result = REGISTRY.run(agent_id, ask, context)
    if result.has_draft:
        body = result.body.lower()
        assert "business profile" not in body
        assert "[" not in result.body  # no bracketed placeholders at all
