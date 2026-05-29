"""The registry is the rule gate. These tests prove a rule break fails CI.

Two halves:

* **Static** — :func:`validate_spec` rejects malformed specs at registration.
* **Runtime** — :func:`validate_output` rejects any draft that violates one of
  the three rules, with the stable machine code CI reports on.

The negative tests are the point of the whole project: a rule-violating agent
must not be able to ship.
"""

from __future__ import annotations

import dataclasses

import pytest

import agent_os.agents  # noqa: F401  (populates REGISTRY)
import agent_os.rules as rules
from agent_os.base import BaseAgent
from agent_os.context import SharedContext
from agent_os.errors import (
    OutputRuleViolation,
    RegistryError,
    SchemaViolation,
)
from agent_os.profile import BusinessProfile
from agent_os.registry import REGISTRY, AgentRegistry
from agent_os.result import AgentResult, OwnerAsk
from agent_os.schema import Channel, TriggerType
from agent_os.trace import ReasoningTrace, TraceStep

from conftest import make_spec


# --------------------------------------------------------------------------- #
# Library is healthy: 18 agents, 8 buckets, every spec valid.                 #
# --------------------------------------------------------------------------- #
def test_registry_has_18_agents_across_8_buckets():
    assert len(REGISTRY) == 18
    assert len(REGISTRY.buckets()) == 8


def test_every_registered_spec_passes_static_validation():
    for spec in REGISTRY.specs():
        rules.validate_spec(spec)  # must not raise


# --------------------------------------------------------------------------- #
# Static schema validation — negatives.                                       #
# --------------------------------------------------------------------------- #
def test_bad_agent_id_rejected():
    spec = make_spec(Channel.report)
    bad = dataclasses.replace(spec, agent_id="Not Snake Case!")
    with pytest.raises(SchemaViolation):
        rules.validate_spec(bad)


def test_missing_display_name_rejected():
    bad = dataclasses.replace(make_spec(Channel.report), display_name="")
    with pytest.raises(SchemaViolation):
        rules.validate_spec(bad)


def test_empty_routes_here_when_rejected():
    bad = dataclasses.replace(make_spec(Channel.report), routes_here_when=())
    with pytest.raises(SchemaViolation):
        rules.validate_spec(bad)


def test_missing_manual_trigger_rejected():
    bad = dataclasses.replace(
        make_spec(Channel.report), triggers_supported=(TriggerType.scheduled,)
    )
    with pytest.raises(SchemaViolation):
        rules.validate_spec(bad)


def test_empty_reasoning_trace_steps_rejected():
    bad = dataclasses.replace(make_spec(Channel.report), reasoning_trace_steps=())
    with pytest.raises(SchemaViolation):
        rules.validate_spec(bad)


def test_example_routing_to_other_agent_rejected():
    spec = make_spec(Channel.report, agent_id="agent_a")
    bad_example = dataclasses.replace(
        spec.example_interactions[0], expected_route="someone_else"
    )
    bad = dataclasses.replace(spec, example_interactions=(bad_example,))
    with pytest.raises(SchemaViolation):
        rules.validate_spec(bad)


def test_no_example_interactions_rejected():
    bad = dataclasses.replace(make_spec(Channel.report), example_interactions=())
    with pytest.raises(SchemaViolation):
        rules.validate_spec(bad)


# --------------------------------------------------------------------------- #
# Runtime output validation — one negative per stable rule code.              #
# --------------------------------------------------------------------------- #
def _trace_with_load() -> ReasoningTrace:
    t = ReasoningTrace()
    t.record_load("Business profile", "loaded fields", describe=lambda s: s)
    return t


def test_rule_honest_trace_violation():
    """A load-style step marked loaded with no summary is rejected."""

    spec = make_spec(Channel.report)
    trace = ReasoningTrace()
    # Hand-built dishonest step (record_load() would never produce this).
    trace.steps.append(
        TraceStep(name="Knowledge base", loaded=True, detail="loaded", summary=None)
    )
    result = AgentResult(
        agent_id=spec.agent_id,
        channel=Channel.report,
        title="Report",
        body="Some grounded owner report.",
        trace=trace,
    )
    with pytest.raises(OutputRuleViolation) as exc:
        rules.validate_output(spec, result, BusinessProfile())
    assert exc.value.rule == "honest_trace"


def test_rule_placeholder_violation_customer_facing():
    spec = make_spec(Channel.sms)
    result = AgentResult(
        agent_id=spec.agent_id,
        channel=Channel.sms,
        title="Reminder",
        body="Hi, please call us at [Phone] to confirm.",
        trace=_trace_with_load(),
    )
    with pytest.raises(OutputRuleViolation) as exc:
        rules.validate_output(spec, result, BusinessProfile(phone="512-555-0100"))
    assert exc.value.rule == "placeholder"


def test_rule_placeholder_violation_sequence_channel():
    """Sequence is treated as customer-facing for placeholder strictness."""

    spec = make_spec(Channel.sequence)
    result = AgentResult(
        agent_id=spec.agent_id,
        channel=Channel.sequence,
        title="Nurture",
        body="Touch 1 — Today: Hi from [Shop Name].",
        trace=_trace_with_load(),
    )
    with pytest.raises(OutputRuleViolation) as exc:
        rules.validate_output(spec, result, BusinessProfile())
    assert exc.value.rule == "placeholder"


def test_rule_placeholder_report_only_for_present_fields():
    """Report channel rejects a placeholder only for a field the profile has."""

    spec = make_spec(Channel.report)
    body = "Owner brief: business is [Business Name]."
    result = AgentResult(
        agent_id=spec.agent_id,
        channel=Channel.report,
        title="Brief",
        body=body,
        trace=_trace_with_load(),
    )
    # Field present → violation.
    with pytest.raises(OutputRuleViolation) as exc:
        rules.validate_output(spec, result, BusinessProfile(business_name="Bright Auto"))
    assert exc.value.rule == "placeholder"
    # Field absent → the report placeholder is tolerated (precise §2 wording).
    rules.validate_output(spec, result, BusinessProfile())


def test_rule_channel_format_violation():
    """A plain-text channel (post) carrying markdown is rejected."""

    spec = make_spec(Channel.post)
    result = AgentResult(
        agent_id=spec.agent_id,
        channel=Channel.post,
        title="Post",
        body="Spring sale! **50% off** all oil changes.",
        trace=_trace_with_load(),
    )
    with pytest.raises(OutputRuleViolation) as exc:
        rules.validate_output(spec, result, BusinessProfile())
    assert exc.value.rule == "channel_format"


def test_rule_empty_draft_has_draft_false_with_body():
    spec = make_spec(Channel.report)
    result = AgentResult(
        agent_id=spec.agent_id,
        channel=Channel.report,
        title="x",
        body="stray body that should not be here",
        trace=_trace_with_load(),
        has_draft=False,
    )
    with pytest.raises(OutputRuleViolation) as exc:
        rules.validate_output(spec, result, BusinessProfile())
    assert exc.value.rule == "empty_draft"


def test_rule_empty_draft_no_reason_surfaced():
    spec = make_spec(Channel.report)
    result = AgentResult(
        agent_id=spec.agent_id,
        channel=Channel.report,
        title="",
        body="",
        trace=_trace_with_load(),
        has_draft=False,
        orchestrator_messages=[],
    )
    with pytest.raises(OutputRuleViolation) as exc:
        rules.validate_output(spec, result, BusinessProfile())
    assert exc.value.rule == "empty_draft"


def test_rule_empty_body_with_has_draft_true():
    spec = make_spec(Channel.report)
    result = AgentResult(
        agent_id=spec.agent_id,
        channel=Channel.report,
        title="Report",
        body="   ",
        trace=_trace_with_load(),
    )
    with pytest.raises(OutputRuleViolation) as exc:
        rules.validate_output(spec, result, BusinessProfile())
    assert exc.value.rule == "empty_draft"


def test_rule_back_channel_leak_into_customer_draft():
    spec = make_spec(Channel.email)
    result = AgentResult(
        agent_id=spec.agent_id,
        channel=Channel.email,
        title="Reply",
        body="Thanks for reaching out. I need your business profile to draft this.",
        trace=_trace_with_load(),
    )
    with pytest.raises(OutputRuleViolation) as exc:
        rules.validate_output(spec, result, BusinessProfile())
    assert exc.value.rule == "placeholder"


def test_clean_customer_draft_passes():
    spec = make_spec(Channel.sms)
    result = AgentResult(
        agent_id=spec.agent_id,
        channel=Channel.sms,
        title="Reminder",
        body="Hi Mike, this is Bright Auto. Call 512-555-0100 to book. Reply STOP to opt out.",
        trace=_trace_with_load(),
    )
    rules.validate_output(spec, result, BusinessProfile())  # must not raise


# --------------------------------------------------------------------------- #
# Architectural gate: a rule-violating AGENT cannot ship through the registry. #
# --------------------------------------------------------------------------- #
class _RoguePlaceholderAgent(BaseAgent):
    spec = make_spec(Channel.sms, "rogue_placeholder")

    def build(self, ask, context, trace):
        return AgentResult(
            agent_id=self.spec.agent_id,
            channel=Channel.sms,
            title="Reminder",
            body="Call us at [Phone] today!",  # rule 2 violation
            trace=trace,
        )


class _RogueMarkdownAgent(BaseAgent):
    spec = make_spec(Channel.post, "rogue_markdown")

    def build(self, ask, context, trace):
        return AgentResult(
            agent_id=self.spec.agent_id,
            channel=Channel.post,
            title="Post",
            body="Check out our **huge** sale.",  # rule 3 violation
            trace=trace,
        )


def test_rogue_placeholder_agent_blocked_by_registry(context: SharedContext):
    reg = AgentRegistry()
    reg.register(_RoguePlaceholderAgent())
    with pytest.raises(OutputRuleViolation) as exc:
        reg.run("rogue_placeholder", OwnerAsk(text="remind Mike"), context)
    assert exc.value.rule == "placeholder"


def test_rogue_markdown_agent_blocked_by_registry(context: SharedContext):
    reg = AgentRegistry()
    reg.register(_RogueMarkdownAgent())
    with pytest.raises(OutputRuleViolation) as exc:
        reg.run("rogue_markdown", OwnerAsk(text="post the sale"), context)
    assert exc.value.rule == "channel_format"


# --------------------------------------------------------------------------- #
# Registry mechanics.                                                          #
# --------------------------------------------------------------------------- #
def test_duplicate_registration_rejected(empty_registry: AgentRegistry):
    empty_registry.register(_RoguePlaceholderAgent())
    with pytest.raises(RegistryError):
        empty_registry.register(_RoguePlaceholderAgent())


def test_unknown_agent_lookup_rejected(empty_registry: AgentRegistry):
    with pytest.raises(RegistryError):
        empty_registry.get("does_not_exist")


def test_register_malformed_spec_rejected(empty_registry: AgentRegistry):
    class _BadSpecAgent(BaseAgent):
        spec = dataclasses.replace(make_spec(Channel.report), display_name="")

        def build(self, ask, context, trace):  # pragma: no cover
            raise NotImplementedError

    with pytest.raises(SchemaViolation):
        empty_registry.register(_BadSpecAgent())
